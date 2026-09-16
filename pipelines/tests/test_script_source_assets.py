"""DVF, DPE, GPU, Géorisques et INSEE dans le graphe d'assets — BUG-20."""

import subprocess
from pathlib import Path
from typing import Any

import pytest
from dagster import AssetKey, DagsterInstance, MultiPartitionKey, materialize

from immo_pipelines.assets import script_sources
from immo_pipelines.assets.script_sources import SCRIPT_ASSETS, SOURCES
from immo_pipelines.definitions import defs

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def by_name(name: str) -> script_sources.ScriptSource:
    return next(source for source in SOURCES if source.name == name)


def test_chaque_source_restante_a_son_asset_et_son_script() -> None:
    assert {source.data_source_id for source in SOURCES} == {
        "DS-06",
        "DS-07",
        "DS-08",
        "DS-09",
        "DS-13",
        "DS-14",
        "DS-15",
        "DS-16",
    }
    assert defs.assets is not None
    keys = {key for definition in defs.assets for key in definition.keys}  # type: ignore[union-attr]
    for source in SOURCES:
        assert AssetKey(source.name) in keys
        assert (SCRIPTS / source.script).is_file()


def test_les_commandes_suivent_la_ligne_de_commande_des_scripts() -> None:
    dpe = by_name("ds13_dpe_new_release").command("2026-09-16-extract", "35")
    assert dpe[2:] == ["2026-09-16-extract", "--department", "35", "--source", "DS-13"]
    census = by_name("ds14_census_release").command("rp-2023", "35")
    assert census[2:] == ["DS-14", "rp-2023", "--department", "35"]
    assert Path(census[1]).name == "import_territorial_release.py"
    dvf = by_name("ds06_dvf_release").command("2026-09-13", "35")
    assert dvf[2:] == ["2026-09-13", "--department", "35"]


def test_le_gpu_dit_qu_il_reprend_et_ne_reproduit_pas() -> None:
    assert "does not reproduce" in by_name("ds08_gpu_release").note


def test_les_partitions_sont_release_par_departement() -> None:
    for definition in SCRIPT_ASSETS:
        partitions = definition.partitions_def
        assert partitions is not None
        names = {d.name for d in partitions.partitions_defs}  # type: ignore[attr-defined]
        assert names == {"department", "release"}


def fake_script(tmp_path: Path, body: str) -> Path:
    root = tmp_path / "root"
    scripts = root / "pipelines" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "import_dvf_release.py").write_text(body, encoding="utf-8")
    return root


def run_dvf(monkeypatch: pytest.MonkeyPatch, root: Path) -> Any:
    monkeypatch.setattr(script_sources, "project_root", lambda: root)
    instance = DagsterInstance.ephemeral()
    instance.add_dynamic_partitions("ds06_dvf_releases", ["2026-09-13"])
    asset = next(a for a in SCRIPT_ASSETS if a.key == AssetKey("ds06_dvf_release"))
    return materialize(
        [asset],
        instance=instance,
        partition_key=MultiPartitionKey({"department": "35", "release": "2026-09-13"}),
        raise_on_error=False,
    )


def test_la_sortie_du_script_devient_la_metadonnee(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fake_script(tmp_path, "import sys\nprint('arguments', *sys.argv[1:])\n")
    result = run_dvf(monkeypatch, root)
    assert result.success
    materialization = result.asset_materializations_for_node("ds06_dvf_release")[0]
    tail = materialization.metadata["output_tail"].value
    assert tail == "arguments 2026-09-13 --department 35"


def test_un_script_en_echec_fait_echouer_la_materialisation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fake_script(tmp_path, "import sys\nprint('checksum divergent')\nsys.exit(3)\n")
    result = run_dvf(monkeypatch, root)
    assert not result.success
    assert result.asset_materializations_for_node("ds06_dvf_release") == []


def test_le_script_tourne_depuis_la_racine_du_projet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, Any] = {}
    real = subprocess.Popen

    def spy(*args: Any, **kwargs: Any) -> Any:
        seen["cwd"] = kwargs["cwd"]
        return real(*args, **kwargs)

    root = fake_script(tmp_path, "print('ok')\n")
    monkeypatch.setattr(script_sources.subprocess, "Popen", spy)
    assert run_dvf(monkeypatch, root).success
    assert seen["cwd"] == root
