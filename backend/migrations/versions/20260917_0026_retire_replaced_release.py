"""BUG-08 : une release remplacée se retire sur décision explicite, tracée — ADR-022.

La purge de `rollback_unpublished_dataset_release` ne couvrait que le cadastre. Elle passe par une
fonction interne commune, qui retire toutes les lignes portées par la release : observations
spatiales et leurs liens, ventes, diagnostics, urbanisme, risques, routes, quarantaines, métriques,
contrôles, runs d'import. Restent les fichiers bruts et leur `raw_asset`, les identifiants de
source, les décisions d'appariement et l'historique de publication.

`retire_replaced_dataset_release` ajoute le geste qui manquait : retirer une release, publiée ou
non, une fois qu'une remplaçante de la même source est importée sur les mêmes territoires.
"""

from alembic import op

revision: str = "20260917_0026"
down_revision: str | None = "20260916_0025"
branch_labels: str | None = None
depends_on: str | None = None

# Les tables filles d'une release, dans l'ordre de suppression. Les enfants en cascade
# (transaction_property, urban_zone, urban_constraint, entity_observation_link,
# transformation_run) partent avec leur parent.
PURGED_TABLES: tuple[str, ...] = (
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

PURGE_FUNCTION = (
    """
CREATE FUNCTION meta.purge_dataset_release_rows(p_release_id text) RETURNS jsonb
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
        for table in PURGED_TABLES
    )
    + """
    RETURN removed;
END
$function$
"""
)

ROLLBACK_FUNCTION = """
CREATE OR REPLACE FUNCTION meta.rollback_unpublished_dataset_release(
    p_release_id text,
    p_actor text,
    p_reason text
) RETURNS void
LANGUAGE plpgsql
AS $function$
BEGIN
    IF EXISTS (SELECT 1 FROM meta.active_dataset_release WHERE release_id = p_release_id)
       OR EXISTS (SELECT 1 FROM meta.publication_event WHERE release_id = p_release_id) THEN
        RAISE EXCEPTION 'Release % has publication history and cannot be purged', p_release_id;
    END IF;

    PERFORM meta.purge_dataset_release_rows(p_release_id);
    UPDATE meta.dataset_release
       SET lifecycle_status = 'retired', acceptance_status = 'pending',
           notes = concat_ws(E'\\n', nullif(notes, ''),
               format('Rolled back by %s: %s', p_actor, p_reason))
     WHERE id = p_release_id;
END
$function$
"""

RETIRE_FUNCTION = """
CREATE FUNCTION meta.retire_replaced_dataset_release(
    p_release_id text,
    p_replacement_id text,
    p_actor text,
    p_reason text
) RETURNS jsonb
LANGUAGE plpgsql
AS $function$
DECLARE
    retired meta.dataset_release%ROWTYPE;
    replacement meta.dataset_release%ROWTYPE;
    uncovered text;
    removed jsonb;
BEGIN
    IF coalesce(length(trim(p_reason)), 0) < 3 OR coalesce(length(trim(p_actor)), 0) = 0 THEN
        RAISE EXCEPTION 'Retiring a release requires an actor and a written reason';
    END IF;

    SELECT * INTO retired FROM meta.dataset_release WHERE id = p_release_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Release % does not exist', p_release_id;
    END IF;
    IF retired.lifecycle_status = 'retired' THEN
        RAISE EXCEPTION 'Release % is already retired', p_release_id;
    END IF;

    SELECT * INTO replacement FROM meta.dataset_release WHERE id = p_replacement_id;
    IF NOT FOUND OR p_replacement_id = p_release_id THEN
        RAISE EXCEPTION 'Replacement % is not a distinct existing release', p_replacement_id;
    END IF;
    IF replacement.data_source_id <> retired.data_source_id THEN
        RAISE EXCEPTION 'Replacement % belongs to %, not to %',
            p_replacement_id, replacement.data_source_id, retired.data_source_id;
    END IF;
    IF replacement.lifecycle_status = 'retired' THEN
        RAISE EXCEPTION 'Replacement % is itself retired', p_replacement_id;
    END IF;

    IF EXISTS (SELECT 1 FROM meta.active_dataset_release WHERE release_id = p_release_id) THEN
        RAISE EXCEPTION 'Release % is active and cannot be retired', p_release_id;
    END IF;
    IF EXISTS (SELECT 1 FROM meta.regional_release_member WHERE release_id = p_release_id) THEN
        RAISE EXCEPTION 'Release % belongs to a regional bundle and cannot be retired',
            p_release_id;
    END IF;

    -- Chaque territoire importé par la release retirée doit l'être aussi par sa remplaçante :
    -- sans cela, le retrait laisserait un territoire sans donnée.
    SELECT string_agg(DISTINCT run.territory_code, ', ') INTO uncovered
      FROM meta.import_run AS run
     WHERE run.release_id = p_release_id AND run.status = 'succeeded'
       AND NOT EXISTS (
           SELECT 1 FROM meta.import_run AS other
            WHERE other.release_id = p_replacement_id AND other.status = 'succeeded'
              AND other.territory_type = run.territory_type
              AND other.territory_code = run.territory_code);
    IF uncovered IS NOT NULL THEN
        RAISE EXCEPTION 'Replacement % is not imported on: %', p_replacement_id, uncovered;
    END IF;

    removed := meta.purge_dataset_release_rows(p_release_id);
    UPDATE meta.dataset_release
       SET lifecycle_status = 'retired',
           notes = concat_ws(E'\\n', nullif(notes, ''),
               format('Retired on %s by %s, replaced by %s: %s',
                      now()::date, p_actor, p_replacement_id, p_reason))
     WHERE id = p_release_id;
    RETURN removed;
END
$function$
"""


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(PURGE_FUNCTION)
    op.execute("REVOKE ALL ON FUNCTION meta.purge_dataset_release_rows(text) FROM PUBLIC")
    op.execute(ROLLBACK_FUNCTION)
    op.execute(RETIRE_FUNCTION)
    op.execute(
        "REVOKE ALL ON FUNCTION meta.retire_replaced_dataset_release(text,text,text,text) "
        "FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION meta.retire_replaced_dataset_release(text,text,text,text) "
        "TO pipeline_rw"
    )
    # Les deux gestes s'exécutent avec les droits de l'appelant : `pipeline_rw` doit pouvoir
    # exécuter la purge. L'appeler seule est possible mais ne laisse aucune trace ; l'outillage
    # (`DatasetCatalog`) ne l'expose pas.
    op.execute("GRANT EXECUTE ON FUNCTION meta.purge_dataset_release_rows(text) TO pipeline_rw")
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute("DROP FUNCTION IF EXISTS meta.retire_replaced_dataset_release(text,text,text,text)")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION meta.rollback_unpublished_dataset_release(
            p_release_id text, p_actor text, p_reason text
        ) RETURNS void
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            IF EXISTS (SELECT 1 FROM meta.active_dataset_release WHERE release_id = p_release_id)
               OR EXISTS (SELECT 1 FROM meta.publication_event WHERE release_id = p_release_id) THEN
                RAISE EXCEPTION 'Release % has publication history and cannot be purged', p_release_id;
            END IF;
            DELETE FROM reference.cadastral_parcel WHERE release_id = p_release_id;
            DELETE FROM reference.cadastral_building WHERE release_id = p_release_id;
            DELETE FROM reference.administrative_area WHERE release_id = p_release_id;
            DELETE FROM meta.data_quality_check WHERE release_id = p_release_id;
            DELETE FROM meta.import_run WHERE release_id = p_release_id;
            UPDATE meta.dataset_release
               SET lifecycle_status = 'retired', acceptance_status = 'pending',
                   notes = concat_ws(E'\\n', nullif(notes, ''),
                       format('Rolled back by %s: %s', p_actor, p_reason))
             WHERE id = p_release_id;
        END
        $function$
        """
    )
    op.execute("DROP FUNCTION IF EXISTS meta.purge_dataset_release_rows(text)")
    op.execute("RESET ROLE")
