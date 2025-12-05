# BWB

Broken Wing Butterfly Scanner

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
bwb = call_spread.BrokenWingButterfly(df)
call_spreads = bwb.generate_call_spreads("AAPL", "2025-11-15")
filtered_spreads = bwb.filter_spreads(call_spreads)
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
