from __future__ import annotations
import argparse
import json
import os
import random
import re
import threading
import time
import uuid
from pathlib import Path
from typing import TypedDict
from openai import OpenAI


REPO_ROOT = Path(__file__).resolve().parents[1]
_ENV_FILE = REPO_ROOT / ".env"

_DEFAULT_WELCOME = "你好，我是鑫哥~"

_WLCM_PROMPT_A = """
你是首页欢迎语生成器。输出一句欢迎语，18个字以内。
风格A：引用屈原、尼采、康德等人的名言、富有哲理。
禁止输出编号、引号、换行和解释。
禁止输出屈原、尼采、康德等人的名字，禁止输出“名言”、“名句”等提示语。
注意：你不能捏造名人名言，要是他们说过的内容才可以引用。
"""

_WLCM_PROMPT_B = """
你是首页欢迎语生成器。输出一句欢迎语，16个字以内。
风格B：口语化、亲切有趣、像朋友打招呼。
禁止输出编号、引号、换行和解释。
"""

_WLCM_PROMPT_C = """
你是首页欢迎语生成器。输出一句欢迎语，16个字以内。
风格C：网络热梗。
禁止输出编号、引号、换行和解释。
"""

_WLCM_USER_PROMPT = "请仅输出一句新的首页欢迎语。不要解释，不要复述提示词。"

_WLCM_DEDUPE_SUFFIX_TEMPLATE = """
需要做去重的记忆：
{memory_block}
避免使用这些常见开头（防止句式重复）：
{forbidden_prefixes}
**注意：避免重复、语义相近的表达！**
**注意：句型句式也要多样化，不能老是同一种套路！**
**注意：他们并不一定就是好的。保持欢迎语的新鲜感和多样性！**
""".strip()

_WLCM_RATIO_A = 0.4
_WLCM_RATIO_B = 0.1
_WLCM_RATIO_C = 1 - _WLCM_RATIO_A - _WLCM_RATIO_B

_MEMORY_ROOT = REPO_ROOT / "Memory"
_SHORT_TERM_DIR = _MEMORY_ROOT / "short_term"
_LONG_TERM_DIR = _MEMORY_ROOT / "long_term"
_SHORT_TERM_WELCOME_CACHE_DIR = _SHORT_TERM_DIR / "welcome_cache"
_LONG_TERM_WELCOME_FILE = _LONG_TERM_DIR / "welcome_words.jsonl"
_SHORT_TERM_MAX_ITEMS = 10
_MEMORY_LOCK = threading.Lock()
_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

_WLCM_MODEL = "qwen-turbo"
_WLCM_TEMPERATURE = 0.9
_WLCM_MAX_TOKENS = 64
_FIRST_TOKEN_TIMEOUT_SECONDS = 1.5

_API_KEY_ENV_CANDIDATES = (
    "DASHSCOPE_API_KEY",
    "ALIYUN_BAILIAN_API_KEY",
    "OPENAI_API_KEY",
    "API_KEY",
)
_BASE_URL_ENV_CANDIDATES = (
    "DASHSCOPE_BASE_URL",
    "ALIYUN_BAILIAN_BASE_URL",
    "OPENAI_BASE_URL",
    "BASE_URL",
)
_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class _DebugSettings(TypedDict):
    api_key: str | None
    base_url: str


class _ABRouting(TypedDict):
    bucket: float
    variant: str
    ratioA: float
    ratioB: float
    ratioC: float
    mode: str


def _ensure_memory_layout() -> None:
    _SHORT_TERM_DIR.mkdir(parents=True, exist_ok=True)
    _SHORT_TERM_WELCOME_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _LONG_TERM_DIR.mkdir(parents=True, exist_ok=True)
    _LONG_TERM_WELCOME_FILE.touch(exist_ok=True)


def normalize_session_id(session_id: str | None) -> str | None:
    candidate = (session_id or "").strip()
    if not candidate:
        return None
    if not _SESSION_ID_PATTERN.fullmatch(candidate):
        return None
    return candidate


def create_welcome_session_id() -> str:
    return uuid.uuid4().hex


def _session_welcome_file(session_id: str) -> Path:
    return _SHORT_TERM_WELCOME_CACHE_DIR / f"{session_id}.jsonl"


def _read_dotenv_value(name: str) -> str | None:
    if not _ENV_FILE.exists():
        return None
    try:
        for raw_line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() != name:
                continue
            return value.strip().strip('"').strip("'")
    except OSError:
        return None
    return None


def _resolve_env_value(names: tuple[str, ...], default: str | None = None) -> str | None:
    for name in names:
        env_value = os.getenv(name)
        if env_value:
            return env_value
    for name in names:
        dotenv_value = _read_dotenv_value(name)
        if dotenv_value:
            return dotenv_value
    return default


def _get_debug_settings() -> _DebugSettings:
    return {
        "api_key": _resolve_env_value(_API_KEY_ENV_CANDIDATES),
        "base_url": _resolve_env_value(_BASE_URL_ENV_CANDIDATES, _DEFAULT_BASE_URL) or _DEFAULT_BASE_URL,
    }


def _normalize_welcome_text(text: str) -> str:
    cleaned = " ".join((text or "").strip().split())
    if not cleaned:
        return _DEFAULT_WELCOME
    # Keep hero text concise for the landing page.
    return cleaned[:42]


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    deduped: list[str] = []
    for item in items:
        normalized = _normalize_welcome_text(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _read_short_term_welcome_memory(
    session_id: str,
    limit: int = _SHORT_TERM_MAX_ITEMS,
) -> list[str]:
    _ensure_memory_layout()
    target_file = _session_welcome_file(session_id)
    target_file.touch(exist_ok=True)
    items: list[str] = []
    try:
        for raw_line in target_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
                text = str(parsed.get("text", "")).strip()
            except Exception:
                text = line
            if text:
                items.append(text)
    except OSError:
        return []
    deduped = _dedupe_keep_order(items)
    return deduped[-max(1, int(limit)) :]


def get_short_term_welcome_memory(
    session_id: str,
    limit: int = _SHORT_TERM_MAX_ITEMS,
) -> list[str]:
    return _read_short_term_welcome_memory(session_id=session_id, limit=limit)


def record_welcome_word(session_id: str, text: str) -> list[str]:
    normalized = _normalize_welcome_text(text)
    if not normalized:
        return _read_short_term_welcome_memory(session_id=session_id, limit=_SHORT_TERM_MAX_ITEMS)

    with _MEMORY_LOCK:
        items = _read_short_term_welcome_memory(session_id=session_id, limit=_SHORT_TERM_MAX_ITEMS)
        items = [item for item in items if item != normalized]
        items.append(normalized)
        items = items[-_SHORT_TERM_MAX_ITEMS:]

        _ensure_memory_layout()
        target_file = _session_welcome_file(session_id)
        payload_lines = [
            json.dumps({"text": item, "ts": int(time.time())}, ensure_ascii=False)
            for item in items
        ]
        target_file.write_text("\n".join(payload_lines), encoding="utf-8")
        return items


def get_default_welcome() -> str:
    return _DEFAULT_WELCOME


def _resolve_abc_ratios() -> tuple[float, float, float]:
    ratio_a = max(0.0, float(_WLCM_RATIO_A))
    ratio_b = max(0.0, float(_WLCM_RATIO_B))
    ratio_c = max(0.0, float(_WLCM_RATIO_C))
    total = ratio_a + ratio_b + ratio_c
    if total <= 0:
        return (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)
    return (ratio_a / total, ratio_b / total, ratio_c / total)


def get_welcome_ab_routing() -> _ABRouting:
    ratio_a, ratio_b, ratio_c = _resolve_abc_ratios()
    bucket = random.random()
    if bucket < ratio_a:
        variant = "A"
    elif bucket < (ratio_a + ratio_b):
        variant = "B"
    else:
        variant = "C"
    return {
        "bucket": bucket,
        "variant": variant,
        "ratioA": ratio_a,
        "ratioB": ratio_b,
        "ratioC": ratio_c,
        "mode": "random-per-request",
    }


def _base_prompt_by_variant(variant: str) -> str:
    if variant == "A":
        return _WLCM_PROMPT_A.strip()
    if variant == "B":
        return _WLCM_PROMPT_B.strip()
    return _WLCM_PROMPT_C.strip()


def _append_short_term_memory_to_prompt(base_prompt: str, memory_items: list[str]) -> str:
    deduped = _dedupe_keep_order(memory_items)
    if not deduped:
        return base_prompt
    memory_block = "\n".join(f"- {item}" for item in deduped)

    prefixes: list[str] = []
    seen: set[str] = set()
    for item in deduped:
        normalized = _normalize_welcome_text(item)
        if not normalized:
            continue
        # Use short leading phrase as a lightweight style fingerprint.
        prefix = normalized[:4]
        if prefix in seen:
            continue
        seen.add(prefix)
        prefixes.append(prefix)
        if len(prefixes) >= 8:
            break
    forbidden_prefixes = "\n".join(f"- {p}" for p in prefixes) if prefixes else "- 无"

    dedupe_suffix = _WLCM_DEDUPE_SUFFIX_TEMPLATE.format(
        memory_block=memory_block,
        forbidden_prefixes=forbidden_prefixes,
    )
    return f"{base_prompt}\n\n{dedupe_suffix}"


def get_welcome_user_prompt() -> str:
    return _WLCM_USER_PROMPT


def get_welcome_prompt(
    wlcm_gen_prompt: str | None = None,
    *,
    session_id: str,
) -> str:
    if wlcm_gen_prompt:
        return wlcm_gen_prompt.strip()
    routing = get_welcome_ab_routing()
    short_term_memory = get_short_term_welcome_memory(session_id=session_id, limit=_SHORT_TERM_MAX_ITEMS)
    base_prompt = _base_prompt_by_variant(routing["variant"])
    return _append_short_term_memory_to_prompt(base_prompt, short_term_memory)


def get_welcome_generation_config(
    wlcm_gen_prompt: str | None = None,
    *,
    session_id: str,
) -> dict:
    routing = get_welcome_ab_routing()
    short_term_memory = get_short_term_welcome_memory(session_id=session_id, limit=_SHORT_TERM_MAX_ITEMS)
    base_prompt = _base_prompt_by_variant(routing["variant"])
    system_prompt = (
        wlcm_gen_prompt.strip()
        if wlcm_gen_prompt
        else _append_short_term_memory_to_prompt(base_prompt, short_term_memory)
    )
    return {
        "model": _WLCM_MODEL,
        "temperature": _WLCM_TEMPERATURE,
        "max_tokens": _WLCM_MAX_TOKENS,
        "first_token_timeout_seconds": _FIRST_TOKEN_TIMEOUT_SECONDS,
        "system_prompt": system_prompt,
        "ab": routing,
        "short_term_memory": short_term_memory,
        "session_id": session_id,
    }


def normalize_welcome_text(text: str) -> str:
    return _normalize_welcome_text(text)


def build_welcome_messages(
    wlcm_gen_prompt: str | None = None,
    *,
    session_id: str,
) -> list[dict]:
    config = get_welcome_generation_config(wlcm_gen_prompt=wlcm_gen_prompt, session_id=session_id)
    prompt = get_welcome_user_prompt()
    return [
        {
            "role": "system",
            "content": str(config["system_prompt"]),
        },
        {"role": "user", "content": prompt},
    ]


def debug_generate_welcome_text(
    wlcm_gen_prompt: str | None = None,
    *,
    session_id: str | None = None,
    print_messages: bool = False,
) -> dict:
    settings = _get_debug_settings()
    default_welcome = get_default_welcome()
    resolved_session_id = normalize_session_id(session_id) or create_welcome_session_id()
    config = get_welcome_generation_config(session_id=resolved_session_id)
    first_token_timeout_seconds = float(config["first_token_timeout_seconds"])
    messages = build_welcome_messages(wlcm_gen_prompt, session_id=resolved_session_id)

    result = {
        "ok": False,
        "fallback": default_welcome,
        "firstTokenLatencySeconds": None,
        "rawText": "",
        "normalizedText": default_welcome,
        "messageCount": len(messages),
        "model": str(config["model"]),
        "request": {
            "model": str(config["model"]),
            "temperature": float(config["temperature"]),
            "max_tokens": int(config["max_tokens"]),
            "timeout": first_token_timeout_seconds,
            "sessionId": resolved_session_id,
            "messages": messages,
        },
        "response": {
            "rawText": "",
            "normalizedText": default_welcome,
            "chunks": [],
        },
    }

    if print_messages:
        print("[welcome-debug] messages:")
        print(json.dumps(messages, ensure_ascii=False, indent=2))

    if not settings["api_key"]:
        result["error"] = "missing api_key"
        return result

    try:
        client = OpenAI(api_key=settings["api_key"], base_url=settings["base_url"])
        start = time.monotonic()
        deadline = start + first_token_timeout_seconds
        stream = client.chat.completions.create(
            model=str(config["model"]),
            messages=messages,
            temperature=float(config["temperature"]),
            max_tokens=int(config["max_tokens"]),
            stream=True,
            timeout=first_token_timeout_seconds,
        )

        parts: list[str] = []
        first_token_latency = None
        for chunk in stream:
            if first_token_latency is None and time.monotonic() > deadline:
                result["error"] = "first token timeout"
                return result

            if not chunk.choices:
                continue

            delta_text = chunk.choices[0].delta.content or ""
            if delta_text:
                if first_token_latency is None:
                    first_token_latency = round(time.monotonic() - start, 4)
                parts.append(delta_text)
                result["response"]["chunks"].append(delta_text)

        raw_text = "".join(parts)
        normalized_text = normalize_welcome_text(raw_text)
        if normalized_text and normalized_text != default_welcome:
            result["response"]["updatedShortTermMemory"] = record_welcome_word(
                session_id=resolved_session_id,
                text=normalized_text,
            )
        result.update(
            {
                "ok": True,
                "firstTokenLatencySeconds": first_token_latency,
                "rawText": raw_text,
                "normalizedText": normalized_text,
            }
        )
        result["response"]["rawText"] = raw_text
        result["response"]["normalizedText"] = normalized_text
        return result
    except Exception as exc:
        result["error"] = str(exc)
        return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Debug welcome prompt generation.")
    parser.add_argument(
        "--prompt",
        default=None,
        help="Override the default welcome prompt text.",
    )
    parser.add_argument(
        "--show-messages",
        action="store_true",
        help="Print full request messages (system + user).",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Optional welcome session id for isolated short-term memory.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    settings = _get_debug_settings()
    resolved_session_id = normalize_session_id(args.session_id) or create_welcome_session_id()
    config = get_welcome_generation_config(session_id=resolved_session_id)

    print(
        "[welcome-debug] config="
        f"model={config['model']} temperature={config['temperature']} "
        f"max_tokens={config['max_tokens']} timeout={config['first_token_timeout_seconds']}s"
    )
    print(
        "[welcome-debug] api="
        f"base_url={settings['base_url']} has_api_key={bool(settings['api_key'])}"
    )
    print(f"[welcome-debug] session_id={resolved_session_id}")

    result = debug_generate_welcome_text(
        wlcm_gen_prompt=args.prompt,
        session_id=resolved_session_id,
        print_messages=args.show_messages,
    )
    print("[welcome-debug] request payload:")
    print(json.dumps(result.get("request", {}), ensure_ascii=False, indent=2))
    print("[welcome-debug] response payload:")
    print(json.dumps(result.get("response", {}), ensure_ascii=False, indent=2))
    print("[welcome-debug] summary:")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
