from __future__ import annotations

import json
from pathlib import Path

from robjy.session.cookies import import_cookie_text, parse_cookie_header


def test_parse_standard_header():
    cookies = parse_cookie_header("a=1; b=two=still")
    assert cookies[0]["name"] == "a" and cookies[0]["value"] == "1"
    assert cookies[1]["name"] == "b" and cookies[1]["value"] == "two=still"
    assert cookies[0]["domain"] == ".shqmxx.com"


def test_parse_charles_cookie_table_lines():
    raw = (
        "cookie\t94_e31aSessionEntity=payloadA\n"
        "cookie\t94_e31aParamsEntity=payloadB\n"
    )
    cookies = parse_cookie_header(raw)
    assert [c["name"] for c in cookies] == [
        "94_e31aSessionEntity",
        "94_e31aParamsEntity",
    ]
    assert cookies[0]["value"] == "payloadA"


def test_import_cookie_writes_storage_state(tmp_path: Path):
    out = tmp_path / "storage_state.json"
    path = import_cookie_text("foo=bar; baz=qux", out)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["cookies"]) == 2
    assert data["cookies"][0]["name"] == "foo"
    assert data["cookies"][0]["secure"] is True
