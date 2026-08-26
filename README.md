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
list of operator addresses and configure Django's SMTP environment variables.
The SMTP backend is enabled by default; `EMAIL_BACKEND` only needs to be set when
using a different Django email backend.

For Brevo SMTP, use:

```dotenv
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_HOST_USER=<your Brevo SMTP login>
EMAIL_HOST_PASSWORD=<your Brevo SMTP key>
EMAIL_USE_TLS=1
DEFAULT_FROM_EMAIL=<a sender verified in Brevo>
CONTACT_NOTIFICATION_RECIPIENTS=<operator@example.com>
```

Use the **SMTP key**, not a Brevo HTTP API key. If delivery fails, the exception
is written to the application log instead of printing a message that looks sent.
Notification messages deliberately contain neither the submitter's address nor
their choices; staff must sign in to view them.
