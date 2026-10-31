import os
from pathlib import Path

# Se define antes de que cualquier test importe la app, porque la configuración se lee al importar.
os.environ["CORS_ORIGINS"] = "http://localhost:3000"

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"
DATA_DIR = Path(__file__).parent / "data"
