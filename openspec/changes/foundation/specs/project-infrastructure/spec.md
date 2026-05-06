## ADDED Requirements

### Requirement: Docker Compose three-service orchestration
The system SHALL define a `docker-compose.yml` at the project root that orchestrates three services: `frontend` (Vue 3, port 3000), `api` (Flask, port 5000), and `qdrant` (port 6333). The `api` service MUST declare `depends_on: qdrant: condition: service_healthy` to prevent startup race conditions. The `qdrant` service MUST include a `healthcheck` using `curl -f http://localhost:6333/health`.

#### Scenario: All services start successfully
- **WHEN** `docker compose up` is run with a valid `.env` file present
- **THEN** all three services start without error, `frontend` is accessible at `http://localhost:3000`, and `api` health check at `http://localhost:5000/api/health` returns HTTP 200

#### Scenario: API waits for Qdrant to be healthy
- **WHEN** `docker compose up` is run and Qdrant takes more than 5 seconds to initialise
- **THEN** the `api` service does not start until the `qdrant` healthcheck passes, and no connection-refused errors appear in the `api` logs

### Requirement: Persistent volumes for data and uploads
The system SHALL define two named Docker volumes: `qdrant_data` (mounted into the `qdrant` service at its default data path) and `uploads` (mounted into the `api` service at `/app/uploads/`). Both volumes MUST persist across `docker compose down` (without `-v`).

#### Scenario: Data persists across container restart
- **WHEN** `docker compose down` is run (without `-v`) and then `docker compose up` is run again
- **THEN** previously ingested Qdrant vectors and uploaded files are still accessible; no data loss occurs

#### Scenario: Clean reset removes all data
- **WHEN** `docker compose down -v` is run
- **THEN** both named volumes are removed and a subsequent `docker compose up` starts with empty Qdrant collections and an empty uploads directory

### Requirement: Environment variable configuration via `.env`
The system SHALL read all secrets and configuration values from a `.env` file at the project root. A `.env.example` file MUST be committed to the repository containing all required variable names with placeholder values and inline comments describing each. The `.env` file MUST be listed in `.gitignore`. The application MUST fail fast at startup with a clear error message identifying any missing required variable.

Required variables: `LLM_PROVIDER`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `LLM_MODEL`, `EMBEDDING_MODEL`, `QDRANT_HOST`, `QDRANT_PORT`, `FLASK_SECRET_KEY`.

#### Scenario: Application starts with all required variables
- **WHEN** a `.env` file contains all required variables with valid values
- **THEN** `docker compose up` starts all services without environment-variable errors

#### Scenario: Missing required variable causes clear failure
- **WHEN** `OPENAI_API_KEY` is absent from the `.env` file
- **THEN** the `api` service exits at startup with a log message that names the missing variable (e.g., `"Missing required environment variable: OPENAI_API_KEY"`)

#### Scenario: `.env` is not committed to git
- **WHEN** `git status` is run after adding a `.env` file
- **THEN** the `.env` file does not appear in the staged or unstaged file list (it is gitignored)

### Requirement: Separate Dockerfiles for API and frontend services
The project SHALL include `Dockerfile.api` for the Flask backend (Python 3.11-slim base, installs `requirements.txt`) and `Dockerfile.frontend` for the Vue frontend (Node 20-alpine base for build, nginx-alpine for serve). The `docker-compose.yml` SHALL reference these Dockerfiles via `build.dockerfile`.

#### Scenario: Images build without errors
- **WHEN** `docker compose build` is run on a machine with Docker installed and internet access
- **THEN** both `api` and `frontend` images build successfully with exit code 0
