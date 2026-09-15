# BUG-16 — Un ticket suffixé au-delà de `b` est invisible des contrôles, sans bruit

**Version :** dette transverse · **Taille :** S · **État :** Terminé
**Nature :** implémentation · **Touche :** scripts/check-commit-ticket, scripts/backlog-status, scripts/tests/
**Dépend de :** — · **Bloque :** —
**Découvert par :** ouverture de E8c, E8d et E8e, 15 septembre 2026

## Contexte à charger

- `scripts/check-commit-ticket`
- `scripts/backlog-status`
- `docs/backlog/BUG-15-collision-identifiants-tickets.md`

Ne rien charger d'autre sans nécessité démontrée.

## Symptôme

La convention d'identifiant est écrite `[A-G]\d[ab]?` dans deux scripts. Elle accepte donc `D6a` et
`D6b`, et **rien au-delà**. Un troisième sous-ticket est impossible, et son ouverture ne produit
aucune erreur.

Constaté le 15 septembre : `E8c`, `E8d` et `E8e` ont été ouverts, travaillés, livrés et commités.
Le tableau de suivi les affiche — `backlog-status` dérive l'identifiant du nom de fichier, pas de
la regex. Mais :

| Contrôle | Effet |
|---|---|
| `make ticket-check` | trois commits signalés « aucun identifiant dans le sujet » |
| dépendances du tableau | `E8d` dépend de `E8c`, `E8e` de `E8d` : les deux affichent « — » |
| `make dod ID=E8c` | non touché — il compare les chaînes, sans regex |

C'est le mode d'échec de [BUG-15](./BUG-15-collision-identifiants-tickets.md) sous une autre forme :
le tableau paraît juste, et l'information manquante ne se signale pas.

## Ce qui est en cause

`ID_RE` sert à deux choses distinctes, et la limite à deux suffixes n'est justifiée pour aucune :

- `backlog-status` y lit les **dépendances** déclarées en en-tête ;
- `check-commit-ticket` y valide le **sujet de commit** et construit les identifiants connus.

Aucune règle écrite ne borne le nombre de sous-tickets. La borne est un accident de rédaction, et
le dépôt venait d'atteindre le plafond sans que rien ne le dise.

## Travail à réaliser

1. Porter la classe de suffixe à `[a-z]?` dans les deux scripts.
2. Vérifier que la limite de frontière `\b` continue de séparer `E8` de `E8c` dans une liste de
   dépendances — `E8c, E8d` doit donner deux identifiants, pas quatre.
3. Étendre les suites de `scripts/tests/` sur un suffixe au-delà de `b`.

## Ce que ce ticket ne fait pas

- **Réécrire l'historique.** Les trois commits sont poussés. Élargir la regex les rend valides
  rétroactivement, ce qui répare `ticket-check` sans toucher à l'historique.
- **Élargir la classe de lettres de série.** `[A-G]` borne les séries existantes ; l'étendre est
  une autre décision, et rien ne la demande.

## Tests obligatoires

- un sujet `E8c — …` est rattaché au ticket `E8c` ;
- une dépendance `E8c, E8d` produit exactement `{E8c, E8d}` ;
- `E8` seul reste reconnu, et n'est pas confondu avec `E8c` ;
- un identifiant inconnu du backlog reste refusé.

## Critères d'acceptation

- `make ticket-check` ne signale plus les trois commits ;
- les dépendances de `E8d` et `E8e` réapparaissent dans le tableau ;
- les suites de `scripts/tests/` couvrent un suffixe au-delà de `b`.

## Preuve

**DoD :** preuve sans objet — la correction se vérifie par `make ticket-check` et `make backlog`,
tous deux dans `make check` ou lancés à la main, et par les tests ajoutés.
