import gzip
from collections.abc import Iterator
from importlib import import_module
from pathlib import Path
from typing import Any, BinaryIO, cast

ijson = cast(Any, import_module("ijson"))


def _open_geojson(path: Path) -> BinaryIO:
    raw = path.open("rb")
    magic = raw.read(2)
    raw.seek(0)
    if magic == b"\x1f\x8b":
        return cast(BinaryIO, gzip.GzipFile(fileobj=raw, mode="rb"))
    return raw


def iter_features(path: Path) -> Iterator[dict[str, Any]]:
    with _open_geojson(path) as stream:
        for value in ijson.items(stream, "features.item", use_float=True):
            if not isinstance(value, dict):
                raise ValueError("GeoJSON features must be objects")
            yield cast(dict[str, Any], value)
