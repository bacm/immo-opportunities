"""BUG-12 : regrouper les enregistrements contigus en bâtiments physiques.

Les contrats `LAND-002` et `LAND-009` demandent des bâtiments **physiques**, **dédupliqués**.
Rien ne l'implémentait : un bâtiment découpé en plusieurs enregistrements source comptait pour
plusieurs, et le comptage naïf surestime de 44 % sur le 35 — 741 379 enregistrements RNB pour
514 859 bâtiments réels.

Le regroupement se fait par **contiguïté**, et ce choix est validé par recoupement : le cadastre,
levé indépendant, donne 517 615 bâtiments pour 865 335 enregistrements. Deux sources qui diffèrent
de 17 % en enregistrements convergent à **0,5 %** en bâtiments. Le fractionnement est donc une
convention d'enregistrement, pas une réalité du terrain.

Ce n'est pas une généralité sur la contiguïté : appliquée au parcellaire (BUG-11), elle produit
des grappes de 3 494 parcelles et un non-sens. Le bâti a des discontinuités naturelles, le
parcellaire non.

**Les enregistrements source ne sont pas touchés.** Le regroupement est une entité de plus, avec
ses membres ; chaque identifiant source reste atteignable, et la donnée d'origine reste telle
qu'elle a été importée.

L'identifiant du groupe est dérivé du plus petit identifiant de ses membres — déterministe,
reproductible d'une reconstruction à l'autre tant que la composition ne change pas, et sans
séquence à gérer.
"""

from alembic import op

revision: str = "20260913_0023"
down_revision: str | None = "20260913_0022"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        """
        CREATE TABLE reference.physical_building (
            id text PRIMARY KEY,
            source text NOT NULL,
            commune_code text NOT NULL,
            department_code text NOT NULL,
            member_count integer NOT NULL,
            grouping_version text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT physical_building_source
                CHECK (source = ANY (ARRAY['rnb', 'cadastre'])),
            CONSTRAINT physical_building_member_count CHECK (member_count >= 1)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE reference.physical_building_member (
            physical_building_id text NOT NULL
                REFERENCES reference.physical_building(id) ON DELETE CASCADE,
            building_id text NOT NULL,
            PRIMARY KEY (physical_building_id, building_id),
            -- Un enregistrement appartient a un seul batiment physique par version de
            -- regroupement : sans cette unicite, un comptage pourrait le voir deux fois, ce qui
            -- est exactement le defaut que ce ticket corrige.
            UNIQUE (building_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX physical_building_commune ON reference.physical_building "
        "(department_code, commune_code)"
    )
    op.execute(
        "CREATE INDEX physical_building_member_building "
        "ON reference.physical_building_member (building_id)"
    )
    op.execute("GRANT SELECT ON reference.physical_building TO api_rw, backup_ro")
    op.execute("GRANT SELECT ON reference.physical_building_member TO api_rw, backup_ro")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON reference.physical_building TO pipeline_rw")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON reference.physical_building_member TO pipeline_rw"
    )
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute("DROP TABLE reference.physical_building_member")
    op.execute("DROP TABLE reference.physical_building")
    op.execute("RESET ROLE")
