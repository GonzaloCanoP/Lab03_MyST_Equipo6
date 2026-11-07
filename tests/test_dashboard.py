"""El dashboard corre sobre los artefactos versionados sin errores y muestra las 7 gráficas de la vista técnica en
cada rango de partición. No recalcula nada: solo lee `artifacts/`."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from dashboard.data import missing_artifacts

APP = str(Path(__file__).resolve().parents[1] / "dashboard" / "app.py")


def test_artifacts_for_dashboard_exist():
    assert missing_artifacts() == [], "corre python main.py para generar los artefactos"


@pytest.mark.parametrize("partition", ["TODO", "TRAIN", "TEST", "VALID"])
def test_dashboard_renders_without_errors(partition):
    app = AppTest.from_file(APP, default_timeout=120).run()
    app.segmented_control(key="range").set_value(partition).run()
    assert not app.exception, [e.value for e in app.exception]
    assert not app.error, [e.value for e in app.error]
    assert len(app.get("plotly_chart")) == 7  # vista técnica: 7 paneles
