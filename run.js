import { spawn } from 'child_process';

const child = spawn('node', [
  '--loader',
  'ts-node/esm',
  '--no-warnings=ExperimentalWarning',
  'src/main.ts'
], {
  stdio: 'inherit',
  shell: true,
  env: { ...process.env, NODE_OPTIONS: '--loader ts-node/esm' }
});

child.on('error', (error) => {
  console.error('Error:', error);
});

child.on('close', (code) => {
  process.exit(code || 0);
});
