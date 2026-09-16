from dagster import Definitions

from immo_pipelines.assets import (
    cadastre_department_release,
    ds02_rnb_release,
    ds05_ban_release,
    foundation_diagnostic,
)

defs = Definitions(
    assets=[foundation_diagnostic, cadastre_department_release, ds02_rnb_release, ds05_ban_release]
)
