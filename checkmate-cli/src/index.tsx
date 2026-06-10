#!/usr/bin/env node
import React from 'react';
import { render } from 'ink';
import meow from 'meow';
import { App } from './components/App.js';
import { scanDocument } from './api.js';
import { DiagnosticTable } from './components/DiagnosticTable.js';
import { loadConfig, saveConfig, getConfigPath } from './config.js';
import chalk from 'chalk';
import fs from 'fs';
import path from 'path';
import readline from 'readline';

const cli = meow(`
  Usage
    $ checkmate [command] [options]

  Commands
    (no command)             Start interactive CheckMate shell (REPL)
    analyze <file_path>      Directly scan a document and show forensic report
    setup                    Interactive first-time setup wizard
    config <key> [value]     Get or set configuration values

  Config Keys
    api_url                  Backend API URL (e.g. https://your-app.up.railway.app)
    api_key                  Your Gemini API key from Google AI Studio

  Options
    --help, -h               Show this usage guide
    --version, -v            Show version information

  Examples
    $ checkmate
    $ checkmate setup
    $ checkmate config api_url https://your-app.up.railway.app
    $ checkmate config api_key AIzaSy...
    $ checkmate analyze docs/aadhaar.pdf
`, {
  importMeta: import.meta,
  flags: {
    help: { type: 'boolean', shortFlag: 'h' },
    version: { type: 'boolean', shortFlag: 'v' }
  }
});

// Prompt helper for interactive setup
function prompt(question: string): Promise<string> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      rl.close();
      resolve(answer.trim());
    });
  });
}

async function runSetup() {
  const gold = chalk.hex('#D4AF37');
  const sage = chalk.hex('#8DECB4');
  const muted = chalk.hex('#4A4A5A');

  console.log('');
  console.log(gold.bold('  CheckMate Setup Wizard'));
  console.log(muted('  ─────────────────────────────────────────'));
  console.log('');
  console.log(chalk.white('  Configure your CheckMate CLI to connect to a backend server.'));
  console.log(chalk.white('  Press Enter to skip a field and keep the current value.'));
  console.log('');

  const config = loadConfig();

  // API URL
  const currentUrl = config.api_url || '(not set)';
  console.log(muted(`  Current API URL: ${currentUrl}`));
  const newUrl = await prompt(gold('  Backend API URL: '));
  if (newUrl) {
    config.api_url = newUrl;
  }

  console.log('');

  // API Key
  const currentKey = config.api_key ? config.api_key.slice(0, 8) + '...' : '(not set)';
  console.log(muted(`  Current API Key: ${currentKey}`));
  console.log(muted('  Get a free key at: https://aistudio.google.com/app/apikey'));
  const newKey = await prompt(gold('  Gemini API Key:  '));
  if (newKey) {
    config.api_key = newKey;
  }

  saveConfig(config);

  console.log('');
  console.log(sage.bold('  Configuration saved!'));
  console.log(muted(`  Location: ${getConfigPath()}`));
  console.log('');
  console.log(chalk.white('  Run ') + gold('checkmate') + chalk.white(' to start the forensic shell.'));
  console.log('');
}

function runConfigCommand(key?: string, value?: string) {
  const gold = chalk.hex('#D4AF37');
  const sage = chalk.hex('#8DECB4');
  const muted = chalk.hex('#4A4A5A');
  const crimson = chalk.hex('#C0392B');

  if (!key) {
    // Show all config
    const config = loadConfig();
    console.log('');
    console.log(gold.bold('  CheckMate Configuration'));
    console.log(muted('  ─────────────────────────────────────────'));
    console.log(`  ${chalk.white('api_url')}  ${config.api_url || muted('(not set)')}`);
    console.log(`  ${chalk.white('api_key')}  ${config.api_key ? config.api_key.slice(0, 8) + '...' : muted('(not set)')}`);
    console.log(muted(`\n  Config file: ${getConfigPath()}`));
    console.log('');
    return;
  }

  if (key !== 'api_url' && key !== 'api_key') {
    console.error(crimson(`  Unknown config key: "${key}"`));
    console.log(muted('  Valid keys: api_url, api_key'));
    process.exit(1);
  }

  if (value === undefined) {
    // Get value
    const config = loadConfig();
    const val = config[key as keyof typeof config];
    if (val) {
      if (key === 'api_key') {
        console.log(val.slice(0, 8) + '...');
      } else {
        console.log(val);
      }
    } else {
      console.log(muted('(not set)'));
    }
    return;
  }

  // Set value
  const config = loadConfig();
  (config as any)[key] = value;
  saveConfig(config);
  console.log(sage(`  Set ${key} = ${key === 'api_key' ? value.slice(0, 8) + '...' : value}`));
}

async function run() {
  const [command, arg1, arg2] = cli.input;

  if (command === 'analyze') {
    if (!arg1) {
      console.error(chalk.red('Error: Please provide a file path to analyze.'));
      console.log('Usage: checkmate analyze <file_path>');
      process.exit(1);
    }
    const fullPath = path.resolve(arg1);
    if (!fs.existsSync(fullPath)) {
      console.error(chalk.red(`Error: File not found at path "${fullPath}"`));
      process.exit(1);
    }
    
    console.log(chalk.yellow(`Scanning ${path.basename(fullPath)} ...`));
    try {
      const results = await scanDocument(fullPath);
      // Render the DiagnosticTable once and exit
      const { unmount } = render(<DiagnosticTable results={results} />);
      // Wait a moment for rendering to complete before exit
      setTimeout(() => {
        unmount();
        process.exit(0);
      }, 100);
    } catch (err: any) {
      console.error(chalk.red(`Scan failed: ${err.message}`));
      process.exit(1);
    }
  } else if (command === 'setup') {
    await runSetup();
  } else if (command === 'config') {
    runConfigCommand(arg1, arg2);
  } else if (command) {
    console.error(chalk.red(`Error: Unknown command "${command}"`));
    cli.showHelp();
  } else {
    // Start interactive shell
    render(<App />);
  }
}

run();
