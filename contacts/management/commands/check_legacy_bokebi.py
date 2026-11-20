from django.core.management.base import BaseCommand, CommandError
from django.db import connections

LEGACY_TABLES = {
    "default": ("surveys_surveyrecord", "surveys_participationrecord"),
    "contacts": ("contacts_contactrequestrecord",),
}


class Command(BaseCommand):
    help = "Vérifie que les deux bases historiques sont vides avant la bascule."

    def handle(self, *args, **options):
        for alias, legacy_tables in LEGACY_TABLES.items():
            connection = connections[alias]
            with connection.cursor() as cursor:
                tables = connection.introspection.table_names(cursor)
                for table in legacy_tables:
                    if table in tables:
                        cursor.execute(f"SELECT 1 FROM {connection.ops.quote_name(table)} LIMIT 1")
                        if cursor.fetchone() is not None:
                            raise CommandError(f"La table historique {table} contient des données. Bascule interrompue.")
