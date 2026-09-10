"""B4 : rappeler un cas en revue, avec le motif du rappel.

Trois cas de la strate `certain_official_identifier` ont été jugés avant que l'écran affiche
l'orthophoto, et leurs motifs disent qu'ils mesurent l'outil et non l'appariement : « je n'ai
pas d'adresse et le code de l'objet de gauche est introuvable sur l'app », « je n'arrive pas à
trouver le bâtiment ».

Les laisser fausserait la strate dans les deux sens : deux `undecidable` sortent du
dénominateur, et un `correct` y entre sans que le bâtiment ait été vu.

Un rappel n'efface rien — l'append-only l'interdit et c'est voulu. Il **redonne** le cas à
juger, en enregistrant pourquoi. Le rapport pourra donc dire que ces cas portent deux verdicts,
et lequel a été rendu avec quelle information.
"""

from alembic import op

revision: str = "20260910_0021"
down_revision: str | None = "20260908_0020"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        """
        CREATE TABLE meta.matching_review_recall (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            case_id bigint NOT NULL
                REFERENCES meta.matching_review_case(id) ON DELETE RESTRICT,
            reason text NOT NULL,
            recalled_by text NOT NULL,
            recalled_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT matching_review_recall_reason CHECK (length(reason) >= 10)
        )
        """
    )
    op.execute("CREATE INDEX matching_review_recall_case ON meta.matching_review_recall (case_id)")
    # Meme regle que les verdicts : un rappel rendu ne se reecrit pas. Sans cela on pourrait
    # effacer la trace d'un rejugement, donc faire passer un second verdict pour un premier.
    op.execute(
        """
        CREATE TRIGGER matching_review_recall_append_only
        BEFORE UPDATE OR DELETE ON meta.matching_review_recall
        FOR EACH ROW EXECUTE FUNCTION meta.forbid_review_rewrite()
        """
    )
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        "DROP TRIGGER IF EXISTS matching_review_recall_append_only ON meta.matching_review_recall"
    )
    op.execute("DROP TABLE meta.matching_review_recall")
    op.execute("RESET ROLE")
