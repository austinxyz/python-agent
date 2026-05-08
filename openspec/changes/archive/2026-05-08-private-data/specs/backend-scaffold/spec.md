## ADDED Requirements

### Requirement: SQLite private_entries and notes tables created at startup
The system SHALL create `private_entries` and `notes` tables idempotently at application startup via `_ensure_private_tables()` in `DatabaseService`. The tables SHALL be added to `backend/db/schema.sql`.

Schema:
```sql
CREATE TABLE IF NOT EXISTS private_entries (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    template_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    title TEXT NOT NULL,
    directory TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    chat_ref TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

#### Scenario: Tables created when absent
- **WHEN** the Flask app starts with a fresh SQLite database
- **THEN** `private_entries` and `notes` tables exist after startup

#### Scenario: Startup is idempotent on existing tables
- **WHEN** the Flask app starts and the tables already exist
- **THEN** no error is raised and the existing data is preserved
