import os
import json
import shutil

def find_matching_jsons(field_name, value_to_match, directory='.'):
    matching_files = []
    separated_directory = os.path.join(directory, 'separated')

    # Check for null pointer references
    if not field_name or not value_to_match:
        raise ValueError("field_name and value_to_match must not be None or empty")

    # Create the 'separated' directory if it doesn't exist
    os.makedirs(separated_directory, exist_ok=True)

    # Split the field_name to handle nested fields
    keys = field_name.split('.')

    # Iterate over the files in the directory
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            try:
                with open(file_path, 'r') as file:
                    data = json.load(file)
                    # Navigate through nested fields
                    current_data = data
                    for key in keys:
                        if key in current_data:
                            current_data = current_data[key]
                        else:
                            current_data = None
                            break
                    
                    if current_data == value_to_match:
                        matching_files.append(file_path)
                        # Move the matching file to the 'separated' directory
                        shutil.move(file_path, os.path.join(separated_directory, filename))
                        print(f"Moved file: {filename} to {separated_directory}")
            except json.JSONDecodeError:
                print(f"Error decoding JSON from file: {file_path}")
            except Exception as e:
                print(f"An error occurred while processing file: {file_path}. Error: {str(e)}")
    return matching_files

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python remove-tests.py <field_name> <value_to_match>")
        sys.exit(1)

    field_name = sys.argv[1]
    value_to_match = sys.argv[2]
    find_matching_jsons(field_name, value_to_match)

