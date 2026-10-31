# Security

SQL Schema Guide opens SQLite read-only and enables query-only mode. Its authorizer allows read operations and a small function list. Query size, row count, runtime, and instruction use are capped. The app runs fixed reviewed recipes with parameters and checks a schema fingerprint before use. SHA-256 helps detect schema changes against a stored fingerprint; it does not encrypt database contents. Use a made-up database in reports.

The SQLite database remains plaintext and follows account permissions. Use your Mac’s disk encryption to protect saved files. The native app has an ad-hoc code signature. This lets the installer check whether its files changed. It does not prove who made the app. The build is not notarized.

Report security issues through [GitHub private vulnerability reporting](https://github.com/gmperkinsmba/sql-schema-guide/security/advisories/new).
