#!/usr/bin/env python3
import os
import sys
from pathlib import Path

def parse_size(size_str):
    """Convert size string (like '100M' or '2G') to bytes"""
    units = {'B': 1, 'K': 1024, 'M': 1024**2, 'G': 1024**3}
    size_str = size_str.upper()
    if size_str[-1] in units:
        number = float(size_str[:-1])
        unit = size_str[-1]
        return int(number * units[unit])
    else:
        return int(size_str)

def split_file(input_file, chunk_size):
    """Split a large file into chunks of approximately chunk_size bytes"""
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: File '{input_file}' not found")
        sys.exit(1)

    # Create splits directory if it doesn't exist
    splits_dir = input_path.parent / 'splits'
    splits_dir.mkdir(exist_ok=True)

    total_size = input_path.stat().st_size
    if total_size == 0:
        print("Error: Input file is empty")
        sys.exit(1)

    # Calculate number of chunks needed
    num_chunks = (total_size + chunk_size - 1) // chunk_size
    
    # Get base filename without path
    base_name = input_path.name

    with open(input_file, 'rb') as f:
        for chunk_num in range(num_chunks):
            output_file = splits_dir / f"{base_name}.{chunk_num:03d}"
            current_size = 0
            
            with open(output_file, 'wb') as out:
                # Read chunk_size plus extra to ensure we don't cut in middle of line
                while current_size < chunk_size:
                    # Read in 1MB blocks
                    buffer = f.read(min(1024*1024, chunk_size - current_size))
                    if not buffer:  # EOF reached
                        break
                    
                    current_size += len(buffer)
                    out.write(buffer)

                # If we're not at the last chunk, read until next newline
                if chunk_num < num_chunks - 1:
                    while True:
                        char = f.read(1)
                        if not char or char == b'\n':
                            if char:
                                out.write(char)
                            break
                        out.write(char)

            actual_size = os.path.getsize(output_file)
            size_diff_percent = abs(actual_size - chunk_size) / chunk_size * 100
            
            if size_diff_percent > 0.1 and chunk_num < num_chunks - 1:
                print(f"Warning: Chunk {output_file} size differs by {size_diff_percent:.2f}% from target")

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 trunc-log.py <input_file> <chunk_size>")
        print("Example: python3 trunc-log.py large.log 100M")
        sys.exit(1)

    input_file = sys.argv[1]
    try:
        chunk_size = parse_size(sys.argv[2])
    except ValueError:
        print("Error: Invalid chunk size format")
        sys.exit(1)

    split_file(input_file, chunk_size)

if __name__ == "__main__":
    main()

