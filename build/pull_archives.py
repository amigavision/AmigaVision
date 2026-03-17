#!/usr/bin/env python3

import argparse
import json
import os
import shlex
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

MEGACMD_APP_BIN = "/Applications/MEGAcmd.app/Contents/MacOS"


def resolve_binary(binary_name):
    binary = shutil.which(binary_name)
    if binary:
        return binary
    app_bundle = Path("/Applications/MEGAcmd.app/Contents/MacOS") / binary_name
    if app_bundle.is_file():
        return str(app_bundle)
    return None


def validate_template_binary(spec):
    if not spec:
        return None
    parts = shlex.split(spec)
    if not parts:
        return None
    binary = resolve_binary(parts[0])
    if binary:
        return [binary, *parts[1:]]
    return None


def render_command(spec, **values):
    if not spec:
        return None
    quoted_values = {k: shlex.quote(v) for k, v in values.items()}
    parts = shlex.split(spec.format(**quoted_values))
    if not parts:
        return None
    binary = resolve_binary(parts[0])
    if binary:
        return [binary, *parts[1:]]
    return None


def run(cmd, capture_output=False):
    env = os.environ.copy()
    path_parts = env.get("PATH", "").split(os.pathsep) if env.get("PATH") else []
    if MEGACMD_APP_BIN not in path_parts:
        env["PATH"] = os.pathsep.join([MEGACMD_APP_BIN, *path_parts]) if path_parts else MEGACMD_APP_BIN
    return subprocess.run(
        cmd,
        check=True,
        text=True,
        capture_output=capture_output,
        env=env,
    )


def list_existing_basenames(titles_dir):
    basenames = set()
    for path in titles_dir.rglob("*.lha"):
        basenames.add(path.name)
    return basenames


def parse_remote_lha_paths(stdout):
    remote_paths = []
    for line in stdout.splitlines():
        candidate = line.strip()
        if not candidate or not candidate.lower().endswith(".lha"):
            continue
        if candidate not in remote_paths:
            remote_paths.append(candidate)
    return remote_paths


def parse_remote_lha_entries_long(stdout):
    entries = []
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) < 6:
            continue
        path = " ".join(parts[5:]).strip()
        if not path.lower().endswith(".lha"):
            continue
        try:
            mtime = datetime.strptime("{} {}".format(parts[3], parts[4]), "%d%b%Y %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        entries.append({"path": path, "mtime": mtime})
    return entries


def normalize_remote_path_for_get(remote_path):
    parts = Path(remote_path).parts
    if len(parts) >= 3 and parts[0] == "/":
        return str(Path("/", *parts[2:]))
    return remote_path


def load_state(state_path):
    if not state_path.is_file():
        return {"remote_paths": [], "updated_at": ""}
    with state_path.open("r") as f:
        return json.load(f)


def save_state(state_path, remote_paths):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("w") as f:
        json.dump(
            {
                "remote_paths": sorted(remote_paths),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            f,
            indent=2,
            sort_keys=True,
        )


def required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit("Missing required local env var: {}".format(name))
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--titles-dir", default="content/titles", help="Canonical titles directory")
    parser.add_argument("--dest", default="content/titles/manual-downloads", help="Download staging directory")
    parser.add_argument("--state-path", default="data/cache/archive-fetch-state.json", help="Local state file used to track seen remote archive paths")
    args = parser.parse_args()

    sync_cmd_template = os.getenv("ARCHIVE_FETCH_SYNC_CMD", "").strip()
    login_cmd_template = os.getenv("ARCHIVE_FETCH_LOGIN_CMD", "").strip()
    list_cmd_template = os.getenv("ARCHIVE_FETCH_LIST_CMD", "").strip()
    list_long_cmd_template = os.getenv("ARCHIVE_FETCH_LIST_LONG_CMD", "").strip()
    get_cmd_template = os.getenv("ARCHIVE_FETCH_GET_CMD", "").strip()
    logout_cmd_template = os.getenv("ARCHIVE_FETCH_LOGOUT_CMD", "").strip()
    cutoff_days = int(os.getenv("ARCHIVE_FETCH_CUTOFF_DAYS", "0") or "0")
    remote_ref = required_env("ARCHIVE_FETCH_REMOTE")

    if sync_cmd_template:
        missing = [name for name, cmd in (
            ("ARCHIVE_FETCH_SYNC_CMD", validate_template_binary(sync_cmd_template)),
        ) if not cmd]
    else:
        if not list_cmd_template:
            raise SystemExit("Missing required local env var: ARCHIVE_FETCH_LIST_CMD")
        if not get_cmd_template:
            raise SystemExit("Missing required local env var: ARCHIVE_FETCH_GET_CMD")
        missing = [name for name, cmd in (
            ("ARCHIVE_FETCH_LOGIN_CMD", validate_template_binary(login_cmd_template) if login_cmd_template else ["optional"]),
            ("ARCHIVE_FETCH_LIST_CMD", validate_template_binary(list_cmd_template)),
            ("ARCHIVE_FETCH_GET_CMD", validate_template_binary(get_cmd_template)),
            ("ARCHIVE_FETCH_LOGOUT_CMD", validate_template_binary(logout_cmd_template) if logout_cmd_template else ["optional"]),
        ) if not cmd]
    if missing:
        raise SystemExit(
            "Archive fetch tool(s) not found from local env config: {}".format(", ".join(missing))
        )

    titles_dir = Path(args.titles_dir).resolve()
    dest_dir = Path(args.dest).resolve()
    state_path = Path(args.state_path).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    existing_basenames = list_existing_basenames(titles_dir)

    if sync_cmd_template:
        print("Downloading archives to staging...")
        run(render_command(sync_cmd_template, remote=remote_ref, path="/", dest=str(dest_dir)))
        return 0

    logged_in = False
    try:
        if login_cmd_template:
            print("Connecting to archive source...")
            run(render_command(login_cmd_template, remote=remote_ref, path="", dest=str(dest_dir)))
            logged_in = True

        print("Listing remote .lha archives...")
        result = run(render_command(list_cmd_template, remote=remote_ref, path="/", dest=str(dest_dir)), capture_output=True)
        remote_paths = parse_remote_lha_paths(result.stdout)
        if not remote_paths:
            print("No remote .lha archives found")
            return 0

        state = load_state(state_path)
        known_remote_paths = set(state.get("remote_paths", []))
        if known_remote_paths:
            candidate_paths = [path for path in remote_paths if path not in known_remote_paths]
            print("Found {} unseen remote archive(s) since last successful pull".format(len(candidate_paths)))
        elif cutoff_days > 0:
            if not list_long_cmd_template:
                raise SystemExit("Missing required local env var: ARCHIVE_FETCH_LIST_LONG_CMD")
            print("Bootstrapping remote archive state using a {}-day cutoff...".format(cutoff_days))
            long_result = run(render_command(list_long_cmd_template, remote=remote_ref, path="/", dest=str(dest_dir)), capture_output=True)
            cutoff = datetime.now(timezone.utc) - timedelta(days=cutoff_days)
            long_entries = parse_remote_lha_entries_long(long_result.stdout)
            candidate_paths = [entry["path"] for entry in long_entries if entry["mtime"] >= cutoff]
            print("Found {} remote archive(s) newer than {}".format(len(candidate_paths), cutoff.date().isoformat()))
        else:
            raise SystemExit(
                "No archive fetch state found. Set ARCHIVE_FETCH_CUTOFF_DAYS for the first bootstrap run."
            )

        downloaded = 0
        skipped = 0
        skipped_basenames = []
        total = len(candidate_paths)
        for index, remote_path in enumerate(candidate_paths, start=1):
            basename = Path(remote_path).name
            if basename in existing_basenames:
                skipped += 1
                skipped_basenames.append(basename)
                continue
            print("Downloading [{}/{}] {}".format(index, total, basename), flush=True)
            get_path = normalize_remote_path_for_get(remote_path)
            run(render_command(get_cmd_template, remote=remote_ref, path=get_path, dest=str(dest_dir)))
            existing_basenames.add(basename)
            downloaded += 1

        save_state(state_path, remote_paths)
        print("Downloaded {} new archive(s); skipped {} existing archive(s)".format(downloaded, skipped))
        if skipped_basenames:
            print("Skipped existing archive basenames:")
            for basename in skipped_basenames:
                print(basename)
        return 0
    finally:
        if logged_in and logout_cmd_template:
            env = os.environ.copy()
            path_parts = env.get("PATH", "").split(os.pathsep) if env.get("PATH") else []
            if MEGACMD_APP_BIN not in path_parts:
                env["PATH"] = os.pathsep.join([MEGACMD_APP_BIN, *path_parts]) if path_parts else MEGACMD_APP_BIN
            subprocess.run(
                render_command(logout_cmd_template, remote=remote_ref, path="", dest=str(dest_dir)),
                check=False,
                env=env,
            )


if __name__ == "__main__":
    raise SystemExit(main())
