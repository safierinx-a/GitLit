# GitLit

I'm building a system for generating and displaying LED patterns on addressable LED strips. The goal is to create a modular and scalable architecture that makes it easy to add new patterns and effects.

## What's Working So Far ✨

I've got the core pattern system working with:

- basic static/moving/particle patterns
- modifier system for tweaking patterns (brightness, speed, etc.)
- basic audio processing with beat detection

## WIP 🛠️

Currently focusing on:

- Making patterns react to music in real-time
- Smooth transitions between patterns
- Performance optimizations
- Better audio analysis

⚠️ TODO: Need to create proper setup scripts for getting everything installed and configured easily.

## The Plan 📋

End goal is to have a nice home lighting system with:

- Web interface for control
- Reactive audio visualizations
- Standalone visual patterns
- Support for both 1D and 2D LED layouts
- Multi-device sync would be cool

## Hardware Setup

I'm using:

- A Raspberry Pi 3B+
- A USB audio card for sound input from a splitter connected to a bluetooth DAC
- WS2812B addressable LED strips

## Software Dependencies

Needs Python 3.11+ and some libraries:

- NumPy
- PyAudio
- librosa
- torchaudio
- JACK Audio (optional but recommended)

## Project Structure

```
backend/
  ├── config/          # Configuration files
  ├── src/
  │   ├── patterns/    # Pattern implementations
  │   ├── audio/       # Audio processing
  │   ├── led/         # LED control
  │   └── control/     # Web interface backend
  └── tests/           # Test suite
  └── docs/            # Documentation

frontend/             # Web control interface (planned)
```

Check out the [docs](./backend/docs/) folder for more details.
