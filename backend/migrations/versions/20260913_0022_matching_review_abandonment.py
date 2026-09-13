"""B4 : abandonner une strate en cours de revue, avec le motif de l'abandon.

Deux des trois strates ont perdu leur critère dès leur première erreur : `certain_source_relation`
sur la relation bâtiment ↔ parcelle est à 42,9 % d'erreur, `ambiguous` sur la relation
adresse ↔ parcelle à 24,4 %. La règle de trois demandait zéro erreur sur 60 ; aucun des cas
restants ne peut y ramener.

Les juger quand même mesurerait plus finement deux échecs déjà caractérisés — la règle du rang
pour la première, l'absence de tout signal géométrique pour la seconde — pendant que la seule
strate encore capable de produire une acceptation attend.

**L'abandon est une donnée, pas une règle de code.** Le rapport doit pouvoir citer quels cas ont
été écartés, quand et pourquoi ; une condition enfouie dans une requête ne se cite pas. D'où
cette table, jumelle de `matching_review_recall` et soumise au même append-only : un abandon
rendu ne se réécrit pas.

Le sens de la déviation compte autant que la déviation : on arrête les strates où le moteur a
échoué, jamais celle où il est propre. L'inverse aurait été un tri favorable.
"""

from alembic import op

revision: str = "20260913_0022"
down_revision: str | None = "20260910_0021"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        """
        CREATE TABLE meta.matching_review_abandonment (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            case_id bigint NOT NULL UNIQUE
                REFERENCES meta.matching_review_case(id) ON DELETE RESTRICT,
            reason text NOT NULL,
            abandoned_by text NOT NULL,
            abandoned_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT matching_review_abandonment_reason CHECK (length(reason) >= 10)
        )
        """
    )
    # Un cas deja juge n'est pas a abandonner : son verdict compte, et l'ecarter apres coup
    # retirerait du denominateur un resultat connu. C'est la definition du tri.
    op.execute(
        """
        CREATE FUNCTION meta.forbid_abandoning_judged_case() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM meta.matching_review_verdict AS verdict
                 WHERE verdict.case_id = NEW.case_id
            ) THEN
                RAISE EXCEPTION
                    'Le cas % porte deja un verdict : l abandonner retirerait un resultat connu '
                    'du denominateur.', NEW.case_id;
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER matching_review_abandonment_unjudged_only
        BEFORE INSERT ON meta.matching_review_abandonment
        FOR EACH ROW EXECUTE FUNCTION meta.forbid_abandoning_judged_case()
        """
    )
    op.execute(
        """
        CREATE TRIGGER matching_review_abandonment_append_only
        BEFORE UPDATE OR DELETE ON meta.matching_review_abandonment
        FOR EACH ROW EXECUTE FUNCTION meta.forbid_review_rewrite()
        """
    )
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        "DROP TRIGGER IF EXISTS matching_review_abandonment_append_only "
        "ON meta.matching_review_abandonment"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS matching_review_abandonment_unjudged_only "
        "ON meta.matching_review_abandonment"
    )
    op.execute("DROP TABLE meta.matching_review_abandonment")
    op.execute("DROP FUNCTION IF EXISTS meta.forbid_abandoning_judged_case()")
    op.execute("RESET ROLE")
