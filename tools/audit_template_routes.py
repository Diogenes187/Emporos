"""Check that server-rendered forms target real routes with required fields."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute

from app.main import app

FORM = re.compile(r"<form\b(?P<tag>[^>]*)>(?P<body>.*?)</form>", re.I | re.S)
ACTION = re.compile(r'action=["\'](?P<value>[^"\']+)', re.I)
METHOD = re.compile(r'method=["\'](?P<value>[^"\']+)', re.I)
NAME = re.compile(r'<(?:input|select|textarea|button)\b[^>]*\bname=["\'](?P<value>[^"\']+)', re.I)
JINJA = re.compile(r"{{.*?}}")

ACTION_ALTERNATIVES = {
    "/{{ mode }}": ("/login", "/register"),
}


def sample_path(action: str) -> str:
    return JINJA.sub("sample", action).split("?", 1)[0]


def main() -> int:
    routes = [route for route in app.routes if isinstance(route, APIRoute)]
    failures: list[str] = []
    checked = 0
    for template in sorted((ROOT / "app" / "templates").glob("*.html")):
        text = template.read_text(encoding="utf-8")
        for match in FORM.finditer(text):
            action_match = ACTION.search(match["tag"])
            method_match = METHOD.search(match["tag"])
            if not action_match or not method_match:
                continue
            method = method_match["value"].upper()
            if method != "POST":
                continue
            supplied = set(NAME.findall(match["body"]))
            actions = ACTION_ALTERNATIVES.get(
                action_match["value"], (sample_path(action_match["value"]),)
            )
            for action in actions:
                route = next(
                    (
                        candidate
                        for candidate in routes
                        if method in candidate.methods
                        and candidate.path_regex.fullmatch(action)
                    ),
                    None,
                )
                if route is None:
                    failures.append(
                        f"{template.name}: no POST route for {action_match['value']} ({action})"
                    )
                    continue
                checked += 1
                required = {
                    parameter.name
                    for parameter in route.dependant.body_params
                    if parameter.field_info.is_required()
                }
                missing = sorted(required - supplied)
                if missing:
                    failures.append(
                        f"{template.name}: {action_match['value']} omits required fields {missing}"
                    )
    print(f"checked {checked} server-rendered POST forms")
    if failures:
        print("\n".join(failures))
        return 1
    print("all form actions resolve and supply their required body fields")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
