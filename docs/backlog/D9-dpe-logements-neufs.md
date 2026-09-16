# D9 — Importer les DPE de logements neufs (DS-13), hors baromètre

**Version :** v0.5 · **Taille :** M · **État :** Terminé
**Nature :** implémentation · **Touche :** contracts/datasets/DS-13/, backend/migrations/versions/, backend/src/immo/, pipelines/src/immo_pipelines/market_data/dpe.py, pipelines/scripts/, apps/web/src/, Makefile, SPEC.md, ARCHITECTURE.md
**Dépend de :** D4 · **Bloque :** —
**Demandé par :** conversation du 16 septembre 2026 — « pourquoi je n'ai aucun DPE sur Betton… le
mien sur la 35024000AP0209 a été réalisé en 2022 lors de la réception de la construction de ma
maison mais n'est pas affiché ».
**DoD :** preuve dans `docs/data/dpe-neuf-matching-35.md`, recomptée

## Contexte à charger

- `SPEC.md` §13.1, §13.3, §13.7, §13.9 — ces sections seulement
- [ADR-021](../decisions/ADR-021-dpe-logements-neufs.md)
- `docs/backlog/D4-import-dpe-ds07.md`
- `pipelines/scripts/pin_dpe_release.py`, `pipelines/scripts/import_dpe_release.py`,
  `pipelines/src/immo_pipelines/market_data/dpe.py`

## Choix retenus

- **Source** : DS-13, jeu `dpe02neuf`, contrat `contracts/datasets/DS-13/v1.json` ; migration qui
  n'insère que la ligne `meta.data_source`.
- **Code partagé** : `pin_dpe_release.py` et `import_dpe_release.py` prennent `--source DS-07|DS-13`
  (DS-07 par défaut) ; la famille porte le jeu ADEME, le préfixe d'archive et la liste fermée de
  modèles. Version de transformation inchangée pour DS-07.
- **Filtre de source** : les lectures de mesure — baromètre, listes E8 et E8f, candidats
  exploratoires, rapport qualité, rapport d'appariement — filtrent DS-07 par la release.
- **Explorer** : la route des diagnostics d'une parcelle renvoie `data_source_id` ; le front
  affiche une pastille « Neuf » ou « Existant ».
- **Preuve** : `dpe_matching_report.py --source DS-13` écrit `dpe-neuf-matching-35.md` ; recomptée.
- **Contrôle du baromètre** : régénéré après coup, empreinte des mesures identique.

## Critères d'acceptation

- ~~la parcelle `35024000AP0209` montre un DPE neuf dans l'onglet Diagnostics~~ — **non atteint**,
  la source ne porte pas ce diagnostic sous un identifiant rattachable (voir Résultat) ; remplacé
  par : une parcelle de Betton porteuse d'un DPE neuf réel (`35024000AP0175`) l'affiche, test e2e ;
- le baromètre régénéré garde l'empreinte `d08dba5d179c319e` ;
- un test échoue si une requête de mesure lit `energy_assessment` sans filtre DS-07 ;
- `make check` vert, `make openapi` régénéré, `pnpm test:e2e` vert.

## Résultat — 16 septembre 2026, verdict `display_only`

**Preuve :** [`dpe-neuf-matching-35.md`](../data/dpe-neuf-matching-35.md), recomptée en
isolement du code le 16 septembre : aucune divergence de valeur. Manifeste
`contracts/datasets/DS-13/releases/2026-09-16-extract-35.json`, SHA-256 `c1bc6853…6979`.

| Classe | Diagnostics | Part |
|---|---:|---:|
| Bâtiment, par `id_rnb` | 9 310 | 23,83 % |
| Adresse seule, par `identifiant_ban` | 9 361 | 23,96 % |
| Non rattaché, motif consigné | 20 401 | 52,21 % |

- **Baromètre** régénéré au 16 septembre après le filtre DS-07 : sortie identique, empreinte
  `d08dba5d179c319e` inchangée.
- **La parcelle `35024000AP0209` reste sans DPE.** L'extrait ne porte aucun diagnostic sous son
  adresse BAN ni son identifiant RNB, ni sous l'adresse saisie. À Betton, 151 des 187 DPE neufs de
  2022 n'ont ni numéro de voie ni identifiant RNB : des programmes déclarés au lot ou à la rue,
  qu'aucune règle honnête ne pose sur une parcelle. Le diagnostic du porteur est vraisemblablement
  l'un d'eux ; son numéro de DPE permettrait de le vérifier.
- **Recompte, écarts de formulation corrigés** : restriction « rattachés à la seule adresse » des
  5 339 contradictions de géocodage ; communes « déclarées par la source » ; date de fraîcheur
  nommée. `uncompressed_byte_size` comptait l'en-tête deux fois (5 888 octets) : corrigé pour les
  prochains épinglages, les manifestes déjà épinglés restent tels quels.
- **Non repris** : le tableau des contrôles ne liste que les contrôles par ligne et par commune
  (`schema` et `checksum` sont vérifiés à l'import).
- **Captures C3** : un `npx playwright test` complet les a réécrites ; restaurées, elles restent
  la preuve datée de v0.4. Lancer `pnpm test:e2e`, qui les exclut.
