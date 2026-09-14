"""D1 : un prix absent reste absent, avec son motif — DS-06.

`observation.transaction.price_eur` était `NOT NULL`. Or 185 des 21 690 mutations du 35 en 2024,
soit 0,9 %, ne portent aucune valeur foncière dans `geo-dvf` — des actes réels, sans prix
déclaré.

Trois issues étaient possibles, deux mauvaises :

- **les rejeter** : on perdrait des mutations réelles, et les métriques de volume et de liquidité
  (`MKT-101` à `MKT-105`) compteraient faux ;
- **écrire zéro** : interdit, et la contrainte `price_eur > 0` le refusait déjà — à juste titre,
  un prix de zéro n'est pas un prix ;
- **rendre l'attribut nullable avec son motif** : c'est la quarantaine par attribut de BUG-03, et
  le ticket D1 demande explicitement de la réutiliser ici.

La nullabilité n'ouvre pas la porte à des `NULL` silencieux : une nouvelle contrainte exige qu'un
prix absent s'accompagne de `is_complex` et d'un `complex_reason`. Un prix ne peut donc pas
disparaître sans que la transaction dise pourquoi.
"""

from alembic import op

revision: str = "20260914_0024"
down_revision: str | None = "20260913_0023"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute("ALTER TABLE observation.transaction ALTER COLUMN price_eur DROP NOT NULL")
    op.execute(
        """
        ALTER TABLE observation.transaction
          ADD CONSTRAINT transaction_missing_price_is_motivated
          CHECK (price_eur IS NOT NULL OR (is_complex AND complex_reason IS NOT NULL))
        """
    )
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        "ALTER TABLE observation.transaction "
        "DROP CONSTRAINT IF EXISTS transaction_missing_price_is_motivated"
    )
    op.execute("DELETE FROM observation.transaction WHERE price_eur IS NULL")
    op.execute("ALTER TABLE observation.transaction ALTER COLUMN price_eur SET NOT NULL")
    op.execute("RESET ROLE")
