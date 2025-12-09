from pathlib import Path
import pandas as pd
from config import get_logger

logger = get_logger(__name__)


class DataLoader:
    """
    A class to handle loading and validation of options chain data from CSV files.
    """

    REQUIRED_COLUMNS = [
        "symbol",
        "expiry",
        "dte",
        "strike",
        "type",
        "bid",
        "ask",
        "mid",
        "delta",
        "iv",
    ]

    def __init__(self):
        pass

    def load_csv(self, file_path: str) -> pd.DataFrame:
        """
        Reads a CSV file and returns a pandas DataFrame with strict validation.

        Raises:
            FileNotFoundError: If file does not exist.
            ValueError: If file is empty, missing columns, or contains invalid data.
            TypeError: If critical columns have wrong data types.
        """
        path = Path(file_path)

        # Validate file exists
        if not path.exists():
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # Validate file is not empty
        if path.stat().st_size == 0:
            error_msg = f"File is empty: {file_path}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Read CSV with error handling
        try:
            df = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            error_msg = f"File contains no data: {file_path}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Error reading file {file_path}: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e

        # Validate DataFrame is not empty
        if df.empty:
            error_msg = f"DataFrame is empty after reading {file_path}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Validate required columns exist
        self._validate_columns(df)

        # Validate no null values in critical columns
        self._validate_no_nulls(df)

        # Validate data types
        self._validate_data_types(df)

        # Validate business rules
        self._validate_business_rules(df)

        # Standardize data types
        df["expiry"] = pd.to_datetime(df["expiry"], errors="coerce")
        df["type"] = df["type"].str.lower().str.strip()
        df["symbol"] = df["symbol"].str.upper().str.strip()

        # Validate date conversion succeeded
        if df["expiry"].isna().any():  # type: ignore
            error_msg = "Invalid date format in expiry column"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(f"Successfully loaded {len(df)} rows from {file_path}")
        return df

    def _validate_columns(self, df: pd.DataFrame) -> None:
        """
        Validates the DataFrame contains all required columns.
        """
        missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            error_msg = f"Missing required columns: {', '.join(missing_cols)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _validate_no_nulls(self, df: pd.DataFrame) -> None:
        """
        Validates the required columns have no null values.
        """
        null_counts = df[self.REQUIRED_COLUMNS].isnull().sum()

        if null_counts.any():
            invalid_cols = null_counts[null_counts > 0].to_dict()
            error_msg = f"Null values found in required columns: {invalid_cols}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _validate_data_types(self, df: pd.DataFrame) -> None:
        """
        Validates each column has the correct data type.

        Expected types:
        - symbol: string/object
        - expiry: date-like (string that can be converted to datetime)
        - dte: integer (whole number)
        - strike: numeric (float)
        - type: string/object (call/put)
        - bid: numeric (float)
        - ask: numeric (float)
        - mid: numeric (float)
        - delta: numeric (float, between 0-1)
        - iv: numeric (float)
        """

        column_types = {
            "symbol": "string",
            "expiry": "date",
            "dte": "integer",
            "strike": "numeric",
            "type": "string",
            "bid": "numeric",
            "ask": "numeric",
            "mid": "numeric",
            "delta": "numeric",
            "iv": "numeric",
        }

        for col, expected_type in column_types.items():
            if col not in df.columns:
                continue  # Already validated in _validate_columns

            if expected_type == "string":
                # Validate string columns
                if not pd.api.types.is_string_dtype(
                    df[col]
                ) and not pd.api.types.is_object_dtype(df[col]):
                    error_msg = (
                        f"{col} column must be string/object type. Got: {df[col].dtype}"
                    )
                    logger.error(error_msg)
                    raise TypeError(error_msg)

            elif expected_type == "date":
                # Validate date can be converted (will be validated later in load_csv)
                try:
                    pd.to_datetime(df[col], errors="raise")
                except (ValueError, TypeError) as e:
                    error_msg = f"{col} column must be date-like. Got: {df[col].dtype}, Error: {e}"
                    logger.error(error_msg)
                    raise TypeError(error_msg)

            elif expected_type == "integer":
                # Validate integer (dte should be whole numbers)
                if not pd.api.types.is_integer_dtype(df[col]):
                    try:
                        # Try to convert to integer
                        converted = pd.to_numeric(
                            df[col], errors="raise", downcast="integer"
                        )
                        # Check if all values are whole numbers
                        if not (converted == converted.astype(int)).all():  # type: ignore
                            error_msg = f"{col} column must be integer (whole numbers). Got non-integer values."
                            logger.error(error_msg)
                            raise TypeError(error_msg)
                    except (ValueError, TypeError) as e:
                        error_msg = f"{col} column must be integer. Got: {df[col].dtype}, Error: {e}"
                        logger.error(error_msg)
                        raise TypeError(error_msg)

            elif expected_type == "numeric":
                # Validate numeric columns
                if not pd.api.types.is_numeric_dtype(df[col]):
                    try:
                        pd.to_numeric(df[col], errors="raise")
                    except (ValueError, TypeError) as e:
                        error_msg = f"{col} column must be numeric. Got: {df[col].dtype}, Error: {e}"
                        logger.error(error_msg)
                        raise TypeError(error_msg)

    def _validate_business_rules(self, df: pd.DataFrame) -> None:
        """
        Validates business rules for options data.
        """
        # Validate delta is between 0 and 1 (for calls)
        if (df["delta"] < 0).any() or (df["delta"] > 1).any():
            invalid_deltas = df[~df["delta"].between(0, 1)]["delta"].tolist()
            error_msg = f"Delta values must be between 0 and 1. Invalid values: {invalid_deltas[:5]}"  # type: ignore
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Validate strike is positive
        if (df["strike"] <= 0).any():
            invalid_strikes = df[df["strike"] <= 0]["strike"].tolist()
            error_msg = f"Strike prices must be positive. Invalid values: {invalid_strikes[:5]}"  # type: ignore
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Validate prices are non-negative
        price_cols = ["bid", "ask", "mid"]
        for col in price_cols:
            if (df[col] < 0).any():
                invalid_prices = df[df[col] < 0][col].tolist()
                error_msg = f"{col} prices must be non-negative. Invalid values: {invalid_prices[:5]}"  # type: ignore
                logger.error(error_msg)
                raise ValueError(error_msg)

        # Validate bid <= ask (market sanity check)
        if (df["bid"] > df["ask"]).any():
            invalid_pairs = df[df["bid"] > df["ask"]][
                ["bid", "ask"]
            ].head()  # type: ignore
            error_msg = (
                f"Bid price cannot exceed Ask price. Invalid pairs: {invalid_pairs}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Validate mid is (bid + ask) / 2
        expected_mid = (df["bid"] + df["ask"]) / 2
        mid_diff = (df["mid"] - expected_mid).abs()
        tolerance = 0.01  # Allow 1 cent difference for rounding
        if (mid_diff > tolerance).any():
            invalid_mids = (
                df[mid_diff > tolerance][["bid", "ask", "mid"]]
                .head()  # type: ignore
                .to_dict("records")  # type: ignore
            )
            error_msg = (
                f"Mid price should be (bid + ask) / 2. Invalid rows: {invalid_mids}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Validate DTE is non-negative
        if (df["dte"] < 0).any():
            invalid_dte = df[df["dte"] < 0]["dte"].tolist()
            error_msg = f"DTE must be non-negative. Invalid values: {invalid_dte[:5]}"  # type: ignore
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Validate type is 'call' or 'put'
        valid_types = {"call", "put"}
        if not df["type"].isin(valid_types).all():  # type: ignore
            invalid_types = df[~df["type"].isin(valid_types)]["type"].unique().tolist()  # type: ignore
            error_msg = f"Type must be 'call' or 'put'. Invalid values: {invalid_types}"
            logger.error(error_msg)
            raise ValueError(error_msg)
