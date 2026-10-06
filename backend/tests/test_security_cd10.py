import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_mock_router_disabled_by_default():
    # Khi ENABLE_MOCK_ROUTER = False (default), route /api/v1/mock không được mount
    response = client.post("/api/v1/mock/retrieve", json={"query": "test"})
    assert response.status_code == 404

def test_chat_error_sanitization():
    # Khi retrieval gặp exception bất ngờ, trả 500 nhưng không rò rỉ exception traceback / internal error message
    with patch("app.api.endpoints.chat.retrieve_with_dynamic_routing", side_effect=ValueError("Secret DB connection failed")):
        response = client.post("/api/v1/chat", json={"query": "Học phí UTH năm 2026"})
        assert response.status_code == 500
        data = response.json()
        assert "Secret DB connection failed" not in data.get("detail", "")
        assert "nội bộ" in data.get("detail", "")

def test_cors_origins_config():
    # Kiểm tra settings parse cors_origins_list đúng từ string comma-separated
    assert isinstance(settings.cors_origins_list, list)
    assert len(settings.cors_origins_list) >= 1
