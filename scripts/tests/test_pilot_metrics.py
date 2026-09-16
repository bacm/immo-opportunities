"""Métriques de fraîcheur et d'import par source et territoire — G7."""

import os
import stat
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "export-pilot-metrics"
ROWS = "\n".join(
    [
        "failure|1789500000|DS-08|department|35",
        "import|1789400000|||",
        "publication|1789300000|DS-01||",
        "published|1781481600|DS-06|department|35",
        "source|0|DS-08|department|35",
        "source|1789400000|DS-06|department|35",
    ]
)


def run(tmp_path: Path) -> tuple[str, list[str]]:
    """Exécute le script avec un faux `docker` qui rend des lignes figées et note ses arguments."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls"
    fake = bin_dir / "docker"
    fake.write_text(f'#!/bin/sh\necho "$@" >> {calls}\ncat <<"ROWS"\n{ROWS}\nROWS\n')
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "RUNTIME_DATA_PATH": str(tmp_path / "runtime"),
        "IMMO_PROJECT_DIR": "/projet",
        "IMMO_ENV_FILE": "/projet/.env.example",
        "IMMO_COMPOSE_FILES": "compose.yaml compose.dev.yaml",
    }
    subprocess.run([str(SCRIPT)], env=env, check=True)
    output = (tmp_path / "runtime" / "metrics" / "pilot.prom").read_text(encoding="utf-8")
    return output, calls.read_text(encoding="utf-8").splitlines()


def test_la_fraicheur_et_les_echecs_sont_par_source_et_territoire(tmp_path: Path) -> None:
    output, _ = run(tmp_path)
    labels = 'dataset="DS-08",territory_type="department",territory="35"'
    assert f"immo_source_last_import_success_timestamp_seconds{{{labels}}} 0" in output
    assert f"immo_source_last_import_failure_timestamp_seconds{{{labels}}} 1789500000" in output
    assert "immo_import_last_success_timestamp_seconds 1789400000" in output
    assert 'immo_source_last_publication_timestamp_seconds{dataset="DS-01"} 1789300000' in output
    assert (
        'immo_source_release_published_timestamp_seconds{dataset="DS-06",'
        'territory_type="department",territory="35"} 1781481600' in output
    )


def test_aucun_motif_d_echec_n_est_une_etiquette(tmp_path: Path) -> None:
    output, _ = run(tmp_path)
    assert "error" not in output
    assert "error_message" not in SCRIPT.read_text(encoding="utf-8").split("psql", 1)[1]


def test_les_fichiers_compose_du_poste_sont_ceux_passes(tmp_path: Path) -> None:
    _, calls = run(tmp_path)
    assert calls[0].startswith(
        "compose --project-directory /projet --env-file /projet/.env.example "
        "-f /projet/compose.yaml -f /projet/compose.dev.yaml exec"
    )
