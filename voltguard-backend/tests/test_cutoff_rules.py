from app.services.cutoff_rules import evaluate_cutoff


def test_no_cutoff_when_no_threshold_configured():
    decision = evaluate_cutoff(current_a=50.0, max_current_a=None, auto_cutoff_enabled=True)
    assert decision.triggered is False


def test_cutoff_triggers_when_current_exceeds_threshold():
    decision = evaluate_cutoff(current_a=16.0, max_current_a=15.0, auto_cutoff_enabled=True)
    assert decision.triggered is True


def test_no_cutoff_when_current_within_threshold():
    decision = evaluate_cutoff(current_a=10.0, max_current_a=15.0, auto_cutoff_enabled=True)
    assert decision.triggered is False


def test_no_cutoff_when_auto_cutoff_disabled_even_over_threshold():
    decision = evaluate_cutoff(current_a=30.0, max_current_a=15.0, auto_cutoff_enabled=False)
    assert decision.triggered is False


def test_current_exactly_at_threshold_does_not_trigger():
    decision = evaluate_cutoff(current_a=15.0, max_current_a=15.0, auto_cutoff_enabled=True)
    assert decision.triggered is False
