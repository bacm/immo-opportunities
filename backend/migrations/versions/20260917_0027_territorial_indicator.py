"""D7 : les variables communales de l'INSEE, DS-14 à DS-16 — ADR-023.

Une population, un nombre d'équipements, l'aire d'attraction d'une commune sont des observations
publiées par un producteur, à la maille communale. Aucune table ne pouvait les porter :
`feature.feature_value` n'admet qu'une unité foncière ou un bâtiment, et `market.market_metric`
suppose une aire de marché déjà définie. D'où `observation.territorial_indicator`, une ligne par
release, commune et indicateur.

La valeur est numérique, textuelle ou absente avec un motif du vocabulaire de `SPEC.md` §13.7 :
jamais deux à la fois, jamais rien. Une valeur dérivée — la distance au pôle — cite les releases
lues dans `source_release_ids`.

La table entre dans la purge d'ADR-022 : sans cela, retirer une release DS-14 laisserait ses
lignes, et la clé étrangère refuserait le retrait.
"""

from alembic import op

revision: str = "20260917_0027"
down_revision: str | None = "20260917_0026"
branch_labels: str | None = None
depends_on: str | None = None

# Les tables purgées par 20260917_0026, dans leur ordre.
PREVIOUS_PURGED_TABLES: tuple[str, ...] = (
    "observation.transaction",
    "observation.energy_assessment",
    "observation.urban_document",
    "observation.risk_observation",
    "observation.road_segment",
    "meta.entity_source_observation",
    "meta.attribute_quarantine",
    "meta.geometry_quarantine",
    "meta.dataset_coverage_metric",
    "meta.entity_match_metric",
    "meta.data_quality_check",
    "reference.cadastral_parcel",
    "reference.cadastral_building",
    "reference.administrative_area",
    "meta.import_run",
)

PURGED_TABLES: tuple[str, ...] = (
    *PREVIOUS_PURGED_TABLES[:5],
    "observation.territorial_indicator",
    *PREVIOUS_PURGED_TABLES[5:],
)

MISSING_REASONS: tuple[str, ...] = (
    "source_value_missing",
    "source_not_accepted",
    "not_applicable",
    "ambiguous_match",
    "support_insufficient",
    "cohort_not_covered",
)

DATA_SOURCES = """
INSERT INTO meta.data_source (
    id, name, producer, homepage_url, licence_spdx,
    licence_name, attribution, usage_notes
) VALUES
    ('DS-14', 'Recensement de la population : populations de référence et logements', 'INSEE',
     'https://www.insee.fr/fr/metadonnees/source/serie/s1321', 'etalab-2.0',
     'Licence Ouverte 2.0', 'Insee, recensement de la population',
     'Agrégats communaux ; variables de segmentation, hors baromètre ; logements vacants '
     'exclus (SPEC §12) — ADR-023.'),
    ('DS-15', 'Base permanente des équipements', 'INSEE',
     'https://www.insee.fr/fr/metadonnees/source/serie/s1161', 'etalab-2.0',
     'Licence Ouverte 2.0', 'Insee, base permanente des équipements',
     'Dénombrement communal par domaine et sous-domaine ; zéro = aucun équipement recensé '
     '— ADR-023.'),
    ('DS-16', 'Zonage en aires d''attraction des villes 2020', 'INSEE',
     'https://www.insee.fr/fr/information/4803954', 'etalab-2.0',
     'Licence Ouverte 2.0', 'Insee, zonage en aires d''attraction des villes 2020',
     'Le pôle d''une commune est la commune-centre de son aire ; aucun seuil — ADR-023.')
ON CONFLICT (id) DO NOTHING
"""


def purge_function(tables: tuple[str, ...]) -> str:
    return (
        """
CREATE OR REPLACE FUNCTION meta.purge_dataset_release_rows(p_release_id text) RETURNS jsonb
LANGUAGE plpgsql
AS $function$
DECLARE
    removed jsonb := '{}'::jsonb;
    affected bigint;
BEGIN
"""
        + "".join(
            f"""
    DELETE FROM {table} WHERE release_id = p_release_id;
    GET DIAGNOSTICS affected = ROW_COUNT;
    removed := removed || jsonb_build_object('{table}', affected);
"""
            for table in tables
        )
        + """
    RETURN removed;
END
$function$
"""
    )


PURGE_FUNCTION = purge_function(PURGED_TABLES)

TABLE = f"""
CREATE TABLE observation.territorial_indicator (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    release_id text NOT NULL REFERENCES meta.dataset_release(id) ON DELETE RESTRICT,
    raw_asset_id bigint REFERENCES meta.raw_asset(id) ON DELETE RESTRICT,
    department_code text NOT NULL,
    commune_code text NOT NULL CHECK (commune_code ~ '^[0-9][0-9AB][0-9]{{3}}$'),
    indicator_code text NOT NULL CHECK (indicator_code ~ '^[a-z][a-z0-9_]*$'),
    -- Période de la donnée (« 2023 » pour un recensement) et millésime du code officiel
    -- géographique dans lequel la commune est exprimée : une fusion de communes les sépare.
    reference_period text NOT NULL,
    geography_vintage smallint NOT NULL CHECK (geography_vintage BETWEEN 2000 AND 2100),
    numeric_value numeric,
    text_value text,
    missing_reason text CHECK (missing_reason IN ({", ".join(f"'{r}'" for r in MISSING_REASONS)})),
    unit text,
    source_release_ids jsonb NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(source_release_ids) = 'array'),
    formula text,
    transformation_version text NOT NULL,
    imported_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT territorial_indicator_identity UNIQUE (release_id, commune_code, indicator_code),
    CONSTRAINT territorial_indicator_one_value CHECK (
        num_nonnulls(numeric_value, text_value, missing_reason) = 1
    )
)
"""


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(DATA_SOURCES)
    op.execute(TABLE)
    op.execute(
        "CREATE INDEX territorial_indicator_commune ON observation.territorial_indicator "
        "(commune_code, indicator_code)"
    )
    op.execute(PURGE_FUNCTION)
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(purge_function(PREVIOUS_PURGED_TABLES))
    op.execute("DROP TABLE IF EXISTS observation.territorial_indicator")
    op.execute("DELETE FROM meta.data_source WHERE id IN ('DS-14', 'DS-15', 'DS-16')")
    op.execute("RESET ROLE")
