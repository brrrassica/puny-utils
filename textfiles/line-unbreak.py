import sys
import os
import re
#!/usr/bin/env python3

import sys
import os
import re

def unbreak_lines(start_pattern, input_file_path):
    """Unbreak lines in a text file based on a starting pattern.
    
    Args:
        start_pattern: Regex pattern that identifies the start of a new line
        input_file_path: Path to the input file to process
    """
    try:
        with open(input_file_path, 'r', newline='') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Input file not found: {input_file_path}")
        sys.exit(1)

    processed_lines = []
    current_line = ''
    
    start_regex = re.compile(re.escape(start_pattern))
    for line in lines:
        line = line.rstrip('\r\n')
        if start_regex.match(line):
            if current_line:
                processed_lines.append(current_line)
            current_line = line
        else:
            current_line += line.lstrip()
    
    if current_line:
        processed_lines.append(current_line)
    
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'processed.txt')
    try:
        with open(output_path, 'w', newline='\n') as f:
            f.write('\n'.join(processed_lines))
    except IOError:
        print(f"Error: Could not write to output file: {output_path}")
        sys.exit(1)

def main():
    if len(sys.argv) != 3:
        print("Usage: ./line-unbreak.py <start_pattern> <input_file_path>")
        sys.exit(1)
    
    start_pattern = sys.argv[1]
    input_file_path = sys.argv[2]
    unbreak_lines(start_pattern, input_file_path)

if __name__ == '__main__':
    main()
