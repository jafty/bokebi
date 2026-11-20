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
    assert values["BREVO_API_KEY"] == ""
    assert values["BREVO_SENDER_EMAIL"] == ""


def test_email_uses_brevo_api_backend_by_default() -> None:
    settings_source = Path("config/settings.py").read_text()

    assert 'os.getenv("EMAIL_BACKEND", "contacts.email_backend.BrevoEmailBackend")' in settings_source
    assert 'os.getenv("EMAIL_TIMEOUT", "10")' in settings_source


def test_missing_secret_fails_at_startup(monkeypatch):
    import runpy

    import pytest
    from django.core.exceptions import ImproperlyConfigured

    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
        runpy.run_path("config/settings.py")


def test_wsgi_and_management_entrypoints(monkeypatch):
    import runpy
    import sys

    from config.wsgi import application

    assert callable(application)
    monkeypatch.setattr(sys, "argv", ["manage.py", "check"])
    runpy.run_path("manage.py", run_name="__main__")


def test_importing_manage_does_not_execute_a_command(monkeypatch):
    import runpy
    import sys

    monkeypatch.setattr(sys, "argv", ["manage.py", "invalid-command"])
    assert runpy.run_path("manage.py")["__name__"] != "__main__"
