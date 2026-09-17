"""La démo ne se met à jour que sur une base restaurée, et à la main seulement — A14."""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]

# `docker` et `curl` factices : chaque appel est journalisé ; `psql` répond FAKE_META.
FAKE_DOCKER = """#!/usr/bin/env bash
echo "docker $*" >> "$CALLS"
case "$*" in
  *psql*) echo "$FAKE_META" ;;
  *"port caddy"*) echo 127.0.0.1:8090 ;;
esac
"""
FAKE_CURL = """#!/usr/bin/env bash
echo "curl $*" >> "$CALLS"
echo ok
"""


def git(clone: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(clone), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    """Un clone minimal du dépôt, son propre `origin`, avec le script à la tête."""
    clone = tmp_path / "clone"
    (clone / "scripts").mkdir(parents=True)
    shutil.copy(ROOT / "scripts" / "deploy-demo", clone / "scripts" / "deploy-demo")
    (clone / "compose.yaml").write_text("services: {}\n")
    git(clone, "init", "--quiet")
    git(clone, "add", ".")
    git(
        clone,
        "-c",
        "user.name=test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "--quiet",
        "-m",
        "init",
    )
    git(clone, "remote", "add", "origin", str(clone))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("docker", FAKE_DOCKER), ("curl", FAKE_CURL)):
        (bin_dir / name).write_text(body)
        (bin_dir / name).chmod(stat.S_IRWXU)
    return clone


def deploy(clone: Path, meta: str) -> tuple[subprocess.CompletedProcess, list[str]]:
    calls = clone.parent / "calls"
    calls.touch()
    env = {
        **os.environ,
        "PATH": f"{clone.parent / 'bin'}{os.pathsep}{os.environ['PATH']}",
        "CALLS": str(calls),
        "FAKE_META": meta,
    }
    env.pop("DEPLOY_DEMO_CHECKED_OUT", None)
    result = subprocess.run(
        [str(clone / "scripts" / "deploy-demo"), git(clone, "rev-parse", "HEAD")],
        env=env,
        capture_output=True,
        text=True,
    )
    return result, calls.read_text().splitlines()


def test_an_unrestored_database_is_never_migrated(clone: Path) -> None:
    result, calls = deploy(clone, meta="f")
    assert result.returncode == 1
    assert "pas restaurée" in result.stderr
    assert not [call for call in calls if "--build" in call]


def test_a_modified_clone_is_refused_before_docker(clone: Path) -> None:
    (clone / "compose.yaml").write_text("services: {changed: {}}\n")
    result, calls = deploy(clone, meta="t")
    assert result.returncode == 1
    assert "modifications suivies" in result.stderr
    assert calls == []


def test_a_restored_database_is_rebuilt_on_the_deployed_commit(clone: Path) -> None:
    result, calls = deploy(clone, meta="t")
    assert result.returncode == 0, result.stderr
    # Détaché sur le commit déployé.
    assert git(clone, "rev-parse", "--abbrev-ref", "HEAD") == "HEAD"
    assert any("up -d --build" in call for call in calls)
    assert calls[-1] == (
        "curl --fail --silent --show-error --retry 24 --retry-delay 5 --retry-all-errors "
        "http://127.0.0.1:8090/health"
    )


def test_the_demo_workflow_only_runs_by_hand() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/deploy-demo.yml").read_text())
    # PyYAML lit la clé `on` comme le booléen True.
    assert workflow[True] == {"workflow_dispatch": None}
