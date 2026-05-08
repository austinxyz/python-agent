## Context

Single-line decision: raise default top-k from 5 to 10 for both
`search_knowledge` and `search_private`. Direct response to a real
recall failure on 2026-05-08 (FBAR/FATCA query against a long private
file).

## Decisions

### 1. Why 10, not 15 or 20

- Doubling is the smallest meaningful bump.
- 10 chunks × ~2000 chars × 2 scopes ≈ 40k chars ≈ ~15k tokens. Well
  under Haiku 4.5's 200k context window.
- More than 10 starts to noise-up the LLM's context for typical
  questions; revisit only if specific failure cases need it.

### 2. Why a default change, not a per-call override

- The chat path always wants more recall. Plumbing a `top_k` parameter
  through `run_agent` → route → frontend just moves the same default
  decision elsewhere.
- Tools still expose `limit` as a kwarg for any direct-call test or
  future agent code that wants tighter control.

## Risks

- **Latency**: +1-2s per turn. Acceptable.
- **Token cost**: ~$0.005 extra per turn at Haiku rates. Negligible.
- **Hallucination from extra noise**: LLM tends to ignore irrelevant
  chunks; if this becomes a problem, re-ranking is the next move
  (separate change).
