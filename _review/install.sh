#!/usr/bin/env bash
# ============================================================
# CheckMate CLI — One-Line Installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/rsprajapati7/checkmate/dev/install.sh | bash
#
# What this script does:
#   1. Checks for Node.js and npm
#   2. Clones the checkmate-cli source
#   3. Installs dependencies and builds
#   4. Links globally so `checkmate` works from anywhere
#   5. Runs the setup wizard for first-time configuration
# ============================================================

set -e

GOLD='\033[38;2;212;175;55m'
SAGE='\033[38;2;141;236;180m'
CRIMSON='\033[38;2;192;57;43m'
RESET='\033[0m'
BOLD='\033[1m'
MUTED='\033[38;2;74;74;90m'

REPO_URL="https://github.com/rsprajapati7/checkmate.git"
BRANCH="dev"
INSTALL_DIR="$HOME/.checkmate/cli"

echo ""
echo -e "${GOLD}${BOLD}  CheckMate CLI Installer${RESET}"
echo -e "${MUTED}  ─────────────────────────────────────────${RESET}"
echo ""

# --- Check prerequisites ---
if ! command -v node &> /dev/null; then
  echo -e "${CRIMSON}  Error: Node.js is not installed.${RESET}"
  echo -e "  Install it from: ${GOLD}https://nodejs.org${RESET}"
  exit 1
fi

NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
  echo -e "${CRIMSON}  Error: Node.js v18+ is required (found $(node -v)).${RESET}"
  exit 1
fi

if ! command -v npm &> /dev/null; then
  echo -e "${CRIMSON}  Error: npm is not installed.${RESET}"
  exit 1
fi

echo -e "  ${SAGE}[1/5]${RESET} Checking prerequisites... Node $(node -v), npm $(npm -v)"

# --- Clone or update the CLI source ---
echo -e "  ${SAGE}[2/5]${RESET} Downloading CheckMate CLI..."

if [ -d "$INSTALL_DIR" ]; then
  cd "$INSTALL_DIR"
  git pull origin "$BRANCH" --quiet 2>/dev/null || true
else
  mkdir -p "$(dirname "$INSTALL_DIR")"
  git clone --branch "$BRANCH" --depth 1 --filter=blob:none --sparse "$REPO_URL" "$INSTALL_DIR" 2>/dev/null
  cd "$INSTALL_DIR"
  git sparse-checkout set checkmate-cli 2>/dev/null
fi

cd "$INSTALL_DIR/checkmate-cli"

# --- Install dependencies ---
echo -e "  ${SAGE}[3/5]${RESET} Installing dependencies..."
npm install --silent 2>/dev/null

# --- Build TypeScript ---
echo -e "  ${SAGE}[4/5]${RESET} Building CLI..."
npm run build --silent 2>/dev/null

# --- Link globally ---
echo -e "  ${SAGE}[5/5]${RESET} Linking global command..."
npm link --silent 2>/dev/null

echo ""
echo -e "${SAGE}${BOLD}  CheckMate CLI installed successfully!${RESET}"
echo ""
echo -e "  Run ${GOLD}checkmate setup${RESET} to configure your backend and API key."
echo -e "  Run ${GOLD}checkmate${RESET}       to start the forensic shell."
echo -e "  Run ${GOLD}checkmate --help${RESET} for all available commands."
echo ""

# --- Ask if user wants to run setup now ---
read -p "  Run setup wizard now? (Y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
  checkmate setup
fi
