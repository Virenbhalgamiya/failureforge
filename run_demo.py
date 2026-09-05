#!/usr/bin/env python3
"""
FailureForge Zero-Friction Launcher.
Automatically installs dependencies if missing and launches the evaluation demo.
"""

import sys
import subprocess
from pathlib import Path

# Add backend directory to python path
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))


def ensure_dependencies():
    """Ensure all required Python packages are installed."""
    required = ["fastapi", "sqlalchemy", "rich", "typer", "structlog", "httpx"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"📦 Installing required dependencies for FailureForge: {', '.join(missing)}...")
        req_file = ROOT_DIR / "requirements.txt"
        if not req_file.exists():
            req_file = BACKEND_DIR / "requirements.txt"

        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req_file)])
        print("✅ Dependencies installed successfully!\n")


def main():
    ensure_dependencies()
    import os
    from failureforge.config import get_settings
    settings = get_settings()

    api_key = settings.get_effective_api_key()
    if api_key:
        print("🔑 LLM API Key detected! Groq / OpenAI active for live LLM agent evaluations.")
    else:
        print("💡 Running in Zero-Setup Local Demo Mode (No API key required).")
        print("   To run live LLM agents, add GROQ_API_KEY or OPENAI_API_KEY to your .env file.\n")

    from failureforge.cli.main import app

    sys.argv = ["failureforge", "demo"]
    app()



if __name__ == "__main__":
    main()
