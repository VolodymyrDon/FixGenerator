import re
import sys
import json

def load_fix_spec(spec_file='fix_spec.json'):
    """
    Load FIX specification from a JSON file.
    Format: {"tag": "FieldName", ...}
    Example: {"1": "Account", "11": "ClOrdID", "35": "MsgType"}
    """
    try:
        with open(spec_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {spec_file} not found. Using basic field names.")
        return {}

def parse_fix_message(message):
    """Parse a FIX message into a dictionary of tag-value pairs."""
    fields = {}
    
    # Try different delimiters
    for delimiter in ['\x01', '|', '\u0001', '^A']:
        if delimiter in message:
            pairs = message.split(delimiter)
            for pair in pairs:
                if '=' in pair:
                    tag, value = pair.split('=', 1)
                    # Store multiple values for repeating tags
                    if tag in fields:
                        if isinstance(fields[tag], list):
                            fields[tag].append(value)
                        else:
                            fields[tag] = [fields[tag], value]
                    else:
                        fields[tag] = value
            break
    
    return fields

def find_orders_in_log(log_file, order_ids, order_id_field='37', msg_type='AK'):
    """
    Find messages of specified type containing specific order IDs.
    
    Args:
        log_file: Path to the FIX log file
        order_ids: List or set of order IDs to search for
        order_id_field: FIX tag for order ID (default '37' for OrderID, 
                       use '11' for ClOrdID)
        msg_type: FIX message type to search for (default 'AK')
                 Common types: D=NewOrder, 8=ExecutionReport, G=OrderCancel, 
                              F=OrderCancelRequest, AK=ListStatus
    
    Returns:
        List of matching messages with metadata
    """
    matches = []
    order_ids_set = set(str(oid) for oid in order_ids)
    
    print(f"Searching for MsgType={msg_type} with {len(order_ids_set)} order IDs in {log_file}...")
    
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            # Check if line contains the specified message type
            if f'35={msg_type}' in line:
                fields = parse_fix_message(line)
                
                # Verify message type
                line_msg_type = fields.get('35')
                if isinstance(line_msg_type, list):
                    line_msg_type = line_msg_type[0]
                
                if line_msg_type == msg_type:
                    # Check if the order ID matches
                    order_id = fields.get(order_id_field, '')
                    if isinstance(order_id, list):
                        order_id = order_id[0]
                    
                    if order_id in order_ids_set:
                        matches.append({
                            'line_number': line_num,
                            'order_id': order_id,
                            'full_line': line.strip(),
                            'fields': fields
                        })
    
    return matches

def format_field_value(value):
    """Format field value (handle lists)."""
    if isinstance(value, list):
        return ', '.join(value)
    return value

def display_match(match, fix_spec, important_tags):
    """Display a single match with proper field names."""
    fields = match['fields']
    
    print(f"Message: {match['full_line']}")
    
    # Display important tags first
    for tag in important_tags:
        if tag in fields:
            field_name = fix_spec.get(tag, f"Tag-{tag}")
            value = format_field_value(fields[tag])
            print(f"  {field_name} ({tag}): {value}")
    
    # Display other fields
    other_tags = sorted([t for t in fields.keys() if t not in important_tags], key=lambda x: int(x) if x.isdigit() else 0)
    for tag in other_tags:
        field_name = fix_spec.get(tag, f"Tag-{tag}")
        value = format_field_value(fields[tag])
        # Skip very long values in console output
        if len(value) > 100:
            value = value[:100] + "..."
        print(f"  {field_name} ({tag}): {value}")
    
    print()

def main():
    # Important tags to display first
    important_tags = ['35', '37', '11', '66', '79', '118', '448', '447', '55', '54', '38', '6', '15', '48', '60']
    
    # Get file names from command line or use defaults
    if len(sys.argv) >= 3:
        order_ids_file = sys.argv[1]
        log_file = sys.argv[2]
        # Preserve original positional behavior:
        # arg3: order_id_field (optional)
        # arg4: spec_file (optional)
        order_id_field = sys.argv[3] if len(sys.argv) > 3 else '37'
        spec_file = sys.argv[4] if len(sys.argv) > 4 else 'fix_spec.json'
        msg_type = sys.argv[5] if len(sys.argv) > 5 else 'AK'
    else:
        # Use default file names
        order_ids_file = 'order_ids.txt'
        log_file = 'ABC.log'
        order_id_field = '37'
        spec_file = 'fix_spec.json'
        msg_type = 'AK'
        print(f"Using default files: {order_ids_file} and {log_file}")
        print("Usage: python fix_parser.py <order_ids_file> <log_file> [order_id_field] [fix_spec_file] [msg_type]")
        print()
    
    # Load FIX specification
    fix_spec = load_fix_spec(spec_file)
    print(f"Loaded {len(fix_spec)} field definitions from FIX spec\n")
    
    # Load order IDs from file
    try:
        with open(order_ids_file, 'r') as f:
            order_ids = [line.strip() for line in f if line.strip()]
        print(f"Loaded {len(order_ids)} order IDs from {order_ids_file}")
    except FileNotFoundError:
        print(f"ERROR: Could not find {order_ids_file}")
        print("Please create a file with one order ID per line.")
        return
    
    # Parse the log file
    try:
        matches = find_orders_in_log(log_file, order_ids, order_id_field, msg_type)
    except FileNotFoundError:
        print(f"ERROR: Could not find {log_file}")
        return
    
    # Display results
    print(f"\n{'='*80}")
    print(f"Found {len(matches)} matching 35={msg_type} messages")
    print(f"{'='*80}\n")
    
    for match in matches:
        display_match(match, fix_spec, important_tags)
    
    # Save results to file
    output_file = 'matching_messages.txt'
    with open(output_file, 'w') as f:
        f.write(f"Found {len(matches)} matching 35={msg_type} messages\n")
        f.write(f"{'='*80}\n\n")
        for match in matches:
            fields = match['fields']
            f.write(f"Message: {match['full_line']}\n")
            
            # Write important tags first
            for tag in important_tags:
                if tag in fields:
                    field_name = fix_spec.get(tag, f"Tag-{tag}")
                    value = format_field_value(fields[tag])
                    f.write(f"  {field_name} ({tag}): {value}\n")
            
            # Write other fields
            other_tags = sorted([t for t in fields.keys() if t not in important_tags], key=lambda x: int(x) if x.isdigit() else 0)
            for tag in other_tags:
                field_name = fix_spec.get(tag, f"Tag-{tag}")
                value = format_field_value(fields[tag])
                f.write(f"  {field_name} ({tag}): {value}\n")
            
            f.write("\n")
    
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    main()