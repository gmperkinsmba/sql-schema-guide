# voodooSQL

Give an analyst the schema details they need before writing a query.

**First principle:**

Help an agent write correct SQL on a new schema. Show evidence for each query. This helps the agent explain it and need fewer fixes.

This local prototype scans an included made-up SQLite database. It shows the schema and evidence about table links. It finds reviewed query examples and runs them with read-only access. It does not connect to outside databases or use a language model.

## Run

You need Python 3.10 or newer. No third-party packages are needed.

```sh
python3 server.py
```

Open http://127.0.0.1:8332. The page gets a request token for local actions each time it starts. Stop the server with Ctrl+C.

## Use

- Browse tables and columns in Schema map.
- Use Query pack to run parameterized examples.
- Ask a question to find the right recipe. If a metric has no definition, the app asks you to define it.
- Run Evaluation to check payment totals. It checks current and as-of history. It checks customer IDs built from several fields. It also checks when the app asks for clarification.
- Settings shows this build's source and motion control. Reduce motion also follows your system setting.

## Test

```sh
python3 -m unittest discover -s tests -v
```

## Limits

The only supported database is SQLite. Schema discovery is complete for the main schema shown in the included file. The adapter cannot apply SQLite file permission filters. It does not inspect attached databases. The app records foreign-key details and connection checks separately. Guessed links are not approved joins. Queries return up to 200 rows. They stop at 1.2 seconds or 200,000 instructions. Evaluation uses only this made-up fixture. There is no model benchmark. The app makes no accuracy claim.

On first run, the app creates the fixture at `~/.voodoosql/demo.sqlite`. Runtime files stay outside this repository. This prototype has no credential feature. Do not put real databases in this repository.

The separate catalog API is `Catalog.from_sqlite(path, allowed_schemas=None)`. It returns key evidence in order. It also reports whether the catalog is complete. `CatalogSnapshot.to_graph()` exports graphify-compatible JSON. `save_catalog(snapshot)` stores metadata in `~/.voodoosql/catalog.sqlite`. Use this adapter for approved SQLite metadata sources. The UI and example recipes still use only the fixture.

## Data choice

The app uses a made-up SQLite fixture only. It has no real schema or customer data. It has no secrets or outside connection details.
