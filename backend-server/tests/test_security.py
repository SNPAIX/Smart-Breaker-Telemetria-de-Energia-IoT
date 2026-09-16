from app.core.security import (
    _DEV_FALLBACK_KEY,
    _warn_if_insecure_key,
    get_password_hash,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = get_password_hash("mi-contraseña-segura")
    assert verify_password("mi-contraseña-segura", hashed) is True


def test_wrong_password_fails_verification():
    hashed = get_password_hash("mi-contraseña-segura")
    assert verify_password("otra-cosa", hashed) is False


def test_malformed_stored_hash_returns_false_instead_of_raising():
    # Si el hash guardado en la BD estuviera corrupto o no fuera un hash
    # bcrypt válido, verify_password no debe tumbar el login con una
    # excepción sin manejar — debe tratarlo como credencial inválida.
    assert verify_password("cualquier-cosa", "esto-no-es-un-hash-bcrypt") is False


def test_warns_when_using_insecure_fallback_key(caplog):
    with caplog.at_level("WARNING"):
        _warn_if_insecure_key(_DEV_FALLBACK_KEY)
    assert any(record.msg == "insecure_secret_key_in_use" for record in caplog.records)


def test_no_warning_when_using_a_real_key(caplog):
    with caplog.at_level("WARNING"):
        _warn_if_insecure_key("una-clave-real-configurada-por-el-usuario")
    assert not any(record.msg == "insecure_secret_key_in_use" for record in caplog.records)
