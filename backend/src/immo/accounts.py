"""Ouvrir l'accès à un compte OIDC — BUG-10.

L'application ne provisionne rien à la première connexion, et c'est voulu : l'accès est
nominatif, B2B, et un compte qui se crée seul serait un compte que personne n'a décidé
d'ouvrir. Il faut donc une commande explicite, et c'est celle-ci.

## Pourquoi cette commande n'a besoin d'aucun privilège particulier

Les trois tables portent une RLS **forcée**, qui s'applique même au propriétaire :

- `app.organization` : `id = current_setting('app.current_organization_id')`
- `app.app_user` : `external_subject = current_setting('app.current_subject')`
- `app.organization_membership` : l'utilisateur **et** l'organisation courants

Créer la première organisation paraît donc impossible — c'est ce qui a laissé la base vide.
Mais les politiques comparent à des variables de session, pas à un état déjà présent : il
suffit de se déclarer être ce qu'on s'apprête à insérer. On ne peut créer qu'un compte dont on
prend l'identité dans la même transaction, ce qui est exactement l'invariant recherché.

Cette commande tourne donc avec le rôle applicatif ordinaire. Aucun `BYPASSRLS`, aucun
superutilisateur, aucune politique désactivée le temps du provisionnement — ce qui aurait été
la façon simple et fausse de s'y prendre.
"""

import argparse
import re
import sys
from typing import Any

from sqlalchemy import text

from immo.database import get_engine

# Memes contraintes que le schema, verifiees ici pour rendre l'erreur lisible avant l'insertion.
SUBJECT = re.compile(r"^[0-9a-f-]{36}$")
ORGANIZATION_ID = re.compile(r"^org:[a-z0-9_-]+$")
ROLES = ("platform_admin", "organization_admin", "analyst", "viewer")


class InvalidAccountError(ValueError):
    """Une donnée d'entrée que le schéma refuserait, signalée avant d'atteindre PostgreSQL."""


def grant_access(
    *,
    subject: str,
    display_name: str,
    email: str | None,
    organization_id: str,
    organization_name: str,
    role: str = "analyst",
) -> dict[str, Any]:
    """Ouvrir l'accès d'un sujet OIDC à une organisation. Idempotent.

    `subject` est le `sub` du jeton, c'est-à-dire l'identifiant Keycloak de l'utilisateur.
    """
    if not SUBJECT.match(subject):
        raise InvalidAccountError(
            f"Le sujet OIDC doit être un UUID de 36 caractères, reçu : {subject!r}"
        )
    if not ORGANIZATION_ID.match(organization_id):
        raise InvalidAccountError(
            f"L'identifiant d'organisation doit suivre `org:<slug>`, reçu : {organization_id!r}"
        )
    if role not in ROLES:
        raise InvalidAccountError(f"Rôle inconnu : {role!r}. Attendus : {', '.join(ROLES)}")
    if not display_name.strip():
        raise InvalidAccountError("Le nom affiché ne peut pas être vide.")

    user_id = f"user:{subject}"
    parameters = {
        "subject": subject,
        "user_id": user_id,
        "display_name": display_name,
        "email": email,
        "organization_id": organization_id,
        "organization_name": organization_name,
        "role": role,
    }

    engine = get_engine()
    with engine.begin() as connection:
        # Se declarer etre ce que l'on insere : c'est ce qui satisfait les trois politiques.
        # `true` sur `set_config` limite la portee a la transaction.
        for setting, value in (
            ("app.current_subject", subject),
            ("app.current_user_id", user_id),
            ("app.current_organization_id", organization_id),
        ):
            connection.execute(
                text("SELECT set_config(:setting, :value, true)"),
                {"setting": setting, "value": value},
            )

        connection.execute(
            text(
                """
                INSERT INTO app.organization (id, name)
                VALUES (:organization_id, :organization_name)
                ON CONFLICT (id) DO UPDATE SET name = excluded.name
                """
            ),
            parameters,
        )
        connection.execute(
            text(
                """
                INSERT INTO app.app_user (id, external_subject, email, display_name)
                VALUES (:user_id, :subject, :email, :display_name)
                ON CONFLICT (external_subject) DO UPDATE
                    SET email = excluded.email, display_name = excluded.display_name
                """
            ),
            parameters,
        )
        # `is_default` a vrai sur la premiere appartenance seulement : la resolution de
        # l'acteur prend `is_default DESC, created_at`, et deux defauts rendraient l'ordre
        # dependant de l'horodatage.
        connection.execute(
            text(
                """
                INSERT INTO app.organization_membership
                       (organization_id, user_id, role, is_default)
                VALUES (:organization_id, :user_id, :role,
                        NOT EXISTS (SELECT 1 FROM app.organization_membership
                                     WHERE user_id = :user_id))
                ON CONFLICT (organization_id, user_id) DO UPDATE SET role = excluded.role
                """
            ),
            parameters,
        )
    return {"user_id": user_id, "organization_id": organization_id, "role": role}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m immo.accounts",
        description="Ouvrir l'accès d'un compte OIDC à une organisation.",
    )
    parser.add_argument("--subject", required=True, help="`sub` du jeton, UUID Keycloak")
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--email", default=None)
    parser.add_argument("--organization-id", required=True, help="`org:<slug>`")
    parser.add_argument("--organization-name", required=True)
    parser.add_argument("--role", default="analyst", choices=ROLES)
    arguments = parser.parse_args(argv)

    try:
        granted = grant_access(
            subject=arguments.subject,
            display_name=arguments.display_name,
            email=arguments.email,
            organization_id=arguments.organization_id,
            organization_name=arguments.organization_name,
            role=arguments.role,
        )
    except InvalidAccountError as error:
        print(f"Refusé : {error}", file=sys.stderr)
        return 2
    print(f"Accès ouvert : {granted['user_id']} → {granted['organization_id']} ({granted['role']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
