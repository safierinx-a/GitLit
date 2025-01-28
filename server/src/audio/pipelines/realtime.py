import essentia
import essentia.standard as es
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from ..state.models import BeatInfo, SpectralInfo, EnergyInfo
from ..analysis.realtime.onset import OnsetDetector
from .base import AudioPipeline, PipelineConfig

class RealtimePipeline(AudioPipeline):
    """Real-time audio processing pipeline using Essentia"""
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        super().__init__(config)
        self.frame_size = self.config.buffer_size
        self.hop_size = self.config.hop_length
        
    def _initialize(self) -> None:
        """Initialize Essentia algorithms"""
        # Initialize onset and beat tracking
        self.onset_detector = OnsetDetector(
            frame_size=self.frame_size,
            hop_size=self.hop_size,
            sample_rate=self.config.sample_rate
        )
        self.beat_tracker = es.BeatTrackerMultiFeature(
            maxTempo=220,
            minTempo=60,
        )
        
        # Windowing and spectrum
        self.w = es.Windowing(type='hann')
        self.spectrum = es.Spectrum(size=self.frame_size)
        
        # Spectral feature extractors
        self.centroid = es.Centroid(range=self.config.sample_rate/2)
        self.bandwidth = es.SpectralBandwidth(range=self.config.sample_rate/2)
        self.rolloff = es.RollOff()
        self.flatness = es.Flatness()
        self.contrast = es.SpectralContrast()
        self.complexity = es.SpectralComplexity()
        self.hfc = es.HFC()
        self.melbands = es.MelBands(
            numberBands=24,
            sampleRate=self.config.sample_rate
        )
        
        # Frequency band analysis
        self.freq_bands = {
            "sub": (20, 60),
            "bass": (60, 250),
            "low_mid": (250, 500),
            "mid": (500, 2000),
            "high_mid": (2000, 4000),
            "high": (4000, 8000),
            "presence": (8000, 20000)
        }
        self.freq_bins = np.fft.rfftfreq(self.frame_size, 1.0 / self.config.sample_rate)
        self.band_indices = self._calculate_band_indices()
        
        # Energy and dynamics
        self.rms = es.RMS()
        self.loudness = es.Loudness()
        self.dynamic_complexity = es.DynamicComplexity()
        
        # Rhythm features
        self.rhythm_extractor = es.RhythmExtractor2013(
            maxTempo=220,
            minTempo=60,
        )
        
        # State
        self.last_beat_time = 0.0
        self.current_tempo = 0.0
        self.beat_confidence = 0.0
        self._reset_features()
        
    def _reset_features(self) -> None:
        """Reset feature history"""
        self.feature_history = {
            'melbands': np.zeros((24, 10)),  # 10 frames of history
            'onsets': [],
            'beat_positions': [],
            'dynamic_complexity': 0.0
        }
        
    def _update_history(self, feature_name: str, value: np.ndarray) -> None:
        """Update feature history"""
        if feature_name == 'melbands':
            self.feature_history[feature_name] = np.roll(
                self.feature_history[feature_name], -1, axis=1
            )
            self.feature_history[feature_name][:, -1] = value
            
    def _calculate_band_indices(self) -> Dict[str, Tuple[int, int]]:
        """Calculate FFT bin indices for each frequency band"""
        indices = {}
        for band, (low, high) in self.freq_bands.items():
            low_idx = np.searchsorted(self.freq_bins, low)
            high_idx = np.searchsorted(self.freq_bins, high)
            indices[band] = (low_idx, high_idx)
        return indices
        
    def _analyze_frequency_bands(self, spectrum: np.ndarray) -> Dict[str, float]:
        """Analyze energy in frequency bands"""
        band_energies = {}
        for band, (start_idx, end_idx) in self.band_indices.items():
            band_energies[band] = float(np.mean(spectrum[start_idx:end_idx]))
        return band_energies
        
    def _find_peak_frequencies(self, spectrum: np.ndarray, num_peaks: int = 3) -> List[float]:
        """Find dominant frequencies"""
        from scipy import signal
        # Find peaks in spectrum
        peaks = signal.find_peaks(spectrum, height=np.mean(spectrum), distance=5)[0]
        
        if len(peaks) == 0:
            return []
            
        # Sort peaks by amplitude
        peak_amplitudes = spectrum[peaks]
        sorted_indices = np.argsort(peak_amplitudes)[::-1]
        top_peaks = peaks[sorted_indices[:num_peaks]]
        
        # Convert peak indices to frequencies
        peak_frequencies = self.freq_bins[top_peaks]
        return peak_frequencies.tolist()
        
    def process(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """Process audio frame and extract features"""
        if not self.running:
            return {}
            
        # Ensure mono audio
        if audio_data.ndim > 1:
            audio_data = np.mean(audio_data, axis=0)
            
        # Onset detection
        onset_data = self.onset_detector.process_frame(audio_data)
        
        # Beat tracking and rhythm features
        beats, tempo = self.beat_tracker(audio_data)
        bpm, beats_positions, beats_magnitude, _, beats_intervals = \
            self.rhythm_extractor(audio_data)
            
        beat_info = BeatInfo(
            confidence=float(onset_data.confidence),
            tempo=float(tempo),
            last_beat_time=float(beats[-1]) if len(beats) > 0 else self.last_beat_time,
            beat_positions=beats.tolist()
        )
        
        # Spectral features
        windowed = self.w(audio_data)
        spectrum = self.spectrum(windowed)
        melbands = self.melbands(spectrum)
        self._update_history('melbands', melbands)
        
        # Analyze frequency bands and peaks
        band_energies = self._analyze_frequency_bands(spectrum)
        peak_freqs = self._find_peak_frequencies(spectrum)
        
        spectral_info = SpectralInfo(
            centroid=float(self.centroid(spectrum)),
            bandwidth=float(self.bandwidth(spectrum)),
            rolloff=float(self.rolloff(spectrum)),
            flatness=float(self.flatness(spectrum)),
            contrast=self.contrast(spectrum)[0].tolist(),  # First band contrast
            complexity=float(self.complexity(spectrum)),
            hfc=float(self.hfc(spectrum)),
            melbands=melbands.tolist(),
            melbands_diff=np.diff(self.feature_history['melbands'], axis=1)[:, -1].tolist(),
            frequency_bands=band_energies,
            peak_frequencies=peak_freqs
        )
        
        # Energy and dynamics
        dyn_comp, dyn_mean = self.dynamic_complexity(audio_data)
        energy_info = EnergyInfo(
            rms=float(self.rms(audio_data)),
            peak=float(np.max(np.abs(audio_data))),
            loudness=float(self.loudness(audio_data)),
            dynamic_complexity=float(dyn_comp),
            dynamic_mean=float(dyn_mean),
            onset_strength=float(onset_data.strengths[0]) if onset_data.strengths else 0.0,
            beats_magnitude=beats_magnitude.tolist() if len(beats_magnitude) > 0 else []
        )
        
        # Update state
        self.last_beat_time = beat_info.last_beat_time
        self.current_tempo = beat_info.tempo
        self.beat_confidence = beat_info.confidence
        
        return {
            "beat": beat_info,
            "spectral": spectral_info,
            "energy": energy_info,
            "rhythm": {
                "bpm": float(bpm),
                "beat_intervals": beats_intervals.tolist(),
                "onset_positions": onset_data.positions,
                "onset_strengths": onset_data.strengths
            }
        }
        
    def reset(self) -> None:
        """Reset pipeline state"""
        self.last_beat_time = 0.0
        self.current_tempo = 0.0
        self.beat_confidence = 0.0
        self._reset_features()
        self.onset_detector.reset()
``` 