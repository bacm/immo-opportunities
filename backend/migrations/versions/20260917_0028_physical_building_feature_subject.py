"""BUG-13 : une feature de bâtiment porte sur le bâtiment physique — ADR-024.

`feature.feature_value.building_id` référence les enregistrements RNB, sujet que BUG-12 a
invalidé. La table gagne une troisième colonne de sujet, `physical_building_id`. L'exclusion reste
stricte, l'identité unique l'inclut, et les familles `BLD-*` et `REN-*` ne peuvent plus s'écrire
sur un enregistrement.

`downgrade` supprime les lignes portées par un bâtiment physique, puis la colonne, et rétablit
les contraintes précédentes : les features d'unité foncière ne bougent pas.
"""

from alembic import op

revision: str = "20260917_0028"
down_revision: str | None = "20260917_0027"
branch_labels: str | None = None
depends_on: str | None = None

SUBJECT_COLUMNS: tuple[str, ...] = ("property_unit_id", "building_id", "physical_building_id")
BUILDING_FAMILIES_PATTERN = "^(BLD|REN)-"


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        """
        ALTER TABLE feature.feature_value
            ADD COLUMN physical_building_id text
                REFERENCES reference.physical_building(id) ON DELETE CASCADE
        """
    )
    op.execute("ALTER TABLE feature.feature_value DROP CONSTRAINT feature_value_subject")
    op.execute(
        f"""
        ALTER TABLE feature.feature_value ADD CONSTRAINT feature_value_subject
            CHECK (num_nonnulls({", ".join(SUBJECT_COLUMNS)}) = 1)
        """
    )
    op.execute("ALTER TABLE feature.feature_value DROP CONSTRAINT feature_value_identity")
    op.execute(
        f"""
        ALTER TABLE feature.feature_value ADD CONSTRAINT feature_value_identity
            UNIQUE NULLS NOT DISTINCT ({", ".join(SUBJECT_COLUMNS)}, feature_code, feature_version)
        """
    )
    op.execute(
        f"""
        ALTER TABLE feature.feature_value ADD CONSTRAINT feature_value_building_family_subject
            CHECK (building_id IS NULL OR feature_code !~ '{BUILDING_FAMILIES_PATTERN}')
        """
    )
    op.execute(
        """
        CREATE INDEX feature_value_physical_building
            ON feature.feature_value (physical_building_id)
         WHERE physical_building_id IS NOT NULL
        """
    )
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute("DELETE FROM feature.feature_value WHERE physical_building_id IS NOT NULL")
    op.execute("DROP INDEX IF EXISTS feature.feature_value_physical_building")
    op.execute(
        "ALTER TABLE feature.feature_value DROP CONSTRAINT feature_value_building_family_subject"
    )
    op.execute("ALTER TABLE feature.feature_value DROP CONSTRAINT feature_value_identity")
    op.execute("ALTER TABLE feature.feature_value DROP CONSTRAINT feature_value_subject")
    op.execute("ALTER TABLE feature.feature_value DROP COLUMN physical_building_id")
    op.execute(
        """
        ALTER TABLE feature.feature_value ADD CONSTRAINT feature_value_subject
            CHECK (num_nonnulls(property_unit_id, building_id) = 1)
        """
    )
    op.execute(
        """
        ALTER TABLE feature.feature_value ADD CONSTRAINT feature_value_identity
            UNIQUE NULLS NOT DISTINCT (property_unit_id, building_id, feature_code, feature_version)
        """
    )
    op.execute("RESET ROLE")
