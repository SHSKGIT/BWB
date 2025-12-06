# BWB

This project is about Broken Wing Butterfly call spread, containing both bull and bear.

### Assumptions

This project makes the following assumptions about the data and strategy:

1.  **Market Data**:

    - **Mid Price**: Calculations for cost/credit are based on the **Mid Price** (average of Bid and Ask) to estimate fair value.
    - **Data Format**: An CSV file is expected to have columns: `symbol`, `expiry`, `dte`, `strike`, `type`, `bid`, `ask`, `mid`, `delta`, `iv`. (`iv` is not used in this project)
    - **Single Chain**: Strategy generation is done per specific `ticker` and `expiry`. It does not support calendar spreads (different expiries).

2.  **Strategy Structure (Broken Wing Butterfly)**:

    - **3 Legs**: Long 1 Call ($K1$), Short 2 Calls ($K2$), Long 1 Call ($K3$).
    - **Strike Order**: $K1 < K2 < K3$.
    - **Asymmetry**: The wings are strictly unequal ($K2 - K1 \neq K3 - K2$). Standard symmetrical butterflies are filtered out.

3.  **Risk/Reward Calculations**:

    - **Max Profit**: Assuming the asset stock price lands exactly at the short strike ($K2$) at expiration. Formula: `Width1 + Net Credit`.
    - **Max Loss**: Assuming the asset stock price is above the highest strike ($K3$). Formula: `Width2 - Width1 - Net Credit`. Max Loss is clipped to 0.

4.  **Filtering**:
    - Default filters is applied to a **Credit** strategy (receive premium to open the trade). Debit spreads are filtered out by default unless `min_credit` is set to a negative value. (Credit means cost < 0, debit means cost > 0)
    - Short strike is based on delta between 0.20 and 0.35 to get a moderate premium.

### ENV

Please create a venv for this project under project root folder.

```
python -m venv venv
```

Activate venv. (Normally IDE's terminal can auto activate it, if not, please do it manually)

```
source venv/bin/activate
```

And install dependencies.

```
pip install -r requirements.txt
```

### Options data

Options data is located in csvs folder.

To load csv data:

```
from modules import data_loader
dl = data_loader.DataLoader()
df = dl.load_csv("csvs/mock_options_data.csv")
```

### Call spread data

```
from modules import call_spread
bwb = call_spread.BrokenWingButterflyCallSpread(df)
call_spreads = bwb.generate_call_spreads("AAPL", "2025-11-15")
filtered_spreads = bwb.filter_spreads(call_spreads)
ranked_spread = bwb.rank_spreads(filtered_spreads)
```

The filtered spreads should look like this:

```
>>> filtered_spreads
   symbol      expiry  dte   k1   k2   k3  width1  width2  cost  price_k1  price_k2  price_k3  delta_k2
0    AAPL  2025-11-15    9   95  100  110       5      10  -0.8     10.55      7.25      3.15       0.3
1    AAPL  2025-11-15    9   95  100  115       5      15  -2.0     10.55      7.25      1.95       0.3
2    AAPL  2025-11-15    9   95  100  120       5      20  -2.8     10.55      7.25      1.15       0.3
3    AAPL  2025-11-15    9   95  100  125       5      25  -3.3     10.55      7.25      0.65       0.3
12   AAPL  2025-11-15    9  100  105  115       5      10  -0.5      7.25      4.85      1.95       0.2
13   AAPL  2025-11-15    9  100  105  120       5      15  -1.3      7.25      4.85      1.15       0.2
14   AAPL  2025-11-15    9  100  105  125       5      20  -1.8      7.25      4.85      0.65       0.2
```

The ranked spreads (descending order by score column) should look like this:

```
>>> ranked_spread
   symbol      expiry   k1   k2   k3  credit  max_profit  max_loss     score
0    AAPL  2025-11-15   95  100  110     0.8         5.8       4.2  1.380952
12   AAPL  2025-11-15  100  105  115     0.5         5.5       4.5  1.222222
1    AAPL  2025-11-15   95  100  115     2.0         7.0       8.0  0.875000
13   AAPL  2025-11-15  100  105  120     1.3         6.3       8.7  0.724138
2    AAPL  2025-11-15   95  100  120     2.8         7.8      12.2  0.639344
14   AAPL  2025-11-15  100  105  125     1.8         6.8      13.2  0.515152
3    AAPL  2025-11-15   95  100  125     3.3         8.3      16.7  0.497006
```

### Unit test (pytest)

All test cases are located in tests/test_bwb.py

To test all functions:

```
With log info print in terminal:
pytest -s -o log_cli=true -o log_cli_level=INFO tests/test_bwb.py

Without log info print in terminal:
pytest tests/test_bwb.py
```

To test each function:

```
With log info print in terminal:
pytest -s -o log_cli=true -o log_cli_level=INFO tests/test_bwb.py::test_generate_call_spreads
pytest -s -o log_cli=true -o log_cli_level=INFO tests/test_bwb.py::test_filter_spreads
pytest -s -o log_cli=true -o log_cli_level=INFO tests/test_bwb.py::test_rank_spreads

Without log info print in terminal:
pytest tests/test_bwb.py::test_generate_call_spreads
pytest tests/test_bwb.py::test_filter_spreads
pytest tests/test_bwb.py::test_rank_spreads
```

### Future integration

1. Use external API to fetch real-time options chain data.

2. Store historical options data into a DB.

3. Create a UI containing a chart to show profit and loss with dates before expiry. This will be integrated into a web server.
