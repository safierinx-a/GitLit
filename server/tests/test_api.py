"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from server.src.api.app import app, init_app
from server.src.core.config import SystemConfig
from server.src.core.exceptions import ValidationError


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def config():
    """Test configuration"""
    return SystemConfig.create_default()


class TestAPIEndpoints:
    """Test REST API endpoints"""

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "starting"]

    def test_get_patterns(self, client):
        """Test pattern listing endpoint"""
        response = client.get("/api/patterns")
        assert response.status_code == 200
        patterns = response.json()
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        # Verify pattern structure
        pattern = patterns[0]
        assert "name" in pattern
        assert "category" in pattern
        assert "parameters" in pattern

    def test_set_pattern(self, client):
        """Test pattern setting endpoint"""
        # Set solid pattern
        response = client.post(
            "/api/patterns/solid",
            json={"parameters": {"red": 255, "green": 0, "blue": 0}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Verify pattern was set
        response = client.get("/api/state")
        assert response.status_code == 200
        state = response.json()
        assert state["active_pattern"] == "solid"

    def test_invalid_pattern(self, client):
        """Test setting invalid pattern"""
        response = client.post("/api/patterns/nonexistent", json={"parameters": {}})
        assert response.status_code == 422

    def test_pattern_validation(self, client):
        """Test pattern parameter validation"""
        # Invalid parameters
        response = client.post(
            "/api/patterns/solid",
            json={
                "parameters": {
                    "red": 300,  # Invalid value
                    "green": 0,
                    "blue": 0,
                }
            },
        )
        assert response.status_code == 422


class TestWebSocket:
    """Test WebSocket functionality"""

    async def test_websocket_connection(self, client):
        """Test WebSocket connection"""
        with client.websocket_connect("/ws") as websocket:
            # Should receive initial state
            data = websocket.receive_json()
            assert "type" in data
            assert data["type"] == "state"

    async def test_frame_broadcast(self, client):
        """Test frame broadcasting"""
        with client.websocket_connect("/ws") as websocket:
            # Set a pattern to trigger frame generation
            client.post(
                "/api/patterns/solid",
                json={"parameters": {"red": 255, "green": 0, "blue": 0}},
            )

            # Should receive frames
            data = websocket.receive_bytes()
            assert len(data) > 0  # Frame data


class TestErrorHandling:
    """Test API error handling"""

    def test_validation_errors(self, client):
        """Test parameter validation errors"""
        response = client.post(
            "/api/patterns/solid", json={"parameters": {"invalid_param": 123}}
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_system_errors(self, client):
        """Test system error handling"""
        # Stop the system
        client.post("/api/system/stop")

        # Try to set pattern while stopped
        response = client.post("/api/patterns/solid", json={"parameters": {}})
        assert response.status_code == 503  # Service Unavailable
