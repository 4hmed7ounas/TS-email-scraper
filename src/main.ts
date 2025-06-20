import { CheerioCrawler, RequestQueue, Dataset } from "crawlee";
import { readFile, writeFile } from 'fs/promises';
import { join } from 'path';

// Define types for our data
interface InputData {
  domainUrls: string[];
  keywords?: string[];
}

interface Result {
  url: string;
  domain: string;
  emails: string[];
  timestamp: string;
}

// Read and parse the input file
const loadInput = async (): Promise<InputData> => {
  try {
    const inputPath = join(process.cwd(), 'storage', 'key_value_stores', 'default', 'INPUT.json');
    const data = await readFile(inputPath, 'utf-8');
    console.log('Loaded input data');
    return JSON.parse(data) as InputData;
  } catch (error) {
    console.error('Error loading input file:', error);
    throw new Error('Failed to load input file. Please run the Python script first.');
  }
};

// Ensure URL has proper protocol
const ensureUrl = (url: string): string => {
  if (!url) return '';
  
  // If already has protocol, return as is
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }
  
  // Otherwise, add https://
  return `https://${url}`;
};

// Extract domain from URL
const extractDomain = (url: string): string => {
  try {
    const cleanUrl = url.split('?')[0].split('#')[0];
    return cleanUrl.replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0];
  } catch (error) {
    console.error(`Error extracting domain from ${url}:`, error);
    return '';
  }
};

// Extract emails from text
const extractEmails = (text: string): string[] => {
  if (!text) return [];
  const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
  return [...new Set(text.match(emailRegex) || [])].map(email => email.toLowerCase());
};

async function main() {
  console.log('Starting email scraper...');
  
  // Load input data
  const { domainUrls } = await loadInput();
  
  // Prepare results array
  const results: Result[] = [];
  
  // Initialize crawler
  const crawler = new CheerioCrawler({
    async requestHandler({ request, $, enqueueLinks }) {
      console.log(`Processing: ${request.url}`);
      
      // Extract emails from the current page
      const pageText = $('body').text();
      const emails = extractEmails(pageText);
      
      // Add to results
      results.push({
        url: request.url,
        domain: extractDomain(request.url),
        emails,
        timestamp: new Date().toISOString()
      });
      
      // Find and enqueue links to other pages on the same domain
      if (emails.length === 0) {
        await enqueueLinks({
          strategy: 'same-domain',
          globs: ['**/contact**', '**/about**', '**/contact-us**'],
          limit: 2 // Limit to 2 additional pages
        });
      }
    },
    
    // Handle failed requests
    async failedRequestHandler({ request }, error) {
      console.error(`Failed to process ${request.url}:`, error);
    }
  });

  // Ensure all URLs have proper protocol and start the crawler
  const validUrls = domainUrls
    .map(url => ensureUrl(url))
    .filter(url => {
      try {
        new URL(url);
        return true;
      } catch (e) {
        console.error(`Invalid URL format: ${url}`);
        return false;
      }
    });

  console.log(`Starting to crawl ${validUrls.length} valid URLs...`);
  if (validUrls.length === 0) {
    console.error('No valid URLs to crawl. Please check your input data.');
    return;
  }
  
  await crawler.run(validUrls);
  
  // Save results
  const outputPath = join(process.cwd(), 'results', 'emails.json');
  await writeFile(outputPath, JSON.stringify(results, null, 2));
  console.log(`\nScraping complete! Results saved to: ${outputPath}`);
  
  // Also save as CSV
  const csvContent = [
    'URL,Domain,Emails,Timestamp',
    ...results.map(r => `"${r.url}","${r.domain}","${r.emails.join('; ')}","${r.timestamp}"`)
  ].join('\n');
  
  const csvPath = join(process.cwd(), 'results', 'emails.csv');
  await writeFile(csvPath, csvContent);
  console.log(`CSV results saved to: ${csvPath}`);
}

// Create results directory if it doesn't exist
import { mkdir } from 'fs/promises';
import { existsSync } from 'fs';
import { dirname } from 'path';

const ensureDir = async (path: string) => {
  if (!existsSync(path)) {
    await mkdir(path, { recursive: true });
  }
};

// Run the main function
(async () => {
  try {
    await ensureDir(join(process.cwd(), 'results'));
    await main();
  } catch (error) {
    console.error('Fatal error:', error);
    process.exit(1);
  }
})();
