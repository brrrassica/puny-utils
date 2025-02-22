import json
import csv
import sys
import os
from pathlib import Path

def process_json_files(folder_path):
    folder = Path(folder_path)
    output_file = folder / "results.csv"
    all_items = []
    fieldnames = None

    # Process all JSON files
    json_files = sorted(folder.glob("*.json"), key=lambda x: int(x.stem))
    if not json_files:
        print("Error: No JSON files found in the specified folder.")
        sys.exit(1)

    for json_file in json_files:
        try:
            with open(json_file, 'r') as file:
                data = json.load(file)
        except FileNotFoundError:
            print(f"Error: File '{json_file}' not found.")
            continue
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON format in file '{json_file}'.")
            continue

        # Check for 'data' array
        if 'data' not in data:
            print(f"Error: No 'data' array found in {json_file}.")
            continue

        items = data['data']
        if not items:
            print(f"Warning: 'data' array is empty in {json_file}.")
            continue

        # Get fieldnames from first file with data
        if fieldnames is None and items:
            fieldnames = list(items[0].keys())

        all_items.extend(items)

    if not all_items:
        print("Error: No valid data found in any JSON file.")
        sys.exit(1)

    # Write all data to CSV
    try:
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_items)
            
        print(f"Successfully created CSV file: {output_file}")
    
    except IOError as e:
        print(f"Error writing CSV file: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 soh-to-csv.py <folder_path>")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    process_json_files(folder_path)

if __name__ == "__main__":
    main()
