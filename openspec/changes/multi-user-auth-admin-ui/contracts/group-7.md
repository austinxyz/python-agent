# Contract: Group 7 — CLAUDE.md update: UI primary, CLI fallback

## Spec

SHALL statements:
- CLAUDE.md SHALL contain language positioning `/admin/users` web UI as the primary path for user management
- CLAUDE.md SHALL contain language positioning the CLI (`python -m app.cli.invite_user`) as emergency fallback (admin locked out / JS broken / debugging)

## Runtime

```
cd backend && pytest tests/test_claude_md.py -v
```

Expected: all assertions pass.

## Code

- Documentation-only update to `CLAUDE.md`
- Reposition the "Inviting users" section: `/admin/users` web UI is the standard path; CLI is kept for emergencies
- Critical for future sessions: without this, agents default back to CLI which breaks the multi-user UX intent

## Threshold

80
