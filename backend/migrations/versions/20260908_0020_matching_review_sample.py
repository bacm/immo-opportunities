"""B4 : echantillon de revue manuelle, et verdicts append-only.

`meta.entity_match_review` existe deja, mais elle ne peut pas porter cette revue, pour trois
raisons qui tiennent au sens et non a la commodite.

**Elle ne reference que `meta.entity_match`.** Les decisions de DS-03 et DS-04 vivent dans
`meta.entity_observation_link` — 1,55 M lignes que la contrainte de cle etrangere rend
inaccessibles. Or B4 doit precisement echantillonner les trois sources ensemble.

**Elle ne sait pas dire « indecidable ».** Sa contrainte n'admet que `certain`, `ambiguous` et
`rejected`. Le ticket exige un verdict `correct / incorrect / indecidable`, et enonce
qu'« indecidable est un resultat valide et ne doit pas etre force ». Reutiliser la table
obligerait a coder l'indecidable comme une decision, ce qui le compterait comme un jugement rendu.

**Elle exprime autre chose.** Un `entity_match_review` est une *correction* : le relecteur
remplace la decision du moteur. Un verdict de B4 est une *mesure* : il dit si la decision etait
juste, sans la changer. Les deux sont utiles et ne se confondent pas — une revue peut conclure
« incorrect » sans qu'on sache par quoi remplacer.

Les deux tables coexistent donc : `entity_match_review` pour corriger, celles-ci pour mesurer.
"""

from alembic import op

revision: str = "20260908_0020"
down_revision: str | None = "20260907_0019"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")

    # Le tirage lui-meme. `size_rationale` est renseigne **avant** le tirage : une taille
    # justifiee apres coup n'est pas une validation, elle est une description du resultat.
    op.execute(
        """
        CREATE TABLE meta.matching_review_sample (
            id text PRIMARY KEY,
            seed bigint NOT NULL,
            target_size integer NOT NULL CHECK (target_size > 0),
            size_rationale text NOT NULL,
            protocol_document text NOT NULL,
            drawn_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT matching_review_sample_rationale CHECK (length(size_rationale) >= 40)
        )
        """
    )

    # Un cas tire. Il pointe vers exactement une decision, de l'un ou l'autre des deux
    # referentiels de decision — et `unmatched` n'en a aucune, puisque c'est une absence.
    op.execute(
        """
        CREATE TABLE meta.matching_review_case (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            sample_id text NOT NULL
                REFERENCES meta.matching_review_sample(id) ON DELETE RESTRICT,
            territorial_stratum text NOT NULL,
            matching_stratum text NOT NULL,
            commune_code text,
            match_id bigint REFERENCES meta.entity_match(id) ON DELETE RESTRICT,
            observation_link_id bigint
                REFERENCES meta.entity_observation_link(id) ON DELETE RESTRICT,
            -- Un cas non apparie n'a pas de decision : il est designe par l'entite qui
            -- aurait du en avoir une. C'est la quatrieme classe, et elle doit etre revue
            -- comme les autres.
            unmatched_entity_type text,
            unmatched_entity_id text,
            drawn_rank integer NOT NULL,
            CONSTRAINT matching_review_case_territorial CHECK (
                territorial_stratum IN ('urbain', 'periurbain', 'rural', 'littoral', 'frontiere')
            ),
            CONSTRAINT matching_review_case_target CHECK (
                (match_id IS NOT NULL)::int
                + (observation_link_id IS NOT NULL)::int
                + (unmatched_entity_id IS NOT NULL)::int = 1
            ),
            CONSTRAINT matching_review_case_unmatched_pair CHECK (
                (unmatched_entity_type IS NULL) = (unmatched_entity_id IS NULL)
            ),
            CONSTRAINT matching_review_case_unique_match UNIQUE (sample_id, match_id),
            CONSTRAINT matching_review_case_unique_link UNIQUE (sample_id, observation_link_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX matching_review_case_strata ON meta.matching_review_case "
        "(sample_id, matching_stratum, territorial_stratum)"
    )

    # Le verdict. Append-only : un jugement rendu ne se reecrit pas, il se complete par un
    # jugement ulterieur qui porte sa propre date et son propre auteur. Un desaccord entre
    # deux relecteurs reste donc visible comme un desaccord, et non ecrase par le dernier.
    op.execute(
        """
        CREATE TABLE meta.matching_review_verdict (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            case_id bigint NOT NULL
                REFERENCES meta.matching_review_case(id) ON DELETE RESTRICT,
            verdict text NOT NULL,
            reviewer text NOT NULL,
            rationale text NOT NULL,
            evidence_consulted text NOT NULL,
            recorded_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT matching_review_verdict_value CHECK (
                verdict IN ('correct', 'incorrect', 'undecidable')
            ),
            CONSTRAINT matching_review_verdict_rationale CHECK (length(rationale) >= 3),
            -- Le relecteur doit dire ce qu'il a consulte : un verdict rendu sur la seule
            -- sortie du moteur mesurerait l'accord avec le moteur, pas l'exactitude.
            CONSTRAINT matching_review_verdict_evidence CHECK (length(evidence_consulted) >= 3)
        )
        """
    )
    op.execute(
        "CREATE INDEX matching_review_verdict_case ON meta.matching_review_verdict (case_id)"
    )

    # L'append-only n'est pas une convention mais une contrainte : une revue qu'on peut
    # reecrire ne prouve plus ce qui a ete juge, ni quand.
    op.execute(
        """
        CREATE FUNCTION meta.forbid_review_rewrite() RETURNS trigger
        LANGUAGE plpgsql AS $function$
        BEGIN
            RAISE EXCEPTION
                'meta.% is append-only: record a new verdict instead of rewriting %',
                TG_TABLE_NAME, TG_OP;
        END
        $function$
        """
    )

    # Un cas **deja juge** est intouchable, pour la meme raison qu'un verdict : le retirer
    # effacerait le denominateur du taux d'exactitude, donc le rendrait invérifiable.
    #
    # Un cas **non juge** n'a rien a proteger. Interdire de le retirer transformerait un tirage
    # rate en dette permanente : c'est arrive au premier tirage de B4, dont une strate est
    # sortie vide faute de commune resolue. La regle porte donc sur ce qui a ete juge, pas sur
    # ce qui a ete tire.
    op.execute(
        """
        CREATE FUNCTION meta.forbid_judged_case_rewrite() RETURNS trigger
        LANGUAGE plpgsql AS $function$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM meta.matching_review_verdict AS verdict
                 WHERE verdict.case_id = OLD.id
            ) THEN
                RAISE EXCEPTION
                    'review case % carries a verdict and cannot be %d', OLD.id, TG_OP;
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END
        $function$
        """
    )
    op.execute(
        """
        CREATE TRIGGER matching_review_verdict_append_only
        BEFORE UPDATE OR DELETE ON meta.matching_review_verdict
        FOR EACH ROW EXECUTE FUNCTION meta.forbid_review_rewrite()
        """
    )
    op.execute(
        """
        CREATE TRIGGER matching_review_case_append_only
        BEFORE UPDATE OR DELETE ON meta.matching_review_case
        FOR EACH ROW EXECUTE FUNCTION meta.forbid_judged_case_rewrite()
        """
    )

    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        "DROP TRIGGER IF EXISTS matching_review_case_append_only ON meta.matching_review_case"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS matching_review_verdict_append_only ON meta.matching_review_verdict"
    )
    op.execute("DROP TABLE meta.matching_review_verdict")
    op.execute("DROP TABLE meta.matching_review_case")
    op.execute("DROP TABLE meta.matching_review_sample")
    op.execute("DROP FUNCTION IF EXISTS meta.forbid_judged_case_rewrite()")
    op.execute("DROP FUNCTION IF EXISTS meta.forbid_review_rewrite()")
    op.execute("RESET ROLE")
