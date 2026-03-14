import csv
import sys
from pathlib import Path


def extract_order_ids(csv_path: str, output_path: str = "order_ids_from_csv.txt"):
    """
    Read a CSV file, find the "Order ID" (or "OrderID") column,
    and write all values from that column to a text file (one per line).

    Args:
        csv_path: Path to the input CSV file.
        output_path: Path to the output text file.
    """
    csv_file = Path(csv_path)
    if not csv_file.is_file():
        print(f"ERROR: CSV file not found: {csv_file}")
        return None

    with csv_file.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            print("ERROR: CSV file has no header row.")
            return None

        # Try common header variants
        header_candidates = ["Order ID", "OrderID", "Order_Id", "OrderId"]
        order_id_col = None
        for name in reader.fieldnames:
            if name in header_candidates:
                order_id_col = name
                break

        if order_id_col is None:
            print("ERROR: Could not find an 'Order ID' column in the CSV header.")
            print("Available columns:", ", ".join(reader.fieldnames))
            return None

        order_ids = []
        for row in reader:
            val = row.get(order_id_col)
            if val is not None and str(val).strip() != "":
                order_ids.append(str(val).strip())

    if not order_ids:
        print("No Order IDs found in the CSV file.")
        return None

    out_file = Path(output_path)
    with out_file.open("w", encoding="utf-8", newline="") as out:
        for oid in order_ids:
            out.write(f"{oid}\n")

    print(f"Extracted {len(order_ids)} order IDs from '{csv_file.name}' into '{out_file.name}'.")
    for oid in order_ids:
        print(oid)

    return order_ids


def search_fix_log_for_order_ids(
    order_ids,
    log_file: str,
    order_id_field: str = "11",
    msg_type: str = "D",
):
    """
    Use fix_parser.find_orders_in_log to search a FIX log for messages
    with the given message type (default 35=D) whose order ID tag matches
    any of the IDs from the CSV.
    """
    try:
        from fix_parser import find_orders_in_log
    except ImportError:
        print("ERROR: Could not import fix_parser.find_orders_in_log. Make sure fix_parser.py is in the same directory.")
        return

    try:
        matches = find_orders_in_log(log_file, order_ids, order_id_field, msg_type)
    except FileNotFoundError:
        print(f"ERROR: Could not find FIX log file: {log_file}")
        return

    print(f"\n{'=' * 80}")
    print(f"Found {len(matches)} matching 35={msg_type} messages in {log_file}")
    print(f"{'=' * 80}")

    if not matches:
        return

    # Print to console
    for m in matches:
        line_no = m.get("line_number")
        full_line = m.get("full_line", "").strip()
        print(f"[line {line_no}] {full_line}")

    # Also write to a file for convenience
    output_file = f"matching_35{msg_type}_from_csv.txt" if msg_type != "" else "matching_from_csv.txt"
    with open(output_file, "w", encoding="utf-8") as out:
        out.write(f"Found {len(matches)} matching 35={msg_type} messages in {log_file}\n")
        out.write(f"{'=' * 80}\n\n")
        for m in matches:
            line_no = m.get("line_number")
            full_line = m.get("full_line", "").strip()
            out.write(f"[line {line_no}] {full_line}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python extract_order_ids_from_csv.py "
            "<input_csv> [output_txt] [fix_log_file] [order_id_field] [msg_type]"
        )
        print("  - order_id_field: FIX tag to match against (default 37)")
        print("  - msg_type: FIX MsgType to search for (default D)")
        sys.exit(1)

    input_csv = sys.argv[1]
    output_txt = sys.argv[2] if len(sys.argv) > 2 else "order_ids_from_csv.txt"

    fix_log_file = sys.argv[3] if len(sys.argv) > 3 else None
    # Default to tag 11 (ClOrdID), since this matches the Order ID column from the CSV
    order_id_field = sys.argv[4] if len(sys.argv) > 4 else "11"
    msg_type = sys.argv[5] if len(sys.argv) > 5 else "D"

    ids_from_csv = extract_order_ids(input_csv, output_txt)

    if ids_from_csv and fix_log_file:
        print(
            f"\nSearching FIX log '{fix_log_file}' for MsgType={msg_type} "
            f"and tag {order_id_field} matching {len(ids_from_csv)} IDs from CSV..."
        )
        search_fix_log_for_order_ids(ids_from_csv, fix_log_file, order_id_field, msg_type)
