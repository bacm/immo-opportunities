"""Les scripts d'outillage n'ont pas d'extension : les charger par leur chemin."""

import importlib.machinery
import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]


def load(name: str) -> ModuleType:
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), str(SCRIPTS / name))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def backlog_status() -> ModuleType:
    return load("backlog-status")


@pytest.fixture(scope="session")
def diff_invariants() -> ModuleType:
    return load("check-diff-invariants")


@pytest.fixture(scope="session")
def ticket_dod() -> ModuleType:
    return load("check-ticket-dod")


@pytest.fixture(scope="session")
def doc_budget() -> ModuleType:
    return load("check-doc-budget")
