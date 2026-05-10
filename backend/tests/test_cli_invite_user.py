"""CLI invite tool — `python -m app.cli.invite_user <email> [role]`."""
import sqlite3

from app.cli.invite_user import main
from app.services.auth_service import canonicalize_email
from app.services.db_service import DatabaseService


class TestInviteUserCLI:
    def test_creates_user_and_token_prints_url(self, capsys):
        DatabaseService()  # apply schema
        rc = main(["wife@gmail.com", "member"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Invite URL:" in out
        assert "/accept-invite?token=" in out

        # User row exists
        db = DatabaseService()
        with db.connection() as conn:
            row = conn.execute(
                "SELECT email, role, status FROM users WHERE email = ?",
                ("wife@gmail.com",),
            ).fetchone()
            assert row is not None
            assert row[0] == "wife@gmail.com"
            assert row[1] == "member"
            assert row[2] == "invited"
            tokens = conn.execute(
                "SELECT COUNT(*) FROM invite_tokens WHERE user_id = "
                "(SELECT id FROM users WHERE email = ?)",
                ("wife@gmail.com",),
            ).fetchone()[0]
            assert tokens == 1

    def test_default_role_is_member(self, capsys):
        DatabaseService()
        rc = main(["uncle@example.com"])
        assert rc == 0
        with DatabaseService().connection() as conn:
            row = conn.execute(
                "SELECT role FROM users WHERE email = ?", ("uncle@example.com",)
            ).fetchone()
            assert row[0] == "member"

    def test_canonicalizes_email(self, capsys):
        DatabaseService()
        rc = main(["  Austin@Gmail.COM  ", "admin"])
        assert rc == 0
        with DatabaseService().connection() as conn:
            row = conn.execute(
                "SELECT email FROM users WHERE email = ?", ("austin@gmail.com",)
            ).fetchone()
            assert row is not None

    def test_duplicate_email_exits_nonzero(self, capsys):
        DatabaseService()
        main(["a@b.com"])
        capsys.readouterr()  # clear
        rc = main(["a@b.com"])
        assert rc != 0
        err = capsys.readouterr().err
        assert "already exists" in err

    def test_invalid_role_returns_error(self, capsys):
        DatabaseService()
        rc = main(["a@b.com", "superuser"])
        assert rc == 2

    def test_invalid_email_returns_error(self, capsys):
        DatabaseService()
        rc = main(["not-an-email"])
        assert rc == 2

    def test_missing_args_returns_usage(self, capsys):
        DatabaseService()
        rc = main([])
        assert rc == 2
        err = capsys.readouterr().err
        assert "Usage" in err
