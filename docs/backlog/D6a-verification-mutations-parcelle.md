# D6a — Voir les mutations d'une parcelle, pour vérifier que DVF tient

**Version :** v0.5 · **Taille :** S · **État :** En cours
**Touche :** backend/src/immo/explorer.py, backend/src/immo/api/routes/explorer.py, apps/web/src/App.tsx, docs/data/dvf-verification-35.md
**Dépend de :** D1 · **Bloque :** —
**Scindé de :** [D6](./D6-revue-manuelle-metier.md), 14 septembre 2026

> **C'est un instrument de vérification, pas une fonctionnalité produit.** Le produit classe des
> candidats ; il n'est pas un consultatif DVF, et le rester est explicitement au périmètre.

## Pourquoi maintenant, et pas dans D6

[D6](./D6-revue-manuelle-metier.md) revoit la **sélection de comparables** : les retenus sont-ils
pertinents, les exclus l'ont-ils été à juste titre. Cela suppose des segments de marché, que
[D1](./D1-import-dvf-ds06.md) a renvoyés à [E1](./E1-profiling-distributions.md) faute de pouvoir
les inventer. D6 est donc loin — il attend D5, qui attend D2, D3 et D4.

Ce ticket vérifie autre chose, de plus élémentaire et de disponible **aujourd'hui** : **les
mutations réellement rattachées à une parcelle sont-elles les bonnes ?** Cela ne met en jeu ni
segment, ni comparable, ni score — seulement l'import et le rattachement.

**133 066 mutations et 337 019 lots sont en base et rien ne les montre.** 165 660 parcelles en
portent au moins une ; la médiane est d'une mutation, le maximum de 238 sur une seule parcelle.

## Ce que la revue manuelle a déjà prouvé

[B4](./B4-revue-manuelle-appariements.md) a produit **trois défauts structurels qu'aucun contrôle
automatique n'avait vus** — [BUG-09](./BUG-09-recouvrement-batiment-parcelle.md),
[BUG-10](./BUG-10-aucun-compte-utilisateur.md),
[BUG-12](./BUG-12-deduplication-batiments-physiques.md) — et il a fallu qu'un humain regarde une
carte pour les voir.

DVF a déjà donné son propre exemple : la première règle d'allocation donnait le prix entier à
**plusieurs lots d'une même mutation** — 5 410 mutations, 13 303 lots, le même argent compté deux
fois. Le défaut a été trouvé en relisant des distributions, tard. Un écran montrant les mutations
d'une parcelle l'aurait rendu évident au premier regard : une maison et son terrain, chacun au
prix de la maison.

**Plus une erreur d'import est trouvée tard, plus elle coûte cher** — D5, E1 et le scoring
s'appuient dessus.

## Ce qu'il faut montrer

Sur la fiche parcelle de l'Explorer, un bloc listant ses mutations :

| Colonne | Pourquoi |
|---|---|
| Date et nature | une vente, un échange et une adjudication ne se lisent pas pareil |
| Valeur foncière | ou son absence, avec le motif |
| Lots de la mutation | c'est là que se voit une mutation complexe |
| Prix alloué, ou son absence motivée | **65,5 % des mutations n'en ont pas** — le montrer est le sujet |
| Surface et type de bien | pour juger si le prix au m² a un sens |

**Un prix absent doit se voir comme une absence motivée, jamais comme un blanc.** C'est ce qui
distingue une donnée manquante d'une donnée oubliée.

## Ce que ce ticket ne doit pas faire

- **Devenir une fonctionnalité.** Pas d'entrée de menu, pas de recherche par prix, pas d'export.
  L'accès se fait depuis une parcelle déjà sélectionnée, comme l'écran de revue de B4.
- **Calculer un prix au m² pour l'affichage.** Le prix alloué et la surface sont montrés tels
  qu'ils sont en base ; dériver un ratio à l'écran fabriquerait une valeur qui n'existe nulle part.
- **Masquer les mutations sans prix.** Elles sont la majorité et elles sont le résultat.

## Travail à réaliser

1. Exposer les mutations d'une unité foncière par l'API privée, sous RLS — jamais par les tuiles.
2. Afficher le bloc dans la fiche parcelle, avec les absences motivées.
3. Vérifier sur un échantillon de parcelles : les mutations sont-elles plausibles, les lots
   correspondent-ils à la parcelle, les montants sont-ils cohérents avec le bien ?
4. Consigner le résultat dans `docs/data/dvf-verification-35.md`, y compris s'il ne trouve rien.

## Critères d'acceptation

- les mutations d'une parcelle sont consultables sur données réelles, sans fixture ;
- une mutation sans prix allouable affiche son motif ;
- le rapport de vérification est écrit, et dit ce qui a été regardé et combien.
