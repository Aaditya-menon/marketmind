import os
import sys
import uvicorn
from fastapi.staticfiles import StaticFiles

# Inject current directory into sys.path to resolve sub-agent module imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from google.adk.cli.fast_api import get_fast_api_app

# 1. Instantiate the ADK FastAPI application
app = get_fast_api_app(
    agents_dir=".",
    web=True,
    use_local_storage=True
)

# 2. Mount the custom frontend directory as static files on the same origin
app.mount("/static", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    print("\n" + "="*80)
    print(" MarketMind Local Server started successfully!")
    print(" Access the custom dashboard directly at: http://127.0.0.1:8000/static/index.html")
    print("="*80 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
