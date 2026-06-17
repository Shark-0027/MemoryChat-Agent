"""ChatAgent — the memory-augmented conversational agent.

This module implements :class:`ChatAgent`, the orchestrator that ties
together the LLM and memory subsystems into a single conversational turn.
All business logic lives here — **never in the Streamlit UI layer**.

Workflow per user message::

    User input
        │
        ▼
    1. Retrieve relevant memories  (MemoryManager.search_memory)
        │
        ▼
    2. Build the system prompt     (llm.prompts.build_system_prompt)
        │
        ▼
    3. Call the LLM                (LLMClient.chat / stream_chat)
        │
        ▼
    4. Extract long-term memories  (MemoryManager.add_memory)
        │
        ▼
    5. Persist memories            (handled inside add_memory)
        │
        ▼
    6. Return the assistant reply

The agent is UI-independent: it accepts a plain user message and returns a
plain reply string (or yields chunks for streaming). The Streamlit layer is
a thin adapter that calls :meth:`ChatAgent.chat` /
:meth:`ChatAgent.stream_chat`.

Example:
    >>> from app.agent import ChatAgent
    >>> agent = ChatAgent()
    >>> reply = agent.chat("Hi, I prefer dark mode.")
    >>> print(reply)
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

from app.exceptions import AgentConfigError, AgentRuntimeError
from config import settings
from llm.client import LLMClient, Message
from llm.prompts import build_system_prompt
from memory.manager import MemoryManager
from utils.logger import get_logger

logger: logging.Logger = get_logger(__name__)


class ChatAgent:
    """Memory-augmented conversational agent.

    The agent orchestrates the LLM and memory subsystems. It is the single
    entry point for conversational turns — UI layers must call
    :meth:`chat` or :meth:`stream_chat` rather than touching the LLM or
    memory clients directly.

    The agent holds no per-user mutable conversation state; callers are
    responsible for maintaining message history (e.g. in Streamlit session
    state) and passing it to :meth:`chat`. This keeps the agent stateless
    and reusable across users.

    Attributes:
        _llm: The :class:`LLMClient` used for chat completions.
        _memory: The :class:`MemoryManager` used for memory CRUD/search.
        _user_id: The user id scoping all memory operations.
    """

    def __init__(
        self,
        llm: LLMClient | None = None,
        memory: MemoryManager | None = None,
        user_id: str | None = None,
    ) -> None:
        """Initialize the agent with optional dependency injection.

        Args:
            llm: An :class:`LLMClient` instance. If ``None``, a new one is
                created lazily on first use.
            memory: A :class:`MemoryManager` instance. If ``None``, a new
                one is created lazily on first use.
            user_id: The user id scoping memory operations. If ``None``,
                falls back to :attr:`config.settings.mem0_default_user_id`.

        Raises:
            AgentConfigError: If neither an API key nor pre-built clients
                are available when first used.
        """
        self._llm: LLMClient | None = llm
        self._memory: MemoryManager | None = memory
        self._user_id: str = user_id or settings.mem0_default_user_id

    # ------------------------------------------------------------------ #
    # Properties — lazy initialization
    # ------------------------------------------------------------------ #
    @property
    def llm(self) -> LLMClient:
        """Return the LLM client, creating it on first access.

        Returns:
            The :class:`LLMClient` instance.
        """
        if self._llm is None:
            logger.info("Creating LLMClient for ChatAgent")
            self._llm = LLMClient()
        return self._llm

    @property
    def memory(self) -> MemoryManager:
        """Return the memory manager, creating it on first access.

        Returns:
            The :class:`MemoryManager` instance.
        """
        if self._memory is None:
            logger.info("Creating MemoryManager for ChatAgent (user=%s)", self._user_id)
            self._memory = MemoryManager(user_id=self._user_id)
        return self._memory

    @property
    def user_id(self) -> str:
        """Return the user id scoping this agent's memory operations.

        Returns:
            The user id string.
        """
        return self._user_id

    # ------------------------------------------------------------------ #
    # Public API — conversational turns
    # ------------------------------------------------------------------ #
    def chat(
        self,
        user_message: str,
        history: list[Message] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """Process a single conversational turn and return the reply.

        Executes the full 6-step workflow:

        1. Retrieve relevant memories for ``user_message``.
        2. Build the system prompt with injected memories.
        3. Call the LLM with the composed messages.
        4. Extract long-term memories from the exchange.
        5. Persist the extracted memories (inside ``add_memory``).
        6. Return the assistant reply.

        Args:
            user_message: The latest user input text.
            history: Prior conversation messages (role/content dicts) to
                include as context. If ``None``, only the current message
                is sent.
            temperature: Sampling temperature for the LLM.
            max_tokens: Maximum tokens to generate. If ``None``, the API
                default is used.

        Returns:
            The assistant's reply text.

        Raises:
            AgentRuntimeError: If any step of the workflow fails.
        """
        logger.info("Chat turn start (user=%s, message=%d chars)", self._user_id, len(user_message))

        # Step 1 — retrieve relevant memories.
        memory_texts = self._retrieve_memories(user_message)

        # Step 2 — build the system prompt.
        system_prompt = build_system_prompt(memories=memory_texts)

        # Step 3 — compose messages and call the LLM.
        messages = self._compose_messages(system_prompt, history, user_message)
        reply = self._call_llm(messages, temperature=temperature, max_tokens=max_tokens)

        # Steps 4 & 5 — extract and persist long-term memories.
        self._extract_and_persist_memories(user_message, reply)

        logger.info("Chat turn complete (reply=%d chars)", len(reply))
        return reply

    def stream_chat(
        self,
        user_message: str,
        history: list[Message] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        """Process a conversational turn with streaming output.

        Same workflow as :meth:`chat`, but the LLM reply is streamed chunk
        by chunk. Memory extraction happens **after** the stream completes,
        so the caller must consume the entire iterator for memories to be
        persisted.

        Args:
            user_message: The latest user input text.
            history: Prior conversation messages (role/content dicts).
            temperature: Sampling temperature for the LLM.
            max_tokens: Maximum tokens to generate. If ``None``, the API
                default is used.

        Yields:
            Successive text chunks from the assistant's reply.

        Raises:
            AgentRuntimeError: If any step of the workflow fails.
        """
        logger.info(
            "Stream chat turn start (user=%s, message=%d chars)",
            self._user_id,
            len(user_message),
        )

        # Step 1 — retrieve relevant memories.
        memory_texts = self._retrieve_memories(user_message)

        # Step 2 — build the system prompt.
        system_prompt = build_system_prompt(memories=memory_texts)

        # Step 3 — compose messages and stream the LLM reply.
        messages = self._compose_messages(system_prompt, history, user_message)

        # Collect the full reply while streaming so we can extract memories.
        collected: list[str] = []
        for chunk in self._stream_llm(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            collected.append(chunk)
            yield chunk

        # Steps 4 & 5 — extract and persist long-term memories.
        full_reply = "".join(collected)
        self._extract_and_persist_memories(user_message, full_reply)

        logger.info("Stream chat turn complete (reply=%d chars)", len(full_reply))

    # ------------------------------------------------------------------ #
    # Workflow steps — private methods (low coupling)
    # ------------------------------------------------------------------ #
    def _retrieve_memories(self, user_message: str) -> list[str]:
        """Step 1 — retrieve relevant memories for the user message.

        Args:
            user_message: The user's input text to search memories with.

        Returns:
            A list of memory text strings relevant to the query. Returns an
            empty list if retrieval fails (non-fatal — the agent continues
            without memory context).
        """
        try:
            response = self.memory.search_memory(
                query=user_message,
                user_id=self._user_id,
                limit=5,
            )
            texts = [item.get("memory", "") for item in response.get("results", [])]
            logger.info("Retrieved %d memory item(s)", len(texts))
            return texts
        except Exception as exc:
            # Memory retrieval is best-effort; don't fail the whole turn.
            logger.warning("Memory retrieval failed (continuing without memories): %s", exc)
            return []

    def _compose_messages(
        self,
        system_prompt: str,
        history: list[Message] | None,
        user_message: str,
    ) -> list[Message]:
        """Step 2 (post-retrieval) — compose the full message list for the LLM.

        Args:
            system_prompt: The system prompt (with memories injected).
            history: Prior conversation messages, or ``None``.
            user_message: The latest user input.

        Returns:
            A list of message dicts ready for the LLM ``chat`` call.
        """
        messages: list[Message] = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        logger.debug("Composed %d message(s) for LLM", len(messages))
        return messages

    def _call_llm(
        self,
        messages: list[Message],
        temperature: float,
        max_tokens: int | None,
    ) -> str:
        """Step 3 — call the LLM (blocking) and return the reply.

        Args:
            messages: The composed message list.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            The assistant's reply text.

        Raises:
            AgentRuntimeError: If the LLM call fails.
        """
        try:
            reply = self.llm.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            logger.info("LLM reply received (%d chars)", len(reply))
            return reply
        except Exception as exc:
            raise AgentRuntimeError(f"LLM call failed: {exc}") from exc

    def _stream_llm(
        self,
        messages: list[Message],
        temperature: float,
        max_tokens: int | None,
    ) -> Iterator[str]:
        """Step 3 (streaming) — call the LLM and yield reply chunks.

        Args:
            messages: The composed message list.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Yields:
            Successive text chunks from the assistant's reply.

        Raises:
            AgentRuntimeError: If the LLM call fails.
        """
        try:
            yield from self.llm.stream_chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            raise AgentRuntimeError(f"LLM stream call failed: {exc}") from exc

    def _extract_and_persist_memories(self, user_message: str, assistant_reply: str) -> None:
        """Steps 4 & 5 — extract long-term memories and persist them.

        The user message and assistant reply are passed to mem0, which uses
        the LLM to extract salient facts and stores them in the vector DB.

        Args:
            user_message: The user's input text for this turn.
            assistant_reply: The assistant's reply text for this turn.

        Note:
            Memory extraction is best-effort. If it fails, the reply is
            still returned to the user; only a warning is logged.
        """
        messages_to_memorize: list[Message] = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_reply},
        ]
        try:
            self.memory.add_memory(
                messages=messages_to_memorize,
                user_id=self._user_id,
            )
            logger.info("Memories extracted and persisted for user=%s", self._user_id)
        except Exception as exc:
            # Memory persistence is best-effort; don't fail the whole turn.
            logger.warning("Memory extraction/persistence failed: %s", exc)

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def close(self) -> None:
        """Release resources held by the LLM and memory clients.

        Safe to call multiple times. After closing, the next chat operation
        will re-initialize the clients.
        """
        for name, resource in (("LLM", self._llm), ("memory", self._memory)):
            if resource is not None:
                try:
                    resource.close()
                    logger.info("%s client closed by ChatAgent", name)
                except Exception as exc:  # pragma: no cover - best-effort
                    logger.warning("Error closing %s client: %s", name, exc)
        self._llm = None
        self._memory = None


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------
def create_agent(user_id: str | None = None) -> ChatAgent:
    """Create a :class:`ChatAgent` wired with default clients.

    Args:
        user_id: Optional user id. If ``None``, uses the configured default.

    Returns:
        A new :class:`ChatAgent` instance.

    Raises:
        AgentConfigError: If the application is not configured (e.g. missing
            API key) and clients cannot be built.
    """
    if not settings.is_configured:
        raise AgentConfigError(
            "OPENAI_API_KEY is not configured. Set it in .env before creating an agent."
        )
    return ChatAgent(user_id=user_id)
