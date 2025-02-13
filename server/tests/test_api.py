"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient

from gitlit.api.app import app, init_app
from gitlit.core.config import SystemConfig
from gitlit.core.exceptions import ValidationError
from gitlit.core.control import SystemController
from gitlit.core.transactions import TransactionContext, TransactionManager


@pytest.fixture
def transaction_manager():
    """Create a test transaction manager"""
    return TransactionManager()


@pytest.fixture
async def async_controller(transaction_manager):
    """Create a test controller for async tests"""
    config = SystemConfig.create_default()
    controller = SystemController(config, transaction_manager=transaction_manager)
    await controller.start()
    yield controller
    await controller.stop()


@pytest.fixture
def controller(transaction_manager):
    """Create a test controller for sync tests"""
    import asyncio

    config = SystemConfig.create_default()
    controller = SystemController(config, transaction_manager=transaction_manager)
    # Run start synchronously
    asyncio.get_event_loop().run_until_complete(controller.start())
    yield controller
    # Run stop synchronously
    asyncio.get_event_loop().run_until_complete(controller.stop())


@pytest.fixture
def client(controller):
    """Create a test client with initialized controller"""
    app = init_app(controller)
    return TestClient(app)


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
        # Set solid pattern with valid parameters
        response = client.post(
            "/api/patterns/solid",
            json={
                "parameters": {
                    "red": 255,
                    "green": 0,
                    "blue": 0,
                }
            },
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

    async def test_websocket_connection(self, client, async_controller):
        """Test WebSocket connection"""
        with client.websocket_connect("/ws") as websocket:
            # Should receive initial state
            data = websocket.receive_json()
            assert "type" in data
            assert data["type"] == "state"

    async def test_frame_broadcast(self, client, async_controller):
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

    async def test_system_errors(self, client, async_controller):
        """Test system error handling"""
        # Stop the system
        await async_controller.stop()

        # Try to set pattern while stopped
        response = client.post(
            "/api/patterns/solid",
            json={"parameters": {"red": 255, "green": 0, "blue": 0}},
        )
        assert response.status_code == 503  # Service Unavailable
