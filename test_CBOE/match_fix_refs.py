"""
Match FIX messages to spreadsheet rows by ISIN + Quantity.
Fills in the 'Reporting Ref ID' column (tag 1003 from FIX messages) and
emails the updated spreadsheet using qemail.pl.

Usage:
    python match_fix_refs.py <spreadsheet.xlsx> <fix1.txt> [<fix2.txt> ...] [output.xlsx]

If the last argument ends with .xlsx it is treated as the output file,
otherwise the default output name 'output_with_refs.xlsx' is used.

FIX tags used:
    48   = ISIN
    32   = Quantity
    75   = Trade Date (YYYYMMDD) – used for email subject date
    1003 = Reporting Ref ID
"""

import sys
import re
import subprocess
import logging
from datetime import datetime, time, timedelta
from pathlib import Path

import pandas as pd


def setup_logging() -> logging.Logger:
    """Configure basic file logging and return the module logger."""
    logger = logging.getLogger("match_fix_refs")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    log_path = Path(__file__).with_suffix(".log")

    handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Also echo to stdout for convenience
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logger.info("Logging initialised, log file: %s", log_path)
    return logger


def parse_trade_date(raw: str, logger: logging.Logger):
    """Parse FIX tag 75 (YYYYMMDD) into a date, or return None."""
    if not raw:
        return None
    try:
        return datetime.strptime(raw.strip(), "%Y%m%d").date()
    except Exception:
        logger.warning("Could not parse trade date from tag 75 value '%s'", raw)
        return None


def parse_fix_messages(filepaths, logger: logging.Logger):
    """
    Parse one or more FIX files and return list of dicts:
    {ISIN, Quantity, RefID, TradeDate}.
    """
    if isinstance(filepaths, (str, Path)):
        filepaths = [filepaths]

    records = []
    for filepath in filepaths:
        filepath = str(filepath)
        logger.info("Parsing FIX messages from %s", filepath)
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # Support both | and SOH (chr 1) as delimiters
                    fields = re.split(r"[|\x01]", line)
                    msg = {}
                    for field in fields:
                        if "=" in field:
                            tag, _, val = field.partition("=")
                            msg[tag.strip()] = val.strip()

                    isin = msg.get("48")
                    qty = msg.get("32")
                    ref_id = msg.get("1003")
                    trade_date = parse_trade_date(msg.get("75"), logger)

                    if isin and qty and ref_id:
                        try:
                            qty_int = int(qty)
                        except ValueError:
                            logger.warning(
                                "Non-integer quantity '%s' for ISIN %s in %s", qty, isin, filepath
                            )
                            continue
                        records.append(
                            {
                                "ISIN": isin,
                                "Quantity": qty_int,
                                "RefID": ref_id,
                                "TradeDate": trade_date,
                            }
                        )
        except FileNotFoundError:
            logger.error("FIX file not found: %s", filepath)
        except Exception as exc:
            logger.error("Error while reading FIX file %s: %s", filepath, exc)

    logger.info("Parsed %d FIX messages with ISIN+Qty+RefID", len(records))
    return records


def parse_bats_batch_records(filepaths, logger: logging.Logger):
    """
    Parse BATS log file(s) and return batch records for AE messages
    between 07:15 and 07:17 based on the log line timestamp.
    Each record is {ISIN, Quantity, RefID, TradeDate}.
    """
    if isinstance(filepaths, (str, Path)):
        filepaths = [filepaths]

    start_window = time(7, 15, 0)
    end_window = time(7, 17, 0)

    records = []

    ts_regex = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})")

    for filepath in filepaths:
        filepath = str(filepath)
        logger.info("Parsing BATS batch from %s", filepath)
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    m = ts_regex.match(line)
                    if not m:
                        continue
                    _, t_str = m.groups()
                    try:
                        t_val = datetime.strptime(t_str, "%H:%M:%S").time()
                    except Exception:
                        continue

                    if not (start_window <= t_val < end_window):
                        continue

                    # Everything after " - in: " is the FIX payload
                    parts = line.split(" - in: ", 1)
                    if len(parts) != 2:
                        continue
                    fix_payload = parts[1].strip()

                    if "35=AE" not in fix_payload:
                        continue

                    fields = re.split(r"[|\x01]", fix_payload)
                    msg = {}
                    for field in fields:
                        if "=" in field:
                            tag, _, val = field.partition("=")
                            msg[tag.strip()] = val.strip()

                    isin = msg.get("48")
                    qty = msg.get("32")
                    ref_id = msg.get("1003")
                    trade_date = parse_trade_date(msg.get("75"), logger)

                    if not (isin and qty and ref_id):
                        logger.warning(
                            "Skipping AE in batch with missing tags: 48=%s 32=%s 1003=%s",
                            isin,
                            qty,
                            ref_id,
                        )
                        continue

                    try:
                        qty_int = int(qty)
                    except ValueError:
                        logger.warning(
                            "Non-integer quantity '%s' for ISIN %s in %s", qty, isin, filepath
                        )
                        continue

                    records.append(
                        {
                            "ISIN": isin,
                            "Quantity": qty_int,
                            "RefID": ref_id,
                            "TradeDate": trade_date,
                        }
                    )
        except FileNotFoundError:
            logger.error("BATS log file not found: %s", filepath)
        except Exception as exc:
            logger.error("Error while reading BATS log file %s: %s", filepath, exc)

    logger.info("Parsed %d AE FIX messages for 07:15-07:17 batch", len(records))
    return records


def build_lookup(fix_records, logger: logging.Logger):
    """
    Build lookup:
        (ISIN, Quantity) -> {'RefIDs': [ref_id1, ref_id2, ...], 'TradeDates': set(date)}
    If multiple messages share the same ISIN+Quantity but different RefIDs,
    all RefIDs are kept (order of appearance) so they can be joined later.
    """
    lookup = {}
    for rec in fix_records:
        key = (rec["ISIN"], rec["Quantity"])
        entry = lookup.get(key)
        if entry is None:
            lookup[key] = {
                "RefIDs": [rec["RefID"]],
                "TradeDates": set([rec["TradeDate"]]) if rec["TradeDate"] else set(),
            }
        else:
            if rec["RefID"] not in entry["RefIDs"]:
                logger.info(
                    "Additional RefID for key %s: existing=%s, new=%s",
                    key,
                    ",".join(entry["RefIDs"]),
                    rec["RefID"],
                )
                entry["RefIDs"].append(rec["RefID"])
            if rec["TradeDate"]:
                entry["TradeDates"].add(rec["TradeDate"])
    logger.info("Built lookup with %d unique ISIN+Qty keys", len(lookup))
    return lookup


def choose_email_date(lookup, logger: logging.Logger):
    """
    Choose email date as (max TradeDate across all records) - 1 day.
    Returns formatted string YYYYMMDD or None if no trade dates.
    """
    all_dates = set()
    for entry in lookup.values():
        all_dates.update(d for d in entry["TradeDates"] if d)

    if not all_dates:
        logger.warning("No TradeDate (tag 75) values found; email subject will use 'UNKNOWN_DATE'")
        return None

    fix_date = max(all_dates)
    email_date = fix_date - timedelta(days=1)
    email_date_str = email_date.strftime("%Y%m%d")
    logger.info(
        "Computed email date: fix_date=%s, email_date=%s", fix_date, email_date_str
    )
    return email_date_str


def choose_email_date_from_dates(trade_dates, logger: logging.Logger):
    """
    Choose email date from a set of dates using the same rule
    as choose_email_date: max(trade_dates) - 1 day.
    Returns formatted string YYYYMMDD or None.
    """
    dates = {d for d in trade_dates if d}
    if not dates:
        logger.warning(
            "No TradeDate values found for batch export; email subject will use 'UNKNOWN_DATE'"
        )
        return None

    fix_date = max(dates)
    email_date = fix_date - timedelta(days=1)
    email_date_str = email_date.strftime("%Y%m%d")
    logger.info(
        "Computed batch email date: fix_date=%s, email_date=%s", fix_date, email_date_str
    )
    return email_date_str


def send_email_with_attachment(
    output_path: Path,
    subject: str,
    body: str,
    logger: logging.Logger,
):
    """Send email using qemail.pl with the given subject/body and attachment."""
    script_dir = Path(__file__).resolve().parent
    qemail_path = script_dir / "qemail.pl"

    if not qemail_path.exists():
        logger.error("qemail.pl not found at %s; cannot send email", qemail_path)
        raise FileNotFoundError(f"qemail.pl not found at {qemail_path}")

    to_address = "volodymyr.don@quodfinancial.com"

    cmd = [
        "perl",
        str(qemail_path),
        "-t",
        to_address,
        "-s",
        subject,
        "-d",
        body,
        str(output_path),
    ]

    logger.info("Invoking qemail.pl to send email: %s", " ".join(cmd))
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("qemail.pl stdout: %s", result.stdout.strip())
        if result.stderr:
            logger.warning("qemail.pl stderr: %s", result.stderr.strip())
    except subprocess.CalledProcessError as exc:
        logger.error("qemail.pl failed with code %s: %s", exc.returncode, exc.stderr)
        raise


def export_bats_batch(log_files, output_path: Path | None, logger: logging.Logger):
    """
    Export 07:15-07:17 AE messages from BATS logs into an Excel file with
    columns: Reporting Ref ID, ISIN, Quantity, and optionally email it.
    """
    if output_path is None:
        output_path = Path("bats_0715_batch.xlsx")

    records = parse_bats_batch_records(log_files, logger)

    # Aggregate by (ISIN, Quantity) and collate all distinct RefIDs
    batch_lookup = {}
    trade_dates = set()
    for rec in records:
        key = (rec["ISIN"], rec["Quantity"])
        entry = batch_lookup.get(key)
        if entry is None:
            batch_lookup[key] = {"RefIDs": [rec["RefID"]]}
        else:
            if rec["RefID"] not in entry["RefIDs"]:
                entry["RefIDs"].append(rec["RefID"])
        if rec["TradeDate"]:
            trade_dates.add(rec["TradeDate"])

    logger.info(
        "BATS batch: %d unique ISIN+Qty keys from %d records",
        len(batch_lookup),
        len(records),
    )

    rows = [
        {
            "Reporting Ref ID": ",".join(entry["RefIDs"]),
            "ISIN": isin,
            "Quantity": qty,
        }
        for (isin, qty), entry in batch_lookup.items()
    ]

    df = pd.DataFrame(rows, columns=["Reporting Ref ID", "ISIN", "Quantity"])

    try:
        df.to_excel(output_path, index=False)
        logger.info("Saved BATS 07:15 batch spreadsheet to %s", output_path)
    except Exception as exc:
        logger.error("Failed to save BATS batch spreadsheet to %s: %s", output_path, exc)
        raise

    # Derive date from trade_dates for subject, if possible
    email_date_str = choose_email_date_from_dates(trade_dates, logger) or "UNKNOWN_DATE"
    subject = f"Missing Ref IDs {email_date_str} (BATS 07:15 batch)"

    body = (
        "BATS 07:15 AE batch export completed.\n"
        f"Total AE messages in window: {len(records)}\n"
        f"Unique ISIN+Quantity keys: {len(batch_lookup)}\n"
        f"Output file: {output_path.name}"
    )

    try:
        send_email_with_attachment(output_path, subject, body, logger)
    except Exception as exc:
        logger.error("Failed to send BATS batch email: %s", exc)
        print(f"ERROR: Failed to send BATS batch email: {exc}")
        sys.exit(1)


def main():
    logger = setup_logging()
    logger.info("Starting match_fix_refs script with args: %s", sys.argv[1:])

    if len(sys.argv) < 2:
        print(
            "Usage:\n"
            "  python match_fix_refs.py <spreadsheet.xlsx> <fix1.txt> "
            "[<fix2.txt> ...] [output.xlsx]\n"
            "  python match_fix_refs.py batch <bats_log1> [<bats_log2> ...] [output.xlsx]"
        )
        sys.exit(1)

    # Batch export mode: python match_fix_refs.py batch <bats_log1> [<bats_log2> ...] [output.xlsx]
    if sys.argv[1].lower() == "batch":
        if len(sys.argv) < 3:
            print(
                "Usage: python match_fix_refs.py batch <bats_log1> "
                "[<bats_log2> ...] [output.xlsx]"
            )
            sys.exit(1)

        other_args = sys.argv[2:]
        output_path: Path | None = None
        if other_args and other_args[-1].lower().endswith(".xlsx"):
            output_path = Path(other_args[-1])
            log_files = [Path(p) for p in other_args[:-1]]
        else:
            log_files = [Path(p) for p in other_args]
            output_path = Path("bats_0715_batch.xlsx")

        logger.info(
            "Running BATS 07:15 batch mode. Logs: %s; Output: %s",
            ", ".join(str(p) for p in log_files),
            output_path,
        )
        export_bats_batch(log_files, output_path, logger)
        logger.info("BATS batch mode completed successfully")
        return

    if len(sys.argv) < 3:
        print(
            "Usage: python match_fix_refs.py <spreadsheet.xlsx> <fix1.txt> "
            "[<fix2.txt> ...] [output.xlsx]"
        )
        sys.exit(1)

    xlsx_path = Path(sys.argv[1])
    other_args = sys.argv[2:]

    output_path: Path | None = None
    if other_args and other_args[-1].lower().endswith(".xlsx"):
        output_path = Path(other_args[-1])
        fix_files = [Path(p) for p in other_args[:-1]]
    else:
        fix_files = [Path(p) for p in other_args]
        output_path = Path("output_with_refs.xlsx")

    if not fix_files:
        print(
            "At least one FIX file must be provided.\n"
            "Usage: python match_fix_refs.py <spreadsheet.xlsx> <fix1.txt> "
            "[<fix2.txt> ...] [output.xlsx]"
        )
        sys.exit(1)

    logger.info("Spreadsheet: %s", xlsx_path)
    logger.info("FIX files: %s", ", ".join(str(p) for p in fix_files))
    logger.info("Output XLSX: %s", output_path)

    # Load spreadsheet
    try:
        df = pd.read_excel(xlsx_path, dtype={"Quantity": int, "ISIN": str})
    except Exception as exc:
        logger.error("Failed to read spreadsheet %s: %s", xlsx_path, exc)
        raise

    # Ensure Reporting Ref ID column exists
    if "Reporting Ref ID" not in df.columns:
        df["Reporting Ref ID"] = ""

    # Parse FIX messages
    fix_records = parse_fix_messages(fix_files, logger)

    # Build lookup: (ISIN, Qty) -> {RefID, TradeDates}
    lookup = build_lookup(fix_records, logger)

    # Match and fill Reporting Ref ID
    matched = 0
    for idx, row in df.iterrows():
        try:
            key = (str(row["ISIN"]).strip(), int(row["Quantity"]))
        except Exception:
            logger.warning("Row %s has invalid ISIN/Quantity: %s", idx, row.to_dict())
            continue

        entry = lookup.get(key)
        if entry:
            # If there are multiple RefIDs for this ISIN+Qty, join them comma-separated.
            df.at[idx, "Reporting Ref ID"] = ",".join(entry["RefIDs"])
            matched += 1

    total_rows = len(df)
    missing = total_rows - matched
    logger.info("Matched %d / %d rows; %d still missing", matched, total_rows, missing)

    # Save updated spreadsheet
    try:
        df.to_excel(output_path, index=False)
        logger.info("Saved updated spreadsheet to %s", output_path)
    except Exception as exc:
        logger.error("Failed to save spreadsheet to %s: %s", output_path, exc)
        raise

    # Compute email subject date from tag 75 values (minus one day)
    email_date_str = choose_email_date(lookup, logger) or "UNKNOWN_DATE"
    subject = f"Missing Ref IDs {email_date_str}"

    body = (
        f"Reporting Ref ID matching completed.\n"
        f"Total rows: {total_rows}\n"
        f"Matched rows: {matched}\n"
        f"Missing rows: {missing}\n"
        f"Output file: {output_path.name}"
    )

    try:
        send_email_with_attachment(output_path, subject, body, logger)
    except Exception as exc:
        logger.error("Failed to send email: %s", exc)
        print(f"ERROR: Failed to send email: {exc}")
        sys.exit(1)

    logger.info("Script completed successfully")


if __name__ == "__main__":
    main()