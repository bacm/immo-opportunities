# Démonstration adresse — département 35

**Date :** 8 septembre 2026
**Environnement :** stack Compose locale, serveur de développement Vite sur données réelles.
**Aucune fixture** : chaque écran provient de l'API interrogeant la base du 35.

Ces captures sont une **preuve**, pas une illustration. Elles sont régénérables :

```bash
pnpm --filter @immo/web capture:demo
```

Le script est `apps/web/tests/e2e/demo-capture.spec.ts`. Il n'intercepte aucune route et il est
exclu de `pnpm test:e2e` : il ne s'exécute que délibérément, pour régénérer ce dossier.

## Releases affichées

| Source | Release | Acceptation |
|---|---|---|
| DS-01 Cadastre | `DS-01@2026-06-01` | `accepted` |
| DS-02 RNB | `DS-02@2026-09-05` | `pending` — **non publiée**, donc invisible de l'API |
| DS-03 BDNB | `DS-03@2026-02-a` | `display_only` |
| DS-04 BD TOPO | `DS-04@2026-06-15` | `display_only` |
| DS-05 BAN | `DS-05@2026-06-17` | `display_only` |

## Les cas choisis, et pourquoi

Le ticket prévient : « ne pas choisir uniquement une adresse qui marche bien ». Les deux adresses
retenues le sont pour ce qu'elles montrent de difficile.

**`address:ban:35001_0001_00002` — 2 Rue Agatha Christie, Acigné.** Porte simultanément un
appariement **certain** et un **ambigu** vers deux parcelles différentes. C'est le cas qui permet
de comparer les deux sur le même écran.

**`address:ban:35002_3n5z8h_00006` — 6 Lieu Dit Penlievre, Amanlis.** Une des 216 adresses réelles
dont la position a été retenue par la quarantaine par attribut de
[BUG-03](../backlog/BUG-03-quarantaine-par-attribut.md).

## Séquence

| # | Capture | Ce qu'elle établit |
|---|---|---|
| 01 | `01-explorer-initial.png` | état initial, aucune couverture affirmée sans territoire observé |
| 02 | `02-recherche-adresse-reelle.png` | recherche d'adresse réelle, **liste** de résultats sans sélection implicite |
| 03 | `03-fiche-adresse-certain-et-ambigu.png` | fiche, carte recadrée, parcelles et bâtiments rendus |
| 04 | `04-couverture-sources-nommees.png` | état de couverture, source manquante **nommée** |
| 05 | `05-appariement-ambigu-visible.png` | certain et ambigu côte à côte, avec méthode et confiance |
| 06 | `06-absence-motivee.png` | la liste dit la vraie raison de son vide |
| 07 | `07-valeur-absente-motif.png` | FR-007 : position absente avec son motif |

## Ce que chaque capture prouve

### Recherche et recentrage

La saisie « rue agatha christie acigne » rend plusieurs adresses plausibles **en liste**. Aucune
n'est sélectionnée automatiquement : le recentrage ne masque pas l'ambiguïté du choix.

La fiche est ensuite ouverte par son **URL partageable**,
`/?address=address:ban:35001_0001_00002&lon=…&lat=…&z=16.00`. C'est à la fois la fonctionnalité
exigée par FR-001 et ce qui rend cette séquence rejouable à l'identique.

### Un appariement certain et un ambigu, sur le même écran

| | Certain | Ambigu |
|---|---|---|
| Parcelle | `35001000ZB0487` | `35001000ZB0374` |
| Méthode | `source_relation` | `source_relation` |
| Confiance | 0,99 | 0,80 |
| Décision | `certain` | `ambiguous` |
| Release | `DS-05@2026-06-17` | `DS-05@2026-06-17` |

L'ambiguïté a **sa propre section**, sous les appariements certains. Elle n'est ni masquée, ni
fondue dans une liste unique où seul le plus probable serait montré.

La justification est affichée telle qu'elle est persistée : « BAN experimental cad_parcelles
relation checked against active parcel geometry ». Elle rappelle que cette relation est
expérimentale — ce qui est précisément pourquoi DS-05 reste en `display_only`.

### Couverture : la source manquante est nommée

La bannière indique « ACIGNE · données partielles — Classement incomplet. Sources absentes :
DS-02 Référentiel National des Bâtiments ». Un avertissement générique aurait laissé croire à un
problème vague ; nommer DS-02 dit exactement ce qui manque, et pourquoi le classement est
incomplet.

Le RNB est pourtant importé, 741 379 bâtiments en base. Sa release est `pending`, donc non
publiée, donc sans pointeur actif : l'API ne peut pas la lire. C'est un état transitoire qui se
résoudra à [B4](../backlog/B4-revue-manuelle-appariements.md).

### FR-007 : l'absence porte son motif

Sur l'adresse d'Amanlis :

- **État** : « Non localisée · `ambiguous_position` » — le motif, pas seulement l'absence ;
- « Cette adresse existe dans la release mais sa position est inutilisable. Elle n'entre dans
  aucune relation spatiale et **la carte n'a pas été recentrée**. » ;
- « Aucun appariement pour cette adresse dans la release active. **C'est une absence, pas un
  rejet** : rien ne permet de la rattacher, et rien ne l'en empêche formellement. »

La carte reste sur le cadrage précédent, visiblement. Recentrer sur un point arbitraire aurait
fait passer une absence pour une localisation.

### La liste ne ment pas sur son vide

« Aucun candidat publié — Les définitions de score doivent être validées avant qu'un candidat réel
apparaisse ici. Les valeurs inconnues ne sont pas converties en zéro. »

Zéro candidat ne veut pas dire zéro potentiel : aucun `OpportunitySnapshot` n'a encore été publié,
et l'écran le dit.

## Ce que ces captures ne montrent pas

**Les trois états de couverture de [C2](../backlog/C2-zone-non-couverte.md) ne sont pas tous
démontrables.** Seul `partial` existe sur données réelles :

- `covered` exigerait que DS-02 soit publiée — donc B4 ;
- `not_covered` exigerait une commune chargée sans aucune source active. `reference.area` ne
  contient que les 332 communes du 35, toutes couvertes : une commune du 22 renvoie 404, pas
  « non couvert ». Ce cas ne se vérifiera qu'à [G1](../backlog/G1-extension-22-29-56.md).

Les deux états sont implémentés et couverts par des tests end-to-end avec routes simulées. Mais
une capture de ces états serait une capture de simulation — donc elle ne vaudrait pas preuve, et
elle n'est pas produite.

**Le zoom fait partie de la démonstration.** Au cadrage par défaut la carte est vide : `parcels`
déclare `minzoom 13`. Ce n'est pas un défaut mais l'ADR MapLibre appliqué — aucun GeoJSON
régional, donc aucun rendu au-dessus du département. Les captures fixent donc `z=16.00` dans
l'URL.
