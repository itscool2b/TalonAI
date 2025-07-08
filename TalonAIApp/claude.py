from anthropic import AsyncAnthropic
from typing import Optional
import os

# Claude Sonnet 3.7 (Feb 2025) – latest Sonnet tier
CLAUDE_MODEL = "claude-3-7-sonnet-20250219"

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

async def call_claude(
    prompt: str,
    model: str = CLAUDE_MODEL,
    system: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> str:
    """
    Reusable async Claude caller using Sonnet 3.7.

    Args:
        prompt (str): The user prompt to send.
        model (str): Claude model ID (default: Sonnet 3.7).
        system (Optional[str]): Optional system instruction.
        temperature (float): Sampling randomness (default deterministic).
        max_tokens (int): Max output tokens from Claude (default 4096).

    Returns:
        str: Claude's plain text response.
    """
    messages = [{"role": "user", "content": prompt}]
    if system:
        messages.insert(0, {"role": "system", "content": system})

    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=messages
    )

    return response.content[0].text.strip()
