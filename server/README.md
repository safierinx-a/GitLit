# GitLit Server

Audio processing and pattern generation server for the GitLit LED system.

## Features

- Real-time audio processing with Essentia
- Pattern generation engine
- WebSocket communication for real-time updates
- FastAPI backend for control and configuration

## Development

1. Create virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -e ".[dev]"
```

3. Run the server:

```bash
uvicorn src.api.app:app --reload
```
