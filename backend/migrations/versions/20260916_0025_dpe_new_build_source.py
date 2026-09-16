"""D9 : les DPE de logements neufs, source distincte DS-13 — ADR-021.

Le diagnostic neuf a la forme d'un diagnostic existant et partage `observation.energy_assessment`.
Seule sa source diffère, et c'est elle que les lectures de mesure filtrent : un DPE neuf
accompagne une livraison, il n'annonce pas une vente. Aucune table n'est ajoutée.
"""

from alembic import op

revision: str = "20260916_0025"
down_revision: str | None = "20260914_0024"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        """
        INSERT INTO meta.data_source (
            id, name, producer, homepage_url, licence_spdx,
            licence_name, attribution, usage_notes
        ) VALUES (
            'DS-13', 'DPE Logements neufs depuis juillet 2021', 'ADEME',
            'https://data.ademe.fr/datasets/dpe-v2-logements-neufs', 'etalab-2.0',
            'Licence Ouverte 2.0', 'ADEME, Observatoire DPE-Audit',
            'DPE déposés à la réception d''une construction ; affichés, jamais dans une mesure '
            'du baromètre ni du radar (ADR-021).'
        )
        ON CONFLICT (id) DO NOTHING
        """
    )
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute("DELETE FROM meta.data_source WHERE id = 'DS-13'")
    op.execute("RESET ROLE")
