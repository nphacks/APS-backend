import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def get_openrouter_client() -> OpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)


def llm_structured(prompt: str, response_format: dict, model: str = "google/gemini-3-flash-preview") -> dict:
    """
    Call LLM via OpenRouter and get structured JSON output.

    Args:
        prompt: The user prompt
        response_format: JSON schema dict describing expected output
        model: Model identifier on OpenRouter

    Returns:
        Parsed dict from LLM response
    """
    client = get_openrouter_client()

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant. Always respond with valid JSON matching the requested schema. No markdown, no extra text.",
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    raw = completion.choices[0].message.content
    return json.loads(raw)


def llm_text(prompt: str, model: str = "google/gemini-3-flash-preview") -> str:
    """Simple text response from LLM via OpenRouter."""
    client = get_openrouter_client()

    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )

    return completion.choices[0].message.content
