"""Resolve the Windows setup from a local file or a successful main Actions build."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.error
import urllib.request
import zipfile

INSTALLER_NAME = "Install AmigaVision for Windows.exe"
REPOSITORY = "amigavision/AmigaVision"
ARTIFACT_NAME = "AmigaVision-Windows-Setup"
LOCAL_INSTALLER = Path("content/distro_emulators") / INSTALLER_NAME


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


class GitHub:
    def __init__(self):
        self.token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        self.gh = shutil.which("gh")
        if not self.token and not self.gh:
            raise RuntimeError(
                "Downloading the Windows installer needs GitHub authentication. "
                "Install GitHub CLI and run 'gh auth login', set GH_TOKEN with Actions read access, "
                "or supply WINDOWS_INSTALLER=/path/to/setup.exe to make emulators. "
                f"Alternatively place the installer at {LOCAL_INSTALLER}."
            )

    def request(self, endpoint):
        return urllib.request.Request(
            "https://api.github.com/" + endpoint,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "AmigaVision-packager",
                     "Authorization": "Bearer " + self.token},
        )

    def json(self, endpoint):
        if not self.token:
            result = subprocess.run([self.gh, "api", endpoint], check=True, capture_output=True)
            return json.loads(result.stdout)
        with urllib.request.urlopen(self.request(endpoint), timeout=60) as response:
            return json.load(response)

    def download(self, endpoint, destination):
        if not self.token:
            with destination.open("wb") as output:
                subprocess.run([self.gh, "api", endpoint], check=True, stdout=output, stderr=subprocess.PIPE)
            return
        # Do not forward the GitHub token to the signed artifact-storage URL.
        opener = urllib.request.build_opener(NoRedirect)
        try:
            response = opener.open(self.request(endpoint), timeout=60)
        except urllib.error.HTTPError as error:
            if error.code != 302:
                raise
            location = error.headers["Location"]
            if not location.startswith("https://"):
                raise RuntimeError("GitHub returned a non-HTTPS artifact download URL") from None
            response = urllib.request.urlopen(location, timeout=120)
        with response, destination.open("wb") as output:
            shutil.copyfileobj(response, output)


def validate_installer(path):
    path = Path(path).expanduser().resolve()
    with path.open("rb") as source:
        if source.read(2) != b"MZ":
            raise ValueError(f"Not a Windows executable: {path}")
    return path


def latest_artifact(client):
    # Skip expired artifacts, but never use PR builds or unsuccessful builds.
    endpoint = f"repos/{REPOSITORY}/actions/workflows/windows-installer.yml/runs"
    for page in range(1, 6):
        runs = client.json(endpoint + f"?branch=main&status=success&per_page=50&page={page}")["workflow_runs"]
        for run in runs:
            if run.get("head_branch") != "main" or run.get("conclusion") != "success":
                continue
            artifacts = client.json(f"repos/{REPOSITORY}/actions/runs/{run['id']}/artifacts?per_page=100")
            for artifact in artifacts["artifacts"]:
                if artifact["name"] == ARTIFACT_NAME and not artifact["expired"]:
                    return run, artifact
        if len(runs) < 50:
            break
    raise RuntimeError("No successful main Windows build with an unexpired installer artifact was found")


def resolve_windows_installer(explicit, download_dir, dry_run=False):
    if explicit:
        return validate_installer(explicit)
    if LOCAL_INSTALLER.is_file():
        return validate_installer(LOCAL_INSTALLER)
    destination = Path(download_dir) / INSTALLER_NAME
    if dry_run:
        print("[dry-run] Would download the latest successful main Windows installer", flush=True)
        return destination
    try:
        client = GitHub()
        run, artifact = latest_artifact(client)
        archive = Path(download_dir) / "windows-installer.zip"
        client.download(f"repos/{REPOSITORY}/actions/artifacts/{artifact['id']}/zip", archive)
        with zipfile.ZipFile(archive) as bundle:
            # Copy only the expected member; do not extract arbitrary paths from the ZIP.
            with bundle.open(INSTALLER_NAME) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)
        validate_installer(destination)
        print(f"Windows installer from successful main build: {run['html_url']}", flush=True)
        return destination
    except (urllib.error.URLError, subprocess.CalledProcessError, zipfile.BadZipFile, KeyError) as error:
        raise RuntimeError(
            "Could not download the Windows installer. Check 'gh auth login' or GH_TOKEN "
            "(Actions read access), or supply WINDOWS_INSTALLER=/path/to/setup.exe. "
            f"Failure: {type(error).__name__}"
        ) from None
