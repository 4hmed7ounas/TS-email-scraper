// Simple script to run the main application
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Import the main application
await import('./src/main.js');

console.log('Application finished running');
