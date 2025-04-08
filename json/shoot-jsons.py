import os
import json
import requests
import sys
import time
import warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Suppress only the single warning from urllib3 needed
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

def post_json_files(url, directory):
    if not url or not directory:
        raise ValueError("URL and directory must not be None or empty")
    
    json_files = sorted(
        (filename for filename in os.listdir(directory) if filename.endswith('.json')),
        key=lambda x: int(x.split('_')[1].split('.')[0])
    )

    for filename in json_files:
        file_path = os.path.join(directory, filename)
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                
                response = requests.post(url, json=data, verify=False)
                
                if response.status_code == 200:
                    print(f"Successfully posted {filename}")
                else:
                    print(f"Failed to post {filename}. Status code: {response.status_code}")
        except json.JSONDecodeError:
            print(f"Error decoding JSON from file: {file_path}")
        except Exception as e:
            print(f"An error occurred while posting file: {file_path}. Error: {str(e)}")
        time.sleep(0.1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python shoot-jsons.py <url> <directory>")
        sys.exit(1)

    url = sys.argv[1]
    directory = sys.argv[2]
    post_json_files(url, directory)

