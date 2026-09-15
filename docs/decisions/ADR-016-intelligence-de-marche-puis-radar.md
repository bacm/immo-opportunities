# ADR-016 — Le produit devient une intelligence de marché, puis un radar de mise en vente

**Date :** 15 septembre 2026

**Contexte.** L'audit du 15 septembre ([`docs/audit-critique-2026-09-15.md`](../audit-critique-2026-09-15.md))
établit que la définition initiale — candidats off-market pour marchands de biens, deux
stratégies, quatre départements — cumule trois impossibilités : l'objet « bien » n'est pas
constructible avec les données autorisées (une unité par parcelle, 24 % et 37 % d'erreur
d'appariement, BUG-11 sans plan) ; « off-market » suppose un propriétaire que `SPEC.md` §13.6
exclut ; la stratégie rénovation-revente est infondée par les données du projet lui-même (décote
énergétique de 3 à 4 % sur les maisons du 35, marge dans le prix d'entrée). Onze jours et 128
commits ont produit un logiciel sans un seul utilisateur, sans un seul entretien, sans un seul
score publié, et un pivot non déclaré vers les « biens probablement en vente ».

Le dépôt possède pourtant deux résultats mesurés que personne ne publie sur le 35 : le dépôt d'un
DPE prédit une mutation à douze mois à 35 % contre 3 % de base, lift × 11,8, stable sur deux
cohortes ; et sur 7 024 paires de reventes, la plus-value nette d'un marchand est × 1,90 quand il
achète sous 60 % du prix de marché, × 1,01 au prix. Ce sont des faits de marché, explicables,
sans modèle ni seuil inventé.

**Alternatives écartées ou différées.** Sept variantes ont été évaluées (audit §14).

- *V0, la plateforme SaaS telle que spécifiée.* Écartée comme définition : elle vend ce que les
  données ne construisent pas, derrière onze tickets dont une extension XL, sans qu'aucun
  professionnel n'ait rien vu.
- *V1, gisement foncier divisible assumé comme produit parcellaire.* Différée. Tenable et
  réutilisant l'existant, mais la divisibilité est déjà vendue par Kel Foncier et Immonator, et
  c'est un produit « stock » à faible rétention. Reste ouverte si les entretiens la réclament.
- *V3, off-market personnes morales par MAJIC PM croisé avec BODACC.* Différée. Seul off-market
  légalement propre avec un propriétaire nommé ; volume inconnu sur le 35. Reste ouverte, à sonder
  en une requête quand la priorité le permet.
- *V4, prestation pour EPCI ayant droit des Fichiers fonciers.* Différée : cycle de vente public
  long, usage borné aux politiques publiques.
- *V6, vendre la couche morphologie et qualité aux outils nationaux.* Différée : quelques acheteurs,
  négociation longue.
- *V7, arrêt et capitalisation open source.* Non retenue tant qu'une variante n'a pas été
  confrontée à un professionnel.

**Décision.**

1. **V5 immédiatement : le produit est une intelligence de marché.** Un baromètre du marché du 35
   par EPCI et commune, construit uniquement sur les données déjà importées et acceptées en
   `display_only` (DS-06 DVF, DS-07 DPE), reproductible par script, recompté avant publication :
   marge de revente observée par prix d'entrée, décote énergétique réelle, courbe de conversion et
   délai dépôt DPE → acte par commune, liquidité observée, effet de l'extension sur le prix au m².
   Un document, pas une plateforme : aucune ligne dans le front, l'API, l'infrastructure ni le
   moteur de score. Il sert de premier artefact public, de prétexte aux entretiens que le projet
   n'a jamais eus, et de premier revenu possible.
2. **V2 comme cible : le radar de mise en vente.** Un flux hebdomadaire des parcelles dont un DPE
   vient d'être déposé, avec l'âge du dépôt, la chance résiduelle observée, l'étiquette et le taux
   communal. C'est un flux, donc un abonnement défendable, et c'est le meilleur résultat mesuré du
   projet. Il n'est **pas** lancé avant deux verrous : un avis juridique écrit sur l'inférence de
   mise en vente à une adresse identifiée, et le verdict des professionnels rencontrés avec le
   baromètre en main.
3. **La plateforme est gelée, pas supprimée.** D6, E1 à E7, F1 à F3, G1 à G8, BUG-02, BUG-08,
   BUG-11, BUG-13, D7, A6, G6, G7 sont suspendus. Rien n'est abandonné dans le backlog tant que le
   verdict de H3 n'est pas écrit ; rien n'y est repris non plus.
4. **Ce que la décision ne change pas.** Le propriétaire personne physique reste hors périmètre
   (`SPEC.md` §13.6). Aucun seuil territorial inventé, aucune valeur manquante convertie en zéro,
   chaque chiffre publié passe par `recompte-preuve`. La réforme DPE du 1er janvier 2026 est traitée
   comme une rupture de série sur les logements chauffés à l'électricité.

**Conséquences.**

- Une série de tickets `H` porte V5 et V2 ; les outils du backlog, limités aux lettres A à G,
  sont étendus par A7.
- `SPEC.md` est réécrit, pas amendé — et toute la documentation de référence avec lui (H6),
  dès maintenant, par décision du 15 septembre : une référence fausse coûte plus qu'une
  référence provisoire. Ce qui dépend du verdict de H3 y est marqué provisoire, et H3 la relit.
- `CLAUDE.md` et `docs/backlog/README.md` désignent le baromètre comme chemin critique. « Le plus
  important maintenant » devient H1.
- Les listes E8 et E8f restent disponibles pour E9, dont le protocole doit être corrigé avant
  usage (aveugle cassé sur E8f, audit §3.4 et §15). E9 n'est plus sur le chemin critique.
- Le signal DPE peut entrer dans le baromètre comme mesure agrégée par commune. Il n'entre dans
  aucune liste nominative par adresse avant H4.
- Cette ADR remplace l'ordre d'exécution de `CLAUDE.md` (« v0.5 → profiling → v0.6 → v0.7 →
  v0.8 ») par : baromètre → entretiens → avis juridique → radar → spécification réécrite.
