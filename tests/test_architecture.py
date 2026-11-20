import ast
import sys
from pathlib import Path

from django.db import models, router

from contacts.models import HelpRequestRecord
from surveys.models import VoteReceipt, WorkplaceSurveyRecord


def test_domain_imports_only_standard_library_or_domain():
    for path in Path("domain").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                assert all(alias.name.split(".")[0] in sys.stdlib_module_names for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and not node.level:
                assert node.module.split(".")[0] in sys.stdlib_module_names | {"domain"}


def test_contacts_are_isolated_and_votes_have_no_individual_choices():
    assert router.db_for_read(HelpRequestRecord) == "contacts"
    assert router.db_for_write(HelpRequestRecord) == "contacts"
    assert router.allow_relation(HelpRequestRecord(), WorkplaceSurveyRecord()) is False
    assert router.allow_migrate("contacts", "contacts")
    assert not router.allow_migrate("default", "contacts")
    assert not router.allow_migrate("contacts", "surveys")
    assert router.allow_migrate("default", "surveys")
    assert {field.name for field in VoteReceipt._meta.fields} == {"id", "survey", "digest"}
    assert not any(isinstance(field, models.ForeignKey) for field in HelpRequestRecord._meta.fields)
