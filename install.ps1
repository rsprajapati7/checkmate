# ============================================================
# CheckMate CLI - Windows Installer (PowerShell)
#
# Usage:
#   irm https://raw.githubusercontent.com/rsprajapati7/checkmate/dev/install.ps1 | iex
#
# What this script does:
#   1. Checks for Node.js and npm
#   2. Clones the checkmate-cli source
#   3. Installs dependencies and builds
#   4. Links globally so `checkmate` works from anywhere
#   5. Runs the setup wizard for first-time configuration
# ============================================================

$ErrorActionPreference = "Stop"

$GOLD = "`e[38;2;212;175;55m"
$SAGE = "`e[38;2;141;236;180m"
$CRIMSON = "`e[38;2;192;57;43m"
$RESET = "`e[0m"
$BOLD = "`e[1m"
$MUTED = "`e[38;2;74;74;90m"

$REPO_URL = "https://github.com/rsprajapati7/checkmate.git"
$BRANCH = "dev"
$INSTALL_DIR = Join-Path $env:USERPROFILE ".checkmate\cli"

Write-Host ""
Write-Host "${GOLD}${BOLD}  CheckMate CLI Installer${RESET}"
Write-Host "${MUTED}  ─────────────────────────────────────────${RESET}"
Write-Host ""

# --- Check prerequisites ---
try {
    $nodeVersion = (node -v 2>$null)
    if (-not $nodeVersion) { throw "not found" }
} catch {
    Write-Host "${CRIMSON}  Error: Node.js is not installed.${RESET}"
    Write-Host "  Install it from: ${GOLD}https://nodejs.org${RESET}"
    exit 1
}

$majorVersion = [int]($nodeVersion -replace 'v(\d+)\..*', '$1')
if ($majorVersion -lt 18) {
    Write-Host "${CRIMSON}  Error: Node.js v18+ is required (found $nodeVersion).${RESET}"
    exit 1
}

try {
    $npmVersion = (npm.cmd -v 2>$null)
    if (-not $npmVersion) { throw "not found" }
} catch {
    Write-Host "${CRIMSON}  Error: npm is not installed.${RESET}"
    exit 1
}

Write-Host "  ${SAGE}[1/5]${RESET} Checking prerequisites... Node $nodeVersion, npm $npmVersion"

# --- Clone or update the CLI source ---
Write-Host "  ${SAGE}[2/5]${RESET} Downloading CheckMate CLI..."

if (Test-Path $INSTALL_DIR) {
    Push-Location $INSTALL_DIR
    git pull origin $BRANCH --quiet 2>$null
    Pop-Location
} else {
    New-Item -ItemType Directory -Path (Split-Path $INSTALL_DIR) -Force | Out-Null
    git clone --branch $BRANCH --depth 1 --filter=blob:none --sparse $REPO_URL $INSTALL_DIR 2>$null
    Push-Location $INSTALL_DIR
    git sparse-checkout set checkmate-cli 2>$null
    Pop-Location
}

$CLI_DIR = Join-Path $INSTALL_DIR "checkmate-cli"
Push-Location $CLI_DIR

# --- Install dependencies ---
Write-Host "  ${SAGE}[3/5]${RESET} Installing dependencies..."
npm.cmd install --silent 2>$null

# --- Build TypeScript ---
Write-Host "  ${SAGE}[4/5]${RESET} Building CLI..."
npm.cmd run build --silent 2>$null

# --- Link globally ---
Write-Host "  ${SAGE}[5/5]${RESET} Linking global command..."
npm.cmd link --silent 2>$null

Pop-Location

Write-Host ""
Write-Host "${SAGE}${BOLD}  CheckMate CLI installed successfully!${RESET}"
Write-Host ""
Write-Host "  Run ${GOLD}checkmate setup${RESET} to configure your backend and API key."
Write-Host "  Run ${GOLD}checkmate${RESET}       to start the forensic shell."
Write-Host "  Run ${GOLD}checkmate --help${RESET} for all available commands."
Write-Host ""

# --- Ask if user wants to run setup now ---
$response = Read-Host "  Run setup wizard now? (Y/n)"
if ($response -eq '' -or $response -eq 'Y' -or $response -eq 'y') {
    checkmate setup
}
