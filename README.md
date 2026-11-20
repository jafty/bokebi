# Bokebi

Bokebi propose un premier échange confidentiel sur les difficultés au travail. Après une demande d’aide, la personne peut partager un court sondage avec ses collègues.

## Développement local

```sh
cp .env.example .env
# Renseigne SECRET_KEY, SURVEY_DB_PASSWORD et CONTACT_DB_PASSWORD avec trois secrets différents.
docker compose up --build
```

Le site est accessible sur <http://localhost:8000>.

```sh
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py maintain_bokebi
```

Pour exécuter les tests en local, installe `requirements-dev.txt`, renseigne une `SECRET_KEY` de test et lance `coverage run -m pytest` puis `coverage report`. SQLite suffit pour les tests courants. Avec `DATABASE_URL` et `CONTACT_DATABASE_URL` pointant vers PostgreSQL, la suite vérifie également les votes concurrents. La CI vérifie la couverture Python et JavaScript à 100 % et exécute les parcours Chromium sur une instance locale.

## Équipe Bokebi

Les demandes sont dans `/admin/`. L’équipe traite les nouvelles demandes par ordre d’échéance, répond depuis `entraide@bokebi.fr`, puis utilise les actions de changement de statut. Les alertes ne contiennent aucune donnée du demandeur. Voir le [guide de déploiement](docs/deployment_plan.md) pour activer Brevo, les relances et la purge.

Voir les [règles d’architecture](docs/architecture_guidelines.md) pour la répartition entre domaine, bases et adaptateurs.
