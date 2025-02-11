"""Tests for core system functionality."""

import asyncio
import pytest
import numpy as np
from fastapi.testclient import TestClient

from server.src.core.config import SystemConfig
from server.src.core.control import SystemController
from server.src.core.state import SystemState
from server.src.core.commands import CommandQueue, SetPatternCommand
from server.src.core.frame_manager import FrameManager, FrameMetrics
from server.src.core.exceptions import ValidationError


@pytest.fixture
def system_config():
    """Test system configuration"""
    return SystemConfig.create_default()


@pytest.fixture
async def controller(system_config):
    """Test system controller"""
    controller = SystemController(system_config)
    await controller.start()
    yield controller
    await controller.stop()


@pytest.fixture
def frame_manager(system_config):
    """Test frame manager"""
    return FrameManager(
        num_leds=system_config.led.count,
        target_fps=system_config.performance.target_fps,
    )


class TestSystemState:
    """Test system state management"""

    async def test_initial_state(self, controller):
        """Test initial system state"""
        state = controller.get_state()
        assert state["system_state"] == "READY"
        assert not state["pattern_engine"]["current_pattern"]

    async def test_state_transitions(self, controller):
        """Test state transitions"""
        # Start system
        await controller.state_manager.start()
        assert controller.state_manager.current_state == SystemState.RUNNING

        # Pause system
        await controller.state_manager.pause()
        assert controller.state_manager.current_state == SystemState.PAUSED

        # Resume system
        await controller.state_manager.resume()
        assert controller.state_manager.current_state == SystemState.RUNNING


class TestCommandSystem:
    """Test command system"""

    async def test_command_queue(self, controller):
        """Test command queueing and execution"""
        # Create test command
        cmd = SetPatternCommand("solid", {"color": [255, 0, 0]})

        # Queue command
        await controller.command_queue.enqueue(cmd)

        # Check command execution
        await asyncio.sleep(0.1)  # Allow time for command processing
        state = controller.get_state()
        assert state["pattern_engine"]["current_pattern"] == "solid"

    async def test_command_validation(self, controller):
        """Test command validation"""
        # Invalid pattern
        with pytest.raises(ValidationError):
            cmd = SetPatternCommand("nonexistent_pattern")
            await controller.command_queue.enqueue(cmd)


class TestFrameGeneration:
    """Test frame generation and management"""

    async def test_frame_generation(self, frame_manager):
        """Test basic frame generation"""
        await frame_manager.start()

        # Generate test frame
        frame, metrics = await frame_manager.generate_frame(
            lambda t: np.zeros((frame_manager.num_leds, 3), dtype=np.uint8)
        )

        assert frame is not None
        assert frame.shape == (frame_manager.num_leds, 3)
        assert frame.dtype == np.uint8

        await frame_manager.stop()

    async def test_frame_buffer(self, frame_manager):
        """Test frame buffer management"""
        await frame_manager.start()

        # Generate and buffer frames
        test_frame = np.zeros((frame_manager.num_leds, 3), dtype=np.uint8)
        for _ in range(3):
            success = await frame_manager.write_frame(test_frame.copy(), FrameMetrics())
            assert success

        # Read frames
        frame, metrics = await frame_manager.read_frame()
        assert frame is not None
        assert frame.shape == test_frame.shape

        await frame_manager.stop()


class TestErrorHandling:
    """Test error handling and recovery"""

    async def test_error_recovery(self, controller):
        """Test system error recovery"""
        # Simulate error
        controller.state_manager.performance.record_error("Test error")

        # Check error state
        state = controller.get_state()
        assert state["performance"]["error_count"] == 1
        assert "Test error" in state["performance"]["last_error_message"]

    async def test_frame_error_handling(self, frame_manager):
        """Test frame generation error handling"""
        await frame_manager.start()

        # Generate invalid frame
        def invalid_generator(t):
            raise Exception("Test error")

        frame, metrics = await frame_manager.generate_frame(invalid_generator)

        # Should return emergency frame
        assert frame is not None
        assert frame.shape == (frame_manager.num_leds, 3)
        assert metrics.dropped_frames == 1

        await frame_manager.stop()
