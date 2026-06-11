import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { loadConfig } from './config.js';

// Get directory paths
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const cliDir = path.resolve(__dirname, '..');
const rootDir = path.resolve(cliDir, '..');

const DEFAULT_API_URL = 'http://localhost:8000';

// Priority: env var > ~/.checkmate/config.json > .env files > default
let envApiUrl = process.env.CHECKMATE_API_URL;
if (!envApiUrl) {
  const userConfig = loadConfig();
  if (userConfig.api_url) {
    envApiUrl = userConfig.api_url;
  }
}
if (!envApiUrl) {
  const envPaths = [
    path.join(cliDir, '.env'),
    path.join(rootDir, '.env')
  ];
  for (const envPath of envPaths) {
    if (fs.existsSync(envPath)) {
      try {
        const envContent = fs.readFileSync(envPath, 'utf8');
        const match = envContent.match(/^\s*CHECKMATE_API_URL\s*=\s*([^\s#]+)/m);
        if (match && match[1]) {
          envApiUrl = match[1].trim();
          if ((envApiUrl.startsWith('"') && envApiUrl.endsWith('"')) ||
              (envApiUrl.startsWith("'") && envApiUrl.endsWith("'"))) {
            envApiUrl = envApiUrl.slice(1, -1);
          }
          break;
        }
      } catch {
        // Ignore read/parse errors
      }
    }
  }
}


let resolvedUrl = envApiUrl || DEFAULT_API_URL;
if (resolvedUrl && !resolvedUrl.startsWith('http://') && !resolvedUrl.startsWith('https://')) {
  if (resolvedUrl.includes('localhost') || resolvedUrl.includes('127.0.0.1')) {
    resolvedUrl = 'http://' + resolvedUrl;
  } else {
    resolvedUrl = 'https://' + resolvedUrl;
  }
}

export const API_URL = resolvedUrl;



export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  db: string;
  llm: string;
  environment: string;
}

export interface PipelineResult {
  score: number;
  flags: string[];
  [key: string]: any;
}

export interface ScanResponse {
  filename: string;
  file_type: string;
  page_count: number;
  is_scanned: boolean;
  risk_tier: string;
  final_score: number;
  pipelines: {
    ela: PipelineResult & { heatmap_b64?: string };
    metadata: PipelineResult;
    seal: PipelineResult & { seals_found: number; suspicious: number };
    nlp: PipelineResult & { entities: Record<string, any> };
  };
  pdf_metadata: Record<string, any>;
  qr_codes: string[];
  ocr_summary: string;
}

export interface ChatResponse {
  response: string;
}

/**
 * Checks if the FastAPI backend is running by pinging its health endpoint.
 */
export async function healthCheck(): Promise<HealthResponse | null> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 1500);
    const res = await fetch(`${API_URL}/health`, { signal: controller.signal });
    clearTimeout(timeout);
    if (res.ok) {
      return await res.json() as HealthResponse;
    }
  } catch (err) {
    // Silent fail if unreachable
  }
  return null;
}

/**
 * Resolves the path to the uvicorn executable within the workspace.
 */
function findUvicorn(): string {
  const potentialPaths = [
    path.join(rootDir, '.venv', 'Scripts', 'uvicorn.exe'),
    path.join(rootDir, 'venv', 'Scripts', 'uvicorn.exe'),
    path.join(rootDir, '.venv-1', 'Scripts', 'uvicorn.exe'),
    path.join(rootDir, '.venv', 'bin', 'uvicorn'),
    path.join(rootDir, 'venv', 'bin', 'uvicorn'),
  ];

  for (const p of potentialPaths) {
    if (fs.existsSync(p)) {
      return p;
    }
  }

  // Fallback to global command
  return 'uvicorn';
}

/**
 * Starts the FastAPI backend server in a detached process and waits for it to become healthy.
 */
export async function startServer(onProgress: (msg: string) => void): Promise<boolean> {
  onProgress('Starting FastAPI backend server...');
  
  const uvicornPath = findUvicorn();
  const args = ['backend.main:app', '--host', '127.0.0.1', '--port', '8000'];
  
  try {
    const child = spawn(uvicornPath, args, {
      cwd: rootDir,
      detached: true,
      stdio: 'ignore',
      shell: true, // Use shell to resolve command names correctly on Windows
    });
    child.unref();

    // Poll health endpoint
    for (let i = 0; i < 10; i++) {
      onProgress(`Waiting for server to start... (${i + 1}/10)`);
      const healthy = await healthCheck();
      if (healthy) {
        onProgress('Server successfully started!');
        return true;
      }
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  } catch (error: any) {
    onProgress(`Failed to launch server process: ${error.message}`);
  }
  
  return false;
}

/**
 * Runs inline scan pipeline for a file path.
 */
export async function scanDocument(filePath: string): Promise<ScanResponse> {
  if (!fs.existsSync(filePath)) {
    throw new Error(`File does not exist: ${filePath}`);
  }

  const fileBuffer = fs.readFileSync(filePath);
  const blob = new Blob([fileBuffer]);
  const formData = new FormData();
  formData.append('file', blob, path.basename(filePath));

  const res = await fetch(`${API_URL}/api/v1/cli/scan`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorText = await res.text();
    let detail = errorText;
    try {
      const parsed = JSON.parse(errorText);
      detail = parsed.detail || errorText;
    } catch {
      // ignore JSON parse error
    }
    throw new Error(detail);
  }

  return await res.json() as ScanResponse;
}

/**
 * Sends chat prompt to Gemma with context and streams back token chunks.
 */
export async function chatWithGemma(
  message: string,
  context: any = null,
  history: { role: string; content: string }[] = [],
  onChunk: (text: string) => void
): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/cli/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, context, history }),
  });

  if (!res.ok) {
    const errorText = await res.text();
    let detail = errorText;
    try {
      const parsed = JSON.parse(errorText);
      detail = parsed.detail || errorText;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  if (!res.body) {
    throw new Error('Response stream body is null');
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let done = false;

  while (!done) {
    const { value, done: doneReading } = await reader.read();
    done = doneReading;
    if (value) {
      const chunk = decoder.decode(value, { stream: !done });
      onChunk(chunk);
    }
  }
}

/**
 * Request PDF/HTML report from backend using active document results and write to local disk.
 */
export async function generateReport(results: ScanResponse): Promise<{ data: Buffer; isPdf: boolean }> {
  const res = await fetch(`${API_URL}/api/v1/cli/report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ results }),
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || 'Failed to generate report');
  }

  const contentType = res.headers.get('content-type') || '';
  const isPdf = contentType.includes('pdf');
  
  const arrayBuffer = await res.arrayBuffer();
  const data = Buffer.from(arrayBuffer);
  
  return { data, isPdf };
}

/**
 * Stream an AI-generated forensic summary for completed scan results.
 * The backend calls Gemma and streams a markdown narrative.
 */
export async function aiSummary(
  results: ScanResponse,
  onChunk: (text: string) => void
): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/cli/ai-summary`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ results }),
  });

  if (!res.ok) {
    const errorText = await res.text();
    let detail = errorText;
    try {
      const parsed = JSON.parse(errorText);
      detail = parsed.detail || errorText;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  if (!res.body) {
    throw new Error('Response stream body is null');
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let done = false;

  while (!done) {
    const { value, done: doneReading } = await reader.read();
    done = doneReading;
    if (value) {
      onChunk(decoder.decode(value, { stream: !done }));
    }
  }
}

