"""Implementations of the `purplelab` subcommands. cli.py just parses argv and
dispatches here.
"""

from __future__ import annotations

import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

import requests

from . import atomics, journal, sigma_pipeline, state, wazuh
from .config import load_config


def cmd_pick(args) -> int:
    config = load_config()
    covered = journal.covered_technique_ids(config.repo_root)
    technique = atomics.pick_uncovered(covered, tactic=args.tactic)

    if technique is None:
        scope = f" in tactic '{args.tactic}'" if args.tactic else ""
        print(f"No uncovered techniques left{scope} in the catalog -- nice work. "
              "Extend tooling/purplelab/data/techniques.json to keep going.")
        return 0

    remote_note = " (better run from kali-vm -- see `purplelab run`)" if technique.remote else ""
    print(f"Next up: {technique.id} -- {technique.name} [{technique.tactic}]{remote_note}")
    print(f"Run it with: purplelab run {technique.id}")
    return 0


def cmd_run(args) -> int:
    config = load_config()
    technique = atomics.get_technique(args.technique_id)
    if technique is None:
        print(f"Unknown technique {args.technique_id!r} -- not in tooling/purplelab/data/techniques.json.")
        return 1

    print("=" * 60)
    print(f"SAFETY: revert victim-vm to its 'clean-baseline' snapshot before proceeding.")
    print("=" * 60)

    mode = "remote" if technique.remote else "local"

    if mode == "local":
        pwsh_cmd = f"Invoke-AtomicTest {technique.id} -GetPrereqs; Invoke-AtomicTest {technique.id}"
        if config.victim_ssh_host and config.victim_ssh_user:
            ssh_target = f"{config.victim_ssh_user}@{config.victim_ssh_host}"
            full_cmd = [
                "ssh",
                "-o", "ConnectTimeout=5",
                ssh_target,
                f'pwsh -NoProfile -Command "{pwsh_cmd}"',
            ]
            print(f"Running on victim-vm over SSH: {' '.join(full_cmd)}")
            try:
                subprocess.run(full_cmd, check=False, timeout=30)
            except FileNotFoundError:
                print("`ssh` not found on this host -- run the command below manually inside victim-vm instead:")
                print(f"  {pwsh_cmd}")
            except subprocess.TimeoutExpired:
                print("SSH to victim-vm timed out -- run the command below manually inside victim-vm instead:")
                print(f"  {pwsh_cmd}")
        else:
            print("No victim_ssh_host/victim_ssh_user configured -- run this manually, inside victim-vm:")
            print(f"  {pwsh_cmd}")
    else:
        print(f"{technique.id} is tagged 'remote' -- this is a hands-on attack staged from kali-vm, not")
        print("a locally-run atomic. Craft the appropriate Metasploit/Nmap/C2 command on kali-vm targeting")
        print("victim-vm yourself; purplelab just records the time window so `check` knows what to query.")

    run_state = state.start_run(config.repo_root, technique.id, mode)
    print(f"\nRecorded start time {run_state.started_at} for {technique.id}. Run `purplelab check {technique.id}` "
          "once you're done.")
    return 0


def cmd_check(args) -> int:
    config = load_config()
    run_state = state.get_run(config.repo_root, args.technique_id)
    if run_state is None:
        print(f"No in-progress run found for {args.technique_id}. Run `purplelab run {args.technique_id}` first.")
        return 1

    since = datetime.fromisoformat(run_state.started_at)
    now = datetime.now(timezone.utc)

    try:
        alerts = wazuh.search_alerts(config, config.victim_agent_name, since=since, until=now)
    except wazuh.WazuhConnectionError as exc:
        print(f"Could not check Wazuh: {exc}")
        return 1

    if not alerts:
        print(f"No alerts fired for {args.technique_id} in the window since {run_state.started_at}.")
        print("Caught blind -- time to write or fix a Sigma rule in detections/.")
        return 0

    first = alerts[0]
    ttd = (datetime.fromisoformat(first.timestamp) - since).total_seconds()
    print(f"{len(alerts)} alert(s) fired for {args.technique_id}. Time to detect: {ttd:.1f}s")
    for a in alerts:
        print(f"  [{a.timestamp}] level={a.rule_level} rule={a.rule_id} -- {a.rule_description}")
    return 0


def cmd_log(args) -> int:
    config = load_config()
    technique = atomics.get_technique(args.technique_id)
    if technique is None:
        print(f"Unknown technique {args.technique_id!r} -- not in tooling/purplelab/data/techniques.json.")
        return 1

    caught_blind = _prompt_yes_no("Was this caught blind (no alert fired)?", default=False)
    sigma_rule = input("Sigma rule path (blank if none): ").strip() or None
    notes = input("Notes: ").strip()
    ttd_raw = input("Time to detect in seconds (blank if none / caught blind, from `check` output): ").strip()
    ttd = float(ttd_raw) if ttd_raw else None

    entry = journal.Entry(
        technique_id=technique.id,
        tactic=technique.tactic,
        date=date.today().isoformat(),
        timestamp=datetime.now(timezone.utc).isoformat(),
        caught_blind=caught_blind,
        sigma_rule=sigma_rule,
        notes=notes,
        time_to_detect_seconds=ttd,
    )
    journal.append_entry(config.repo_root, entry)
    state.clear_run(config.repo_root, technique.id)
    print(f"Logged {technique.id}. journal/entries.jsonl and journal/LOG.md updated.")
    return 0


def cmd_today(args) -> int:
    config = load_config()
    streak = journal.current_streak_days(config.repo_root)
    recent = journal.recent_entries(config.repo_root, limit=5)

    print(f"Streak: {streak} day{'s' if streak != 1 else ''}")
    if recent:
        print("\nRecent entries:")
        for e in recent:
            result = "caught" if not e.caught_blind else "MISSED"
            print(f"  {e.date}  {e.technique_id:<14} [{e.tactic}]  {result}")
    else:
        print("\nNo entries yet.")

    covered = journal.covered_technique_ids(config.repo_root)
    next_technique = atomics.pick_uncovered(covered)
    if next_technique:
        print(f"\nNext up: {next_technique.id} -- {next_technique.name} [{next_technique.tactic}]")
        print(f"Run `purplelab run {next_technique.id}` to start.")
    else:
        print("\nAll cataloged techniques covered -- extend tooling/purplelab/data/techniques.json.")
    return 0


def _prompt_yes_no(question: str, default: bool) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    answer = input(f"{question} {suffix} ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def _rule_path_for_technique(repo_root: Path, technique_id: str) -> Path | None:
    matches = list((repo_root / "detections").glob(f"*/{technique_id}.yml"))
    return matches[0] if matches else None


def cmd_sigma_convert(args) -> int:
    config = load_config()
    if args.path:
        rule_path = Path(args.path)
        try:
            queries = sigma_pipeline.convert_rule(rule_path)
        except sigma_pipeline.SigmaPipelineError as exc:
            print(f"Invalid rule: {exc}")
            return 1
        print(f"{rule_path}:")
        for q in queries:
            print(f"  {q}")
        return 0

    detections_dir = config.repo_root / "detections"
    rules = sigma_pipeline.find_rules(detections_dir)
    if not rules:
        print(f"No rules found under {detections_dir}.")
        return 0

    failed = False
    for rule_path in rules:
        try:
            queries = sigma_pipeline.convert_rule(rule_path)
        except sigma_pipeline.SigmaPipelineError as exc:
            print(f"INVALID  {rule_path}: {exc}")
            failed = True
            continue
        print(f"OK       {rule_path}")
        for q in queries:
            print(f"           {q}")
    return 1 if failed else 0


def cmd_sigma_deploy(args) -> int:
    config = load_config()

    if args.path:
        rule_paths = [Path(args.path)]
    else:
        rule_paths = sigma_pipeline.find_rules(config.repo_root / "detections")

    if not rule_paths:
        print("No rules to deploy.")
        return 0

    failed = False
    for rule_path in rule_paths:
        technique_id = sigma_pipeline.technique_id_for(rule_path)
        try:
            monitor_id = sigma_pipeline.deploy_rule(config, rule_path)
        except sigma_pipeline.SigmaPipelineError as exc:
            print(f"INVALID  {rule_path}: {exc}")
            failed = True
            continue
        except requests.RequestException as exc:
            print(f"Could not deploy {rule_path} to {config.wazuh_base_url}: {exc}")
            failed = True
            continue
        print(f"Deployed {technique_id} -> monitor {monitor_id} ({sigma_pipeline.monitor_name_for(technique_id)})")
    return 1 if failed else 0


def cmd_sigma_test(args) -> int:
    """Detection test harness: revert reminder -> run the atomic -> assert
    the matching Sigma-backed monitor produced a finding -> pass/fail.
    """
    config = load_config()
    rule_path = _rule_path_for_technique(config.repo_root, args.technique_id)
    if rule_path is None:
        print(f"No Sigma rule found for {args.technique_id} under detections/*/{args.technique_id}.yml")
        return 1

    print(f"Deploying {rule_path} before testing...")
    try:
        monitor_id = sigma_pipeline.deploy_rule(config, rule_path)
    except (sigma_pipeline.SigmaPipelineError, requests.RequestException) as exc:
        print(f"Could not deploy rule: {exc}")
        return 1

    run_result = cmd_run(args)
    if run_result != 0:
        return run_result

    input("\nPress Enter once the atomic/attack has finished executing (allow a few minutes for the monitor "
          f"schedule to catch up -- it runs every {sigma_pipeline.MONITOR_SCHEDULE_MINUTES} minutes)... ")

    run_state = state.get_run(config.repo_root, args.technique_id)
    since = datetime.fromisoformat(run_state.started_at)
    until = datetime.now(timezone.utc)

    try:
        findings = sigma_pipeline.search_findings(config, monitor_id, since=since, until=until)
    except requests.RequestException as exc:
        print(f"Could not query findings: {exc}")
        return 1

    if findings:
        print(f"PASS -- {len(findings)} finding(s) for {args.technique_id} via {monitor_id}.")
        return 0

    print(f"FAIL -- no findings for {args.technique_id}. The monitor didn't fire (or hasn't run yet -- "
          "it's on a fixed schedule, not real-time).")
    return 1
