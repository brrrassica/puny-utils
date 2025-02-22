import json
import csv
import sys
import os
from pathlib import Path

def json_to_csv(json_file_path):
    # Create results directory if it doesn't exist
    results_dir = Path('results')
    results_dir.mkdir(exist_ok=True)
    
    # Read JSON file
    try:
        with open(json_file_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Error: File '{json_file_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in file '{json_file_path}'.")
        sys.exit(1)
    
    # Check for 'data' array
    if 'data' not in data:
        print("Error: No 'data' array found in JSON.")
        sys.exit(1)
    
    items = data['data']
    if not items:
        print("Warning: 'data' array is empty.")
        return
    
    # Create output CSV file path
    input_file_name = Path(json_file_path).stem
    output_file = results_dir / f"{input_file_name}.csv"
    
    # Write to CSV
    try:
        with open(output_file, 'w', newline='') as csvfile:
            # Get headers from first item
            fieldnames = list(items[0].keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write headers and data
            writer.writeheader()
            writer.writerows(items)
            
        print(f"Successfully created CSV file: {output_file}")
    
    except IOError as e:
        print(f"Error writing CSV file: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 soh-to-csv.py <json_file>")
        sys.exit(1)
    
    json_file_path = sys.argv[1]
    json_to_csv(json_file_path)

if __name__ == "__main__":
    main()
