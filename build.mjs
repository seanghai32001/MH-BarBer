import { copyFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const projectDir = dirname(fileURLToPath(import.meta.url));
const apiBaseUrl = (process.env.TSH_API_BASE_URL || '').trim().replace(/\/+$/, '');

if (!apiBaseUrl) {
  throw new Error('Set TSH_API_BASE_URL in Vercel Project Environment Variables.');
}

let parsedApiUrl;
try {
  parsedApiUrl = new URL(apiBaseUrl);
} catch {
  throw new Error('TSH_API_BASE_URL must be a valid HTTPS origin.');
}

if (parsedApiUrl.protocol !== 'https:' || parsedApiUrl.pathname !== '/' ||
    parsedApiUrl.search || parsedApiUrl.hash || parsedApiUrl.username || parsedApiUrl.password) {
  throw new Error('TSH_API_BASE_URL must be an HTTPS origin without a path, query, or credentials.');
}

const outputDir = join(projectDir, 'dist');
mkdirSync(outputDir, { recursive: true });
copyFileSync(join(projectDir, 'index.html'), join(outputDir, 'index.html'));
copyFileSync(join(projectDir, 'logo.png'), join(outputDir, 'logo.png'));
writeFileSync(
  join(outputDir, 'config.js'),
  `window.TSH_API_BASE_URL = ${JSON.stringify(parsedApiUrl.origin)};\n`,
  'utf8',
);

console.log(`Built frontend for ${parsedApiUrl.origin}`);
