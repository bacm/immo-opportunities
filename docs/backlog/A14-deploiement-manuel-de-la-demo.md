# A14 — Mettre à jour la démo du VPS depuis GitHub Actions, sur lancement manuel

**Version :** transverse · **Taille :** S · **État :** Terminé
**Nature :** implémentation · **Touche :** .github/workflows/deploy-demo.yml, scripts/deploy-demo, scripts/tests/test_deploy_demo.py, DEPLOYMENT.md
**Dépend de :** A6 · **Bloque :** —
**Demandé par :** conversation du 17 septembre 2026
**DoD :** preuve sans objet — outillage de déploiement, aucun chiffre publié ; le test suffit

## Contexte à charger

- `DEPLOYMENT.md` §5
- `.github/workflows/deploy-vps.yml`
- `scripts/restore-demo-subset`

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

A6 déploie la démo par un runbook à la main (`DEPLOYMENT.md` §5). L'installation initiale est
ponctuelle : export depuis la base du poste, secrets, restauration, proxy, Cloudflare Access,
compte Keycloak. Seule la mise à jour du code se répète : `git pull`, puis
`docker compose up --build`. Le porteur veut la lancer depuis GitHub Actions, **uniquement à la
main**.

## Choix retenus — 17 septembre 2026

- **Déclenchement `workflow_dispatch` seul** : aucun `push`, aucune planification. La version
  déployée est le commit de la référence choisie au lancement (`GITHUB_SHA`), pas la tête de
  `main` au moment où le VPS la lit.
- **Nouveau workflow, pas `deploy-vps.yml`** : ce dernier lance Ansible sur une machine qu'il
  croit vierge (A6, « Pas d'Ansible sur cette machine »).
- **Images construites sur le VPS** (`up --build`), sans registre : pas de GHCR à ouvrir pour une
  démo ; le coût est un build de quelques minutes sur 2 vCPU.
- **Le travail distant est un script du dépôt**, `scripts/deploy-demo`, lancé après le
  `git checkout` du commit : il se teste, et le workflow se réduit à SSH.
- **Refus sans restauration** : si la base `immo` n'a pas le schéma `meta`, le script s'arrête
  avant tout `up`. Un `up` sur une base vide la migrerait, et `restore-demo-subset` refuserait
  ensuite de restaurer. Refus aussi si l'arbre de travail du VPS a des modifications suivies.
- **Vérification locale** : `/health` sur `127.0.0.1:${DEMO_HTTP_PORT:-8080}` depuis le VPS ;
  l'URL publique est derrière Cloudflare Access, qu'un jeton de service ne contournera pas pour
  si peu.
- **Réglages GitHub** dans l'environnement `demo` : variables `DEMO_HOST`, `DEMO_USER`,
  `DEMO_SSH_PORT` (défaut 22), `DEMO_DIR` ; secrets `DEMO_SSH_PRIVATE_KEY`,
  `DEMO_SSH_KNOWN_HOSTS`. Aucun secret applicatif ne passe par GitHub : ils restent sur le VPS.
- **Aucun nettoyage d'images** : `docker image prune` toucherait les autres projets de la machine.

## Hors périmètre

- l'installation initiale (`DEPLOYMENT.md` §5, étapes 1 à 7) ;
- la lisibilité des secrets en `0600` par les conteneurs non root sous Linux (`DEPLOYMENT.md` §2,
  point 3), qui s'applique aussi à la démo.

## Critères d'acceptation

- le workflow ne se déclenche que par `workflow_dispatch` ;
- `scripts/deploy-demo` refuse une base non restaurée sans lancer `up`, et le test le prouve ;
- `DEPLOYMENT.md` §5 décrit les réglages GitHub et le lancement.
