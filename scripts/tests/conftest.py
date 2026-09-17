"""Les scripts d'outillage n'ont pas d'extension : les charger par leur chemin."""

import importlib.machinery
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]


def load(name: str) -> ModuleType:
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), str(SCRIPTS / name))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    # `dataclass` retrouve son module par `sys.modules`.
    sys.modules[loader.name] = module
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


@pytest.fixture(scope="session")
def commit_ticket() -> ModuleType:
    return load("check-commit-ticket")


@pytest.fixture(scope="session")
def demo() -> ModuleType:
    return load("export-demo-subset")
