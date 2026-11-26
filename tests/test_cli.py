#!/usr/bin/env python3
"""Tests for the console manager and target parsing."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

loader = importlib.machinery.SourceFileLoader("zapret_flowseal", str(ROOT / "zapret-flowseal"))
spec = importlib.util.spec_from_loader(loader.name, loader)
cli = importlib.util.module_from_spec(spec)
loader.exec_module(cli)


class CLITests(unittest.TestCase):
    def test_no_subcommand_defaults_to_menu(self) -> None:
        args = cli.build_parser().parse_args([])
        self.assertIsNone(args.command)
        self.assertIn("best", cli.build_parser()._subparsers._group_actions[0].choices)

    def test_best_options(self) -> None:
        args = cli.build_parser().parse_args(
            ["best", "--apply", "--start", "--limit", "3", "--timeout", "2", "--workers", "8"]
        )
        self.assertTrue(args.apply)
        self.assertTrue(args.start)
        self.assertEqual(args.limit, 3)
        self.assertEqual(args.timeout, 2)
        self.assertEqual(args.workers, 8)

    def test_parse_targets(self) -> None:
        upstream = Path("/tmp/opencode/zapret-upstream/utils/targets.txt")
        if not upstream.exists():
            self.skipTest("upstream checkout not available")
        targets = cli.parse_targets(upstream)
        urls = [item for item in targets if item["kind"] == "url"]
        pings = [item for item in targets if item["kind"] == "ping"]
        self.assertGreaterEqual(len(urls), 10)
        self.assertGreaterEqual(len(pings), 4)
        self.assertTrue(all(item["value"].startswith("https://") for item in urls))

    def test_parse_targets_inline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "targets.txt"
            path.write_text('Discord = "https://discord.com"\nDNS = "PING:1.1.1.1"\n')
            parsed = cli.parse_targets(path)
        self.assertEqual(parsed, [
            {"name": "Discord", "kind": "url", "value": "https://discord.com"},
            {"name": "DNS", "kind": "ping", "value": "1.1.1.1"},
        ])

    def test_test_strategy_counts(self) -> None:
        result = cli.test_strategy(
            [
                {"name": "A", "kind": "url", "value": "https://a"},
                {"name": "B", "kind": "ping", "value": "1.1.1.1"},
            ],
            timeout=1,
            workers=2,
        )
        self.assertEqual(len(result["tokens"]["A"]), 3)
        self.assertEqual(result["tokens"]["B"], ["PING:OK" if result["ping_ok"] else "PING:--"])


if __name__ == "__main__":
    unittest.main()
