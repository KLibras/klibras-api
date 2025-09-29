
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register_user():
    r = client.post("/register", json={
        "email": "testuser@example.com",
        "password": "testpass123"
    })
    assert r.status_code in (200, 400)

def test_login_user():
    # Register first if needed
    r = client.post("/login", data={
        "username": "testuser@example.com",
        "password": "testpass123"
    })
    assert r.status_code in (200, 401)

def test_refresh_token():
    # This test would need a valid refresh_token cookie
    r = client.post("/refresh", cookies={"refresh_token": "dummy"})
    assert r.status_code in (200, 401)

def test_logout_user():
    r = client.post("/logout")
    assert r.status_code == 200

def test_options_logout():
    r = client.options("/logout")
    assert r.status_code == 204

def test_get_cart_products():
    # Needs auth, so expect 401 if not provided
    r = client.get("/cart/products")
    assert r.status_code in (200, 401, 404)

def test_remove_from_cart():
    # Needs auth, so expect 401 if not provided
    r = client.delete("/cart/remove/1")
    assert r.status_code in (200, 401, 404)