import csv
import re


# === KONFIGURATION ===
CT_TYPE        = "Spend"
CT_EXCHANGE    = "WithCL"
CT_TRADEGROUP  = "python"

SF_IN  = "CL_INPUT.csv"
SF_OUT = "CT_OUTPUT.csv"

CHECK_COL_NAMES = True
EXPECTED_COLS = [
    "Timestamp",
    "Merchant",
    "Merchant Type",
    "Transaction Currency",
    "Transaction currency amount",
    "Card currency",
    "Card currency amount",
    "Mastercard exchange rate",
    "ECB exchange rate",
    "Program markup%",
    "Funding Source",
]

ALLOW_SIMPLIFIED_HANDLING_OF_SEVERAL_FUNDINGS_PER_ROW = True
IGNORE_FURTHER_COLUMNS = True


# === TEMPLATE ===
CT_TEMPLATE = {
    "Type":             CT_TYPE,
    "Buy Amount":       "",
    "Buy Currency":     "",
    "Sell Amount":      "",
    "Sell Currency":    "",
    "Fee":              "",
    "Fee Currency":     "",
    "Exchange":         CT_EXCHANGE,
    "Group":      CT_TRADEGROUP,
    "Comment":          "",
    "Date":             "",
    "Liquidity pool":      "",
    "Tx-ID":              "", # Optional
    "Buy Value in Account Currency":  "",# Optional
    "Sell Value in Account Currency":  "",# Optional
}

CT_COLS = list(CT_TEMPLATE.keys())


def log(msg):
    print(f"[DEBUG] {msg}")


def parse_funding(funding_str):
    """Extrahiert Betrag und Waehrung aus einem Funding-String wie '123.45 eurt'."""
    funding_str = str(funding_str).strip()
    match = re.match(r'^([\d.]+)\s*(\w+)$', funding_str)
    if not match:
        raise ValueError(f"Kann Funding nicht parsen: '{funding_str}'")
    return match.group(1), match.group(2).lower()


def get_extra_columns(row):
    """Liefert Spalten die nicht in EXPECTED_COLS sind (normalisiert Leerzeichen)."""
    extra = []
    expected_normalized = {c.strip(): c for c in EXPECTED_COLS}
    for key in row.keys():
        key_normalized = key.strip() if key else ""
        if key_normalized not in expected_normalized:
            extra.append(key)
    return extra


def main():
    log(f"Start - Input: {SF_IN}, Output: {SF_OUT}")
    log(f"CHECK_COL_NAMES={CHECK_COL_NAMES}")
    log(f"ALLOW_SIMPLIFIED_HANDLING_OF_SEVERAL_FUNDINGS_PER_ROW={ALLOW_SIMPLIFIED_HANDLING_OF_SEVERAL_FUNDINGS_PER_ROW}")
    log(f"IGNORE_FURTHER_COLUMNS={IGNORE_FURTHER_COLUMNS}")

    with open(SF_IN, "r", newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        rows_in = list(reader)

    log(f"Gelesen: {len(rows_in)} Zeilen")

    extra_cols_all = set()
    for row in rows_in:
        extra_cols_all.update(get_extra_columns(row))

    if extra_cols_all:
        log(f"Extra-Spalten gefunden: {extra_cols_all}")
        num_extra = len(extra_cols_all)

        if num_extra > 1:
            if not IGNORE_FURTHER_COLUMNS:
                raise ValueError(f"Mehr als 1 Extra-Spalte ({num_extra}): {extra_cols_all}")

        if num_extra == 1:
            if not ALLOW_SIMPLIFIED_HANDLING_OF_SEVERAL_FUNDINGS_PER_ROW:
                raise ValueError(f"1 Extra-Spalte gefunden aber ALLOW_SIMPLIFIED_HANDLING_OF_SEVERAL_FUNDINGS_PER_ROW=False: {extra_cols_all}")
        elif num_extra > 1:
            if not IGNORE_FURTHER_COLUMNS:
                raise ValueError(f"Mehrere Extra-Spalten gefunden aber IGNORE_FURTHER_COLUMNS=False: {extra_cols_all}")

    rows_out = []
    for idx, row in enumerate(rows_in):
        log(f"Verarbeite Input-Zeile {idx+1}/{len(rows_in)}")

        extra_cols = get_extra_columns(row)
        log(f"Extra-Spalten: {extra_cols}")

        funding_values = []
        if "Funding Source" in row:
            val = row["Funding Source"]
            if val:
                funding_values.append(val.strip())

        for col in extra_cols:
            val = row[col]
            if val:
                if isinstance(val, list):
                    for item in val:
                        if str(item).strip():
                            funding_values.append(str(item).strip())
                else:
                    funding_values.append(str(val).strip())

        funding_raw = ", ".join(funding_values)
        log(f"Funding Source roh: '{funding_raw}'")

        fundings = [f.strip() for f in funding_raw.split(",") if f.strip()]
        log(f"Gefundene Fundings ({len(fundings)}): {fundings}")

        if len(fundings) > 1 and not ALLOW_SIMPLIFIED_HANDLING_OF_SEVERAL_FUNDINGS_PER_ROW:
            raise ValueError(
                f"Zeile {idx+1} enthaelt mehrere Fundings, aber "
                f"ALLOW_SIMPLIFIED_HANDLING_OF_SEVERAL_FUNDINGS_PER_ROW=False: {fundings}"
            )

        date = row.get("Timestamp", "") or ""
        comment_multi = "Single expense multiple Fundings" if len(fundings) > 1 else ""

        for funding_str in fundings:
            amount, currency = parse_funding(funding_str)
            log(f"  -> Sell: {amount} {currency}")

            ct_row = CT_TEMPLATE.copy()
            ct_row["Date"]          = date
            ct_row["Sell Amount"]   = amount
            ct_row["Sell Currency"] = currency
            ct_row["Comment"]       = comment_multi
            rows_out.append(ct_row)

    log(f"Output-Zeilen gesamt: {len(rows_out)}")

    with open(SF_OUT, "w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=CT_COLS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows_out)

    log(f"Fertig - geschrieben: {SF_OUT}")


if __name__ == "__main__":
    main()
