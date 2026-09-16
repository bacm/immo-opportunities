"""Journal d'accès : gabarit de route et exceptions corrélées par `request_id` — G7."""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from immo.main import create_app


def completed(caplog: pytest.LogCaptureFixture) -> str:
    lines = [r.getMessage() for r in caplog.records if r.name == "immo.access"]
    return next(line for line in lines if line.startswith("request_completed"))


def test_le_journal_porte_le_gabarit_de_route_et_non_l_identifiant(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="immo.access")
    client.get("/api/v1/energy-assessments/pas-un-numero", headers={"X-Request-ID": "g7-route"})
    line = completed(caplog)
    assert "request_id=g7-route" in line
    assert "route=/api/v1/energy-assessments/{dpe_number} " in line


def test_une_route_inconnue_reste_une_seule_etiquette(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="immo.access")
    client.get("/api/v1/nulle-part/35024000AP0001")
    assert "route=unmatched " in completed(caplog)


def test_une_exception_est_journalisee_avec_son_request_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="immo.access")
    client = TestClient(create_app(), raise_server_exceptions=False)
    with patch("immo.api.routes.health.check_database", side_effect=RuntimeError("boom")):
        response = client.get("/health/ready", headers={"X-Request-ID": "g7-crash"})
    assert response.status_code == 500
    failures = [r for r in caplog.records if r.getMessage().startswith("request_failed")]
    assert len(failures) == 1
    assert "request_id=g7-crash" in failures[0].getMessage()
    assert "route=/health/ready" in failures[0].getMessage()
    assert failures[0].exc_info is not None


def test_le_journal_immo_a_un_handler_unique_au_niveau_info() -> None:
    create_app()
    create_app()
    logger = logging.getLogger("immo")
    assert logger.level == logging.INFO
    assert sum(getattr(h, "immo_handler", False) for h in logger.handlers) == 1


def test_uvicorn_n_ecrit_plus_la_chaine_de_requete() -> None:
    dockerfile = Path(__file__).parents[2] / "docker" / "api" / "Dockerfile"
    assert '"--no-access-log"' in dockerfile.read_text(encoding="utf-8")
