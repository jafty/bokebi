# Architecture guidelines

## Dependency rule

`domain/` is the innermost hexagon. It contains immutable entities/value-like identifiers, use-case interactors, and abstract ports. It may import only the Python standard library and itself. It must never import Django, an ORM, network, filesystem, or database package. `tests/test_architecture.py` enforces this boundary.

Django is an outer adapter. Views translate HTTP input into use-case arguments and translate results into templates. Repository adapters implement domain ports and map ORM records to domain entities. Token generation, password hashing, and the clock are gateways because each touches infrastructure or nondeterminism.

## Domain rules

* A survey is created without an account and receives an unpredictable public ID and a 128-bit deletion key. Only a hash of the deletion key is persisted, so the creator must retain it.
* Every participation contains exactly the five standardized answers; each answer is an integer from 1 through 5.
* Results contain no averages until at least three participations exist.
* Contact is optional and occurs only after answer submission.
* A contact record contains only an email and contact preferences. It contains no survey ID, participation ID, timestamp imported from the answers database, foreign key, or other correlation token.
* Survey/answer data and contact data use distinct PostgreSQL databases. Django's router prevents contact models migrating to or relating with the survey database.

This deliberate non-linkability means Bokebi cannot automatically determine which survey led to an opt-in. Operational contact workflows must preserve that guarantee rather than add correlation metadata later.

## Pseudo-TDD

Implement the smallest complete behavior directly, with one fast isolated test for every success, boundary, and error variation. Domain tests use hand-written in-memory port implementations—never mocks, patching, `unittest.mock`, or `MagicMock`. Adapter tests are separate and may use Django's test database. A new use case is incomplete until its domain variations are covered.

## Direction of change

1. Express business language in domain entities and ports.
2. Add or update isolated stub-based tests.
3. Implement the interactor without infrastructure imports.
4. Implement repository/gateway adapters.
5. Wire the adapter in a thin controller and render a template.
