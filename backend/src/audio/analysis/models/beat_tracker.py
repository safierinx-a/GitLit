import librosa
import numpy as np
from typing import Dict
import time


class BeatTracker:
    """Beat tracking using librosa's pretrained model"""

    def __init__(self, config):
        self.config = config
        self.tempo_history = []
        self.current_tempo = 0.0

        # Parameters tuned for real-time performance
        self.hop_length = 512
        self.start_bpm = 120

        print("Initialized librosa beat tracker")

    def process(self, audio: np.ndarray, current_time: float) -> Dict:
        """Process audio for beat and rhythm information"""
        try:
            # Get onset strength
            onset_env = librosa.onset.onset_strength(
                y=audio, sr=self.config.sample_rate, hop_length=self.hop_length
            )

            # Enhanced beat tracking with tempo estimation
            tempo, beats = librosa.beat.beat_track(
                onset_envelope=onset_env,
                sr=self.config.sample_rate,
                hop_length=self.hop_length,
                start_bpm=self.start_bpm,
                tightness=100,  # More precise beat tracking
            )

            # Convert beat frames to timestamps
            beat_times = librosa.frames_to_time(
                beats, sr=self.config.sample_rate, hop_length=self.hop_length
            )

            # Calculate beat strength
            beat_strength = np.mean(onset_env[beats]) if len(beats) > 0 else 0.0

            # Update tempo history for smoothing
            if tempo > 0:
                self.tempo_history.append(tempo)
                if len(self.tempo_history) > 10:
                    self.tempo_history.pop(0)
                self.current_tempo = np.median(self.tempo_history)

            return {
                "beats": [
                    {
                        "time": current_time + beat_time,
                        "strength": float(onset_env[beat])
                        if beat < len(onset_env)
                        else 0.0,
                    }
                    for beat, beat_time in zip(beats, beat_times)
                ],
                "tempo": float(self.current_tempo),
                "beat_strength": float(beat_strength),
            }

        except Exception as e:
            print(f"Error in beat tracking: {e}")
            return {"beats": [], "tempo": 0.0, "beat_strength": 0.0}
