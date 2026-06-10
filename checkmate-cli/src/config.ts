/**
 * CheckMate CLI — User Configuration Manager
 *
 * Stores user-level config at ~/.checkmate/config.json
 * Supports: CHECKMATE_API_URL, GEMMA_API_KEY
 */

import fs from 'fs';
import path from 'path';
import os from 'os';

export interface CheckMateConfig {
  api_url?: string;
  api_key?: string;
}

const CONFIG_DIR = path.join(os.homedir(), '.checkmate');
const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json');

/**
 * Ensure the ~/.checkmate directory exists.
 */
function ensureConfigDir(): void {
  if (!fs.existsSync(CONFIG_DIR)) {
    fs.mkdirSync(CONFIG_DIR, { recursive: true });
  }
}

/**
 * Load configuration from disk. Returns empty object if not found.
 */
export function loadConfig(): CheckMateConfig {
  try {
    if (fs.existsSync(CONFIG_FILE)) {
      const raw = fs.readFileSync(CONFIG_FILE, 'utf8');
      return JSON.parse(raw) as CheckMateConfig;
    }
  } catch {
    // Corrupted config — return defaults
  }
  return {};
}

/**
 * Save configuration to disk.
 */
export function saveConfig(config: CheckMateConfig): void {
  ensureConfigDir();
  fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2), 'utf8');
}

/**
 * Get a specific config value.
 */
export function getConfigValue(key: keyof CheckMateConfig): string | undefined {
  const config = loadConfig();
  return config[key];
}

/**
 * Set a specific config value.
 */
export function setConfigValue(key: keyof CheckMateConfig, value: string): void {
  const config = loadConfig();
  config[key] = value;
  saveConfig(config);
}

/**
 * Get the path to the config file (for display purposes).
 */
export function getConfigPath(): string {
  return CONFIG_FILE;
}
