from datetime import datetime, timezone

import pytest
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
    try:
        row = historical.create(**values)
        state = MigrationExecutor(connection).migrate(current_targets)
        assert historical.filter(pk=row.pk).exists()
        with pytest.raises(LookupError):
            state.apps.get_model(app, model_name)
    finally:
        historical.all().delete()
