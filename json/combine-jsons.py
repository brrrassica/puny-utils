import glob
import os
import json

def combine_json_files(directory='.'):
    combined_file_path = os.path.join(directory, 'combined.txt')
    json_file_count = 0
    
    with open(combined_file_path, 'w') as combined_file:
        for json_file in glob.glob(os.path.join(directory, '*.json')):
            with open(json_file, 'r') as file:
                data = json.load(file)  # Load the JSON data
                combined_file.write(json.dumps(data) + '\r\n')  # Flatten and write as a single line
                json_file_count += 1  # Increment the count of JSON files processed

    print(f"Combined {json_file_count} JSON files into: {combined_file_path}")

if __name__ == "__main__":
    combine_json_files()


