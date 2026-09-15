# Vercel Python function entrypoint. For local development use:
#   uvicorn ingestion.service:app --reload --port 8010
from ingestion.service import app
