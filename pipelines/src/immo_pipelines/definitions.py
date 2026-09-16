from dagster import Definitions

from immo_pipelines.assets import (
    cadastre_department_release,
    ds02_rnb_release,
    ds03_bdnb_release,
    ds04_bdtopo_release,
    ds05_ban_release,
    foundation_diagnostic,
)
from immo_pipelines.assets.script_sources import SCRIPT_ASSETS

defs = Definitions(
    assets=[
        foundation_diagnostic,
        cadastre_department_release,
        ds02_rnb_release,
        ds03_bdnb_release,
        ds04_bdtopo_release,
        ds05_ban_release,
        *SCRIPT_ASSETS,
    ]
)
