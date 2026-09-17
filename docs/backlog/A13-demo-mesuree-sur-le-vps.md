# A13 — Déployer la démo sur le VPS du porteur, et y mesurer ce que le poste ne dit pas

**Version :** transverse · **Taille :** S · **État :** À faire
**Nature :** revue humaine · **Preuve :** docs/data/demo-subset-35-vps.md
**Dépend de :** A6 · **Bloque :** —
**Demandé par :** A6, 17 septembre 2026 — seul le porteur a accès à la machine

## Contexte à charger

- `DEPLOYMENT.md` §5
- `docs/data/demo-subset-35.md`, sections « Mémoire et tuiles » et « Machine cible »

Ne rien charger d'autre sans nécessité démontrée.

## Contexte

A6 a produit l'export des cinq communes, la stack `compose.demo.yaml` et leurs mesures **sur le
poste de développement**. La machine visée est le VPS Hetzner du porteur (2 vCPU, 4 Go, 80 Go),
qui sert déjà d'autres conteneurs derrière son propre Caddy et Cloudflare. Un poste à SSD local ne
dit rien d'un disque et d'un CPU partagés.

## Travail à réaliser

1. Suivre `DEPLOYMENT.md` §5, y compris Cloudflare Access sur le sous-domaine et la fermeture de
   l'origine à tout ce qui ne vient pas de Cloudflare. **Vérifier depuis un réseau extérieur**
   qu'une requête directe à l'IP de la machine n'atteint ni l'API ni les tuiles.
2. Mesurer et consigner :
   - la taille restaurée ;
   - `free -m` et `docker stats`, au repos puis après navigation sur Rennes ;
   - l'usage de la mémoire d'échange ;
   - le p95 des tuiles de Rennes à froid, sur la même emprise et les mêmes zooms que
     `docs/data/demo-subset-35.md`.
3. Si la machine utilise sa mémoire d'échange en navigation, l'agrandir (« Rescale », CPU et RAM
   seuls) et remesurer.

## Critères d'acceptation

- la démo répond sur son sous-domaine, derrière Cloudflare Access, et pas en direct ;
- les mesures ci-dessus sont consignées dans la preuve, avec le gabarit de la machine ;
- le palier retenu (4 Go ou 8 Go) est écrit, avec sa raison.
