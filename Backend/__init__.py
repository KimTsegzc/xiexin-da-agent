__all__ = ["LLMProvider", "SearchProvider"]


def __getattr__(name: str):
	if name == "LLMProvider":
		from .llm_provider import LLMProvider

		return LLMProvider
	if name == "SearchProvider":
		from .search_provider import SearchProvider

		return SearchProvider
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
