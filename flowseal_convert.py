#!/usr/bin/env python3
"""Convert Flowseal Windows .bat strategies into nfqws2 (zapret2 Linux) arguments.

Only strategies shipped in Flowseal/zapret-discord-youtube are supported.
Nothing is invented here: every nfqws2 option comes from a general*.bat file.
Windows-only WinDivert options (--wf-*) are dropped, batch placeholders are
expanded to Linux paths and the game filter variables are substituted.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path

_WINWS_RE = re.compile(r"winws2(?:2)?(?:\.exe)?[\"']?\s*(.*)$", re.IGNORECASE)
_WINDOWS_ONLY = ("--wf-tcp-out=", "--wf-udp-out=", "--wf-")
# zapret2 init scripts already load these two files from the engine lua dir.
# During sync that directory is replaced by the Flowseal copies of the same
# files, so loading them again would be a duplicate.
_ENGINE_LUA_INIT = ("zapret-lib.lua", "zapret-antidpi.lua")
_PLACEHOLDER_RE = re.compile(r"%([A-Za-z_][A-Za-z0-9_]*)%")


@dataclass
class ConvertedStrategy:
    name: str
    source: str
    args: list[str]
    warnings: list[str]


def _command_tail(lines: list[str]) -> str | None:
    """Find the winws2 invocation and join its batch '^' continuations."""
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("::") or "%~n0" in line and "start" not in line.lower():
            continue
        match = _WINWS_RE.search(line)
        if not match:
            continue

        buffer = line.rstrip()
        cursor = index + 1
        while buffer.endswith("^"):
            buffer = buffer[:-1].rstrip()
            # Flowseal separates logical blocks with empty lines after '^'.
            while cursor < len(lines) and not lines[cursor].strip():
                cursor += 1
            if cursor >= len(lines):
                break
            buffer += " " + lines[cursor].strip()
            cursor += 1
        return match.group(1) if (match := _WINWS_RE.search(buffer)) else None
    return None


def _expand(text: str, values: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1).upper()
        if key not in values:
            raise ValueError(f"unknown batch placeholder %{match.group(1)}%")
        return values[key]

    return _PLACEHOLDER_RE.sub(replace, text)


def convert_strategy(
    path: str | Path,
    *,
    lua_dir: str,
    lists_dir: str,
    bin_dir: str,
    engine_dir: str,
    game_tcp: str = "12",
    game_udp: str = "12",
    add_chdir: bool = True,
) -> ConvertedStrategy:
    source = Path(path)
    text = source.read_text(encoding="utf-8-sig", errors="replace")
    tail = _command_tail(text.splitlines())
    if tail is None:
        raise ValueError(f"{source}: no winws2 command found")

    tail = _expand(
        tail,
        {
            "BIN": bin_dir.rstrip("/") + "/",
            "LUA": lua_dir.rstrip("/") + "/",
            "LISTS": lists_dir.rstrip("/") + "/",
            "GAMEFILTERTCP": game_tcp,
            "GAMEFILTERUDP": game_udp,
        },
    )

    warnings: list[str] = []
    args: list[str] = []
    for token in shlex.split(tail, posix=True):
        if token.startswith(_WINDOWS_ONLY):
            warnings.append(f"dropped Windows-only option: {token.split('=', 1)[0]}")
            continue
        if token.startswith("--lua-init=") and token.endswith(_ENGINE_LUA_INIT):
            warnings.append(f"skipped duplicate lua-init: {token.split('=', 1)[1]}")
            continue
        if any(char.isspace() for char in token):
            # NFQWS2_OPT is expanded unquoted by the zapret2 init script.
            # Profile names are labels only, so underscores are safe here.
            normalized = re.sub(r"\s+", "_", token)
            warnings.append(f"normalized spaces: {token!r} -> {normalized!r}")
            token = normalized
        args.append(token)

    if add_chdir:
        # blobs.lua looks for *.bin in "" and "bin/" relative to cwd.
        args.insert(0, f"--chdir={engine_dir.rstrip('/')}")

    return ConvertedStrategy(
        name=source.stem,
        source=str(source),
        args=args,
        warnings=warnings,
    )


def render_config_value(args: list[str]) -> str:
    """Render arguments as a shell variable value consumed by zapret2 init scripts."""
    return "\n".join(args)
