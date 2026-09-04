from dagster import Definitions

from immo_pipelines.assets import foundation_diagnostic
from immo_pipelines.assets.cadastre import cadastre_department_release

defs = Definitions(assets=[foundation_diagnostic, cadastre_department_release])
