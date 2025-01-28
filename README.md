# GitLit

A distributed LED lighting system with audio reactivity and pattern generation.

## Architecture

The project is split into three main components:

1. **Server**: Audio processing and pattern generation

   - FastAPI backend for pattern control
   - Real-time audio processing with Essentia
   - Pattern generation engine
   - WebSocket for real-time updates

2. **Controller**: Raspberry Pi LED control

   - LED hardware interface
   - Audio capture and streaming
   - Real-time pattern rendering
   - Network communication with server

3. **Frontend**: Web interface
   - Pattern control UI
   - Audio visualization
   - System monitoring
   - Configuration management

## Project Structure

```
GitLit/
├── server/              # Audio processing & pattern generation server
│   ├── src/
│   │   ├── api/        # FastAPI endpoints
│   │   ├── audio/      # Audio processing
│   │   ├── patterns/   # Pattern generation
│   │   └── core/       # Core utilities
│   ├── tests/
│   └── requirements.txt
│
├── controller/          # Raspberry Pi LED controller
│   ├── src/
│   │   ├── led/        # LED hardware control
│   │   ├── client/     # Audio streaming client
│   │   └── config/     # Configuration
│   ├── tests/
│   └── requirements.txt
│
├── frontend/           # Web interface
│   ├── src/
│   ├── public/
│   └── package.json
│
├── docs/              # Project documentation
│   ├── architecture/
│   ├── api/
│   └── setup/
│
└── tools/             # Shared development tools
    ├── sync-pi.sh
    └── setup.sh
```

## Requirements

### Server

- Python 3.11+
- FastAPI
- Essentia
- Librosa
- NumPy

### Controller (Raspberry Pi)

- Python 3.11+
- rpi_ws281x
- NumPy
- sounddevice
- websockets

### Frontend

- Node.js 18+
- React
- TypeScript

## Setup

1. Server Setup:

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Controller Setup (on Raspberry Pi):

```bash
cd controller
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Frontend Setup:

```bash
cd frontend
npm install
```

## Development

### Running the Server

```bash
cd server
uvicorn src.api.app:app --reload --port 8000
```

### Running the Controller

```bash
cd controller
python src/client/audio_client.py --host SERVER_IP
```

### Running the Frontend

```bash
cd frontend
npm run dev
```

## Deployment

### Syncing with Raspberry Pi

Use the sync script to deploy controller code:

```bash
./tools/sync-pi.sh to_pi
```

See [docs/setup/raspberry-pi.md](docs/setup/raspberry-pi.md) for detailed setup instructions.

## Documentation

- [Architecture Overview](docs/architecture/overview.md)
- [API Documentation](docs/api/README.md)
- [Setup Guide](docs/setup/README.md)

## License

MIT License - See LICENSE file for details
