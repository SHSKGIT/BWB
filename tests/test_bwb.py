import pytest
import pandas as pd
from modules.call_spread import BrokenWingButterflyCallSpread
from modules.data_loader import DataLoader
from config import get_logger

logger = get_logger(__name__)

# this is to mock data from csv file.
TEST_DATA = {
    "symbol": ["AAPL"] * 7,
    "expiry": ["2025-11-15"] * 7,
    "dte": [8] * 7,
    "strike": [95, 100, 105, 110, 115, 120, 125],
    "type": ["call"] * 7,
    "bid": [10.50, 7.20, 4.80, 3.10, 1.90, 1.10, 0.60],
    "ask": [10.60, 7.30, 4.90, 3.20, 2.00, 1.20, 0.70],
    "mid": [10.55, 7.25, 4.85, 3.15, 1.95, 1.15, 0.65],
    "delta": [0.40, 0.30, 0.20, 0.15, 0.10, 0.08, 0.05],
    "iv": [0.15] * 7,
}


@pytest.fixture
def options_data():
    df = pd.DataFrame(TEST_DATA)
    # Simulate the data type conversion that happens in DataLoader
    df["expiry"] = pd.to_datetime(df["expiry"])

    return df


@pytest.fixture
def bwb_call_spread_instance(options_data):

    return BrokenWingButterflyCallSpread(options_data)


def test_generate_call_spreads(bwb_call_spread_instance):
    ticker = "AAPL"
    expiry = "2025-11-15"

    spreads = bwb_call_spread_instance.generate_call_spreads(ticker, expiry)

    logger.info(f"spreads: {spreads}")
    assert not spreads.empty

    # Check a specific known spread from the mock data
    # 100 / 105 / 115
    # Width1 = 5, Width2 = 10
    # Cost = 7.25 - 2(4.85) + 1.95 = -0.5
    known_spread = spreads[
        (spreads["k1"] == 100) & (spreads["k2"] == 105) & (spreads["k3"] == 115)
    ]

    assert not known_spread.empty
    assert known_spread.iloc[0]["width1"] == 5
    assert known_spread.iloc[0]["width2"] == 10
    # need precision to avoid decimal point error, ex: 0.4999999 -> 0.50
    assert pytest.approx(known_spread.iloc[0]["cost"], 0.001) == -0.5


def test_filter_spreads(bwb_call_spread_instance):
    ticker = "AAPL"
    expiry = "2025-11-15"
    spreads = bwb_call_spread_instance.generate_call_spreads(ticker, expiry)

    # Test default credit filter
    # min_credit=0.50
    filtered_spreads = bwb_call_spread_instance.filter_spreads(
        spreads,
        min_credit=0.50,
        min_dte=1,
        max_dte=10,
        min_short_delta=0.20,
        max_short_delta=0.35,
    )

    # The spread 100/105/115 has cost -0.5 (credit = -cost = 0.5).
    # Delta of 105 is 0.20.
    # It should be included.

    # Check if specific spread exists in filtered results
    target_spread = filtered_spreads[
        (filtered_spreads["k1"] == 100)
        & (filtered_spreads["k2"] == 105)
        & (filtered_spreads["k3"] == 115)
    ]
    logger.info(f"target_spread (default creditfilter): {target_spread}")
    assert not target_spread.empty

    # Test strict creditfilter
    # If credit > 0.6, it should be filtered out
    target_spread = bwb_call_spread_instance.filter_spreads(
        spreads,
        min_credit=0.60,
        min_dte=1,
        max_dte=10,
        min_short_delta=0.20,
        max_short_delta=0.35,
    )
    target_spread = target_spread[
        (target_spread["k1"] == 100)
        & (target_spread["k2"] == 105)
        & (target_spread["k3"] == 115)
    ]
    logger.info(f"target_spread (strict credit filter): {target_spread}")
    assert target_spread.empty


def test_rank_spreads(bwb_call_spread_instance):
    ticker = "AAPL"
    expiry = "2025-11-15"
    spreads = bwb_call_spread_instance.generate_call_spreads(ticker, expiry)

    filtered_spreads = bwb_call_spread_instance.filter_spreads(spreads)

    ranked_spreads = bwb_call_spread_instance.rank_spreads(filtered_spreads)

    # Check Score Calculation for spread (100/105/115):
    # cost = 7.25 - 2(4.85) + 1.95 = -0.5
    # credit = -cost = 0.5
    # Max Profit = Width1 (5) + Credit (0.5) = 5.5
    # Max Loss = Width2 (10) - Width1 (5) - Credit (0.5) = 4.5
    # Score = 5.5 / 4.5 = 1.22

    row = ranked_spreads[ranked_spreads["k1"] == 100].iloc[0]
    logger.info(f"row: {row}")
    assert pytest.approx(row["max_profit"], 0.1) == 5.5
    assert pytest.approx(row["max_loss"], 0.1) == 4.5
    assert pytest.approx(row["score"], 0.01) == 1.22


# ========== NEW ADDED EDGE CASES & ERROR HANDLING TESTS ==========


def test_data_loader_missing_columns():
    invalid_data = pd.DataFrame({"symbol": ["AAPL"], "strike": [100]})
    loader = DataLoader()
    with pytest.raises(ValueError, match="Missing required columns"):
        loader._validate_columns(invalid_data)


def test_data_loader_null_values():
    data_with_nulls = pd.DataFrame(TEST_DATA)
    data_with_nulls.loc[0, "strike"] = None
    loader = DataLoader()
    with pytest.raises(ValueError, match="Null values found"):
        loader._validate_no_nulls(data_with_nulls)


def test_data_loader_invalid_delta():
    invalid_data = pd.DataFrame(TEST_DATA)
    invalid_data.loc[0, "delta"] = 1.5
    loader = DataLoader()
    with pytest.raises(ValueError, match="Delta values must be between 0 and 1"):
        loader._validate_business_rules(invalid_data)


def test_data_loader_bid_exceeds_ask():
    invalid_data = pd.DataFrame(TEST_DATA)
    invalid_data.loc[0, "bid"] = 10.0
    invalid_data.loc[0, "ask"] = 5.0
    loader = DataLoader()
    with pytest.raises(ValueError, match="Bid price cannot exceed Ask price"):
        loader._validate_business_rules(invalid_data)


def test_generate_call_spreads_empty_dataframe():
    with pytest.raises(ValueError, match="DataFrame cannot be empty"):
        BrokenWingButterflyCallSpread(pd.DataFrame())


def test_generate_call_spreads_invalid_ticker():
    bwb = BrokenWingButterflyCallSpread(pd.DataFrame(TEST_DATA))
    with pytest.raises(ValueError, match="Ticker must be a non-empty string"):
        bwb.generate_call_spreads("", "2025-11-15")


def test_generate_call_spreads_insufficient_strikes():
    limited_data = pd.DataFrame(
        {
            "symbol": ["AAPL"] * 2,
            "expiry": ["2025-11-15"] * 2,
            "dte": [8] * 2,
            "strike": [100, 105],
            "type": ["call"] * 2,
            "bid": [7.20, 4.80],
            "ask": [7.30, 4.90],
            "mid": [7.25, 4.85],
            "delta": [0.30, 0.20],
            "iv": [0.15] * 2,
        }
    )
    limited_data["expiry"] = pd.to_datetime(limited_data["expiry"])
    bwb = BrokenWingButterflyCallSpread(limited_data)
    result = bwb.generate_call_spreads("AAPL", "2025-11-15")
    assert result.empty


def test_filter_spreads_invalid_parameters():
    bwb = BrokenWingButterflyCallSpread(pd.DataFrame(TEST_DATA))
    spreads = pd.DataFrame([{"dte": 5, "delta_k2": 0.25, "cost": -0.5}])

    # Test min_dte > max_dte
    with pytest.raises(ValueError, match="min_dte.*cannot exceed max_dte"):
        bwb.filter_spreads(spreads, min_dte=10, max_dte=5)

    # Test invalid delta range
    with pytest.raises(
        ValueError, match="min_short_delta.*cannot exceed max_short_delta"
    ):
        bwb.filter_spreads(spreads, min_short_delta=0.5, max_short_delta=0.2)


def test_rank_spreads_negative_widths():
    bwb = BrokenWingButterflyCallSpread(pd.DataFrame(TEST_DATA))
    invalid_spreads = pd.DataFrame([{"width1": -5, "width2": 10, "cost": -0.5}])

    with pytest.raises(ValueError, match="Widths must be non-negative"):
        bwb.rank_spreads(invalid_spreads)


def test_full_pipeline_integration(bwb_call_spread_instance):
    ticker = "AAPL"
    expiry = "2025-11-15"

    # Generate
    spreads = bwb_call_spread_instance.generate_call_spreads(ticker, expiry)
    assert not spreads.empty
    assert "width1" in spreads.columns
    assert "width2" in spreads.columns
    assert "cost" in spreads.columns

    # Filter
    filtered = bwb_call_spread_instance.filter_spreads(spreads)
    assert len(filtered) <= len(spreads)
    assert not filtered.empty

    # Rank
    ranked = bwb_call_spread_instance.rank_spreads(filtered)
    assert len(ranked) == len(filtered)
    assert "score" in ranked.columns

    # Validate sorting (should be descending by score)
    if len(ranked) > 1:
        assert ranked["score"].is_monotonic_decreasing
