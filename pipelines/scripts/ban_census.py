import argparse
import json
from pathlib import Path
from typing import Any, cast

from immo_pipelines.cadastre.contract import sha256_file
from immo_pipelines.spatial.ban import census_ban_archive


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Count one BAN department archive without importing it"
    )
    parser.add_argument("release")
    parser.add_argument("--department", choices=("22", "29", "35", "56"), required=True)
    parser.add_argument(
        "--archive", type=Path, required=True, help="Local copy of the pinned BAN archive"
    )
    arguments = parser.parse_args()
    manifest_path = (
        project_root()
        / "contracts"
        / "datasets"
        / "DS-05"
        / "releases"
        / f"{arguments.release}-{arguments.department}.json"
    )
    manifest = cast(dict[str, Any], json.loads(manifest_path.read_text(encoding="utf-8")))
    asset = cast(dict[str, Any], cast(list[object], manifest["assets"])[0])
    expected_sha = str(asset["sha256"])
    # Un décompte cité dans un rapport n'a de valeur que s'il porte sur l'archive épinglée :
    # on refuse plutôt que de produire des chiffres invérifiables.
    actual_sha = sha256_file(arguments.archive)
    if actual_sha != expected_sha:
        parser.error(
            f"Archive checksum mismatch: manifest pins {expected_sha}, file is {actual_sha}"
        )
    census = census_ban_archive(arguments.archive)
    print(
        json.dumps(
            {
                "release_key": str(manifest["release_key"]),
                "department": arguments.department,
                "sha256": actual_sha,
                **census.summary(),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
