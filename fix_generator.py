import os
import sys
import uuid
import csv
from datetime import datetime, timezone
from fix_parser import parse_fix_message


def format_fix_utc_now():
    # FIX UTC timestamp with milliseconds: YYYYMMDD-HH:MM:SS.sss
    now = datetime.now(timezone.utc)
    return now.strftime('%Y%m%d-%H:%M:%S.') + f"{int(now.microsecond/1000):03d}"


def format_fix_utc_now_no_ms():
    # FIX UTC timestamp without milliseconds: YYYYMMDD-HH:MM:SS
    now = datetime.now(timezone.utc)
    return now.strftime('%Y%m%d-%H:%M:%S')


def compute_body_length(message_fields_with_soh):
    # BodyLength (9) is the number of bytes from after tag 9 field delimiter to before tag 10
    # We construct the message with 8,9 placeholders, rest, then compute length
    # message_fields_with_soh is a list of 'tag=value' strings already delimited by SOH when joined
    # We'll join with SOH to compute length
    soh = '\x01'
    # Build preliminary without 9 and 10 first
    # Expect the list order to already have 8 and then 9 slot reserved
    message_without_9_10 = soh.join(message_fields_with_soh)
    # Replace the placeholder '9=' value later; here compute based on bytes between after '9=...\x01' and before '10='
    # We'll rebuild precisely below in build_fix_message
    return len(message_without_9_10.encode('ascii'))


def compute_checksum(raw_bytes):
    total = sum(raw_bytes) % 256
    return f"{total:03d}"


def build_fix_message(base_fields):
    # base_fields is a dict of tag->value (strings), must include at least 8 and 35
    soh = '\x01'

    # Header order (common minimal): 8,9,35,49,56,34,52
    # Then application-specific fields, then 10 at the end.
    ordered_tags = [
        '8', '9', '35', '49', '56', '34', '52',
        # common app fields we may include if present
        '129', '116', '128', '115', '57', '50', '8003', '8007',
        '11', '12', '13', '15', '21', '22', '38', '40', '44', '48', '54', '55', '109', '58', '59', '60', '100'
    ]

    # Start building fields (without 9 and 10)
    parts = []
    # 8
    begin_string = base_fields.get('8', 'FIX.4.4')
    parts.append(f"8={begin_string}")
    # placeholder for 9 (will insert later)
    parts.append("9=")

    # Append the rest in order if present
    for tag in ordered_tags[2:]:  # skip 8 and 9 already handled
        if tag in base_fields and base_fields[tag] is not None:
            parts.append(f"{tag}={base_fields[tag]}")

    # Now compute BodyLength: length of everything after 9=...<SOH> up to and including the last field before 10
    # Build a temporary with 9=000 to get correct framing
    temp = parts.copy()
    temp[1] = '9=000'
    body_bytes = soh.join(temp[2:]).encode('ascii')  # from after 9 field
    body_length = len(body_bytes)

    # Set 9 to actual length
    parts[1] = f"9={body_length}"

    # Compute checksum on full message without 10
    raw_without_10 = soh.join(parts).encode('ascii') + soh.encode('ascii')
    chksum = compute_checksum(raw_without_10)

    # Append 10
    parts.append(f"10={chksum}")

    return soh.join(parts)


def build_fix_message_from_file_format(base_fields):
    """
    Build FIX message matching the specific format from file input.
    Order: 8,9,115,35,49,56,34,52,50,60,63,9243,38,40,100,11,15,48,109,5000,21,22,54,55,207,59,10
    """
    soh = '\x01'
    
    # Exact tag order matching the example message
    # Order: 8,9,115,35,49,56,34,52,50,60,63,9243,38,40,100,11,15,48,109,5000,21,22,54,55,207,59,10
    # Tag 115 is optional and should come before 35 if present
    ordered_tags = [
        '8', '9', '115', '35', '49', '56', '34', '52', '50', '60', '63', '9243',
        '38', '40', '100', '11', '15', '48', '109', '5000', '21', '22', '54', '55', '207', '59'
    ]
    
    parts = []
    nine_index = None
    
    # Build message with tags in exact order
    for i, tag in enumerate(ordered_tags):
        if tag == '9':
            # Placeholder for body length
            parts.append("9=")
            nine_index = i
        elif tag in base_fields and base_fields[tag] is not None:
            parts.append(f"{tag}={base_fields[tag]}")
    
    # Calculate body length: everything after 9=...<SOH> up to before 10
    # Body length is the number of bytes from after the 9 field delimiter to before the 10 field
    # So we need: all fields after 9, joined with SOH
    body_parts = parts[nine_index + 1:]  # Everything after tag 9
    body_bytes = soh.join(body_parts).encode('ascii')
    body_length = len(body_bytes)
    
    # Set body length (4 digits with leading zeros)
    parts[nine_index] = f"9={body_length:04d}"
    
    # Compute checksum on full message without 10
    # Need to include SOH after the last field before 10
    raw_without_10 = soh.join(parts).encode('ascii') + soh.encode('ascii')
    chksum = compute_checksum(raw_without_10)
    
    # Append checksum
    parts.append(f"10={chksum}")
    
    return soh.join(parts)


def build_minimal_new_order_defaults(overrides, begin_string):
    base = {}
    base['8'] = begin_string
    base['35'] = 'D'
    base['49'] = 'NYFXIN'
    base['56'] = 'TSAFIN'
    base['34'] = '1'
    base['52'] = '$TIMESTAMP'
    base['11'] = '$UNIQUE'
    base['21'] = '3'
    base['22'] = '4'
    base['38'] = '1000.0'
    base['40'] = '2'
    base['44'] = '8.665'
    base['54'] = '1'
    base['60'] = '$TIMESTAMP'
    # Client-provided overrides
    base['115'] = overrides['115'] or 'CAAMRCT1'
    base['109'] = overrides['109'] or 'CAAMRCT1'
    base['55'] = overrides['55'] or 'SAN SM'
    base['48'] = overrides['48'] or 'ES0113900J37'
    base['15'] = overrides['15'] or 'EUR'
    base['100'] = overrides['100'] or 'XMAD'
    return base


def parse_listings_file(file_path):
    """
    Parse a CSV or similar file containing listing information.
    Expected columns (case-insensitive):
    - security_id (for tag 48)
    - currency (for tag 15)
    - bbg_exchangecode or exchangecode (for tags 100 and 207)
    - symbol (for tag 55, optional)
    - client_id (for tag 109, optional)
    - Other fields as needed
    
    Returns a list of dictionaries with the parsed data.
    """
    listings = []
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        # Try to detect if it's CSV
        sample = f.read(1024)
        f.seek(0)
        
        # Check if it looks like CSV (has commas or tabs)
        if ',' in sample or '\t' in sample:
            # Try CSV first (handles quoted fields automatically)
            try:
                reader = csv.DictReader(f)
                for row in reader:
                    # Normalize column names (case-insensitive)
                    normalized_row = {k.lower().strip(): (v.strip() if v else '') for k, v in row.items()}
                    listings.append(normalized_row)
            except Exception:
                # Fall back to tab-separated
                f.seek(0)
                reader = csv.DictReader(f, delimiter='\t')
                for row in reader:
                    normalized_row = {k.lower().strip(): (v.strip() if v else '') for k, v in row.items()}
                    listings.append(normalized_row)
        else:
            # Assume simple format: one listing per line, key=value pairs
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # Parse key=value pairs
                row = {}
                for pair in line.split(','):
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        row[key.strip().lower()] = value.strip()
                if row:
                    listings.append(row)
    
    return listings


def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python fix_generator.py <MsgType|input_log_file|listings_file> <output_file> [count] [BeginString]")
        print("Examples:")
        print("  python fix_generator.py D generated.txt 5 FIX.4.2")
        print("  python fix_generator.py ABC.log generated_from_log.txt 50 FIX.4.4")
        print("  python fix_generator.py listings.csv generated.txt")
        print("")
        print("File mode:")
        print("  When first arg is a file (CSV or similar), generates 35=D messages for each row.")
        print("  Expected columns: security_id, currency, bbg_exchangecode (or exchangecode)")
        return

    arg1 = sys.argv[1]
    output_file = sys.argv[2]
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    begin_string = sys.argv[4] if len(sys.argv) > 4 else 'FIX.4.4'
    
    # Check if it's a listings file (not a log file with 35=D messages)
    if os.path.exists(arg1):
        # First check if it's clearly a log file (contains 35=D)
        is_log_file = False
        try:
            with open(arg1, 'r', encoding='utf-8', errors='ignore') as f:
                first_chunk = f.read(1024)
                if '35=D' in first_chunk or arg1.endswith('.log'):
                    is_log_file = True
        except:
            pass
        
        # If not a log file, try parsing as listings file
        if not is_log_file:
            try:
                listings = parse_listings_file(arg1)
                if listings:
                    generate_from_listings_file(arg1, output_file, begin_string)
                    return
            except Exception as e:
                # If parsing fails, fall through to log file handling
                pass

    print("Enter values for the following tags (leave blank to use defaults):")
    overrides = {
        '115': input("115 (RefCompID): ").strip(),
        '109': input("109 (ClientID): ").strip(),
        '55': input("55 (Symbol): ").strip(),
        '48': input("48 (SecurityID): ").strip(),
        '15': input("15 (Currency): ").strip(),
        '100': input("100 (ExDestination): ").strip(),
    }

    messages = []
    if os.path.exists(arg1):
        # From log: scan for 35=D and generate minimal messages per record using only necessary + 6 overrides
        produced = 0
        with open(arg1, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if '35=D' not in line:
                    continue
                fields = parse_fix_message(line)
                if fields.get('35') != 'D':
                    continue
                base = build_minimal_new_order_defaults(overrides, begin_string)
                # Take some necessary values from the source if present
                base['49'] = fields.get('49', base['49'])
                base['56'] = fields.get('56', base['56'])
                base['54'] = fields.get('54', base['54'])
                base['38'] = fields.get('38', base['38'])
                base['44'] = fields.get('44', base['44'])
                # Always refresh timestamps and ClOrdID
                base['52'] = '$TIMESTAMP'
                base['60'] = '$TIMESTAMP'
                base['11'] = '$UNIQUE'
                raw_fix = build_fix_message(base)
                messages.append('Send:Empty:' + raw_fix.replace('\x01', '|'))
                produced += 1
                if produced >= count:
                    break
    else:
        # From message type
        msg_type = arg1
        for _ in range(count):
            if msg_type == 'D':
                base = build_minimal_new_order_defaults(overrides, begin_string)
            elif msg_type == '8':
                base = {}
                base['8'] = begin_string
                base['35'] = '8'
                base['49'] = 'NYFXIN'
                base['56'] = 'TSAFIN'
                base['34'] = '1'
                base['52'] = '$TIMESTAMP'
                base['11'] = '$UNIQUE'
                base['17'] = uuid.uuid4().hex[:12].upper()
                base['150'] = '0'
                base['39'] = '0'
                base['37'] = base['11']
                base['55'] = overrides['55'] or 'SAN SM'
                base['48'] = overrides['48'] or 'ES0113900J37'
                base['54'] = '1'
                base['38'] = '1000.0'
                base['44'] = '8.665'
                base['151'] = '1000.0'
                base['14'] = '0'
                base['6'] = '0'
                base['15'] = overrides['15'] or 'EUR'
                base['60'] = '$TIMESTAMP'
                base['100'] = overrides['100'] or 'XMAD'
                base['109'] = overrides['109'] or 'CAAMRCT1'
            else:
                base = {}
                base['8'] = begin_string
                base['35'] = msg_type
                base['49'] = 'NYFXIN'
                base['56'] = 'TSAFIN'
                base['34'] = '1'
                base['52'] = '$TIMESTAMP'
                base['11'] = '$UNIQUE'
                base['55'] = overrides['55'] or 'SYMBOL'
                base['48'] = overrides['48'] or 'SECID'
                base['15'] = overrides['15'] or 'EUR'
                base['60'] = '$TIMESTAMP'
                if overrides['100']:
                    base['100'] = overrides['100']
                if overrides['109']:
                    base['109'] = overrides['109']
            raw_fix = build_fix_message(base)
            messages.append('Send:Empty:' + raw_fix.replace('\x01', '|'))

    with open(output_file, 'w', encoding='utf-8') as out:
        for m in messages:
            out.write(m)
            out.write('\n')

    if os.path.exists(arg1):
        print(f"Generated {len(messages)} 35=D messages from log to {output_file}")
    else:
        print(f"Generated {len(messages)} 35={arg1} messages to {output_file}")


def generate_from_listings_file(listings_file, output_file, begin_string='FIX.4.2'):
    """Generate FIX 35=D messages from listings file."""
    print(f"Reading listings from {listings_file}...")
    
    try:
        listings = parse_listings_file(listings_file)
        
        if not listings:
            print("No listings found in file.")
            return
        
        print(f"Found {len(listings)} listings")
        
        # Prompt for tags 49, 56, 115, and 109 (common across all orders)
        print("\nEnter values for the following tags (common across all orders):")
        tag_49 = input("49 (SenderCompID): ").strip()
        tag_56 = input("56 (TargetCompID): ").strip()
        tag_115 = input("115 (RefCompID): ").strip()
        tag_109 = input("109 (ClientID): ").strip()
        
        # Default values for other fields
        defaults = {
            '34': '1993',  # Starting sequence number
            '50': '',  # SenderSubID (optional)
            '63': '0',
            '9243': '25',
            '38': '50000',
            '40': '1',
            '5000': 'PARTG',
            '21': '2',
            '22': '4',
            '54': '1',
            '59': '0',
        }
        
        messages = []
        seq_num = int(defaults.get('34', '1993'))
        
        for idx, listing in enumerate(listings):
            # Extract values from listing using CSV column names (case-insensitive)
            # CSV columns: venueid, lookupsymbol, securityexchange, currency, securityid, bloombergexchcode
            security_id = listing.get('securityid', '').strip()
            currency = listing.get('currency', '').strip()
            bbg_exchangecode = listing.get('bloombergexchcode', '').strip()
            lookupsymbol = listing.get('lookupsymbol', '').strip()
            
            if not security_id:
                print(f"Warning: Row {idx + 1} missing securityid, skipping")
                continue
            
            if not bbg_exchangecode:
                print(f"Warning: Row {idx + 1} missing bloombergexchcode, skipping")
                continue
            
            # Build message fields matching the exact format
            base = {}
            base['8'] = begin_string
            base['35'] = 'D'
            if tag_49:
                base['49'] = tag_49
            if tag_56:
                base['56'] = tag_56
            base['34'] = str(seq_num)
            seq_num += 1
            
            # Use literal placeholders for timestamps
            base['52'] = '$TIMESTAMP'
            base['60'] = '$TIMESTAMP'
            
            if defaults.get('50'):
                base['50'] = defaults['50']
            
            base['63'] = defaults.get('63', '0')
            base['9243'] = defaults.get('9243', '25')
            base['38'] = defaults.get('38', '50000')
            base['40'] = defaults.get('40', '1')
            
            # IMPORTANT: Use bbg_exchangecode for both 100 and 207
            base['100'] = bbg_exchangecode
            base['207'] = bbg_exchangecode
            
            # Use literal placeholder for ClOrdID
            base['11'] = '$UNIQUE'
            
            base['15'] = currency if currency else 'GBp'
            base['48'] = security_id
            base['109'] = tag_109 if tag_109 else ''
            if tag_115:
                base['115'] = tag_115
            base['5000'] = defaults.get('5000', 'PARTG')
            base['21'] = defaults.get('21', '2')
            base['22'] = defaults.get('22', '4')
            base['54'] = defaults.get('54', '1')
            base['55'] = lookupsymbol if lookupsymbol else ''
            base['59'] = defaults.get('59', '0')
            
            # Build message using the file format function
            raw_fix = build_fix_message_from_file_format(base)
            messages.append('Send:Empty:' + raw_fix.replace('\x01', '|'))
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as out:
            for m in messages:
                out.write(m)
                out.write('\n')
        
        print(f"\nGenerated {len(messages)} FIX 35=D messages to {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()


