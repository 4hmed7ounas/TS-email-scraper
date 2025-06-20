import pandas as pd
import json
import os
from typing import List, Dict, Any

def process_csv_to_json(input_file: str, output_dir: str = 'storage/key_value_stores/default') -> None:
    """
    Process the hotels CSV file and create input files for TypeScript crawler.
    
    Args:
        input_file (str): Path to the input CSV file
        output_dir (str): Directory to store the output JSON files
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the CSV file with appropriate encoding
    encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
    df = None
    
    for encoding in encodings:
        try:
            df = pd.read_csv(input_file, encoding=encoding)
            print(f"Successfully read file with {encoding} encoding")
            break
        except UnicodeDecodeError:
            print(f"Failed to read with {encoding} encoding, trying next...")
            continue
    
    if df is None:
        raise ValueError("Could not read the CSV file with any of the attempted encodings")
    
    # Remove duplicates based on name (case insensitive)
    df = df.drop_duplicates(subset=['Name'], keep='first')
    
    # Create a list of unique domains
    def extract_domain(url):
        if pd.isna(url) or not isinstance(url, str):
            return None
        try:
            clean_url = str(url).split('?')[0].split('#')[0]
            domain = clean_url.replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0]
            return domain.lower()
        except:
            return None
    
    df['Domain'] = df['Website'].apply(extract_domain)
    df = df[df['Domain'].notna()]
    
    # Convert domains to full URLs
    df['FullUrl'] = df['Domain'].apply(lambda x: f'https://{x}' if x and not x.startswith(('http://', 'https://')) else x)
    
    # Create input for TypeScript crawler
    input_data = {
        "keywords": ["hotel", "resort", "accommodation", "lodging"],
        "domainUrls": df['FullUrl'].dropna().tolist()
    }
    
    # Save the input file
    input_file_path = os.path.join(output_dir, 'INPUT.json')
    with open(input_file_path, 'w') as f:
        json.dump(input_data, f, indent=2)
    
    print(f"Processed {len(df)} unique hotels. Input file created at: {input_file_path}")
    return input_file_path

if __name__ == "__main__":
    input_file = "hotels & resorts in new york - GMS output.csv"
    try:
        process_csv_to_json(input_file)
        print("\nNow run the TypeScript crawler with: npm start")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
