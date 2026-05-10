## 1. <!-- First task group: setup or scaffold -->

- [ ] 1.1 RED — <!-- failing test for first behavior -->
- [ ] 1.2 GREEN — <!-- minimal implementation to pass 1.1 -->
- [ ] 1.3 RED — <!-- next failing test -->
- [ ] 1.4 GREEN — <!-- minimal impl -->
- [ ] 1.Z Run superpowers:requesting-code-review on the diff for group 1; address CRITICAL/HIGH findings before moving on

## 2. <!-- Next task group: feature work -->

<!-- For frontend tasks that touch a VIEW / MODAL / named LAYOUT (>50 lines):
     sandwich the GREEN with MOCK + VISUAL DIFF tasks. Example: -->

- [ ] 2.1 MOCK — open docs/superpowers/specs/mocks/{{date}}-{{change}}-mocks.html#<anchor>; note Notion tokens used (bg-notion-*, text-notion-*) and verbatim text strings
- [ ] 2.2 RED — <!-- vitest case asserting wrapper.classes() includes the tokens -->
- [ ] 2.3 GREEN — <!-- implement the view -->
- [ ] 2.4 VISUAL DIFF — bring up dev stack (npm run dev:up); navigate to the route; eyeball rendered UI against the mock; fix any token/color/text drift
- [ ] 2.Z Run superpowers:requesting-code-review on the diff for group 2

## 3. <!-- Verification + ship -->

- [ ] 3.1 Run full pytest suite — ensure no regressions
- [ ] 3.2 Run full vitest suite — ensure no regressions
- [ ] 3.3 Run Playwright e2e suite (if applicable)
- [ ] 3.4 Run superpowers:verification-before-completion (cd backend && pytest; cd frontend && npm test; grep -r console.log frontend/src; diff review; grep -rn "search_private\|qdrant.*private" backend/app --include="*.py" | grep -v "user_id" — ensure no Qdrant private query is missing the user_id filter)
- [ ] 3.5 Final superpowers:requesting-code-review on the entire change diff
