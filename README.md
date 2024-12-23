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

## Deployment

### Syncing with Raspberry Pi

The project includes a sync script to easily deploy code to your Raspberry Pi:

1. Copy `.env.example` to `.env` and update with your configuration:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your Raspberry Pi details:

   ```bash
   PI_USER="your-pi-username"
   PI_HOST="your-pi-hostname.local"
   LOCAL_DIR="/path/to/your/local/directory"
   REMOTE_DIR="/path/to/your/pi/directory"
   ```

3. Use the sync script to deploy:

   ```bash
   # Push local changes to Pi
   ./sync-pi.sh to_pi

   # Pull changes from Pi to local
   ./sync-pi.sh from_pi
   ```

The sync script automatically excludes temporary files, Python cache, logs, and development artifacts.

See [docs](./backend/docs/) for detailed specifications.
