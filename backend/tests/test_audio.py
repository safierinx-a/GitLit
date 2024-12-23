#!/usr/bin/env python3
import os
import sys
import time
import curses
from typing import Dict, Optional
import numpy as np
from collections import deque
import pyaudio

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from src.audio.processor import AudioProcessor, ProcessorConfig


class AudioVisualizer:
    """Advanced audio analysis visualization"""

    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.start_color()
        curses.use_default_colors()

        # Initialize color pairs
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_YELLOW, -1)
        curses.init_pair(3, curses.COLOR_RED, -1)
        curses.init_pair(4, curses.COLOR_CYAN, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)

        self.GREEN = curses.color_pair(1)
        self.YELLOW = curses.color_pair(2)
        self.RED = curses.color_pair(3)
        self.CYAN = curses.color_pair(4)
        self.MAGENTA = curses.color_pair(5)

        # Initialize history
        self.beat_times = deque(maxlen=50)
        self.energy_history = deque(maxlen=50)
        self.genre_history = deque(maxlen=10)
        self.mood_history = deque(maxlen=10)

    def draw_bar(self, value: float, width: int = 50, char: str = "█") -> tuple:
        """Draw a bar graph with color"""
        filled = int(value * width)
        if value < 0.3:
            color = self.GREEN
        elif value < 0.7:
            color = self.YELLOW
        else:
            color = self.RED

        bar = char * filled + "░" * (width - filled)
        return bar, color

    def draw_metrics(self, analysis: Dict):
        """Draw all audio analysis metrics"""
        self.stdscr.clear()
        y = 0

        # Title
        self.stdscr.addstr(y, 0, "SOTA Audio Analysis", curses.A_BOLD)
        y += 2

        # Beat and Rhythm Information
        self.stdscr.addstr(y, 0, "Rhythm Analysis:", curses.A_BOLD)
        y += 1
        tempo = analysis["beat"]["tempo"]
        self.stdscr.addstr(y, 0, f"Tempo: {tempo:.1f} BPM")

        # Visualize recent beats
        if analysis["beat"]["last_beats"]:
            self.beat_times.append(time.time())
            beat_viz = "♪ " * len(self.beat_times)
            self.stdscr.addstr(y, 20, beat_viz, self.CYAN | curses.A_BOLD)
        y += 2

        # Frequency Spectrum
        self.stdscr.addstr(y, 0, "Frequency Analysis:", curses.A_BOLD)
        y += 1
        for band, energy in analysis["spectral"].items():
            bar, color = self.draw_bar(energy)
            self.stdscr.addstr(y, 0, f"{band:>10}: ")
            self.stdscr.addstr(bar, color)
            self.stdscr.addstr(f" {energy:.3f}")
            y += 1

        # Musical Analysis
        y += 1
        self.stdscr.addstr(y, 0, "Musical Analysis:", curses.A_BOLD)
        y += 1

        # Genre
        genre = analysis["music"]["genre"]
        self.genre_history.append(genre["label"])
        self.stdscr.addstr(y, 0, f"Genre: {genre['label']} ")
        self.stdscr.addstr(f"({genre['confidence']:.2f})", self.YELLOW)
        y += 1

        # Mood
        mood = analysis["music"]["mood"]
        self.mood_history.append(mood["label"])
        self.stdscr.addstr(y, 0, f"Mood: {mood['label']} ")
        energy_bar, color = self.draw_bar(mood["energy"], width=20)
        self.stdscr.addstr(energy_bar, color)
        y += 1

        # Musical Structure
        structure = analysis["music"]["structure"]
        if structure["section_change"]:
            self.stdscr.addstr(y, 0, "SECTION CHANGE", self.MAGENTA | curses.A_BOLD)
        y += 1

        # Musical Events
        y += 1
        self.stdscr.addstr(y, 0, "Musical Events:", curses.A_BOLD)
        y += 1
        events = analysis["music"]["events"]
        if events["build_up"]:
            self.stdscr.addstr(y, 0, "BUILD-UP ", self.YELLOW | curses.A_BOLD)
        if events["drop"]:
            self.stdscr.addstr(y, 10, "DROP!", self.RED | curses.A_BOLD)
        y += 2

        # History Analysis
        self.stdscr.addstr(y, 0, "Recent History:", curses.A_BOLD)
        y += 1

        # Most common genre
        if self.genre_history:
            common_genre = max(set(self.genre_history), key=self.genre_history.count)
            self.stdscr.addstr(y, 0, f"Dominant Genre: {common_genre}")
        y += 1

        # Most common mood
        if self.mood_history:
            common_mood = max(set(self.mood_history), key=self.mood_history.count)
            self.stdscr.addstr(y, 0, f"Dominant Mood: {common_mood}")
        y += 2

        # Instructions
        self.stdscr.addstr(y, 0, "Press 'q' to quit", curses.A_DIM)

        self.stdscr.refresh()


def on_beat(beat_info):
    """Handle beat events"""
    pass


def on_feature_update(features):
    """Handle feature updates"""
    pass


def on_analysis_update(analysis):
    """Handle analysis updates"""
    pass


def select_audio_device(processor: AudioProcessor) -> Optional[Dict]:
    """Select the best audio input device"""
    devices = processor.list_devices()

    # First try to find USB audio device
    for dev in devices.values():
        if "usb" in dev["name"].lower():
            print(f"Selected USB audio device: {dev['name']}")
            return dev

    # Then try to find any working device
    for dev in devices.values():
        try:
            sample_rate = processor.get_device_sample_rate(dev["index"])
            print(f"Testing device: {dev['name']} at {sample_rate}Hz")

            # Try to open the device
            stream = processor.pa.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=sample_rate,
                input=True,
                input_device_index=dev["index"],
                frames_per_buffer=1024,
            )
            stream.close()

            print(f"Selected working device: {dev['name']}")
            return dev
        except Exception as e:
            print(f"Device {dev['name']} not suitable: {e}")
            continue

    return None


def main(stdscr):
    # Set up curses
    curses.curs_set(0)
    stdscr.nodelay(1)

    # Initialize audio processor
    config = ProcessorConfig(use_gpu=False)
    processor = AudioProcessor(config)

    # Select audio device
    device = select_audio_device(processor)
    if not device:
        print("No suitable audio device found!")
        return

    # Initialize visualizer
    viz = AudioVisualizer(stdscr)

    try:
        processor.start(device["index"])

        while True:
            c = stdscr.getch()
            if c == ord("q"):
                break

            analysis = processor.get_current_analysis()
            viz.draw_metrics(analysis)

            time.sleep(0.02)

    except Exception as e:
        print(f"Error during processing: {e}")
    finally:
        processor.cleanup()


if __name__ == "__main__":
    curses.wrapper(main)
