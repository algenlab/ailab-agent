"""LLM API client wrapping OpenAI-compatible endpoint."""
import json, os, re
from pathlib import Path
from openai import OpenAI

os.environ["no_proxy"] = os.environ.get("no_proxy", "") + ",baidu-int.com,baidu.com,localhost,127.0.0.1"

DEFAULT_BASE_URL = "http://yy.dbh.baidu-int.com/v1"
_LOCAL_API_SETTINGS = None
BASE_URL = os.environ.get("ALGOLAB_LLM_BASE_URL") or DEFAULT_BASE_URL
API_KEY = os.environ.get("ALGOLAB_LLM_API_KEY")

_client = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        settings = api_settings()
        if not settings["api_key"]:
            raise RuntimeError("缺少 ALGOLAB_LLM_API_KEY 环境变量，或本地 api_settings.json/yaml")
        _client = OpenAI(base_url=settings["base_url"], api_key=settings["api_key"])
    return _client

DEFAULT_MODEL = "gemini-3.1-pro-preview"
DEFAULT_TIMEOUT_S = 240
DEFAULT_MAX_TOKENS = 16384
DEFAULT_JSON_RETRIES = 1


def _model_name(model: str | None = None) -> str:
    return model or os.environ.get("ALGOLAB_LLM_MODEL") or DEFAULT_MODEL


def _timeout_s() -> float:
    raw = os.environ.get("ALGOLAB_LLM_TIMEOUT_S")
    if not raw:
        return DEFAULT_TIMEOUT_S
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_TIMEOUT_S


def _max_tokens() -> int:
    raw = os.environ.get("ALGOLAB_LLM_MAX_TOKENS")
    if not raw:
        return DEFAULT_MAX_TOKENS
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_MAX_TOKENS


def _json_retries() -> int:
    raw = os.environ.get("ALGOLAB_LLM_JSON_RETRIES")
    if not raw:
        return DEFAULT_JSON_RETRIES
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_JSON_RETRIES


def api_settings() -> dict:
    local = _load_local_api_settings()
    return {
        "base_url": os.environ.get("ALGOLAB_LLM_BASE_URL") or local.get("base_url") or DEFAULT_BASE_URL,
        "api_key": os.environ.get("ALGOLAB_LLM_API_KEY") or local.get("api_key") or "",
        "source": "env" if os.environ.get("ALGOLAB_LLM_API_KEY") else local.get("source", ""),
    }


def _load_local_api_settings() -> dict:
    global _LOCAL_API_SETTINGS
    if _LOCAL_API_SETTINGS is not None:
        return _LOCAL_API_SETTINGS
    paths = [
        Path(os.environ["ALGOLAB_LLM_SETTINGS_FILE"])
        if os.environ.get("ALGOLAB_LLM_SETTINGS_FILE")
        else None,
        Path("api_settings.json"),
        Path("api_settings.yaml"),
        Path("api_settings.yml"),
        Path(".algolab_api_settings.json"),
        Path(".algolab_api_settings.yaml"),
        Path(".algolab_api_settings.yml"),
    ]
    for path in [item for item in paths if item is not None]:
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8")
        data = _parse_api_settings(raw)
        data["source"] = str(path)
        _LOCAL_API_SETTINGS = data
        return data
    _LOCAL_API_SETTINGS = {}
    return _LOCAL_API_SETTINGS


def _parse_api_settings(raw: str) -> dict:
    text = raw.strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
        return _normalize_api_settings(data)
    except json.JSONDecodeError:
        return _parse_simple_yaml_api_settings(text)


def _normalize_api_settings(data: object) -> dict:
    if not isinstance(data, dict):
        return {}
    section = data.get("api_settings") if isinstance(data.get("api_settings"), dict) else data
    return {
        "base_url": str(section.get("base_url") or "").strip(),
        "api_key": str(section.get("api_key") or "").strip(),
    }


def _parse_simple_yaml_api_settings(text: str) -> dict:
    current_section = ""
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith((" ", "\t")) and line.endswith(":"):
            current_section = line[:-1].strip()
            continue
        if current_section and current_section != "api_settings":
            continue
        key, sep, value = line.strip().partition(":")
        if not sep:
            continue
        cleaned = value.strip().strip('"').strip("'")
        if key in {"base_url", "api_key"}:
            values[key] = cleaned
    return {
        "base_url": values.get("base_url", ""),
        "api_key": values.get("api_key", ""),
    }


def llm_config() -> dict:
    settings = api_settings()
    return {
        "model": _model_name(),
        "base_url": settings["base_url"],
        "api_key_configured": bool(settings["api_key"]),
        "api_key_source": settings["source"],
        "timeout_s": _timeout_s(),
        "max_tokens": _max_tokens(),
        "json_retries": _json_retries(),
    }


class LLMJsonError(ValueError):
    """Raised when a model response cannot be parsed as JSON."""


def parse_json_content(content: str):
    text = (content or "").strip()
    if not text:
        raise LLMJsonError("模型返回空内容，无法解析 JSON")
    try:
        return json.loads(text)
    except json.JSONDecodeError as original:
        fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            candidate = fenced.group(1).strip()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
        extracted = _extract_json_span(text)
        if extracted and extracted != text:
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                pass
        raise LLMJsonError(f"模型返回内容不是合法 JSON：{original}; preview={_preview(text)}") from original


def _extract_json_span(text: str) -> str:
    starts = [idx for idx in (text.find("{"), text.find("[")) if idx >= 0]
    if not starts:
        return ""
    start = min(starts)
    open_char = text[start]
    close_char = "}" if open_char == "{" else "]"
    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    return ""


def _preview(text: str, limit: int = 500) -> str:
    compact = text.replace("\n", "\\n")
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "...<truncated>"


def chat_json(system_prompt: str, user_prompt: str, model: str | None = None) -> dict:
    client = get_client()
    messages = [{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}]
    last_error: Exception | None = None
    for attempt in range(_json_retries() + 1):
        response = client.chat.completions.create(
            model=_model_name(model), messages=messages,
            response_format={"type": "json_object"}, temperature=0.2, max_tokens=_max_tokens(), timeout=_timeout_s())
        content = response.choices[0].message.content or ""
        try:
            return parse_json_content(content)
        except LLMJsonError as exc:
            last_error = exc
            if attempt >= _json_retries():
                break
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": "\n\n".join(
                        [
                            user_prompt,
                            "上一轮输出不是合法 JSON，必须重试。",
                            str(exc),
                            "现在只返回一个完整、紧凑、可被 json.loads 解析的 JSON 对象。不要 markdown。不要截断。若内容过长，减少 events、reason 和 pseudocode，而不是输出残缺 JSON。",
                        ]
                    ),
                },
            ]
    raise last_error or LLMJsonError("模型返回内容不是合法 JSON")

def chat_text(system_prompt: str, user_prompt: str, model: str | None = None) -> str:
    client = get_client()
    response = client.chat.completions.create(
        model=_model_name(model), messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}],
        temperature=0.3, max_tokens=_max_tokens(), timeout=_timeout_s())
    return response.choices[0].message.content


VISION_MODEL = "gemini-3-flash-preview"


def chat_vision(system_prompt: str, user_text: str, image_b64: str,
                model: str = VISION_MODEL) -> str:
    """Call a multimodal model with an image.

    Args:
        system_prompt: System-level instruction
        user_text: Text prompt describing what to evaluate
        image_b64: Base64-encoded image (without data: URL prefix)
        model: Model name, defaults to gemini-3-flash-preview
    """
    import base64
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": system_prompt + "\n\n" + user_text},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
            ]
        }],
        temperature=0.2,
        max_tokens=1024,
    )
    return response.choices[0].message.content


def figure_to_b64(fig) -> str:
    """Convert a matplotlib Figure to base64 PNG string."""
    import base64, io
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")
