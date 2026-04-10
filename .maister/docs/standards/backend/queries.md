## Database Queries

### Parameterized Queries
Always use parameterized queries or ORM methods; never interpolate user input into SQL.

### Avoid N+1
Use eager loading or joins to fetch related data in one query.

### Select Only Needed Columns
Request only the columns you need rather than SELECT *.

### Index Strategic Columns
Index columns used in WHERE, JOIN, and ORDER BY clauses.

### Transactions
Wrap related operations in transactions to maintain consistency.

### Query Timeouts
Set timeouts to prevent runaway queries from impacting performance.

### Cache Expensive Queries
Cache results of complex or frequent queries when appropriate.

### Hybrid Storage -- SQLite + JSON
SQLite (`robopong.db`, 11 tables) for relational data. File-based JSON for factory defaults + user overrides. Presets in separate `presets.db`. Pattern: `_default.json` (factory) + `._user.json` (user overrides).

### Session Role Management
WebSocket sessions have roles: CONTROLLER (commands), OBSERVER (read-only), PENDING. Force takeover protocol for control handoff.
