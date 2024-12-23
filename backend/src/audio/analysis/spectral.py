import numpy as np
from typing import Dict, List
from scipy import signal
import numpy.fft as fft


class SpectralAnalyzer:
    """Frequency domain analysis"""

    # Frequency band definitions (Hz)
    FREQ_BANDS = {
        "sub": (20, 60),
        "bass": (60, 250),
        "low_mid": (250, 500),
        "mid": (500, 2000),
        "high_mid": (2000, 4000),
        "high": (4000, 8000),
        "presence": (8000, 20000),
    }

    def __init__(self, sample_rate: int, buffer_size: int):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size

        # Prepare FFT
        self.window = signal.hann(buffer_size)
        self.freq_bins = fft.rfftfreq(buffer_size, 1 / sample_rate)

        # Prepare band indices
        self.band_indices = self._calculate_band_indices()

        # History and smoothing
        self.spectrum_history = []
        self.band_energies = {band: 0.0 for band in self.FREQ_BANDS.keys()}
        self.smoothing_factor = 0.2

        print(f"Initialized SpectralAnalyzer with sample rate: {sample_rate}Hz")
        print(f"Frequency resolution: {self.sample_rate / self.buffer_size:.1f}Hz")

    def _calculate_band_indices(self) -> Dict[str, tuple]:
        """Calculate FFT bin indices for each frequency band"""
        indices = {}
        for band, (low, high) in self.FREQ_BANDS.items():
            low_idx = np.searchsorted(self.freq_bins, low)
            high_idx = np.searchsorted(self.freq_bins, high)
            indices[band] = (low_idx, high_idx)
            print(f"Band {band}: {low}Hz-{high}Hz (bins {low_idx}-{high_idx})")
        return indices

    def analyze(self, buffer: np.ndarray) -> Dict:
        """Perform spectral analysis on audio buffer"""
        # Normalize input
        buffer = buffer / (np.max(np.abs(buffer)) + 1e-10)

        # Apply window and compute FFT
        windowed = buffer * self.window
        spectrum = np.abs(fft.rfft(windowed))

        # Normalize spectrum
        spectrum = spectrum / len(spectrum)

        # Calculate band energies with smoothing
        band_energies = {}
        for band, (start_idx, end_idx) in self.band_indices.items():
            # Calculate band energy
            band_energy = np.mean(spectrum[start_idx:end_idx])

            # Apply smoothing
            current_energy = self.band_energies[band]
            smoothed_energy = (
                self.smoothing_factor * band_energy
                + (1 - self.smoothing_factor) * current_energy
            )

            # Store smoothed energy
            band_energies[band] = smoothed_energy
            self.band_energies[band] = smoothed_energy

        # Calculate spectral centroid (brightness)
        if np.sum(spectrum) > 0:
            centroid = np.sum(self.freq_bins * spectrum) / np.sum(spectrum)
        else:
            centroid = 0

        # Update spectrum history
        self.spectrum_history.append(spectrum)
        if len(self.spectrum_history) > 100:
            self.spectrum_history.pop(0)

        return {
            "bands": band_energies,
            "centroid": centroid,
            "spectrum": spectrum,
            "peak_frequencies": self._find_peak_frequencies(spectrum),
        }

    def _find_peak_frequencies(
        self, spectrum: np.ndarray, num_peaks: int = 3
    ) -> List[float]:
        """Find dominant frequencies"""
        # Find peaks in spectrum
        peaks = signal.find_peaks(spectrum, height=np.mean(spectrum), distance=5)[0]

        # Sort peaks by amplitude
        peak_amplitudes = spectrum[peaks]
        sorted_indices = np.argsort(peak_amplitudes)[::-1]
        top_peaks = peaks[sorted_indices[:num_peaks]]

        # Convert peak indices to frequencies
        peak_frequencies = self.freq_bins[top_peaks]

        return peak_frequencies.tolist()
