"""Authentication and authorization security tests."""

from app.core.security import decode_token


def test_login_success(client, seeded):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    payload = decode_token(data["access_token"], expected_type="access")
    assert payload["email"] == "admin@example.com"


def test_login_invalid_password(client, seeded):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_disabled_user_cannot_authenticate(client, seeded):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "disabled@example.com", "password": "DisabledPass123!"},
    )
    assert response.status_code == 401
    assert "disabled" in response.json()["error"]["message"].lower()


def test_me_requires_auth(client, seeded):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_permissions(client, seeded):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    token = login.json()["access_token"]
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "admin@example.com"
    assert "users:manage" in body["permissions"]


def test_readonly_cannot_create_users(client, seeded):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "readonly@example.com", "password": "ReadPass123!"},
    )
    token = login.json()["access_token"]
    response = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "new.user@example.com",
            "password": "NewUserPass123!",
            "first_name": "New",
            "last_name": "User",
            "role_codes": ["standard_user"],
        },
    )
    assert response.status_code == 403


def test_admin_can_create_users(client, seeded):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    token = login.json()["access_token"]
    response = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "new.user@example.com",
            "password": "NewUserPass123!",
            "first_name": "New",
            "last_name": "User",
            "role_codes": ["standard_user"],
        },
    )
    assert response.status_code == 201
    assert response.json()["email"] == "new.user@example.com"


def test_refresh_and_revoke(client, seeded):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    tokens = login.json()
    refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh.status_code == 200
    new_refresh = refresh.json()["refresh_token"]

    # Old refresh should be revoked after rotation
    reused = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert reused.status_code == 401

    # Logout revokes current refresh
    access = refresh.json()["access_token"]
    logout = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access}"},
        json={"refresh_token": new_refresh},
    )
    assert logout.status_code == 200
    after_logout = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_refresh},
    )
    assert after_logout.status_code == 401


def test_roles_list_requires_permission(client, seeded):
    # standard path: readonly has roles:read? No — read_only has AUDIT_READ etc but
    # ROLE_PERMISSION_MAP for READ_ONLY does NOT include roles:read
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "readonly@example.com", "password": "ReadPass123!"},
    )
    token = login.json()["access_token"]
    response = client.get(
        "/api/v1/roles",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
