from pathlib import Path

from questionnaire_core.api import create_app
from questionnaire_core.settings import ExtractorSettings

EXAMPLES_DIR = Path(__file__).resolve().parents[3] / "examples"
DATA_DIR = Path(__file__).parent / "data"

TEST_SETTINGS = ExtractorSettings(CORS_ORIGINS="http://localhost:3000")


def unavailable_extractor():
    """En los tests el extractor siempre se reemplaza; si se usara el real, el test debe fallar."""
    msg = "Los tests deben reemplazar el extractor con app.dependency_overrides."
    raise AssertionError(msg)


test_app = create_app("extractor-test", TEST_SETTINGS, unavailable_extractor)
