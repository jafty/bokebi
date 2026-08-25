import ast
from pathlib import Path

def test_domain_has_no_framework_or_io_imports():
    forbidden = {"django", "requests", "urllib", "pathlib", "socket", "sqlite3", "psycopg"}
    imports = set()
    for file in Path("domain").glob("*.py"):
        for node in ast.walk(ast.parse(file.read_text())):
            if isinstance(node, ast.Import): imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module: imports.add(node.module.split(".")[0])
    assert not imports & forbidden

def test_contact_model_has_no_survey_or_answer_link():
    tree = ast.parse(Path("contacts/models.py").read_text())
    assert all(not (isinstance(node, ast.Name) and node.id in {"ForeignKey", "OneToOneField", "ManyToManyField"}) for node in ast.walk(tree))
