from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
MODEL_PATH = os.getenv("MODEL_PATH", "models/Mortgage4.mdl")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AUTO_MATCH_THRESHOLD = float(os.getenv("AUTO_MATCH_THRESHOLD", "0.90"))
CONFIRM_THRESHOLD = float(os.getenv("CONFIRM_THRESHOLD", "0.65"))
USE_WEB_SEARCH_FOR_REAL_WORLD = os.getenv("USE_WEB_SEARCH_FOR_REAL_WORLD", "true").lower() == "true"

# Dynamic model horizon is preferred. Only used if model horizon cannot be detected.
FALLBACK_WINDOW_START = float(os.getenv("FALLBACK_WINDOW_START", "0"))
FALLBACK_WINDOW_END = float(os.getenv("FALLBACK_WINDOW_END", "100"))
