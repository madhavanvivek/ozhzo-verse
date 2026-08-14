from src.core.security import hash_password, verify_password, create_access_token, decode_token


def test_password_hashing():
    raw_password = "SecretPassword123!"
    hashed = hash_password(raw_password)
    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_generation_and_decoding():
    subject = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    home_id = "7fa85f64-5717-4562-b3fc-2c963f66afa7"
    token = create_access_token(subject=subject, active_home_id=home_id)
    assert isinstance(token, str)

    payload = decode_token(token)
    assert payload["sub"] == subject
    assert payload["home_id"] == home_id
    assert payload["type"] == "access"
