from server.core.security import PasswordHasher


def test_hash_returns_bcrypt_digest_different_from_plain():
    hasher = PasswordHasher()
    hashed = hasher.hash("SecretPass1")

    assert hashed != "SecretPass1"
    assert hashed.startswith("$2")


def test_verify_returns_true_for_matching_password():
    hasher = PasswordHasher()
    hashed = hasher.hash("SecretPass1")

    assert hasher.verify("SecretPass1", hashed) is True


def test_verify_returns_false_for_wrong_password():
    hasher = PasswordHasher()
    hashed = hasher.hash("SecretPass1")

    assert hasher.verify("WrongPass1", hashed) is False


def test_hash_produces_unique_salts():
    hasher = PasswordHasher()
    first = hasher.hash("SecretPass1")
    second = hasher.hash("SecretPass1")

    assert first != second
    assert hasher.verify("SecretPass1", first)
    assert hasher.verify("SecretPass1", second)
