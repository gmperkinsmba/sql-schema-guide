# Domain

## Catalog snapshot
The snapshot records visible SQLite objects, columns, ordered primary keys, declared foreign keys and a schema fingerprint.
An empty relationship list does not prove that no business relationship exists.
The adapter cannot report permission-limited SQLite metadata beyond what the opened file exposes.

## Relationship evidence
Declared keys come from SQLite metadata. Inferred links are separate and marked for review.
Enforcement reports the source connection's foreign-key setting; it does not claim universal enforcement.
Many-to-many links pass through a bridge table and may change row counts.

## Query pack
Recipes state expected output grain, join logic and source fingerprint.
The executor allows bounded, parameterized, read-only SELECT statements.
Unknown business definitions require clarification.

## Evaluation fixture
The included customers, orders, lines, payments, history, tags and bridge rows are fabricated.
Evaluation checks canonical result values, composite identity, fan-out and latest-history selection.
