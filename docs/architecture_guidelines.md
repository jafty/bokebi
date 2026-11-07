# Architecture guidelines

## Dependency rule

`domain/` is the innermost hexagon. It contains immutable entities/value-like identifiers, use-case interactors, and abstract ports. It may import only the Python standard library and itself. It must never import Django, an ORM, network, filesystem, or database package. `tests/test_architecture.py` enforces this boundary.

Django is an outer adapter. Views translate HTTP input into use-case arguments and translate results into templates. Repository adapters implement domain ports and map ORM records to domain entities. Token generation, password hashing, and the clock are gateways because each touches infrastructure or nondeterminism.

## Domain rules

* A survey is created without an account and receives an unpredictable public ID and a high-entropy deletion key (legacy keys remain valid). Only a hash of the deletion key is persisted.
* Every participation contains exactly the five standardized answers; each answer is an integer from 1 through 5.
* Results contain no averages until at least three participations exist.
* Contact is optional and occurs only after answer submission.
* A contact record contains an email, contact preferences, a workplace/group label and operational timestamps. It contains no survey ID, participation ID, timestamp imported from the answers database, or foreign key.
* Survey/answer data and contact data use distinct PostgreSQL databases. Django's router prevents contact models migrating to or relating with the survey database.

The group label supports manual matching but can identify a workplace and may be shared by unrelated surveys. The separate databases do not guarantee anonymity or prevent correlation through labels, timing, or other information. Operational workflows must account for these limitations.

## Pseudo-TDD

Implement the smallest complete behavior directly, with one fast isolated test for every success, boundary, and error variation. Domain tests use hand-written in-memory port implementations—never mocks, patching, `unittest.mock`, or `MagicMock`. Adapter tests are separate and may use Django's test database. A new use case is incomplete until its domain variations are covered.

## Direction of change

1. Express business language in domain entities and ports.
2. Add or update isolated stub-based tests.
3. Implement the interactor without infrastructure imports.
4. Implement repository/gateway adapters.
5. Wire the adapter in a thin controller and render a template.

## Measuring domain tests

Install development dependencies with `pip install -r requirements-dev.txt`,
then run `scripts/check-domain.sh` from the repository root with the virtual
environment activated. The script requires 100% branch and statement coverage
of `domain/` using only the isolated domain tests, and fails if mutmut reports
any surviving, untested, timed-out, or otherwise unresolved mutant. It removes
the generated `mutants/` cache before each run so test mappings are fresh.
The normal full suite remains `SECRET_KEY=test-secret pytest -q`.

Mutation testing is evidence, not proof that all requirements or defects have
been discovered. Mutmut 3.3.1 does not mutate dataclass bodies or module-level
constants. Business decisions in dataclass methods therefore delegate to named
functions that mutmut can mutate; thin delegation, entity fields, port
signatures, and question text are still outside its mutation scope. Review those
boundaries and the generated mutation results when the domain changes. Do not
weaken assertions or exclude mutations merely to reach a score.

## Product safety and operator workflow

Names are not requested with answers, but the three-response threshold does not prevent inference, especially as results change over time. Contact labels and timestamps can also allow correlation. Staff must verify that requests belong to the same group and obtain agreement before connecting people; a matching label alone is insufficient. Deleting a survey does not delete separate contact requests. Avoid claims of guaranteed anonymity, invented response deadlines, or unverified partnerships.
