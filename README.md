# Bokebi

Bokebi is a confidential, account-free workplace survey built with a pure-Python domain core and Django adapters.

## Local development

```bash
cp .env.example .env
# Fill the three empty values with independently generated secrets, for example:
# openssl rand -base64 48
docker compose up --build
```

`SECRET_KEY`, `SURVEY_DB_PASSWORD`, and `CONTACT_DB_PASSWORD` are deliberately
unset in the example file. Never commit the generated values.

The application is available at <http://localhost:8000>. See `docs/architecture_guidelines.md` and `docs/deployment_plan.md` for design and deployment details.

## Operator access

Contact requests are available only to authenticated staff at `/admin/`. Create
the first administrator after the databases have been migrated:

```bash
docker compose exec web python manage.py createsuperuser
```

The contact-request list can be filtered by request type and processing status;
it includes the survey's group label so operators can bring together requests
from the same workplace without storing a survey identifier or any answers.
Operators can mark selected requests as contacted. To receive privacy-preserving
notifications, configure `CONTACT_NOTIFICATION_RECIPIENTS` with a comma-separated
list of operator addresses and configure the Brevo transactional API. The HTTP
API backend is enabled by default and avoids holding a web request open while an
SMTP connection is established.

For Brevo, use:

```dotenv
BREVO_API_KEY=<your Brevo API key>
BREVO_SENDER_EMAIL=<a sender verified in Brevo>
CONTACT_NOTIFICATION_RECIPIENTS=<operator@example.com>
```

Use a Brevo **API key**, not an SMTP key. `EMAIL_TIMEOUT` controls the HTTP request
timeout and defaults to 10 seconds. If delivery fails, the exception is written
to the application log instead of printing a message that looks sent.
Notification messages deliberately contain neither the submitter's address nor
their choices; staff must sign in to view them.
