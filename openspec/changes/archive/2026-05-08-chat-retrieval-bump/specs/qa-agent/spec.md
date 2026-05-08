## MODIFIED Requirements

### Requirement: Agent tools are unit-testable with mocked Qdrant
The QA agent tools (`search_knowledge`, `search_private`, `get_entry`) SHALL be independently callable Python functions that accept a mocked Qdrant client. **Default `limit` for both `search_knowledge` and `search_private` SHALL be 10** (raised from 5 in the original implementation) so long documents whose relevant content sits at rank 6-10 are still surfaced.

#### Scenario: search_knowledge default limit is 10
- **WHEN** `search_knowledge(query)` is called without an explicit `limit`
- **THEN** the underlying QdrantService.search_knowledge is invoked with `limit=10`

#### Scenario: search_private default limit is 10
- **WHEN** `search_private(query)` is called without an explicit `limit`
- **THEN** the underlying QdrantService.search_private is invoked with `limit=10` AND the user_id filter

#### Scenario: caller can still override the limit
- **WHEN** `search_knowledge(query, limit=3)` is called explicitly
- **THEN** the request uses `limit=3`
