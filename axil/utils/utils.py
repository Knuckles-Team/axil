#!/usr/bin/env python3
import importlib.metadata
import logging
import os

# Resolve centralized log directory via the single backend seam
from axil.services.backend_adapter import backend

axil_log_dir = backend.resolve_log_dir()
axil_log_dir.mkdir(parents=True, exist_ok=True)
axil_log_path = axil_log_dir / "axil.log"

logger = logging.getLogger("axil")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
fh = logging.FileHandler(axil_log_path)
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)


def check_package(package: str = "None") -> bool:
    found = False
    try:
        version = importlib.metadata.version(package)
        logger.info(f"{package} ({version}) is installed")
        found = True
    except importlib.metadata.PackageNotFoundError:
        logger.info(f"{package} is NOT installed")
    return found


def resource_path(relative_path: str = "None") -> str:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    fallback = os.path.dirname(os.path.dirname(__file__))
    try:
        # PyInstaller sets _MEIPASS/_MEIPASS2 for bundled apps; named
        # fallback keeps the dev-tree default explicit for static scanners.
        base_path = os.environ.get("_MEIPASS", fallback)
        base_path = os.environ.get("_MEIPASS2", base_path)
    except Exception:
        base_path = fallback
    if not os.path.exists(base_path) or base_path == "":
        base_path = fallback
    return os.path.join(base_path, relative_path)
