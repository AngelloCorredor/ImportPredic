from src.auth import security


def test_hash_y_verificacion():
    h = security.hash_password("Clave1234")
    assert h.startswith("scrypt$") and "Clave1234" not in h
    assert security.verify_password("Clave1234", h)
    assert not security.verify_password("clave1234", h)
    assert security.hash_password("Clave1234") != h  # sal aleatoria


def test_hash_corrupto_no_explota():
    assert not security.verify_password("x", "basura")
    assert not security.verify_password("x", "bcrypt$1$2$3$4$5")


def test_politica_de_contrasenas():
    assert security.validate_password_policy("corta1")
    assert security.validate_password_policy("sololetras")
    assert security.validate_password_policy("antony123", username="antony")
    assert security.validate_password_policy("Importacion2026") == []


def test_firma_de_artefactos():
    k = b"k"
    firma = security.sign_bytes(b"datos", k)
    assert security.verify_signature(b"datos", firma, k)
    assert not security.verify_signature(b"datoz", firma, k)
    assert not security.verify_signature(b"datos", firma, b"otra")
