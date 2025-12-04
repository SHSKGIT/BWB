import pandas as pd
from config import get_logger
from itertools import combinations
from typing import List, cast

logger = get_logger(__name__)


class BrokenWingButterflyCallSpread:
    """
    Constructs Broken Wing Butterfly (BWB) call spreads.

    Pattern:
    - Long 1 call at K1
    - Short 2 calls at K2
    - Long 1 call at K3

    Where K1 < K2 < K3 and (K2 - K1) != (K3 - K2)
    """

    def __init__(self, df: pd.DataFrame):
        """
        Initialize with options chain data.

        Args:
            df (pd.DataFrame): Options chain data containing strike, type, expiry, etc.
        """
        self.df = df

    # This method is combined bull call spread (buy 1 call at k1 and sell 1 call at k2) and bear call spread (sell 1 call at k1 and buy 1 call at k2), which means buy 1 call at K1, sell 2 calls at K2, and buy 1 call at K3
    def generate_call_spreads(
        self, ticker: str, expiry: str | pd.Timestamp
    ) -> pd.DataFrame:
        """
        Generate all valid BWB call spreads for a specific ticker and expiry.

        Args:
            ticker (str): The symbol to filter by.
            expiry (str | pd.Timestamp): The expiration date to filter by.

        Returns:
            pd.DataFrame: A DataFrame of valid BWB spreads with columns:
                          [symbol, expiry, k1, k2, k3, width1, width2, net_credit/debit, dte, delta_k2]
        """
        # Filter data for specific ticker, expiry, and call options
        filtered_df = self.df[
            (self.df["symbol"] == ticker)
            & (self.df["expiry"] == pd.to_datetime(expiry))
            & (self.df["type"] == "call")
        ].copy()

        if filtered_df.empty:
            logger.warning(f"No call options found for {ticker} expiring on {expiry}")
            return pd.DataFrame()

        # Ensure strikes are numeric
        filtered_df["strike"] = pd.to_numeric(filtered_df["strike"])

        # Explicitly cast to DataFrame for type checkers
        filtered_df = cast(pd.DataFrame, filtered_df)
        filtered_df = filtered_df.dropna(subset=["strike"])

        # Sort by strike, and filter out duplicate strikes
        filtered_df = filtered_df.sort_values(by="strike").drop_duplicates(
            subset=["strike"]
        )

        # convert to list for combinations and ensure type checker knows they are floats
        strikes = cast(List[float], filtered_df["strike"].tolist())

        # Create a lookup for price (mid) by strike, ex: {95: 10.50, 100: 7.20, 120: 4.80}
        strike_price_map = filtered_df.set_index("strike")["mid"].to_dict()
        # Create lookup for delta by strike for filtering
        strike_delta_map = filtered_df.set_index("strike")["delta"].to_dict()

        # Get DTE from the first row (expiry is the same for all rows)
        current_dte = filtered_df["dte"].iloc[0]

        spreads = []

        # Generate all combinations of 3 strikes (K1, K2, K3), and ensure 3 distinct strikes, and in order K1 < K2 < K3
        for k1, k2, k3 in combinations(strikes, 3):
            width1 = k2 - k1
            width2 = k3 - k2

            # Check for asymmetric wings (Broken Wing). Standard Butterfly has width1 == width2
            if width1 == width2:
                continue

            # Calculate pricing
            # Long 1 call at K1, Short 2 calls at K2, Long 1 call at K3
            # Cost = P(K1) - 2*P(K2) + P(K3)
            # If Cost > 0, it's a debit spread. If Cost < 0, it's a credit spread.
            p1 = strike_price_map[k1]
            p2 = strike_price_map[k2]
            p3 = strike_price_map[k3]

            delta_k2 = strike_delta_map[k2]

            cost = p1 - (2 * p2) + p3

            spreads.append(
                {
                    "symbol": ticker,
                    "expiry": expiry,
                    "dte": current_dte,
                    "k1": k1,
                    "k2": k2,
                    "k3": k3,
                    "width1": width1,
                    "width2": width2,
                    "cost": cost,
                    "price_k1": p1,
                    "price_k2": p2,
                    "price_k3": p3,
                    "delta_k2": delta_k2,
                }
            )

        result_df = pd.DataFrame(spreads)
        logger.info(f"Generated {len(result_df)} BWB spreads for {ticker} on {expiry}")

        return result_df

    def filter_spreads(
        self,
        spreads_df: pd.DataFrame,
        min_credit: float = 0.50,
        min_dte: int = 1,
        max_dte: int = 10,
        min_short_delta: float = 0.20,
        max_short_delta: float = 0.35,
    ) -> pd.DataFrame:
        """
        Filter spreads based on provided criteria:
        - DTE between 1 and 10 days
        - Minimum net credit (e.g. ≥ $0.50)
        - Short strike delta between 0.20 and 0.35

        Args:
            spreads_df (pd.DataFrame): The DataFrame of generated spreads.
            min_credit (float): Minimum net credit required (default: 0.50).
            min_dte (int): Minimum days to expiration (default: 1).
            max_dte (int): Maximum days to expiration (default: 10).
            min_short_delta (float): Minimum delta for the short strike (K2) (default: 0.20).
            max_short_delta (float): Maximum delta for the short strike (K2) (default: 0.35).

        Returns:
            pd.DataFrame: The filtered DataFrame.
        """
        if spreads_df.empty:
            return spreads_df

        filtered_spreads_df = spreads_df.copy()

        # Filter by DTE
        filtered_spreads_df = filtered_spreads_df[
            (filtered_spreads_df["dte"] >= min_dte)
            & (filtered_spreads_df["dte"] <= max_dte)
        ]

        # Filter by Short Strike Delta (K2)
        filtered_spreads_df = filtered_spreads_df[
            (filtered_spreads_df["delta_k2"] >= min_short_delta)
            & (filtered_spreads_df["delta_k2"] <= max_short_delta)
        ]

        # Filter by Minimum Net Credit
        # Cost < 0 means credit. Credit = -Cost.
        # I want Credit >= min_credit -> -Cost >= min_credit -> Cost <= -min_credit
        # Use a small epsilon for floating point comparison robustness, ex: 0.4999999 -> 0.50 If not, this spread will be filtered out.
        epsilon = 1e-9
        filtered_spreads_df = filtered_spreads_df[
            filtered_spreads_df["cost"] <= (-min_credit + epsilon)
        ]

        logger.info(
            f"Filtered spreads from {len(spreads_df)} to {len(filtered_spreads_df)}"
        )
        return cast(pd.DataFrame, filtered_spreads_df)

    def rank_spreads(
        self,
        spreads_df: pd.DataFrame,
        sort_by: str = "score",
        ascending: bool = False,
    ) -> pd.DataFrame:
        """
        Rank the candidate BWBs by a score.

        Score = Max Profit / Max Loss

        Args:
            spreads_df (pd.DataFrame): The DataFrame of spreads (either filtered or unfiltered).
            sort_by (str): Column to sort by. Default is "score".
            ascending (bool): Sort order. Default is False (descending order).

        Returns:
            pd.DataFrame: Sorted DataFrame with columns:
                          [symbol, expiry, k1, k2, k3, credit, max_profit, max_loss, score]
        """
        if spreads_df.empty:
            return pd.DataFrame()

        df = spreads_df.copy()

        # Calculate Credit (-Cost)
        df["credit"] = -df["cost"]

        # Max Profit = Width of first wing + Net Credit, at around K2
        df["max_profit"] = df["width1"] + df["credit"]

        # Max Loss, at above K3.
        # Loss = (Width2 - Width1) - Credit
        # If the result is negative (i.e. it's still profitable), Max Loss is 0.
        df["max_loss"] = (df["width2"] - df["width1"] - df["credit"]).clip(lower=0)

        # Score = Max Profit / Max Loss
        # Pandas handles zero division error, it won't raise ZeroDivisionError. It will return NaN.
        df["score"] = df["max_profit"] / df["max_loss"]

        # Select columns to return
        cols_to_return = [
            "symbol",
            "expiry",
            "k1",
            "k2",
            "k3",
            "credit",
            "max_profit",
            "max_loss",
            "score",
        ]

        # Sorting
        sorted_df = df.sort_values(by=sort_by, ascending=ascending)

        return sorted_df[cols_to_return]
