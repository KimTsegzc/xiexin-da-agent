__all__ = ["LLMProvider"]


def __getattr__(name: str):
	if name == "LLMProvider":
		from .llm_provider import LLMProvider

		return LLMProvider
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
