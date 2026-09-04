import argparse
from uuid import uuid4

from sqlalchemy import text

from immo.database import get_engine

ROLES = ("platform_admin", "organization_admin", "analyst", "viewer")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Associate a verified Keycloak subject with an application organization."
    )
    result.add_argument("--subject", required=True, help="Keycloak user sub claim")
    result.add_argument("--organization-id", required=True)
    result.add_argument("--organization-name", required=True)
    result.add_argument("--display-name", required=True)
    result.add_argument("--email")
    result.add_argument("--role", choices=ROLES, default="analyst")
    return result


def main() -> None:
    args = parser().parse_args()
    if not args.organization_id.startswith("org:"):
        raise SystemExit("--organization-id must start with 'org:'")
    with get_engine().begin() as connection:
        connection.execute(text("SET LOCAL ROLE migration_owner"))
        connection.execute(
            text("SELECT set_config('app.current_subject', :subject, true)"),
            {"subject": args.subject},
        )
        connection.execute(
            text("SELECT set_config('app.current_organization_id', :organization_id, true)"),
            {"organization_id": args.organization_id},
        )
        connection.execute(
            text(
                """
                INSERT INTO app.organization (id, name) VALUES (:id, :name)
                ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
                """
            ),
            {"id": args.organization_id, "name": args.organization_name},
        )
        user_id = connection.execute(
            text(
                """
                INSERT INTO app.app_user (
                    id, external_subject, email, display_name
                ) VALUES (:id, :subject, :email, :display_name)
                ON CONFLICT (external_subject) DO UPDATE SET
                    email = EXCLUDED.email, display_name = EXCLUDED.display_name
                RETURNING id
                """
            ),
            {
                "id": f"user:{uuid4()}",
                "subject": args.subject,
                "email": args.email,
                "display_name": args.display_name,
            },
        ).scalar_one()
        connection.execute(
            text("SELECT set_config('app.current_user_id', :user_id, true)"),
            {"user_id": user_id},
        )
        connection.execute(
            text(
                "UPDATE app.organization_membership SET is_default = false "
                "WHERE user_id = :user_id AND organization_id <> :organization_id"
            ),
            {"user_id": user_id, "organization_id": args.organization_id},
        )
        connection.execute(
            text(
                """
                INSERT INTO app.organization_membership (
                    organization_id, user_id, role, is_default
                ) VALUES (:organization_id, :user_id, :role, true)
                ON CONFLICT (organization_id, user_id) DO UPDATE SET
                    role = EXCLUDED.role, is_default = true
                """
            ),
            {
                "organization_id": args.organization_id,
                "user_id": user_id,
                "role": args.role,
            },
        )
    print(f"Provisioned {args.subject} in {args.organization_id} as {args.role}")


if __name__ == "__main__":
    main()
