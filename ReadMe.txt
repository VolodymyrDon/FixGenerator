

## FIX Parser & Generator Toolkit
---

### Prerequisites
- Python 3.9 or newer (tested on 3.11)
- `pip install -r requirements.txt` *(if present; otherwise ensure `requests` and `beautifulsoup4` are available for the scraper)*
- Access to any FIX logs you plan to parse

---

### 1. Scrape or Refresh the FIX Spec
`fix_spec_scraper.py` pulls the tag dictionary from the OnixS FIX docs and stores it as `fix_spec.json`, which both the generator and parser use to render tag names.

```
python fix_spec_scraper.py 4.4 fix_spec.json
```

- First argument is the FIX version (`4.2`, `4.4`, `5.0`, `5.0.SP2`).
- Second argument is the output JSON path (defaults to `fix_spec.json`).
- The script prints a few sample mappings once the file is written.

> Skip this step only if you already have a valid `fix_spec.json`.

---

### 2. Generate Sample FIX Messages
`fix_generator.py` can synthesize FIX messages either from scratch (by message type) or by cloning existing messages from a log. Each output line is formatted as `Send:Empty:<FIX fields...>` using pipe delimiters for readability.

**Usage**
```
python fix_generator.py <MsgType|input_log_file> <output_file> [count] [BeginString]
```

**Interactive overrides**  
When the script starts, it prompts for values such as RefCompID (115), ClientID (109), Symbol (55), etc. Press Enter to keep defaults, or enter a value to overwrite every generated message.

**Common scenarios**
- Generate five NewOrderSingle (35=D) messages with FIX 4.2 headers:
  ```
  python fix_generator.py D generated.txt 5 FIX.4.2
  ```
- Generate ten ExecutionReports (35=8) using defaults:
  ```
  python fix_generator.py 8 generated_reports.txt 10
  ```
- Clone up to 50 orders from a production log, keeping only essential tags:
  ```
  python fix_generator.py ABC.log sanitized.txt 50
  ```
  The script scans the log for `35=D`, rebuilds a minimal order with fresh timestamps/ClOrdIDs, and stops once it reaches the requested count.

Each message has recalculated `9=BodyLength` and `10=Checksum`, so you can pipe the output into other FIX-aware systems.

---

### 3. Parse Logs for Specific Orders
`fix_parser.py` filters large FIX logs by message type and order identifiers, then prints human-readable summaries and writes a report to `matching_messages.txt`.

**Usage**
```
python fix_parser.py <order_ids_file> <log_file> [order_id_field] [fix_spec_file] [msg_type]
```

- `<order_ids_file>`: plain text list of IDs (one per line).
- `<log_file>`: FIX log to scan.
- `[order_id_field]`: tag that holds the ID you care about (`37` = OrderID, `11` = ClOrdID, default `37`).
- `[fix_spec_file]`: overrides the tag dictionary path (default `fix_spec.json`).
- `[msg_type]`: FIX message type to search for (`D`, `8`, `AK`, etc., default `AK`).

**Sample runs**
- Parse default files with defaults (useful for a quick smoke test):
  ```
  python fix_parser.py
  ```
- Search for `ClOrdID` matches in a specific log:
  ```
  python fix_parser.py order_ids.txt prod.log 11
  ```
- Use a custom spec file and target ExecutionReports:
  ```
  python fix_parser.py order_ids.txt prod.log 37 custom_spec.json 8
  ```

**Output**
- Console: lists each matching message, showing “important” tags first (`35`, `37`, `11`, etc.) with friendly field names from the spec file.
- File: `matching_messages.txt` mirrors the console output so you can share or diff results later.

> Tip: The parser accepts logs that use either SOH (`\x01`) or printable delimiters like `|` or `^A`. Mixed logs are handled automatically.

---

### 4. Typical Workflow
1. Refresh `fix_spec.json` (optional if already up-to-date).
2. Use `fix_generator.py` to build sanitized sample traffic or to create synthetic test flows.
3. Ingest real logs with `fix_parser.py` to trace problem orders or reconcile downstream systems.
4. Compare parser output against generator samples to verify field coverage or to share minimal repro data with partners.




