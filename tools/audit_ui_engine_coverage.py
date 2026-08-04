"""Inventory authoritative engine commands that do or do not reach the web app."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine"
APP_COMMANDS = (ROOT / "app" / "commands.py").read_text(encoding="utf-8")


def command_definitions() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for path in sorted(ENGINE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                node.name.endswith("_command") and not node.name.startswith("_")
            ):
                found.append((path.name, node.name))
    return found


def main() -> int:
    commands = command_definitions()
    exposed = [(module, name) for module, name in commands if name in APP_COMMANDS]
    engine_only = [(module, name) for module, name in commands if name not in APP_COMMANDS]
    lines = [
        "# Emporos UI-to-Engine Coverage Audit",
        "",
        "This generated inventory identifies authoritative engine commands with a "
        "direct application wrapper. Engine-only commands are review candidates, "
        "not automatically missing buttons: some are internal, AI-tool, referee, "
        "or deliberately lower-level operations.",
        "",
        "## Snapshot",
        "",
        f"- Engine command entry points: {len(commands)}",
        f"- Direct web-application wrappers: {len(exposed)}",
        f"- Engine-only review candidates: {len(engine_only)}",
        "",
        "## Engine-only review candidates",
        "",
        "| Engine module | Command |",
        "|---|---|",
    ]
    lines.extend(
        f"| `{module}` | `{name}` |" for module, name in engine_only
    )
    lines.extend(["", "## Directly wrapped commands", "", "| Engine module | Command |", "|---|---|"])
    lines.extend(f"| `{module}` | `{name}` |" for module, name in exposed)
    (ROOT / "UI_ENGINE_COVERAGE.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(
        f"audited {len(commands)} engine commands: {len(exposed)} wrapped, "
        f"{len(engine_only)} review candidates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
