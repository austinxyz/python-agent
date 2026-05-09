"""argon2id password hashing — auth_service.hash_password / verify_password."""
from app.services.auth_service import hash_password, verify_password


class TestHashPassword:
    def test_returns_argon2id_string(self):
        h = hash_password("hello12345")
        assert h.startswith("$argon2id$"), f"expected argon2id prefix, got {h[:30]}"

    def test_unique_salts(self):
        a = hash_password("samepw")
        b = hash_password("samepw")
        assert a != b, "different invocations must produce different hashes (unique salt)"


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        h = hash_password("hello12345")
        assert verify_password(h, "hello12345") is True

    def test_wrong_password_returns_false(self):
        h = hash_password("hello12345")
        assert verify_password(h, "wrong") is False

    def test_empty_inputs_return_false(self):
        h = hash_password("hello12345")
        assert verify_password(h, "") is False
        assert verify_password("", "hello12345") is False

    def test_malformed_hash_returns_false(self):
        # never raises; just returns False
        assert verify_password("not-a-hash", "anything") is False

    def test_none_inputs_return_false(self):
        assert verify_password(None, "x") is False
        assert verify_password("x", None) is False
