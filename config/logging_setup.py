"""UTF-8 safe logging for Windows consoles."""
import logging
import os
import sys


def setup_logging(name: str = "jobradar", log_file: str = "data/jobradar.log") -> logging.Logger:
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
        force=True,
    )
    return logging.getLogger(name)
