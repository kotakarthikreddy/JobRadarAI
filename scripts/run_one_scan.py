"""Run a single scan cycle (for testing)."""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()
os.makedirs("data", exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from scanner.orchestrator import run_scan


if __name__ == "__main__":
    result = asyncio.run(run_scan())
    print("\n=== Scan result ===")
    for k, v in result.items():
        print(f"  {k}: {v}")
