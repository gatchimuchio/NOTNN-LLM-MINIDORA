from fastapi.testclient import TestClient

from minidora.api import create_app


def test_openai_chat(tmp_path):
    client = TestClient(create_app(tmp_path / "api.sqlite3", admin_auth_required=False))
    response = client.post("/v1/chat/completions", json={
        "model": "minidora-notnn-1",
        "messages": [{"role": "user", "content": "Project Atlasは文書をどこに保存していますか？"}],
        "reasoning_effort": "high",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["minidora"]["status"] == "PASS"
    assert "/srv/aurora" in body["choices"][0]["message"]["content"]


def test_stream(tmp_path):
    client = TestClient(create_app(tmp_path / "api.sqlite3", admin_auth_required=False))
    response = client.post("/v1/chat/completions", json={
        "model": "minidora-notnn-1",
        "messages": [{"role": "user", "content": "Aurora Indexは何ができますか？"}],
        "stream": True,
    })
    assert response.status_code == 200
    assert "data: [DONE]" in response.text


def test_admin_fail_closed(tmp_path):
    client = TestClient(create_app(tmp_path / "api.sqlite3", admin_auth_required=True))
    assert client.post("/api/v1/admin/doctor").status_code == 403


def test_request_limit(tmp_path):
    client = TestClient(create_app(tmp_path / "api.sqlite3", admin_auth_required=False, max_request_bytes=1024))
    response = client.post("/v1/chat/completions", json={
        "model": "minidora-notnn-1",
        "messages": [{"role": "user", "content": "x" * 2000}],
    })
    assert response.status_code == 413
