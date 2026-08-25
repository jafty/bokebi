# Railway deployment plan

## Prerequisites

Create a Railway project, connect the Git repository, and provision **two** managed PostgreSQL services: `bokebi-data` for surveys/answers and `bokebi-contacts` for contact requests. Keeping two credentials and databases is a required anonymity control, not an optional scaling choice.

## Configuration

1. Add an application service from the repository. Railway detects the root `Dockerfile`.
2. Set `DATABASE_URL` to the private connection URL of `bokebi-data`.
3. Set `CONTACT_DATABASE_URL` to the private connection URL of `bokebi-contacts`.
4. Generate a long random `SECRET_KEY`; set `DEBUG=0`.
5. Set `ALLOWED_HOSTS` to the Railway hostname and custom domain, comma-separated.
6. Set `CSRF_TRUSTED_ORIGINS` to each public HTTPS origin.
7. Do not expose either PostgreSQL service publicly. Limit Railway project access and rotate credentials after staff changes.
8. Configure SMTP and `CONTACT_NOTIFICATION_RECIPIENTS` if operators should be notified of new contact requests. Notifications contain no submitter data; operators retrieve it from the authenticated admin.

## Build and release

The image installs pinned dependencies as an unprivileged user. `entrypoint.sh` migrates the default database, migrates the isolated contacts database, collects static assets, and then executes Gunicorn. Railway injects `PORT`; Gunicorn defaults to 8000 locally.

After the first deployment:

1. Inspect logs and confirm both migration commands succeed against different hosts/databases.
2. Open `/`, create a survey, retain its deletion phrase, and submit three test participations.
3. Confirm results are locked at one/two and unlocked at three.
4. Submit a contact opt-in and inspect only the contacts database: it may contain the disclosed group label, but it must contain no survey/participation identifiers or answers.
5. Delete the test survey with its phrase.
6. Configure health monitoring on `/` and backups/retention independently for both databases.
7. Run `python manage.py createsuperuser`, sign in at `/admin/`, and confirm that the contact-request queue is visible only after authentication.

## Local parity

Copy `.env.example` to `.env`, generate independent random values for
`SECRET_KEY`, `SURVEY_DB_PASSWORD`, and `CONTACT_DB_PASSWORD`, and then run
`docker compose up --build`. The Compose file deliberately fails fast when any
of these values is absent. Compose starts the application and two separate
PostgreSQL containers. Run tests independently with
`docker compose run --rm web pytest -q`. Never commit `.env`; only the empty
`.env.example` belongs in source control.

## Rollback

Use Railway's previous deployment rollback for application failures. Before destructive schema changes, take both database backups. Roll back each database only with its own backup; never merge or export the two datasets into a shared analytical store.
