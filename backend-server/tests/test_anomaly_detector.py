from app.services.anomaly_detector import (
    IsolationForestDetector,
    RuleBasedDetector,
    get_detector,
)


def test_rule_based_flags_large_spike():
    detector = RuleBasedDetector(z_threshold=3.0, min_history=5)
    history = [60.0, 62.0, 58.0, 61.0, 59.0]
    result = detector.evaluate(history, 400.0)
    assert result.is_anomaly is True
    assert result.detector_name == "rule_based"


def test_rule_based_does_not_flag_normal_reading():
    detector = RuleBasedDetector(z_threshold=3.0, min_history=5)
    history = [60.0, 62.0, 58.0, 61.0, 59.0]
    result = detector.evaluate(history, 61.5)
    assert result.is_anomaly is False


def test_rule_based_needs_minimum_history():
    detector = RuleBasedDetector(min_history=5)
    result = detector.evaluate([60.0, 61.0], 400.0)
    assert result.is_anomaly is False


def test_rule_based_zero_variance_flags_any_change():
    # Historial perfectamente constante (std=0): el z-score no se puede
    # calcular (división por cero), así que cualquier cambio se marca
    # como anómalo directamente, en vez de comparar contra un umbral.
    detector = RuleBasedDetector(min_history=5)
    history = [100.0, 100.0, 100.0, 100.0, 100.0]
    result = detector.evaluate(history, 100.0)
    assert result.is_anomaly is False

    result = detector.evaluate(history, 105.0)
    assert result.is_anomaly is True


def test_isolation_forest_needs_minimum_history():
    detector = IsolationForestDetector(min_history=10)
    result = detector.evaluate([60.0, 61.0, 59.0], 400.0)
    assert result.is_anomaly is False
    assert result.detector_name == "isolation_forest"


def test_isolation_forest_flags_large_spike():
    detector = IsolationForestDetector(min_history=10)
    rng = __import__("random")
    rng.seed(0)
    history = [60.0 + rng.uniform(-1.5, 1.5) for _ in range(30)]  # ~60W con variación normal
    result = detector.evaluate(history, 500.0)
    assert result.is_anomaly is True
    assert result.detector_name == "isolation_forest"


def test_factory_returns_rule_based_by_default():
    detector = get_detector("anything_else")
    assert detector.name == "rule_based"


def test_factory_returns_isolation_forest_when_requested():
    detector = get_detector("isolation_forest")
    assert detector.name == "isolation_forest"
