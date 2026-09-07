"""DS-04 BD TOPO : la voirie est une observation de contexte, jamais une entite canonique.

`meta.entity_source_observation` n'admet que les cinq types canoniques — `area`, `address`,
`parcel`, `building`, `property_unit`. Un troncon de route n'en est pas un sixieme : il sert a
calculer une distance ou un acces, il ne cree aucune identite. D'ou une table dediee dans
`observation`, aux cotes des autres observations non canoniques (zones d'urbanisme, risques,
diagnostics).

Les batiments BD TOPO, eux, restent des observations d'une entite canonique existante — le
batiment RNB — et vont donc dans `meta.entity_source_observation` sans table nouvelle.

Voir B2b.
"""

from alembic import op

revision: str = "20260907_0019"
down_revision: str | None = "20260904_0018"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute(
        """
        CREATE TABLE observation.road_segment (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            release_id text NOT NULL REFERENCES meta.dataset_release(id) ON DELETE RESTRICT,
            raw_asset_id bigint REFERENCES meta.raw_asset(id) ON DELETE RESTRICT,
            source_identifier text NOT NULL,
            source_row_number bigint,
            -- Le departement de rattachement est resolu depuis la geometrie, pas depuis le nom
            -- de l'export : celui du 35 deborde sur 143 communes limitrophes.
            department_code text,
            commune_code_left text,
            commune_code_right text,
            nature text,
            importance text,
            is_private boolean,
            is_fictitious boolean,
            geom geometry(MultiLineString, 2154) NOT NULL,
            properties jsonb NOT NULL DEFAULT '{}'::jsonb,
            record_checksum char(64) NOT NULL CHECK (record_checksum ~ '^[0-9a-f]{64}$'),
            imported_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT road_segment_source UNIQUE (release_id, source_identifier),
            CONSTRAINT road_segment_geom_valid CHECK (
                ST_IsValid(geom) AND NOT ST_IsEmpty(geom)
            )
        )
        """
    )
    op.execute("CREATE INDEX road_segment_geom_gist ON observation.road_segment USING gist (geom)")
    op.execute(
        "CREATE INDEX road_segment_release_department ON observation.road_segment "
        "(release_id, department_code)"
    )

    # `meta.entity_match` relie deux entites canoniques et sa contrainte
    # `entity_match_entity_types` impose `left_entity_type <> right_entity_type`. Elle ne peut
    # donc pas porter le rattachement d'une observation BD TOPO au batiment canonique RNB :
    # ce n'est pas un appariement entre deux entites, c'est une observation qui s'attache a
    # une entite. Cette decision-la n'avait aucun lieu ou vivre.
    #
    # `entity_source_observation.entity_id` ne portait qu'un rattachement binaire et sans
    # motif : il dit *que* l'observation appartient a une entite, jamais *comment* on l'a
    # etabli ni pourquoi on a renonce. La quatrieme classe — non apparie — etait donc
    # indistinguable d'un rattachement rejete.
    #
    # DS-03 (groupes BDNB) et DS-07 (DPE) posent exactement le meme probleme : voir B2a et D4.
    op.execute(
        """
        CREATE TABLE meta.entity_observation_link (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            observation_id bigint NOT NULL
                REFERENCES meta.entity_source_observation(id) ON DELETE CASCADE,
            entity_type text NOT NULL,
            entity_id text NOT NULL,
            method text NOT NULL,
            algorithm_code text NOT NULL,
            algorithm_version text NOT NULL,
            confidence numeric(6,5) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
            decision text NOT NULL,
            rationale text NOT NULL,
            evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
            release_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT entity_observation_link_identity UNIQUE (
                observation_id, entity_type, entity_id, algorithm_code, algorithm_version
            ),
            CONSTRAINT entity_observation_link_entity_type CHECK (
                entity_type IN ('area', 'address', 'parcel', 'building', 'property_unit')
            ),
            CONSTRAINT entity_observation_link_decision CHECK (
                decision IN ('certain', 'ambiguous', 'rejected')
            ),
            CONSTRAINT entity_observation_link_method CHECK (
                method IN (
                    'official_identifier', 'source_relation', 'spatial_intersection',
                    'proximity', 'normalized_address', 'temporal_consistency', 'manual'
                )
            )
        )
        """
    )
    op.execute(
        "CREATE INDEX entity_observation_link_entity_idx ON meta.entity_observation_link "
        "(entity_type, entity_id, decision)"
    )
    op.execute(
        "CREATE INDEX entity_observation_link_observation_idx ON meta.entity_observation_link "
        "(observation_id, decision)"
    )
    op.execute("RESET ROLE")


def downgrade() -> None:
    op.execute("SET LOCAL ROLE migration_owner")
    op.execute("DROP TABLE meta.entity_observation_link")
    op.execute("DROP TABLE observation.road_segment")
    op.execute("RESET ROLE")
