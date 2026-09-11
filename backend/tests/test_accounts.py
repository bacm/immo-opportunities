"""Ouvrir un accès sans désactiver la RLS — BUG-10.

Les trois tables du compte portent une RLS **forcée**, qui s'applique même au propriétaire. La
façon simple et fausse de provisionner aurait été de passer superutilisateur, ou de désactiver
les politiques le temps de l'insertion : le provisionnement aurait alors pu créer n'importe
quoi, y compris ce qu'aucun acteur n'a le droit de voir.

La façon juste tient à ce que les politiques comparent à des **variables de session** : on se
déclare être ce que l'on s'apprête à insérer, donc on ne peut créer qu'un compte dont on prend
l'identité dans la même transaction.

Ces tests portent sur les validations et sur le texte de la commande, faute de banc PostgreSQL
dans `make check`. Le chemin réel est vérifié par `scripts/check-oidc-login`, qui obtient un
jeton du réalm et résout deux acteurs de deux organisations.
"""

import inspect

import pytest

from immo import accounts
from immo.accounts import InvalidAccountError, grant_access

VALID = {
    "subject": "3744923a-e0f9-4561-94d2-d9068186816d",
    "display_name": "Alpha Développement",
    "email": "dev-alpha@example.test",
    "organization_id": "org:dev-alpha",
    "organization_name": "Organisation Alpha (développement)",
}


@pytest.mark.parametrize(
    ("champ", "valeur"),
    [
        ("subject", "dev-alpha"),
        ("subject", ""),
        ("organization_id", "dev-alpha"),
        ("organization_id", "org:Dev Alpha"),
        ("display_name", "   "),
    ],
)
def test_une_entree_que_le_schema_refuserait_est_refusee_avant(champ: str, valeur: str) -> None:
    """Le schéma refuserait aussi, mais avec un message de contrainte illisible."""
    with pytest.raises(InvalidAccountError):
        grant_access(**{**VALID, champ: valeur})


def test_un_role_inconnu_est_refuse() -> None:
    with pytest.raises(InvalidAccountError, match="Rôle inconnu"):
        grant_access(**VALID, role="proprietaire")


def test_les_roles_acceptes_sont_ceux_du_schema() -> None:
    """La liste vit à deux endroits ; si elle diverge, l'insertion échoue en production."""
    assert accounts.ROLES == ("platform_admin", "organization_admin", "analyst", "viewer")


def test_la_commande_se_declare_avant_d_inserer() -> None:
    """Sans ces trois `set_config`, les politiques rejettent les trois insertions."""
    source = inspect.getsource(grant_access)
    for setting in ("app.current_subject", "app.current_user_id", "app.current_organization_id"):
        assert setting in source, f"`{setting}` n'est pas positionné : l'insertion sera rejetée."


def test_aucun_contournement_de_la_rls() -> None:
    """Le jour où quelqu'un « répare » cette commande, que ce soit un échec de test.

    Le contrôle porte sur le corps de `grant_access` et non sur le module : la note d'en-tête
    cite justement les contournements pour dire pourquoi ils sont écartés.
    """
    source = inspect.getsource(grant_access)
    for interdit in (
        "BYPASSRLS",
        "DISABLE ROW LEVEL SECURITY",
        "SET ROLE postgres",
        "SET SESSION AUTHORIZATION",
    ):
        assert interdit not in source, (
            f"`{interdit}` contourne la RLS. Le provisionnement doit se déclarer être ce qu'il "
            "insère, pas s'autoriser à insérer n'importe quoi."
        )


def test_une_seule_appartenance_par_defaut() -> None:
    """`is_default` décide de l'organisation servie ; deux défauts rendraient l'ordre instable."""
    source = inspect.getsource(grant_access)
    assert "NOT EXISTS (SELECT 1 FROM app.organization_membership" in source
