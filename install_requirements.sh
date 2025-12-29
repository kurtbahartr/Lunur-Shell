#!/bin/bash
set -e

echo "Starting Lunur Shell requirements installation..."

# -------------------------
# Ensure required base tools
# -------------------------

ensure_pkg() {
  local pkg="$1"
  if ! pacman -Qq "$pkg" &>/dev/null; then
    echo "Installing $pkg..."
    sudo pacman -S --noconfirm --needed "$pkg"
  else
    echo "$pkg is already installed."
  fi
}

ensure_pkg git
ensure_pkg python
ensure_pkg base-devel

# -------------------------
# Locate script directory
# -------------------------

echo "Detecting script location..."
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
echo "Script directory: $SCRIPT_DIR"
cd "$SCRIPT_DIR"

PKG_DIR="$HOME/.config/Lunur-Shell/assets/packages/arch"
OFFICIAL_PKGS_FILE="$PKG_DIR/packages_official.txt"
AUR_PKGS_FILE="$PKG_DIR/packages_aur.txt"

# -------------------------
# Install official packages
# -------------------------

if [[ -f "$OFFICIAL_PKGS_FILE" ]]; then
  echo "Installing official Arch packages..."

  mapfile -t OFFICIAL_PKGS < <(grep -vE '^\s*#|^\s*$' "$OFFICIAL_PKGS_FILE")

  if ((${#OFFICIAL_PKGS[@]} > 0)); then
    sudo pacman -S --noconfirm --needed "${OFFICIAL_PKGS[@]}"
  else
    echo "No official packages to install."
  fi
else
  echo "Official package list not found: $OFFICIAL_PKGS_FILE"
fi

# -------------------------
# Install AUR packages
# -------------------------

if [[ -f "$AUR_PKGS_FILE" ]]; then
  echo "Installing AUR packages..."

  # Detect AUR helper
  AUR_HELPER=""
  for helper in yay paru trizen; do
    if command -v "$helper" &>/dev/null; then
      AUR_HELPER="$helper"
      break
    fi
  done

  if [[ -z "$AUR_HELPER" ]]; then
    echo "ERROR: No AUR helper found (yay / paru / trizen)."
    echo "Please install one before running this script."
    exit 1
  fi

  mapfile -t AUR_PKGS < <(grep -vE '^\s*#|^\s*$' "$AUR_PKGS_FILE")

  if ((${#AUR_PKGS[@]} > 0)); then
    "$AUR_HELPER" -S --noconfirm --needed "${AUR_PKGS[@]}"
  else
    echo "No AUR packages to install."
  fi
else
  echo "AUR package list not found: $AUR_PKGS_FILE"
fi

# -------------------------
# Python virtual environment
# -------------------------

echo "Setting up Python virtual environment..."

python -m venv venv
source venv/bin/activate

echo "Installing Python requirements..."
pip install --upgrade pip
pip install -r requirements.txt

echo "All Lunur Shell requirements installed successfully!"
