from typing import Optional, Dict, Any, Callable
from threading import Lock
from .models import (
    AudioState,
    BeatInfo,
    SpectralInfo,
    EnergyInfo,
    RhythmInfo,
    StructureInfo,
    HarmonyInfo,
    SeparationInfo,
)


class StateManager:
    """Manages shared state between audio pipelines"""

    def __init__(self):
        self._state = AudioState()
        self._lock = Lock()
        self._callbacks: Dict[str, Callable[[AudioState], None]] = {}

        # Feature caching
        self._feature_cache = {}
        self._cache_lifetime = 5.0  # seconds

    def register_callback(
        self, name: str, callback: Callable[[AudioState], None]
    ) -> None:
        """Register a callback for state updates"""
        self._callbacks[name] = callback

    def unregister_callback(self, name: str) -> None:
        """Unregister a callback"""
        self._callbacks.pop(name, None)

    def _notify_callbacks(self) -> None:
        """Notify all registered callbacks of state change"""
        for callback in self._callbacks.values():
            try:
                callback(self._state)
            except Exception as e:
                print(f"Error in state callback: {e}")

    def update_realtime_features(self, features: Dict[str, Any]) -> None:
        """Update real-time features"""
        with self._lock:
            if "beat" in features:
                self._state.beat = BeatInfo(**features["beat"])

            if "spectral" in features:
                self._state.spectral = SpectralInfo(**features["spectral"])

            if "energy" in features:
                self._state.energy = EnergyInfo(**features["energy"])

            if "rhythm" in features:
                self._state.rhythm = RhythmInfo(**features["rhythm"])

            self._notify_callbacks()

    def update_analysis_features(self, features: Dict[str, Any]) -> None:
        """Update analysis features"""
        with self._lock:
            if "structure" in features:
                self._state.structure = StructureInfo(**features["structure"])

            if "harmony" in features:
                self._state.harmony = HarmonyInfo(**features["harmony"])

            if "separation" in features:
                self._state.separation = SeparationInfo(**features["separation"])

            # Cache analysis results
            self._update_cache(features)
            self._notify_callbacks()

    def _update_cache(self, features: Dict[str, Any]) -> None:
        """Update feature cache"""
        import time

        current_time = time.time()

        # Add new features to cache with timestamp
        for key, value in features.items():
            self._feature_cache[key] = {"data": value, "timestamp": current_time}

        # Clean old cache entries
        self._clean_cache(current_time)

    def _clean_cache(self, current_time: float) -> None:
        """Remove old cache entries"""
        expired_keys = [
            key
            for key, value in self._feature_cache.items()
            if current_time - value["timestamp"] > self._cache_lifetime
        ]

        for key in expired_keys:
            del self._feature_cache[key]

    def get_cached_feature(self, feature_name: str) -> Optional[Any]:
        """Get a cached feature if available"""
        with self._lock:
            if feature_name in self._feature_cache:
                return self._feature_cache[feature_name]["data"]
        return None

    @property
    def current_state(self) -> AudioState:
        """Get current state (thread-safe)"""
        with self._lock:
            return self._state

    def to_dict(self) -> Dict[str, Any]:
        """Convert current state to dictionary (thread-safe)"""
        with self._lock:
            return self._state.to_dict()
