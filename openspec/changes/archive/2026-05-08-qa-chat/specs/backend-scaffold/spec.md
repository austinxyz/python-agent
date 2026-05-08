## ADDED Requirements

### Requirement: SQLite chat tables created at startup
The system SHALL create `chat_sessions` and `chat_messages` tables idempotently at application startup via `_ensure_chat_tables()` in `DatabaseService`. The tables SHALL be added to `backend/db/schema.sql`.

Schema:
```sql
CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT 'haiku',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('user','assistant')),
    content TEXT NOT NULL,
    sources TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

#### Scenario: Tables created when absent
- **WHEN** the Flask app starts with a fresh SQLite database
- **THEN** `chat_sessions` and `chat_messages` tables exist after startup

#### Scenario: Startup is idempotent on existing tables
- **WHEN** the Flask app starts and the tables already exist
- **THEN** no error is raised and the existing data is preserved
