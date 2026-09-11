from app.services.cost_projection import project_monthly_cost


def test_empty_history_returns_zeroed_projection():
    result = project_monthly_cost([])
    assert result.projected_monthly_kwh == 0.0
    assert result.projected_monthly_cost_mxn == 0.0
    assert result.percent_change_vs_previous_period is None


def test_stable_consumption_projects_linear_monthly_total():
    # 1000 Wh/día constante durante 10 días -> ~30,000 Wh = 30 kWh en el mes
    daily = [1000.0] * 10
    result = project_monthly_cost(daily, tariff_mxn_per_kwh=2.0)
    assert result.projected_monthly_kwh == 30.0
    assert result.projected_monthly_cost_mxn == 60.0
    assert result.is_trending_up is False


def test_growing_consumption_flags_trending_up():
    # segunda mitad claramente más alta que la primera (refrigerador que
    # empieza a consumir más de lo normal)
    daily = [500.0, 500.0, 500.0, 500.0, 900.0, 900.0, 900.0, 900.0]
    result = project_monthly_cost(daily)
    assert result.is_trending_up is True
    assert result.percent_change_vs_previous_period > 0.30


def test_stable_consumption_does_not_flag_trending_up():
    daily = [500.0, 510.0, 495.0, 505.0, 500.0, 502.0, 498.0, 500.0]
    result = project_monthly_cost(daily)
    assert result.is_trending_up is False


def test_higher_tariff_increases_projected_cost():
    daily = [1000.0] * 10
    low = project_monthly_cost(daily, tariff_mxn_per_kwh=1.0)
    high = project_monthly_cost(daily, tariff_mxn_per_kwh=3.0)
    assert high.projected_monthly_cost_mxn > low.projected_monthly_cost_mxn


def test_short_history_skips_trend_anomaly_check():
    # menos de 4 días: no hay suficiente historial para comparar mitades
    daily = [500.0, 9000.0]
    result = project_monthly_cost(daily)
    assert result.percent_change_vs_previous_period is None
    assert result.is_trending_up is False


def test_factors_include_expected_keys():
    result = project_monthly_cost([500.0] * 6)
    factor_names = {f["factor"] for f in result.factors}
    assert factor_names == {
        "avg_daily_energy_wh",
        "trend_wh_per_day",
        "percent_change_vs_previous_period",
    }
