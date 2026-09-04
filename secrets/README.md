# Secrets

Ce répertoire ne doit contenir en clair que les secrets locaux jetables sous `secrets/dev/`, qui est ignoré par Git.

## Développement

```text
make dev-secrets
```

La commande complète les secrets manquants sans jamais écraser une valeur existante.

## Staging et production

1. Générer une identité `age` et conserver la clé privée hors du dépôt.
2. Copier `staging.sops.yaml.example` ou `production.sops.yaml.example` sans le suffixe `.example`.
3. Remplacer les valeurs factices.
4. Chiffrer immédiatement le fichier avec SOPS pour le destinataire `age` configuré.
5. Vérifier que le fichier contient une section `sops:` avant tout commit.

Ansible déchiffre le document en mémoire depuis le conteneur opérateur et installe chaque valeur sous `/etc/immo/secrets` avec le mode `0400`.
