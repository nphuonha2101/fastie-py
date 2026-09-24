def test_register_login_profile_and_refresh(client):
    credentials = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "correct-horse-battery-staple",
    }

    registered = client.post("/api/v1/user/register", json=credentials)
    assert registered.status_code == 201

    issued = client.post(
        "/api/v1/auth/token",
        data={
            "username": credentials["email"],
            "password": credentials["password"],
        },
    )
    assert issued.status_code == 200
    tokens = issued.json()
    assert tokens["token_type"] == "bearer"

    profile = client.get(
        "/api/v1/auth/profile",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert profile.status_code == 200
    assert profile.json()["data"]["user"]["email"] == credentials["email"]

    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refreshed.status_code == 200
    rotated_tokens = refreshed.json()
    assert rotated_tokens["refresh_token"] != tokens["refresh_token"]

    reused = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert reused.status_code == 401
    assert reused.json()["detail"] == "Refresh token reuse detected"

    family_token_reuse = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": rotated_tokens["refresh_token"]},
    )
    assert family_token_reuse.status_code == 401
    assert family_token_reuse.json()["detail"] == "Refresh token reuse detected"
