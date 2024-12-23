# GitLit

A modular LED pattern system for addressable LED strips, with audio reactivity and extensible effects.

## Current Status ✨

### Working Features

- Core pattern system with:
  - Static patterns (Solid, Gradient)
  - Moving patterns (Wave, Rainbow, Chase, Scan)
  - Particle patterns (Twinkle, Meteor, Breathe)
- Basic modifier system:
  - Effect modifiers (Brightness, Speed, Direction, Color, etc.)
  - Basic state management
- Audio processing:
  - Device management and audio capture
  - Basic beat detection
  - Basic feature extraction

### In Progress 🛠️

- Audio reactivity:
  - Volume-based modifiers
  - Beat-based modifiers
  - Spectrum analysis
- Pattern system improvements:
  - Pattern transitions (framework exists)
  - Performance optimizations
  - State management refinements

### Planned 📋

- Web interface for control
- Advanced audio analysis
- Pattern sequences and composition
- 2D LED layout support
- Multi-device synchronization

## Hardware Setup

- Raspberry Pi 3B+
- USB audio card (for sound input)
- WS2812B LED strips

## Software Requirements

- Python 3.11+
- Core dependencies:
  - NumPy
  - PyAudio
  - librosa (for audio processing)
  - torchaudio (for feature extraction)

## Project Structure

```
backend/
  ├── config/          # Configuration files
  ├── src/
  │   ├── patterns/    # Pattern implementations
  │   ├── audio/       # Audio processing
  │   ├── led/         # LED control
  │   └── core/        # Core utilities
  ├── tests/           # Test suite
  └── docs/            # Documentation

frontend/             # Web interface (planned)
```

See [docs](./backend/docs/) for detailed specifications.
