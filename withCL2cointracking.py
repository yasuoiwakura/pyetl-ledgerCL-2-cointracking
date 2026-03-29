import csv
import re
import hashlib


# === KONFIGURATION ===
SF_IN  = "CL_INPUT.csv"
SF_OUT = "CT_OUTPUT.csv"

CT_TYPE        = "Spend"
CT_EXCHANGE    = "WithCL"
CT_TRADEGROUP  = "python"

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

CREATE_VIRTUAL_TXID = True


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
    "Tx-ID":              "",
    "Buy Value in Account Currency":  "",
    "Sell Value in Account Currency":  "",
}

CT_COLS = list(CT_TEMPLATE.keys())


def log(msg):
    print(f"[DEBUG] {msg}")


def sanitize_for_txid(value):
    """Ersetzt problematische Zeichen durch Bindestrich."""
    return re.sub(r'[^\w]', '-', str(value))


def generate_txid_hash(data):
    """Generiert kurzen Hash (6 Zeichen) aus den Tx-Daten."""
    h = hashlib.sha1(data.encode('utf-8')).hexdigest()[:6]
    return h


def generate_txid(h, tx_base, dup_index, funding_index):
    """Generiert Tx-ID mit Hash, Daten und Indices."""
    txid = f"{h}-{tx_base}-dup{dup_index:03d}-funding{funding_index:02d}"
    return txid


def parse_funding(funding_str):
    """Extrahiert Betrag und Waehrung aus einem Funding-String wie '123.45 eurt'."""
    funding_str = str(funding_str).strip()
    match = re.match(r'^([\d.]+)\s*(\w+)$', funding_str)
    if not match:
        raise ValueError(f"Kann Funding nicht parsen: '{funding_str}'")
    return match.group(1), match.group(2).lower()


def format_amount_currency(amount, currency):
    """Formatiert Betrag mit deutschen Tausendertrennzeichen und Waehrung."""
    amount = float(amount)
    if currency == "VND":
        formatted = f"{amount:,.0f}".replace(",", ".")
    else:
        s = f"{amount:,.2f}"
        parts = s.split('.')
        formatted = parts[0].replace(',', '.') + ',' + parts[1]
    return f"{formatted} {currency}"


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
    log(f"CREATE_VIRTUAL_TXID={CREATE_VIRTUAL_TXID}")

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
    seen_tx_base = {}

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
        merchant_type = row.get("Merchant Type", "") or ""
        merchant = row.get("Merchant", "") or ""
        tx_currency = row.get("Transaction Currency", "") or ""
        tx_amount = row.get("Transaction currency amount", "") or ""
        card_currency = row.get("Card currency", "") or ""
        card_amount = row.get("Card currency amount", "") or ""
        comment_multi = "Single expense multiple Fundings" if len(fundings) > 1 else ""

        tx_base_template = (
            f"{sanitize_for_txid(date)}-"
            f"{sanitize_for_txid(merchant_type)}-"
            f"{sanitize_for_txid(merchant)}-"
            f"{sanitize_for_txid(tx_currency)}-"
            f"{sanitize_for_txid(tx_amount)}-"
            f"{sanitize_for_txid(card_currency)}-"
            f"{sanitize_for_txid(card_amount)}"
        )

        for fidx, funding_str in enumerate(fundings, start=1):
            amount, currency = parse_funding(funding_str)
            log(f"  -> Sell: {amount} {currency}")

            tx_amount_fmt = format_amount_currency(tx_amount, tx_currency)
            card_amount_fmt = format_amount_currency(card_amount, card_currency)

            if comment_multi:
                comment = f"{comment_multi} | {tx_amount_fmt} | {card_amount_fmt}"
            else:
                comment = f"{tx_amount_fmt} | {card_amount_fmt}"

            ct_row = CT_TEMPLATE.copy()
            ct_row["Date"]          = date
            ct_row["Sell Amount"]   = amount
            ct_row["Sell Currency"] = currency
            ct_row["Comment"]       = comment

            if CREATE_VIRTUAL_TXID:
                tx_base = (
                    f"{tx_base_template}-"
                    f"{sanitize_for_txid(amount)}-"
                    f"{sanitize_for_txid(currency)}"
                )
                h = generate_txid_hash(tx_base)

                dup_count = seen_tx_base.get(tx_base, 0)
                dup_index = dup_count + 1
                seen_tx_base[tx_base] = dup_index

                txid = generate_txid(h, tx_base, dup_index, fidx)
                ct_row["Tx-ID"] = txid

            rows_out.append(ct_row)

    log(f"Output-Zeilen gesamt: {len(rows_out)}")

    with open(SF_OUT, "w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=CT_COLS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows_out)

    log(f"Fertig - geschrieben: {SF_OUT}")


if __name__ == "__main__":
    main()
