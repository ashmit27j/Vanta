"""Entry point for the `purplelab` CLI: the daily-loop commands (pick, run,
check, log, today). Sigma-pipeline, coverage, containment-check, and detonate
subcommands are added in later prompts (see docs/prompt-chain.md).
"""

from __future__ import annotations

import argparse
import sys

from . import commands


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="purplelab", description="Vanta daily-loop CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    pick = sub.add_parser("pick", help="Suggest the next uncovered ATT&CK technique")
    pick.add_argument("--tactic", default=None, help="Restrict to one ATT&CK tactic")
    pick.set_defaults(func=commands.cmd_pick)

    run = sub.add_parser("run", help="Run (or stage) a technique against victim-vm")
    run.add_argument("technique_id")
    run.set_defaults(func=commands.cmd_run)

    check = sub.add_parser("check", help="Query Wazuh for what fired since the last run")
    check.add_argument("technique_id")
    check.set_defaults(func=commands.cmd_check)

    log = sub.add_parser("log", help="Record the result of a technique run")
    log.add_argument("technique_id")
    log.set_defaults(func=commands.cmd_log)

    today = sub.add_parser("today", help="Show streak, recent entries, and what's next")
    today.set_defaults(func=commands.cmd_today)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
