import os
import sys
import uuid
from datetime import datetime, timezone
from fix_parser import parse_fix_message


def format_fix_utc_now():
    # FIX UTC timestamp with milliseconds: YYYYMMDD-HH:MM:SS.sss
    now = datetime.now(timezone.utc)
    return now.strftime('%Y%m%d-%H:%M:%S.') + f"{int(now.microsecond/1000):03d}"


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


def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python fix_generator.py <MsgType|input_log_file> <output_file> [count] [BeginString]")
        print("Examples:")
        print("  python fix_generator.py D generated.txt 5 FIX.4.2")
        print("  python fix_generator.py ABC.log generated_from_log.txt 50 FIX.4.4")
        return

    arg1 = sys.argv[1]
    output_file = sys.argv[2]
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    begin_string = sys.argv[4] if len(sys.argv) > 4 else 'FIX.4.4'

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


if __name__ == '__main__':
    main()


