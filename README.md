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
