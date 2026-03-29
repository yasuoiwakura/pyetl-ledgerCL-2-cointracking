# pyetl-ledgerCL-2-cointracking

Converts withCL crypto debit card CSV exports to CoinTracking-compatible CSV format.


## Overview

This Python script converts CSV exports from the withCL crypto debit card into the CSV format expected by CoinTracking.

## Target Format (CoinTracking)

CoinTracking expects the following columns:
"Type", "Buy Amount", "Buy Currency", "Sell Amount", "Sell Currency", "Fee", "Fee Currency", "Exchange", "Trade-Group", "Comment", "Date"

Optional:
"Liquidity pool (optional)", "Tx-ID (optional)", "Buy Value in Account Currency (optional)", "Sell Value in Account Currency (optional)"

## withCL Export Format

The withCL CSV contains the following columns:
- Timestamp
- Merchant
- Merchant Type
- Transaction Currency
- Transaction currency amount
- Card currency
- Card currency amount
- Mastercard exchange rate
- ECB exchange rate
- Program markup%
- Funding Source

## Mapping (Spend/Expenses)

| CoinTracking | withCL |
|--------------|--------|
| Type | "Spend" |
| Sell Amount | **Funding Source** (crypto amount) |
| Sell Currency | **Funding Source** (crypto currency) |
| Fee | 0 (not available) |
| Exchange | "WithCL" |
| Comment | "Single expense multiple Fundings" (when multiple fundings) |
| Date | Timestamp |

**Important:** The "Funding Source" column contains the crypto amount and currency (e.g., `56.61 eurt`), not the transaction currency.

## Issues in withCL Export

The withCL CSV has technical issues:

1. **Leading spaces in column names** – Headers like ` ECB exchange rate`, ` Program markup%` have leading whitespace
2. **Unescaped commas** – Some rows contain commas in data, e.g., `56.61132571 eurt, 63.9979846 usdt`

The script uses `csv.DictReader` (not pandas) and normalizes column names (trims whitespace) to handle this robustly.

## Configuration

```python
CT_TYPE        = "Spend"           # CoinTracking Type
CT_EXCHANGE    = "WithCL"          # Exchange name
CT_TRADEGROUP  = "python"          # Trade-Group

ALLOW_SIMPLIFIED_HANDLING_OF_SEVERAL_FUNDINGS_PER_ROW = True  # Allow multiple fundings per row
IGNORE_FURTHER_COLUMNS = True                                # Ignore additional columns
```

When a row contains multiple fundings (e.g., `eurt, usdt`), it is split into multiple output rows.

## Features

- MVP: Import of expenses (Spend)
- Virtual Tx-ID generation (hash-based, row-independent)
- Comment extension with formatted amounts (German locale: `1.234,56 EUR`)
- Robust handling of broken CSV (extra columns as split funding)
- Split of multiple fundings per row
- `csv.QUOTE_ALL` for safe output

## Tx-ID Format

Format: `{hash}-{date}-{merchantType}-{merchant}-{txCurrency}-{txAmount}-{cardCurrency}-{cardAmount}-{fundingAmount}-{fundingCurrency}-dup{dup:03d}-funding{fundingIndex:02d}`

- **Hash**: SHA1 (6 chars) from transaction base data
- **dup**: Index for duplicate transactions (same tx_base)
- **funding**: Index for multi-funding splits (starts at 01)

Tx-ID is deterministic and does not depend on row numbers.

## Limitations (Current MVP)

### 1. Non-RFC-4180-Compliant Input CSV

The withCL CSV violates RFC 4180 (CSV standard) in two ways:

- **Leading spaces in column names** – Headers like ` ECB exchange rate` contain leading whitespace
- **Unescaped commas** – Row 22 contains `56.61132571 eurt, 63.9979846 usdt` without quotes

**Impact:** The script must normalize column names and handle split rows.

### 2. Heuristic Assumption: Extra Columns = Additional Fundings

When `csv.DictReader` encounters an unescaped comma in a field, it creates an extra column. The script interprets this extra column as an additional funding source.

**Warning:** This heuristic can cause **incorrect output** if:
- withCL adds new columns in the future
- The CSV format changes (e.g., new metadata fields)
- Any field contains an unescaped comma

**Current behavior with configuration flags:**

| `ALLOW_SIMPLIFIED_HANDLING` | `IGNORE_FURTHER_COLUMNS` | Result |
|----------------------------|--------------------------|--------|
| `True` | `True` | Extra columns treated as fundings, silently ignored if unparseable |
| `True` | `False` | Extra columns treated as fundings only (error if >1 extra) |
| `False` | `True` | Error if any extra column exists |
| `False` | `False` | Error if any extra column exists |

### 3. Only "Spend" Transaction Type

The script only handles "Spend" (expense) transactions.

| Limitation | Impact |
|------------|--------|
| Only "Spend" type | Cannot import Deposits, Withdrawals, Rewards, Top-ups |
| No CLI arguments | Hardcoded input/output filenames |
| No output validation | Cannot verify CoinTracking compatibility |
| No error recovery | Stops on first unhandled exception |
| No tests | Manual verification only |
| Flat mapping | Doesn't capture fiat side (Card currency amount) |

## Milestones / Future Features

| Milestone | Description |
|-----------|-------------|
| **M1: CLI Interface** | Arguments for input file, output file, exchange name, dry-run |
| **M2: All transaction types** | Support Deposits, Withdrawals, Rewards/Cashback, Refunds |
| **M3: Extended mapping** | Capture Card currency amount as Buy Amount, calculate implied fees |
| **M4: Output validation** | Schema validation, verify row counts, check currency codes |
| **M5: Unit tests** | Test malformed CSV handling, funding parsing, edge cases |
| **M6: Config file** | YAML/JSON config instead of hardcoded variables |
| **M7: Logging** | Replace print() with proper logging, log levels |
| **M8: Error recovery** | Skip invalid rows, collect errors, summary report |

## Contributing & Feedback

Found a bug? Missing an important feature? Have a feature request?

Please open a GitHub issue or contact me directly.

This script aims to handle all transaction types from withCL exports. If something is missing or broken, please let me know.

## Links

- [WithCL Ledger Kreditkarte](https://withcl.com)
- [CoinTracking](https://cointracking.info)
- Telegram - CoinTracking User2User Support (look it up)

## Usage

```bash
python withCL2cointracking.py
```

Expects `CL_INPUT.csv` in the same directory and produces `CT_OUTPUT.csv`.

## Disclaimer

This script is for educational use only. Not tax advice.
Data might get deleted or false data returned - absolutely no warranty!

## Changelog

### v0.2.0 (2026-03-29)
- Virtual Tx-ID generation (hash-based, row-independent)
- Comment extension with formatted amounts (German locale: `1.234,56 EUR`)
- Multi-funding split support for rows with multiple funding sources

### v0.1.0 (2026-03-29)
- MVP: Import of expenses (Spend)
- Robust CSV handling (malformed withCL export)
- `csv.QUOTE_ALL` for safe output
