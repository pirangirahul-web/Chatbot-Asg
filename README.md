# 🌱 Eco-Travel Advisor — Rasa Chatbot

A conversational agent that helps travellers plan environmentally responsible trips.

## Features
- Multi-turn trip intake (destination, dates, budget, sustainability preference)
- Real-time carbon footprint estimates (Climatiq API + fallback factors)
- Eco-certified hotel recommendations (Amadeus sandbox + mock data)
- Weighted ranking (carbon × price × user preferences)
- Human advisor handover with full context
- Two-stage fallback clarification
- Colour-coded UI cards (green / amber / red)
- GDPR-conscious: no persistent PII, `.env` never committed

## Quickstart

### 1. Clone & set up
```bash
git clone https://github.com/<you>/eco-travel-advisor.git
cd eco-travel-advisor
python3.9 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure API keys
```bash
cp .env.example .env
# edit .env with your Climatiq + Amadeus credentials
```

### 3. Train & run
```bash
rasa train
rasa run actions &          # terminal 1
rasa run --enable-api --cors "*"   # terminal 2
```

### 4. Open frontend
```bash
cd frontend && python -m http.server 8080
# visit http://localhost:8000
```

## Docker
```bash
docker compose up --build
```

## Testing
```bash
rasa test nlu --cross-validation
rasa test core
pytest tests/
```

## Deployment
- Recommended: HuggingFace Spaces (Docker SDK) — see `Dockerfile`.
- Alternative: AWS ECS, Azure Container Apps, GCP Cloud Run.

## Ethics & Privacy
- No PII persisted beyond session.
- API keys loaded from environment only.
- Carbon methodology transparent (Climatiq + documented fallback factors).
- Screen-reader friendly UI, keyboard-navigable quick replies.

## License
MIT