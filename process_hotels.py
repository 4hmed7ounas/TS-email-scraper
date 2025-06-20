import pandas as pd
import re
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import time
from concurrent.futures import ThreadPoolExecutor
import csv

# Function to extract domain from URL
def extract_domain(url):
    if pd.isna(url) or not isinstance(url, str):
        return None
    try:
        # Remove any query parameters and fragments
        clean_url = url.split('?')[0].split('#')[0]
        # Extract domain
        domain = urlparse(clean_url).netloc
        # Remove www. if present
        domain = domain.replace('www.', '')
        return domain.lower()
    except:
        return None

# Function to extract emails from text
def extract_emails(text):
    if pd.isna(text) or not isinstance(text, str):
        return []
    # Simple email regex pattern
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(email_pattern, text)

# Function to scrape emails from a website
def scrape_emails(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all text in the page
        page_text = soup.get_text()
        
        # Find all email addresses in the page
        emails = extract_emails(page_text)
        
        # Also check contact, about, and other common pages
        contact_links = []
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            if any(term in href for term in ['contact', 'about', 'connect', 'reach']):
                if href.startswith('http'):
                    contact_links.append(href)
                elif href.startswith('/'):
                    # Convert relative URL to absolute
                    base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                    contact_links.append(base_url + href)
        
        # Deduplicate contact links
        contact_links = list(set(contact_links))
        
        # Check contact pages for additional emails
        for contact_url in contact_links[:2]:  # Limit to first 2 contact pages to avoid too many requests
            try:
                contact_response = requests.get(contact_url, headers=headers, timeout=5, allow_redirects=True)
                contact_response.raise_for_status()
                contact_text = contact_response.text
                contact_emails = extract_emails(contact_text)
                emails.extend(contact_emails)
            except:
                continue
        
        # Deduplicate emails and clean
        emails = list(set(emails))
        emails = [email.lower().strip() for email in emails if '@' in email]
        
        return emails
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return []

# Main function to process the CSV
def process_hotels(input_file, output_file):
    # Try different encodings to read the CSV file
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
    
    # Initialize result list
    results = []
    
    # Process each hotel
    for _, row in df.iterrows():
        name = row['Name']
        phone = row.get('Phone', '')
        website = row.get('Website', row.get('Google Maps URL', ''))
        
        # Skip if no website
        if pd.isna(website) or not website:
            print(f"Skipping {name}: No website")
            continue
            
        # Clean and get domain
        domain = extract_domain(website)
        if not domain:
            print(f"Skipping {name}: Could not extract domain from {website}")
            continue
        
        # Ensure URL has scheme
        if not website.startswith(('http://', 'https://')):
            website = 'https://' + website
        
        print(f"Processing {name}...")
        
        # Scrape emails
        emails = []
        try:
            emails = scrape_emails(website)
            # If no emails found, try with www. prefix
            if not emails and not website.startswith('https://www.'):
                www_website = website.replace('https://', 'https://www.')
                emails = scrape_emails(www_website)
        except Exception as e:
            print(f"Error processing {name}: {str(e)}")
        
        # Add to results
        results.append({
            'Name': name,
            'Domain': domain,
            'Phone': phone,
            'Emails': ', '.join(emails) if emails else '',
            'Website': website
        })
        
        # Be nice to the server
        time.sleep(1)
    
    # Save results to CSV
    if results:
        output_df = pd.DataFrame(results)
        output_df.to_csv(output_file, index=False, quoting=csv.QUOTE_ALL)
        print(f"\nResults saved to {output_file}")
    else:
        print("No results to save.")

if __name__ == "__main__":
    input_file = "hotels & resorts in pennsylvania - GMS output.csv"
    output_file = "pennsylvania_hotels_emails.csv"
    
    # Add error handling for file not found
    try:
        process_hotels(input_file, output_file)
    except FileNotFoundError:
        print(f"Error: The file '{input_file}' was not found. Please check the file name and try again.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
