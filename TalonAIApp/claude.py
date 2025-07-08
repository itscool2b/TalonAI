from anthropic import AsyncAnthropic
from typing import Optional
import os

# Claude Sonnet 3.5 - stable model
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"

async def call_claude(
    prompt: str,
    model: str = CLAUDE_MODEL,
    system: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> str:
    """
    Reusable async Claude caller using Sonnet 3.5.

    Args:
        prompt (str): The user prompt to send.
        model (str): Claude model ID (default: Sonnet 3.5).
        system (Optional[str]): Optional system instruction.
        temperature (float): Sampling randomness (default deterministic).
        max_tokens (int): Max output tokens from Claude (default 4096).

    Returns:
        str: Claude's plain text response.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY environment variable not set!")
        raise ValueError("ANTHROPIC_API_KEY environment variable is required")
    
    print(f"🤖 Claude API call - Model: {model}, Temperature: {temperature}")
    
    client = AsyncAnthropic(api_key=api_key)
    messages = [{"role": "user", "content": prompt}]
    if system:
        messages.insert(0, {"role": "system", "content": system})

    try:
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages
        )
        
        result = response.content[0].text.strip()
        print(f"✅ Claude response received ({len(result)} chars)")
        return result
        
    except Exception as e:
        print(f"❌ Claude API error: {e}")
        raise
