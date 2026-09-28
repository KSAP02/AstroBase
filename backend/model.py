"""The only place an LLM client is constructed.

Everything else calls get_chat_model(). Changing model or provider is an .env edit, not a code change.
"""

from backend.config import get_settings


class LLMConfigError(RuntimeError):
    """The LLM isn't configured; the message says exactly what to fix."""


def get_chat_model():
    s = get_settings()
    if s.llm_provider != "openai":
        raise LLMConfigError(f"LLM_PROVIDER={s.llm_provider!r} is not supported; set LLM_PROVIDER=openai in .env")
    if not s.llm_api_key:
        raise LLMConfigError("LLM_API_KEY is empty; set it in .env")
    if not s.llm_model:
        raise LLMConfigError("LLM_MODEL is empty; set it in .env (e.g. gpt-6-luna)")

    try:
        from langchain_openai import ChatOpenAI
    except ImportError as e:
        raise LLMConfigError("langchain-openai is not installed; run pip install -r requirements.txt") from e

    return ChatOpenAI(
        model=s.llm_model,
        api_key=s.llm_api_key,
        base_url=s.llm_base_url or None,                    # blank -> official OpenAI endpoint
        reasoning_effort=s.llm_reasoning_effort or None,    # reasoning models: none/low/medium/high/xhigh
        max_retries=0,   # the SDK would otherwise retry twice: keep it to ONE call per evaluation
        timeout=120,     # seconds; a stuck request can't hang the API forever
        # No temperature: GPT-6 reasoning models only accept the default and reject 0.
    )
