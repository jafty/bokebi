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
