from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable


DEFAULT_DOMAIN = ".shqmxx.com"
DEFAULT_ORIGIN = "https://h5.shqmxx.com"


def parse_cookie_header(raw: str) -> list[dict]:
    """把 HTTP Cookie 头或 name=value 多行文本解析为 Playwright cookies。

    支持：
    - 标准头：`a=1; b=2`
    - Charles Cookies 面板粘贴：每行 `name=value`（可带前缀 cookie\\t）
    - 值中可含 `=`（只按第一个 `=` 分割 name/value）
    """
    text = raw.strip()
    if not text:
        raise ValueError("Cookie 内容为空")

    # 统一成分号分隔
    lines: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Charles 表格粘贴可能带 "cookie\t"
        if line.lower().startswith("cookie") and ("\t" in line or line[6:7] in {" ", "="}):
            # cookie\tname=value 或 cookie name=value
            line = re.sub(r"(?i)^cookie[\t ]+", "", line)
        lines.append(line)

    joined = " ".join(lines)
    # 若是多行 name=value 且没有分号，用换行意合成；已 join 成空格
    # 优先按 `;` 拆；若只有一段且含换行风格，再按空白中的 name= 模式拆
    parts = [p.strip() for p in joined.split(";") if p.strip()]
    if len(parts) == 1 and len(lines) > 1:
        parts = lines

    cookies: list[dict] = []
    for part in parts:
        if "=" not in part:
            raise ValueError(f"无法解析 Cookie 片段（缺少=）: {part[:80]!r}")
        name, value = part.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name:
            raise ValueError(f"Cookie 名为空: {part[:80]!r}")
        cookies.append(_playwright_cookie(name, value))
    return cookies


def _playwright_cookie(
    name: str,
    value: str,
    *,
    domain: str = DEFAULT_DOMAIN,
) -> dict:
    return {
        "name": name,
        "value": value,
        "domain": domain,
        "path": "/",
        "expires": -1,
        "httpOnly": False,
        "secure": True,
        "sameSite": "Lax",
    }


def build_storage_state(
    cookies: Iterable[dict],
    *,
    origin: str = DEFAULT_ORIGIN,
    local_storage: list[dict] | None = None,
) -> dict:
    cookie_list = list(cookies)
    if not cookie_list:
        raise ValueError("至少需要一条 Cookie")
    state: dict = {"cookies": cookie_list, "origins": []}
    if local_storage:
        state["origins"] = [{"origin": origin, "localStorage": local_storage}]
    return state


def write_storage_state(path: str | Path, state: dict) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def import_cookie_text(
    raw: str,
    output: str | Path,
    *,
    domain: str = DEFAULT_DOMAIN,
) -> Path:
    cookies = parse_cookie_header(raw)
    # 允许覆盖 domain
    for c in cookies:
        c["domain"] = domain
    state = build_storage_state(cookies)
    return write_storage_state(output, state)
