"""System prompt templates for MemoryChat-Agent.

All prompts are centralized here so they can be tuned independently of the
LLM client logic. The :func:`build_system_prompt` helper composes the final
system message by injecting retrieved memories into a base template.

Templates:
    SYSTEM_PROMPT_BASE: The base persona / behavior instructions.
    MEMORY_CONTEXT_TEMPLATE: A template that wraps retrieved memories.

Example:
    >>> from llm.prompts import build_system_prompt
    >>> prompt = build_system_prompt(memories=["Prefers dark mode", "Likes Python"])
    >>> "Prefers dark mode" in prompt
    True
"""

from __future__ import annotations

from collections.abc import Iterable

# ---------------------------------------------------------------------------
# Base system prompt — defines the assistant's persona and behavior.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_BASE: str = """\
You are MemoryChat-Agent, a helpful AI assistant with long-term memory.

Your role:
- Answer the user's questions clearly and concisely.
- Use the provided long-term memories to personalize your responses.
- When relevant memories exist, naturally incorporate them without explicitly
  saying "according to your memory" unless the user asks about past context.
- If no memories are provided or they are irrelevant, answer normally.

Guidelines:
- Be friendly, professional, and direct.
- Ask clarifying questions when the user's intent is ambiguous.
- Never fabricate facts about the user that are not in the provided memories.
"""

# ---------------------------------------------------------------------------
# Memory context template — injected when retrieved memories are available.
# ---------------------------------------------------------------------------
MEMORY_CONTEXT_TEMPLATE: str = """\
## Long-Term Memories
The following memories were retrieved from past conversations with this user. \
Use them to personalize your response when relevant:

{memories_block}
## End of Memories
"""

# Separator used to format each memory entry in the memories block.
_MEMORY_BULLET: str = "- {memory}"


def _format_memories_block(memories: Iterable[str]) -> str:
    """Format an iterable of memory strings into a bulleted block.

    Args:
        memories: An iterable of memory text strings.

    Returns:
        A newline-separated bulleted string, or a placeholder message when
        the iterable is empty.
    """
    items = [m.strip() for m in memories if m and m.strip()]
    if not items:
        return "(No relevant memories available.)"
    return "\n".join(_MEMORY_BULLET.format(memory=m) for m in items)


def build_system_prompt(memories: Iterable[str] | None = None) -> str:
    """Build the full system prompt, optionally injecting memories.

    Args:
        memories: An iterable of retrieved memory strings to inject into the
            prompt. If ``None`` or empty, only the base prompt is returned.

    Returns:
        The composed system prompt string.
    """
    if not memories:
        return SYSTEM_PROMPT_BASE

    memories_list = list(memories)
    if not memories_list:
        return SYSTEM_PROMPT_BASE

    memories_block = _format_memories_block(memories_list)
    memory_section = MEMORY_CONTEXT_TEMPLATE.format(memories_block=memories_block)
    return f"{SYSTEM_PROMPT_BASE}\n{memory_section}"
