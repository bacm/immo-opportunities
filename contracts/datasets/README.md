# Contrats de datasets

Chaque source déclare au minimum son identifiant `DS-*`, producteur, URL, licence, millésime, couverture, checksum, schéma attendu, contrôles qualité, transformations, rétention et politique de publication.

Les contrats réels [DS-01 Cadastre v1](./DS-01/v1.json), [DS-02 RNB v1](./DS-02/v1.json),
[DS-03 BDNB Open v1](./DS-03/v1.json), [DS-04 BD TOPO v1](./DS-04/v1.json) et
[DS-05 BAN v1](./DS-05/v1.json), [DS-06 DVF+ v1](./DS-06/v1.json),
[DS-07 DPE v1](./DS-07/v1.json), [DS-08 GPU v1](./DS-08/v1.json) et
[DS-09 Géorisques v1](./DS-09/v1.json) sont versionnés. Chaque millésime et territoire possède
ensuite un manifeste sous `DS-*/releases/`. Une URL
`latest` peut servir à découvrir une release, mais n'est jamais enregistrée comme URL d'import
reproductible. Le checksum calculé sur les octets téléchargés doit être renseigné avant import.
