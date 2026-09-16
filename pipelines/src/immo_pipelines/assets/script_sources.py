"""DVF, DPE, GPU, Géorisques et INSEE dans le graphe d'assets — BUG-20.

Chaque asset exécute le script d'import de sa source, avec les arguments de sa partition
release x département. Les scripts gardent leur idempotence, leur purge de version et leur
reprise : les appeler, plutôt que les réécrire, laisse intact ce qui a été éprouvé sur la base
réelle. Un code de sortie non nul fait échouer la matérialisation.
"""

import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from dagster import (
    AssetExecutionContext,
    AssetsDefinition,
    DynamicPartitionsDefinition,
    Failure,
    MaterializeResult,
    MetadataValue,
    MultiPartitionsDefinition,
    asset,
)

from immo_pipelines.assets.cadastre import cadastre_department_partitions
from immo_pipelines.assets.spatial_sources import partition_keys
from immo_pipelines.cadastre.manifest import project_root

# Les dernieres lignes de sortie, gardees en metadonnee : le resume que le script imprime.
OUTPUT_TAIL = 20


@dataclass(frozen=True, slots=True)
class ScriptSource:
    name: str
    data_source_id: str
    script: str
    # Arguments places avant la release (la source, pour INSEE).
    leading: Sequence[str] = ()
    # Arguments places apres le departement (la famille DPE).
    trailing: Sequence[str] = ()
    note: str = "pending explicit acceptance"

    def command(self, release_key: str, department_code: str) -> list[str]:
        script = project_root() / "pipelines" / "scripts" / self.script
        return [
            sys.executable,
            str(script),
            *self.leading,
            release_key,
            "--department",
            department_code,
            *self.trailing,
        ]


SOURCES: tuple[ScriptSource, ...] = (
    ScriptSource("ds06_dvf_release", "DS-06", "import_dvf_release.py"),
    ScriptSource(
        "ds07_dpe_release", "DS-07", "import_dpe_release.py", trailing=("--source", "DS-07")
    ),
    ScriptSource(
        "ds13_dpe_new_release", "DS-13", "import_dpe_release.py", trailing=("--source", "DS-13")
    ),
    ScriptSource(
        "ds08_gpu_release",
        "DS-08",
        "import_gpu_release.py",
        note=(
            "no checksum and no archive at the source: a rematerialization resumes the batch "
            "from the database, it does not reproduce a state"
        ),
    ),
    # Une release Georisques est une famille : `<famille>--<date>`.
    ScriptSource("ds09_georisques_release", "DS-09", "import_georisques_release.py"),
    ScriptSource(
        "ds14_census_release", "DS-14", "import_territorial_release.py", leading=("DS-14",)
    ),
    ScriptSource(
        "ds15_equipment_release", "DS-15", "import_territorial_release.py", leading=("DS-15",)
    ),
    ScriptSource(
        "ds16_attraction_release", "DS-16", "import_territorial_release.py", leading=("DS-16",)
    ),
)


def run_script(source: ScriptSource, context: AssetExecutionContext) -> MaterializeResult[Any]:
    release_key, department_code = partition_keys(context)
    command = source.command(release_key, department_code)
    context.log.info("Running %s", " ".join(command[1:]))
    tail: list[str] = []
    with subprocess.Popen(
        command,
        cwd=project_root(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    ) as process:
        assert process.stdout is not None
        for line in process.stdout:
            text = line.rstrip()
            context.log.info(text)
            tail = [*tail[-(OUTPUT_TAIL - 1) :], text]
        returncode = process.wait()
    if returncode != 0:
        raise Failure(
            description=f"{source.script} exited with {returncode}",
            metadata={"output_tail": MetadataValue.text("\n".join(tail))},
        )
    return MaterializeResult(
        metadata={
            "data_source_id": source.data_source_id,
            "release_key": release_key,
            "department": department_code,
            "script": source.script,
            "output_tail": MetadataValue.text("\n".join(tail)),
            "publication": source.note,
        }
    )


def script_release_asset(source: ScriptSource) -> AssetsDefinition:
    @asset(
        name=source.name,
        group_name="script_sources",
        partitions_def=MultiPartitionsDefinition(
            {
                "department": cadastre_department_partitions,
                "release": DynamicPartitionsDefinition(name=f"{source.name}s"),
            }
        ),
        description=(
            f"Import one {source.data_source_id} release x department partition with "
            f"pipelines/scripts/{source.script}."
        ),
    )
    def _asset(context: AssetExecutionContext) -> MaterializeResult[Any]:
        return run_script(source, context)

    return _asset


SCRIPT_ASSETS: tuple[AssetsDefinition, ...] = tuple(script_release_asset(s) for s in SOURCES)
