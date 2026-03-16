# APS Backend

FastAPI server handling REST APIs and WebSocket voice connections.

## Setup

```bash
pip install -r requirements.txt
```

## Environment Variables

Create `.env`:
```
TIDB_HOST=...
TIDB_PORT=4000
TIDB_USER=...
TIDB_PASSWORD=...
TIDB_DB_NAME=...
MONGO_URI=...
MONGO_DB_NAME=...
JWT_SECRET_KEY=...
GOOGLE_API_KEY=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...
AWS_REGION=eu-central-1
PREPROD_GRAPH_URL=http://127.0.0.1:2024
```

## Run Locally

```bash
uvicorn main:app --reload --port 8000
```

## Reproducible Testing

### Health Check
```bash
curl http://localhost:8000/health
```

### Test Screenplay API
```bash
# Get screenplay by MongoDB ID
curl http://localhost:8000/api/screenplay/mongo/YOUR_MONGODB_ID

# Get scenes
curl http://localhost:8000/api/screenplay/scenes/YOUR_MONGODB_ID
```

### Test Voice WebSocket
Use a WebSocket client (wscat, Postman, or browser):
```bash
wscat -c ws://localhost:8000/voice
```

Send start message:
```json
{"type": "start", "service": "gemini", "screenplay_id": "YOUR_MONGODB_ID", "project_id": "YOUR_PROJECT_ID"}
```

### Test with Deployed Graph
Set `PREPROD_GRAPH_URL` to the deployed Gradient endpoint and include `DIGITALOCEAN_API_TOKEN` for auth.
