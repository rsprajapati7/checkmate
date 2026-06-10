#!/usr/bin/env node
import React from 'react';
import { render } from 'ink';
import meow from 'meow';
import { App } from './components/App.js';
import { scanDocument } from './api.js';
import { DiagnosticTable } from './components/DiagnosticTable.js';
import chalk from 'chalk';
import fs from 'fs';
import path from 'path';

const cli = meow(`
  Usage
    $ checkmate [command] [options]

  Commands
    (no command)             Start interactive CheckMate shell (REPL)
    analyze <file_path>      Directly scan a document and show forensic report

  Options
    --help, -h               Show this usage guide
    --version, -v            Show version information

  Examples
    $ checkmate
    $ checkmate analyze docs/aadhaar.pdf
`, {
  importMeta: import.meta,
  flags: {
    help: { type: 'boolean', shortFlag: 'h' },
    version: { type: 'boolean', shortFlag: 'v' }
  }
});

async function run() {
  const [command, arg1] = cli.input;

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
  } else if (command) {
    console.error(chalk.red(`Error: Unknown command "${command}"`));
    cli.showHelp();
  } else {
    // Start interactive shell
    render(<App />);
  }
}

run();
