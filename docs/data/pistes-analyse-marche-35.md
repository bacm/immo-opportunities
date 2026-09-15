# Pistes d'analyse du signal de vente et de la valeur pour le marchand — département 35

**Noté le :** 15 septembre 2026 · **Origine :** conversation du 15 septembre 2026, à la suite de
[`dpe-signal-vente-35.md`](./dpe-signal-vente-35.md) et de [D8](../backlog/D8-historique-dvf-2014.md)
**Statut :** notes. Aucune de ces pistes n'est mesurée, décidée ni ouverte en ticket. Chacune dit
ce qu'elle mesurerait, sur quelle donnée, ce qu'elle servirait, et où elle se rattacherait.

Le sujet de fond tient en deux questions : *qui est sur le marché*, et *que vaut le bien pour un
marchand*. Les pistes sont classées par ce que les données déjà importées permettent, puis par ce
qui demanderait une source nouvelle.

## 1. Affiner le signal DPE avec ce qui est déjà en base

Toutes ces pistes se calculent sur `DS-06` et `DS-07` tels qu'importés. Ce sont des recomptages,
pas des modèles : aucune n'invente de seuil, chacune stratifie une mesure existante.

### 1.1 Courbe de conversion dans le temps, pas un taux à douze mois

Sur la cohorte 2024, mesurer la part vendue à 1, 3, 6, 9, 12 et 18 mois après le dépôt. Un DPE de
cinq mois sans mutation n'a plus la même probabilité résiduelle qu'un DPE de trois semaines.

- **Sert :** un rang à l'intérieur de la liste de [E8f](../backlog/E8f-liste-biens-en-vente.md),
  observé, sans seuil inventé. Aujourd'hui la cohorte « signal » est une fenêtre plate de six mois.
- **Coût :** faible, même requête que le lift, ventilée par délai.
- **Rattachement :** extension de `dpe-signal-vente-35.md`.

### 1.2 Stabilité inter-cohortes — mesurable dès maintenant

La limite 4 du rapport dit « une seule cohorte annuelle ». Or DVF couvre 2021 à 2025 : les
cohortes 2022 et 2023 ont chacune leurs douze mois de suivi. Trois lifts au lieu d'un.

- **Sert :** crédibilité du × 11,8, ou sa relativisation. C'est ce que [E9](../backlog/E9-test-terrain-deux-professionnels.md)
  devrait avoir en main avant de tester la promesse.
- **Coût :** faible.
- **Réserve :** la cohorte 2022 est tronquée à gauche — l'extrait DPE commence en juillet 2021,
  donc « premier DPE » y est moins sûr.

### 1.3 Stratifier par étiquette, surtout F et G

Depuis le 1er janvier 2025 un logement classé G ne peut plus être mis en location. Un DPE G frais
est donc rarement un DPE de location : cela lève **en partie** la dilution vente/location que le
rapport déclare irréductible. F et G sont aussi la cible de la stratégie rénovation-revente.

- **Sert :** un lift par étiquette, et une lecture différente des candidats F/G de la liste.
- **Coût :** faible.
- **Réserve :** l'interdiction G ne vaut que depuis 2025, la cohorte 2024 ne la porte pas encore.
  L'effet se lira sur les cohortes 2025 et suivantes, donc après le prochain millésime DVF.

### 1.4 Premier DPE, DPE de remplacement, DPE d'immeuble, maison ou appartement

Les champs `numero_dpe_remplace` et `numero_dpe_immeuble_associe` distinguent une réédition, un
diagnostic collectif et un premier diagnostic. Leur taux de conversion n'a aucune raison d'être le
même ; idem pour `type_batiment`.

- **Sert :** sortir proprement les DPE collectifs de la liste, et qualifier la réédition.
- **Coût :** faible.

### 1.5 Un confondant à mesurer : l'obsolescence réglementaire

Les DPE antérieurs à 2018 sont invalides depuis le 1er janvier 2023, ceux de 2018 à juin 2021
depuis le 1er janvier 2025. Cela produit des vagues de rééditions sans lien avec une vente,
attendues fin 2022 et fin 2024. La cohorte 2024 en porte probablement, ce qui **sous-estimerait**
le lift.

- **Sert :** un taux de conversion par mois de dépôt, qui fera apparaître les vagues.
- **Coût :** faible.
- **Rattachement :** à écrire comme cinquième limite de `dpe-signal-vente-35.md` si la vague est
  visible.

## 2. Ce que douze ans de DVF ouvrent pour le marchand

D8 a porté l'historique à 2014. Ces pistes n'existaient pas avec cinq ans.

### 2.1 Marge de revente observée — ventes répétées

Même parcelle vendue deux fois : écart de prix, délai entre les deux actes, présence d'un DPE ou
d'un changement de surface bâtie entre les deux.

- **Sert :** la question centrale du produit — la marge **réellement réalisée** localement en
  rénovation-revente — qui n'est aujourd'hui ni mesurée ni supposée. Le même calcul donne un indice
  de prix par ventes répétées, plus robuste que la tendance sur médianes annuelles prévue pour
  `MKT-105`.
- **Coût :** moyen. La pré-qualification des mutations complexes de D1 s'applique aux deux ventes.
- **Rattachement :** [E7](../backlog/E7-decision-valorisation.md) pour la valorisation,
  [E1](../backlog/E1-profiling-distributions.md) pour `MKT-105`.
- **Réserve :** l'identité de mutation d'Etalab n'est pas reproductible entre millésimes, voir
  `dvf-quality-35.md`. Le rapprochement se fait par parcelle et date, pas par `id_mutation`.

### 2.2 Décote énergétique observée

Sur les ventes portant à la fois un prix DVF et une étiquette DPE — 21 718 sur le 35 — comparer le
prix au m² des F/G à celui des C/D, à commune et période égales.

- **Sert :** l'arbitrage que le marchand exploite, mesuré plutôt que postulé. C'est aussi une
  pondération observée pour `REN-004` dans le moteur, à la place d'un poids déclaré.
- **Coût :** moyen — le support statistique par commune sera le facteur limitant, comme pour les
  comparables.
- **Rattachement :** E1, E7.

### 2.3 Durée de détention

L'absence de mutation depuis 2014 redevient une information, comme le ticket D8 l'annonçait : sur
cinq ans, 85,1 % des parcelles de 35051 n'avaient aucune mutation, ce qui ne discriminait rien.

- **Sert :** attribut de **contexte** de la fiche — dernière mutation connue, ou « aucune depuis
  2014 ».
- **Interdit :** en faire une propension du propriétaire à vendre. `SPEC.md` l'exclut, et
  `dpe-signal-vente-35.md` le rappelle.
- **Coût :** faible ; la colonne « Dernière mutation » de la liste E8f existe déjà, il s'agit de
  l'étendre à douze ans.

### 2.4 Délai de vente et température de marché par commune

Le délai dépôt DPE → acte est un proxy du délai de vente, donnée rare en open data. Par commune,
avec le taux de conversion à douze mois, cela donne une liquidité observée.

- **Sert :** une définition de `MKT-005` (`market_liquidity_proxy`) fondée sur un délai réel plutôt
  que sur un ratio volume/stock.
- **Coût :** faible sur la mesure, moyen sur son intégration au moteur.
- **Rattachement :** E1.
- **Réserve :** même dilution location/vente que le signal lui-même.

## 3. Sources absentes du contrat

### 3.1 Sitadel — autorisations d'urbanisme

Open data du SDES, avec identifiant de parcelle depuis 2017. Deux usages, qu'aucune source en
contrat ne couvre :

- **Vérité terrain ex post pour [E8](../backlog/E8-liste-exploratoire-terrain.md).** Les parcelles
  jugées divisibles ont-elles fait l'objet d'une déclaration préalable de division ou d'un permis
  après mutation ? C'est la seule mesure de précision de la liste « où pourrait-on construire »
  qui ne dépende pas d'un relecteur.
- **Contexte pour E8f.** Un permis en cours sur une parcelle à DPE frais signifie que le
  propriétaire rénove ou vend avec permis : le signal ne se lit plus de la même façon.

Demande un contrat `DS-10`, un audit de source comme `market-data-sources-audit.md`, et donc un
ticket. Pièges attendus : la parcelle de Sitadel est déclarative et peut porter un numéro périmé
après division ; la granularité communale des extractions anciennes.

### 3.2 Registre national des copropriétés

Open data de l'ANAH. Sert à identifier les immeubles en copropriété et à sortir proprement les DPE
collectifs, en complément de 1.4. Rendement modeste, à ne pas ouvrir avant que 1.4 ait montré que
le champ DPE ne suffit pas.

## 4. Ce qui n'est pas poursuivi, et pourquoi

| Piste | Motif |
|---|---|
| Déclarations d'intention d'aliéner | pas en open data ; quelques communes les publient en délibération, sans structure |
| Annonces immobilières | scraping, hors périmètre par `SPEC.md` |
| Fichiers fonciers, MAJIC, LOVAC | données propriétaires sans droit, hors périmètre |
| Indicateurs communaux INSEE (résidences secondaires, évolution de population) | trop grossiers pour classer des parcelles ; utilisables au mieux comme contexte de commune |

## Ordre suggéré

1. **1.1, 1.2, 1.3** — trois recomptages à faible coût, qui renforcent directement ce que E9 va
   tester. À faire avant E9 si le calendrier le permet.
2. **2.1 et 2.2** — les deux chiffres qui parlent au marchand, calculables sans nouvelle source.
3. **3.1** — un contrat à ouvrir, donc un ticket à part, après le verdict de E9 sur la promesse E8.
