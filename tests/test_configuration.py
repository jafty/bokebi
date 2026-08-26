from pathlib import Path

def test_compose_requires_external_secret_values() -> None:
    compose = Path("docker-compose.yml").read_text()

    for variable in (
        "SECRET_KEY",
        "SURVEY_DB_PASSWORD",
        "CONTACT_DB_PASSWORD",
    ):
        assert f"${{{variable}:?" in compose


def test_example_environment_contains_no_secret_values() -> None:
    values = dict(
        line.split("=", 1)
        for line in Path(".env.example").read_text().splitlines()
        if line and not line.startswith("#")
    )

    assert values["SECRET_KEY"] == ""
    assert values["SURVEY_DB_PASSWORD"] == ""
    assert values["CONTACT_DB_PASSWORD"] == ""
    assert values["EMAIL_HOST_PASSWORD"] == ""


def test_email_uses_smtp_backend_by_default() -> None:
    settings_source = Path("config/settings.py").read_text()

    assert 'os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")' in settings_source
    assert 'os.getenv("EMAIL_TIMEOUT", "10")' in settings_source
