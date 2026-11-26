#!/usr/bin/env python3
"""Tests for the Flowseal .bat -> nfqws2 converter.

Run with: python3 -m unittest discover -s tests -v
Set FLOWSEAL_UPSTREAM=/path/to/zapret-discord-youtube to test all real strategies.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flowseal_convert import convert_strategy, render_config_value  # noqa: E402

FIXTURE = """@echo off
chcp 65001 > nul
cd /d "%~dp0"
call service.bat status_zapret
set "BIN=%~dp0bin\\"
set "LISTS=%~dp0lists\\"
set "LUA=%~dp0lua\\"
cd /d %BIN%

start "zapret: %~n0" /min "%BIN%winws2.exe" --debug=0 --wf-tcp-out=80,443,%GameFilterTCP% --wf-udp-out=443,%GameFilterUDP% ^

--lua-init=@"%LUA%blobs.lua" ^
--lua-init=@"%LUA%zapret-lib.lua" ^

--name="Domain Quic" ^
--filter-udp=443 ^
--hostlist="%LISTS%list-general.txt" ^
--payload=quic_initial ^
--lua-desync=fake:blob=quic_google:repeats=6 ^
--new ^

--name="GameFilter TCP" ^
--filter-tcp=%GameFilterTCP% ^
--payload=all ^
--lua-desync=multisplit:pos=1:payload=all
"""


class ConverterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bat = self.root / "general (TEST).bat"
        self.bat.write_text(FIXTURE, encoding="utf-8")
        self.kwargs = dict(
            lua_dir="/opt/zapret2/lua",
            lists_dir="/opt/zapret2/flowseal/assets/lists",
            bin_dir="/opt/zapret2/bin",
            engine_dir="/opt/zapret2",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_windows_only_options_dropped(self) -> None:
        result = convert_strategy(self.bat, **self.kwargs)
        self.assertFalse(any(arg.startswith("--wf-") for arg in result.args))
        self.assertTrue(any("Windows-only" in item for item in result.warnings))

    def test_placeholders_expanded(self) -> None:
        result = convert_strategy(self.bat, **self.kwargs)
        self.assertNotIn("%", " ".join(result.args))
        self.assertIn("--lua-init=@/opt/zapret2/lua/blobs.lua", result.args)
        self.assertIn("--hostlist=/opt/zapret2/flowseal/assets/lists/list-general.txt", result.args)

    def test_game_filter_values(self) -> None:
        result = convert_strategy(self.bat, **self.kwargs, game_tcp="1024-65535", game_udp="5000-6000")
        self.assertIn("--filter-tcp=1024-65535", result.args)
        self.assertNotIn("--wf-tcp-out=80,443,1024-65535", result.args)

    def test_profile_names_have_no_spaces(self) -> None:
        result = convert_strategy(self.bat, **self.kwargs)
        self.assertIn("--name=Domain_Quic", result.args)
        self.assertTrue(all(not any(char.isspace() for char in arg) for arg in result.args))

    def test_duplicate_engine_lua_skipped(self) -> None:
        bat = self.root / "general (LUA).bat"
        bat.write_text(
            FIXTURE.replace(
                '--lua-init=@"%LUA%blobs.lua" ^\n',
                '--lua-init=@"%LUA%blobs.lua" ^\n--lua-init=@"%LUA%zapret-lib.lua" ^\n--lua-init=@"%LUA%zapret-antidpi.lua" ^\n',
            ),
            encoding="utf-8",
        )
        result = convert_strategy(bat, **self.kwargs)
        self.assertIn("--lua-init=@/opt/zapret2/lua/blobs.lua", result.args)
        self.assertFalse(any("zapret-lib.lua" in arg for arg in result.args))
        self.assertFalse(any("zapret-antidpi.lua" in arg for arg in result.args))

    def test_chdir_added_first(self) -> None:
        result = convert_strategy(self.bat, **self.kwargs)
        self.assertEqual(result.args[0], "--chdir=/opt/zapret2")

    def test_rendered_config_is_one_option_per_line(self) -> None:
        result = convert_strategy(self.bat, **self.kwargs)
        rendered = render_config_value(result.args)
        self.assertEqual(len(rendered.splitlines()), len(result.args))
        self.assertTrue(all(" " not in line for line in rendered.splitlines()))

    @unittest.skipUnless(os.environ.get("FLOWSEAL_UPSTREAM"), "FLOWSEAL_UPSTREAM not set")
    def test_all_upstream_strategies(self) -> None:
        upstream = Path(os.environ["FLOWSEAL_UPSTREAM"])
        names = sorted(upstream.glob("general*.bat"))
        self.assertGreaterEqual(len(names), 20)
        for path in names:
            with self.subTest(strategy=path.name):
                result = convert_strategy(path, **self.kwargs)
                self.assertTrue(result.args)
                self.assertFalse(any(arg.startswith("--wf-") for arg in result.args))
                self.assertFalse(any("%" in arg for arg in result.args))
                self.assertIn("--chdir=/opt/zapret2", result.args)
                self.assertTrue(all(not any(char.isspace() for char in arg) for arg in result.args))


if __name__ == "__main__":
    unittest.main()
