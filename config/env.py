from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - environment guard
    def load_dotenv(*args, **kwargs) -> bool:
        return False


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
