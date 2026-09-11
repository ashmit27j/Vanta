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

    sigma = sub.add_parser("sigma", help="Sigma detection pipeline")
    sigma_sub = sigma.add_subparsers(dest="sigma_command", required=True)

    sigma_convert = sigma_sub.add_parser("convert", help="Sigma YAML -> Lucene query (all rules, or one path)")
    sigma_convert.add_argument("path", nargs="?", default=None)
    sigma_convert.set_defaults(func=commands.cmd_sigma_convert)

    sigma_deploy = sigma_sub.add_parser("deploy", help="Deploy rule(s) as OpenSearch Alerting monitors")
    sigma_deploy.add_argument("path", nargs="?", default=None)
    sigma_deploy.set_defaults(func=commands.cmd_sigma_deploy)

    sigma_test = sigma_sub.add_parser("test", help="Detection test harness: run a technique, assert it fires")
    sigma_test.add_argument("technique_id")
    sigma_test.set_defaults(func=commands.cmd_sigma_test)

    coverage = sub.add_parser("coverage", help="Generate the ATT&CK Navigator layer + HTML coverage report")
    coverage.set_defaults(func=commands.cmd_coverage)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
