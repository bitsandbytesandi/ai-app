# AI App

FastAPI backend + static chat UI. Uses OpenRouter free models with fallback.

## Run locally

```bash
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill keys
uvicorn main:app --reload --host 0.0.0.0 --port 8000
Open http://localhost:8000

