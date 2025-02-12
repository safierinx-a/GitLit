from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, ClassVar
from enum import Enum
import logging

from .exceptions import ValidationError

logger = logging.getLogger(__name__)


class ConfigValidationMixin:
    """Mixin to add validation capabilities to config classes"""

    def validate(self) -> None:
        """Validate configuration values"""
        validators = getattr(self, "validators", {})
        for field_name, validator in validators.items():
            value = getattr(self, field_name)
            if not validator(value):
                raise ValidationError(f"Invalid {field_name}: {value}")


@dataclass
class SystemDefaults:
    """Hardware and protocol constants for WS2812B LED system"""

    # WS2812B Protocol Timing (in nanoseconds)
    T0H: ClassVar[int] = 350  # 0 bit high voltage time
    T0L: ClassVar[int] = 800  # 0 bit low voltage time
    T1H: ClassVar[int] = 700  # 1 bit high voltage time
    T1L: ClassVar[int] = 600  # 1 bit low voltage time
    RESET_TIME_NS: ClassVar[int] = 50_000  # Reset time (50 microseconds)

    # Hardware Limits
    MAX_STRIP_LENGTH: ClassVar[int] = 1000  # Maximum supported LEDs
    MIN_REFRESH_TIME_NS: ClassVar[int] = 50_000  # Minimum time between updates (50us)
    MAX_REFRESH_RATE: ClassVar[int] = 60  # Maximum refresh rate in Hz
    LED_BITS_PER_PIXEL: ClassVar[int] = 24  # 24 bits per LED (8 each for G,R,B)

    # Default Hardware Settings
    DEFAULT_LED_COUNT: ClassVar[int] = 600
    DEFAULT_LED_PIN: ClassVar[int] = 18
    DEFAULT_LED_FREQ_HZ: ClassVar[int] = 800_000  # 800kHz signal frequency
    DEFAULT_LED_DMA: ClassVar[int] = 10
    DEFAULT_LED_BRIGHTNESS: ClassVar[float] = 1.0
    DEFAULT_LED_CHANNEL: ClassVar[int] = 0
    DEFAULT_COLOR_ORDER: ClassVar[str] = "GRB"  # WS2812B uses GRB color order

    # Performance Defaults
    DEFAULT_FPS: ClassVar[int] = 60
    DEFAULT_BUFFER_SIZE: ClassVar[int] = 2
    DEFAULT_GAMMA: ClassVar[float] = 2.8

    # Network Defaults
    DEFAULT_WS_PORT: ClassVar[int] = 8765
    DEFAULT_HEARTBEAT_MS: ClassVar[int] = 1000
    DEFAULT_TIMEOUT_MS: ClassVar[int] = 5000
    DEFAULT_MAX_HEARTBEATS: ClassVar[int] = 3

    @classmethod
    def get_all_defaults(cls) -> Dict[str, Any]:
        """Get all default values as a dictionary"""
        return {
            name: value
            for name, value in cls.__dict__.items()
            if (
                not name.startswith("_")
                and isinstance(value, (int, float, str, bool))
                and name.startswith("DEFAULT_")
            )
        }

    @classmethod
    def get_protocol_timing(cls) -> Dict[str, int]:
        """Get WS2812B protocol timing constants"""
        return {
            "T0H": cls.T0H,
            "T0L": cls.T0L,
            "T1H": cls.T1H,
            "T1L": cls.T1L,
            "RESET_TIME": cls.RESET_TIME_NS,
        }


@dataclass
class HardwareTimingConfig:
    """WS2812B hardware timing configuration"""

    data_rate_hz: int = SystemDefaults.DEFAULT_LED_FREQ_HZ
    reset_time_ns: int = SystemDefaults.RESET_TIME_NS
    led_bits: int = SystemDefaults.LED_BITS_PER_PIXEL
    color_order: str = SystemDefaults.DEFAULT_COLOR_ORDER

    # GPIO settings
    pin: int = SystemDefaults.DEFAULT_LED_PIN
    dma_channel: int = SystemDefaults.DEFAULT_LED_DMA
    invert_signal: bool = False

    def calculate_bit_time(self) -> float:
        """Calculate time for one bit transmission in nanoseconds"""
        # Convert data rate from Hz to ns
        bit_time_ns = 1_000_000_000 / self.data_rate_hz
        return bit_time_ns

    def calculate_led_time(self) -> float:
        """Calculate time for one LED transmission in nanoseconds"""
        return self.calculate_bit_time() * self.led_bits

    def calculate_timing(self, num_leds: int) -> Dict[str, float]:
        """Calculate timing constraints for LED strip"""
        if num_leds <= 0 or num_leds > SystemDefaults.MAX_STRIP_LENGTH:
            raise ValidationError(
                f"LED count must be between 1 and {SystemDefaults.MAX_STRIP_LENGTH}"
            )

        # Calculate timings in nanoseconds
        bit_time_ns = self.calculate_bit_time()
        led_time_ns = self.calculate_led_time()
        total_data_time_ns = led_time_ns * num_leds
        total_frame_time_ns = total_data_time_ns + self.reset_time_ns

        # Calculate maximum theoretical FPS
        max_fps = 1_000_000_000 / total_frame_time_ns

        # Convert some values to microseconds for easier human reading
        return {
            "bit_time_ns": bit_time_ns,
            "led_time_ns": led_time_ns,
            "total_data_time_us": total_data_time_ns / 1000,
            "total_frame_time_us": total_frame_time_ns / 1000,
            "theoretical_max_fps": max_fps,
            "min_frame_time_ms": 1000 / max_fps,
        }


@dataclass
class PerformanceConfig:
    """Performance and timing settings"""

    target_fps: int = SystemDefaults.DEFAULT_FPS
    buffer_size: int = SystemDefaults.DEFAULT_BUFFER_SIZE
    enable_vsync: bool = True
    min_frame_time_ms: float = field(init=False)  # Calculated in post_init
    max_frame_time_ms: float = field(init=False)  # Calculated in post_init
    frame_budget_ms: float = field(init=False)  # Calculated in post_init

    def __post_init__(self):
        """Initialize calculated fields"""
        self.min_frame_time_ms = 1000 / self.target_fps
        self.max_frame_time_ms = self.min_frame_time_ms * 2  # Allow up to 2x frame time
        self.frame_budget_ms = (
            self.min_frame_time_ms * 0.9
        )  # 90% of frame time for processing

    def validate(self, hardware_timing: Dict[str, float]) -> None:
        """Validate performance settings against hardware constraints"""
        # Check FPS against hardware limits
        max_fps = hardware_timing["theoretical_max_fps"]
        if self.target_fps > max_fps:
            logger.warning(
                f"Target FPS {self.target_fps} exceeds hardware maximum {max_fps:.1f}. "
                f"Adjusting to {min(SystemDefaults.MAX_REFRESH_RATE, int(max_fps))}"
            )
            self.target_fps = min(SystemDefaults.MAX_REFRESH_RATE, int(max_fps))

        # Validate minimum refresh time
        min_frame_time_ns = (
            hardware_timing["total_frame_time_us"] * 1000
        )  # Convert to ns
        if min_frame_time_ns < SystemDefaults.MIN_REFRESH_TIME_NS:
            raise ValidationError(
                f"Frame time {min_frame_time_ns}ns is below minimum refresh time "
                f"{SystemDefaults.MIN_REFRESH_TIME_NS}ns"
            )

        # Update calculated fields with validated FPS
        self.__post_init__()

        # Validate buffer size
        if (
            self.buffer_size < 1
            or self.buffer_size > SystemDefaults.DEFAULT_BUFFER_SIZE * 2
        ):
            raise ValidationError(
                f"Buffer size must be between 1 and {SystemDefaults.DEFAULT_BUFFER_SIZE * 2}"
            )

    def get_timing_info(self) -> Dict[str, float]:
        """Get current timing information"""
        return {
            "target_fps": self.target_fps,
            "min_frame_time_ms": self.min_frame_time_ms,
            "max_frame_time_ms": self.max_frame_time_ms,
            "frame_budget_ms": self.frame_budget_ms,
            "vsync_enabled": self.enable_vsync,
            "buffer_size": self.buffer_size,
        }


@dataclass
class NetworkConfig:
    """Network communication settings"""

    websocket_port: int = SystemDefaults.DEFAULT_WS_PORT
    heartbeat_interval_ms: int = SystemDefaults.DEFAULT_HEARTBEAT_MS
    connection_timeout_ms: int = SystemDefaults.DEFAULT_TIMEOUT_MS
    max_missed_heartbeats: int = SystemDefaults.DEFAULT_MAX_HEARTBEATS
    max_clients: int = 10
    client_buffer_size: int = 1024 * 1024  # 1MB

    # Frame transmission settings
    compress_frames: bool = False
    max_queue_size: int = SystemDefaults.DEFAULT_BUFFER_SIZE
    frame_batch_size: int = 1
    max_frame_size: int = 1024 * 1024  # 1MB

    def __post_init__(self):
        """Initialize derived settings"""
        # Calculate timeout from heartbeat settings
        self.effective_timeout_ms = min(
            self.connection_timeout_ms,
            self.heartbeat_interval_ms * self.max_missed_heartbeats,
        )

    def validate(self) -> None:
        """Validate network settings"""
        # Validate port range
        if not 1024 <= self.websocket_port <= 65535:
            raise ValidationError("WebSocket port must be between 1024 and 65535")

        # Validate timing settings
        if self.heartbeat_interval_ms < 100:
            raise ValidationError("Heartbeat interval must be at least 100ms")
        if self.connection_timeout_ms < self.heartbeat_interval_ms * 2:
            raise ValidationError(
                "Connection timeout must be at least 2x heartbeat interval"
            )
        if not 1 <= self.max_missed_heartbeats <= 10:
            raise ValidationError("Max missed heartbeats must be between 1 and 10")

        # Validate client settings
        if not 1 <= self.max_clients <= 100:
            raise ValidationError("Max clients must be between 1 and 100")
        if self.client_buffer_size < 1024:
            raise ValidationError("Client buffer size must be at least 1KB")
        if self.client_buffer_size > 10 * 1024 * 1024:
            raise ValidationError("Client buffer size must not exceed 10MB")

        # Validate frame settings
        if not 1 <= self.frame_batch_size <= 10:
            raise ValidationError("Frame batch size must be between 1 and 10")
        if not 1 <= self.max_queue_size <= SystemDefaults.DEFAULT_BUFFER_SIZE * 4:
            raise ValidationError(
                f"Max queue size must be between 1 and {SystemDefaults.DEFAULT_BUFFER_SIZE * 4}"
            )
        if self.max_frame_size > 10 * 1024 * 1024:
            raise ValidationError("Max frame size must not exceed 10MB")

        # Performance warnings
        if self.max_queue_size > SystemDefaults.DEFAULT_BUFFER_SIZE:
            logger.warning(
                f"Large queue size ({self.max_queue_size}) may cause increased latency"
            )
        if self.frame_batch_size > 1:
            logger.warning(
                f"Frame batching ({self.frame_batch_size}) may increase latency"
            )
        if self.compress_frames:
            logger.info("Frame compression enabled - may impact CPU usage")

    def get_timing_info(self) -> Dict[str, int]:
        """Get network timing information"""
        return {
            "heartbeat_interval_ms": self.heartbeat_interval_ms,
            "connection_timeout_ms": self.connection_timeout_ms,
            "effective_timeout_ms": self.effective_timeout_ms,
            "max_missed_heartbeats": self.max_missed_heartbeats,
        }


@dataclass
class LEDConfig:
    """LED strip configuration"""

    count: int = 600
    brightness: float = 1.0

    # Hardware timing
    timing: HardwareTimingConfig = field(default_factory=HardwareTimingConfig)

    def validate(self) -> None:
        """Validate LED configuration"""
        if self.count <= 0 or self.count > 1000:
            raise ValidationError("LED count must be between 1 and 1000")
        if not 0 <= self.brightness <= 1:
            raise ValidationError("Brightness must be between 0 and 1")


@dataclass
class FeatureFlags:
    """System feature flags"""

    audio_enabled: bool = False
    performance_monitoring: bool = True
    error_reporting: bool = True


@dataclass
class SystemConfig:
    """Main system configuration"""

    led: LEDConfig = field(default_factory=LEDConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)

    def __post_init__(self):
        """Validate entire configuration"""
        try:
            # Validate individual components
            self.led.validate()
            self.network.validate()

            # Calculate hardware timing
            timing = self.led.timing.calculate_timing(self.led.count)

            # Validate performance settings against hardware constraints
            self.performance.validate(timing)

            logger.info(
                f"Hardware timing: Maximum theoretical FPS: {timing['theoretical_max_fps']:.1f}"
            )
            logger.info(f"Operating at {self.performance.target_fps} FPS")

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise

    @classmethod
    def create_default(cls) -> "SystemConfig":
        """Create default configuration"""
        return cls()

    def update(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values"""
        if "led" in updates:
            self.led = LEDConfig(**updates["led"])
        if "performance" in updates:
            self.performance = PerformanceConfig(**updates["performance"])
        if "network" in updates:
            self.network = NetworkConfig(**updates["network"])

        # Revalidate after updates
        self.__post_init__()
