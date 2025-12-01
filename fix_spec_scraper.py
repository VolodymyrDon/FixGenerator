import requests
from bs4 import BeautifulSoup
import json
import sys

def scrape_fix_spec(version='5.0.SP2'):
    """
    Scrape FIX specification from onixs.biz website.
    
    Args:
        version: FIX version (e.g., '4.2', '4.4', '5.0.SP2')
    """
    # Map versions to URL format
    version_map = {
        '4.2': '4.2',
        '4.4': '4.4',
        '5.0': '5.0',
        '5.0.SP2': '5.0.SP2'
    }
    
    url_version = version_map.get(version, version)
    url = f'https://www.onixs.biz/fix-dictionary/{url_version}/fields_by_tag.html'
    
    print(f"Fetching FIX {version} specification from {url}...")
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"ERROR: Failed to fetch specification: {e}")
        return None
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find the table with field definitions
    table = soup.find('table')
    if not table:
        print("ERROR: Could not find fields table on page")
        return None
    
    fix_spec = {}
    rows = table.find_all('tr')[1:]  # Skip header row
    
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 2:
            tag = cols[0].text.strip()
            field_name = cols[1].text.strip()
            fix_spec[tag] = field_name
    
    print(f"Successfully scraped {len(fix_spec)} field definitions")
    return fix_spec

def save_fix_spec(fix_spec, output_file='fix_spec.json'):
    """Save FIX specification to JSON file."""
    with open(output_file, 'w') as f:
        json.dump(fix_spec, f, indent=2)
    print(f"Saved FIX specification to {output_file}")

def main():
    version = sys.argv[1] if len(sys.argv) > 1 else '5.0.SP2'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'fix_spec.json'
    
    print(f"Scraping FIX {version} specification...")
    fix_spec = scrape_fix_spec(version)
    
    if fix_spec:
        save_fix_spec(fix_spec, output_file)
        print("\nSample mappings:")
        for tag in ['1', '11', '35', '37', '55', '79', '118', '448', '447']:
            if tag in fix_spec:
                print(f"  Tag {tag}: {fix_spec[tag]}")
    else:
        print("Failed to scrape FIX specification")

if __name__ == "__main__":
    main()