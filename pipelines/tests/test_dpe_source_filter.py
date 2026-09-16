"""Un DPE neuf n'entre dans aucune mesure — D9, ADR-021.

DS-07 (logements existants) et DS-13 (logements neufs) partagent `observation.energy_assessment`.
Un DPE neuf accompagne une livraison, il n'annonce pas une vente : le baromètre, les listes et les
rapports de qualité ne lisent que DS-07. Chaque lecture de la table dans ces scripts porte donc un
filtre de source ; le test le vérifie sur le texte, faute de banc PostgreSQL dans `make check`.

`dpe_matching_report.py` n'est pas dans la liste : il filtre chaque requête par une release
précise, déjà choisie par source.
"""

import re
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
MEASUREMENT_SCRIPTS = (
    "market_barometer.py",
    "market_listing_candidates.py",
    "exploratory_candidates.py",
    "market_data_quality_report.py",
)
READ = re.compile(r"(?:FROM|JOIN)\s*\"?\s*\"?\s*observation\.energy_assessment\b")
SOURCE_FILTER = "data_source_id = 'DS-07'"


@pytest.mark.parametrize("script", MEASUREMENT_SCRIPTS)
def test_chaque_lecture_des_dpe_filtre_la_source_ds07(script: str) -> None:
    source = (SCRIPTS / script).read_text(encoding="utf-8")
    reads = [match.start() for match in READ.finditer(source)]
    assert reads, f"{script} ne lit plus energy_assessment : retirer le script de la liste"
    for start in reads:
        # Le filtre suit la lecture dans la même requête, quelques lignes plus bas au plus.
        window = source[start : start + 600]
        statement_end = window.find('"""', 1)
        statement = window if statement_end < 0 else window[:statement_end]
        assert SOURCE_FILTER in statement, (
            f"{script} lit observation.energy_assessment sans filtrer DS-07 près de : "
            f"{source[start : start + 80]!r}"
        )
