from datetime import datetime, timezone

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connections
from django.db.migrations.executor import MigrationExecutor

pytestmark = pytest.mark.django_db(transaction=True, databases=["default", "contacts"])


@pytest.mark.parametrize(
    "alias, app, previous, current, model_name, values",
    [
        (
            "default", "surveys", "0001_initial",
            "0002_surveycreationreceipt_workplacesurveyrecord_and_more", "SurveyRecord",
            {
                "public_id": "legacy-poll", "team_name": "Legacy team", "deletion_key_hash": "hash",
                "created_at": datetime(2026, 11, 20, tzinfo=timezone.utc),
            },
        ),
        (
            "contacts", "contacts", "0003_contactrequestrecord_group_label",
            "0004_helprequestrecord_delete_contactrequestrecord", "ContactRequestRecord",
            {"email": "legacy@example.com", "group_label": "Legacy team"},
        ),
    ],
)
def test_cutover_never_drops_historical_rows(alias, app, previous, current, model_name, values):
    connection = connections[alias]
    previous_targets = [(app, previous)]
    current_targets = [(app, current)]
    old_state = MigrationExecutor(connection).migrate(previous_targets)
    historical = old_state.apps.get_model(app, model_name).objects.using(alias)
    historical.create(**values)
    try:
        with pytest.raises(CommandError, match="Bascule interrompue"):
            call_command("check_legacy_bokebi")
        with pytest.raises(RuntimeError, match="Bascule interrompue"):
            MigrationExecutor(connection).migrate(current_targets)
        assert historical.count() == 1
    finally:
        historical.all().delete()
        call_command("check_legacy_bokebi")
        MigrationExecutor(connection).migrate(current_targets)
    assert not any("contactrequestrecord" in table or table == "surveys_surveyrecord"
                   for table in connection.introspection.table_names())
