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
        Reads a CSV file and returns a pandas DataFrame.
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            df = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            logger.error(f"File is empty: {file_path}")
            raise ValueError(f"File is empty: {file_path}")
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise

        self._validate_columns(df)

        # Standardize data types
        df["expiry"] = pd.to_datetime(df["expiry"])
        df["type"] = df["type"].str.lower().str.strip()
        df["symbol"] = df["symbol"].str.upper().str.strip()

        logger.info(f"Successfully loaded {len(df)} rows from {file_path}")
        return df

    def _validate_columns(self, df: pd.DataFrame) -> None:
        """
        Validates that the DataFrame contains all required columns.

        Args:
            df (pd.DataFrame): The DataFrame to validate.

        Raises:
            ValueError: If required columns are missing.
        """
        missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            error_msg = f"Missing required columns: {', '.join(missing_cols)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
