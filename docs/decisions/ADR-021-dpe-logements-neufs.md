# ADR-021 — Les DPE de logements neufs entrent comme une source distincte, DS-13, hors baromètre

**Date :** 16 septembre 2026

**Contexte.** DS-07 n'importe que le jeu ADEME « DPE logements existants » (`dpe03existant`).
L'ADEME en publie un second, « DPE logements neufs » (`dpe02neuf`) : le diagnostic établi à la
réception d'une construction. Il manque donc toute la construction neuve depuis juillet 2021 —
39 072 diagnostics dans le 35, 506 à Betton contre 2 152 existants, relevés à l'API le
16 septembre 2026. Le porteur l'a constaté sur sa propre maison, construite en 2022 : parcelle
et bâtiment bien rattachés, aucun diagnostic.

Les deux jeux ont le même schéma, à deux différences près : les modèles déclarés (« DPE NEUF
logement : RT2012 », « … : RE2020 ») et l'absence de `dpe_desactive`, déjà absente de la vue
des existants.

**Le piège.** Un DPE neuf n'annonce pas une vente : il accompagne la livraison d'un bâtiment.
Le signal « dépôt de DPE → mutation à douze mois » du baromètre (BAR-005 à BAR-007) et du radar
repose sur les DPE existants ; y mêler les neufs le fausserait. Or la plupart des lecteurs de
`observation.energy_assessment` lisent la table entière, sans filtrer la source.

**Alternatives écartées.**

- *Étendre DS-07 à une seconde couche.* Les deux jeux partageraient une release et une
  couverture, et les distinguer demanderait une colonne ou une propriété dans chaque lecture.
- *Une nouvelle table.* Interdit pour le baromètre, et inutile : le diagnostic a la même forme.
- *Ne rien importer.* L'outil de vérification continuerait de montrer une construction neuve sans
  diagnostic, ce qui est faux.

**Décision.**

1. **Une source distincte, DS-13** « DPE logements neufs depuis juillet 2021 », contrat et
   manifestes propres, mêmes règles d'import que DS-07 (extrait archivé et checksumé, diagnostics
   déposés, rattachement par identifiant déclaré), liste fermée de modèles propre.
2. **Même table**, `observation.energy_assessment` ; la source se lit par la release
   (`meta.dataset_release.data_source_id`). Aucune table ajoutée ; une migration enregistre la
   source.
3. **Hors baromètre et hors radar.** Toute lecture qui sert une mesure, une liste ou une feature
   filtre explicitement DS-07. `SPEC.md` §13.1 et §13.3 le disent.
4. **Affichée dans l'outil de vérification**, marquée « neuf » diagnostic par diagnostic.

**Conséquences.**

- Chaque requête de mesure porte un filtre de source ; un test le vérifie sur le texte des
  requêtes, faute de banc PostgreSQL dans `make check`.
- Le baromètre doit ressortir à l'identique : son empreinte de mesures ne change pas.
- Une mesure du neuf par commune devient possible ; elle serait une mesure nouvelle, à inscrire
  au registre §13.4 par décision, pas un effet de bord de cet import.
