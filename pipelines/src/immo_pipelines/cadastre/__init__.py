"""DS-01 Cadastre ingestion primitives."""

from immo_pipelines.cadastre.contract import DatasetContract, load_contract
from immo_pipelines.cadastre.processor import CadastreFeatureProcessor

__all__ = ["CadastreFeatureProcessor", "DatasetContract", "load_contract"]
