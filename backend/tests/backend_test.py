"""Regression coverage for EventAtlas public discovery, auth, and admin CRUD APIs."""
import os
import uuid

import pytest
import requests


def _base_url():
    value = os.environ.get("REACT_APP_BACKEND_URL")
    if not value:
        env_path = "/app/frontend/.env"
        with open(env_path, encoding="utf-8") as env_file:
            for line in env_file:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    value = line.strip().split("=", 1)[1]
                    break
    assert value, "REACT_APP_BACKEND_URL is required"
    return value.rstrip("/")


BASE_URL = _base_url()


@pytest.fixture
def client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def test_discovery_events_are_seeded(client):
    response = client.get(f"{BASE_URL}/api/events")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 5
    assert body["items"]
    assert all("id" in event and event["status"] == "published" for event in body["items"])


def test_featured_and_detail_are_consistent(client):
    featured = client.get(f"{BASE_URL}/api/events/featured")
    assert featured.status_code == 200
    items = featured.json()
    assert items and all(event["featured"] for event in items)
    detail = client.get(f"{BASE_URL}/api/events/{items[0]['id']}")
    assert detail.status_code == 200
    assert detail.json()["name"] == items[0]["name"]


def test_filters_and_pagination(client):
    filtered = client.get(f"{BASE_URL}/api/events", params={"search": "Barcelona"})
    assert filtered.status_code == 200
    assert filtered.json()["total"] >= 1
    paged = client.get(f"{BASE_URL}/api/events", params={"page": 2, "limit": 2})
    assert paged.status_code == 200
    assert paged.json()["page"] == 2


def test_auth_cookie_me_and_unauthenticated_mutation(client):
    unauth = client.post(f"{BASE_URL}/api/events", json={})
    assert unauth.status_code == 401
    login = client.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@eventatlas.com", "password": "admin123"})
    assert login.status_code == 200
    assert "access_token" in login.cookies
    assert login.cookies.get_dict()["access_token"]
    me = client.get(f"{BASE_URL}/api/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "admin"


def test_admin_crud_persists_and_deletes(client):
    login = client.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@eventatlas.com", "password": "admin123"})
    assert login.status_code == 200
    payload = {
        "name": f"TEST_Event_{uuid.uuid4().hex[:8]}",
        "description": "A regression event with enough descriptive text.",
        "category": "Conference", "industry": "Technology",
        "start_date": "2026-09-10", "end_date": "2026-09-11",
        "venue": "Test Hall", "city": "London", "country": "United Kingdom",
        "organizer": "Test Organizer", "organizer_email": "test@example.com",
        "website": "https://example.com", "image_url": "https://example.com/image.jpg",
        "status": "draft", "featured": False,
    }
    created = client.post(f"{BASE_URL}/api/events", json=payload)
    assert created.status_code == 200
    event_id = created.json()["id"]
    try:
        fetched = client.get(f"{BASE_URL}/api/events/{event_id}")
        assert fetched.status_code == 200
        assert fetched.json()["name"] == payload["name"]
        updated_payload = {**payload, "name": payload["name"] + " Updated"}
        updated = client.put(f"{BASE_URL}/api/events/{event_id}", json=updated_payload)
        assert updated.status_code == 200
        assert updated.json()["name"].endswith("Updated")
        deleted = client.delete(f"{BASE_URL}/api/events/{event_id}")
        assert deleted.status_code == 200
        assert client.get(f"{BASE_URL}/api/events/{event_id}").status_code == 404
    finally:
        client.delete(f"{BASE_URL}/api/events/{event_id}")