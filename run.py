import sys
import os
from livekit.agents import cli
from livekit.agents import WorkerOptions

# Ensure we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.agent import entrypoint

if __name__ == "__main__":
    # This allows running: python run.py console
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
