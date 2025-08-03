#!/bin/bash

# Install Git if not present.
echo "Checking if Git is already installed..."
if ! command -v git > /dev/null; then
  echo "Git was not found. Installing..."
  sudo pacman -S --noconfirm git
else
  echo "Git is already installed!"
fi

# Install an AUR helper if there's none installed.
echo "Checking if a supported AUR helper (yay/paru/aura) is installed..."
if ! command -v yay paru aura > /dev/null; then
  echo "No AUR helper found. Installing yay..."
  cd ~
  git clone https://aur.archlinux.org/yay yay-aur
  cd yay-aur
  sudo pacman -S --noconfirm --needed base-devel
  makepkg -siC
  cd -
  echo "yay has been successfully installed!"
else
  echo "A supported AUR helper is already installed!"
fi

# Try to find the AUR helper installed on this system.
echo "Setting up environment..."
if command -v yay > /dev/null; then
  echo "Detected helper: yay"
  AUR_HELPER="yay"
  echo "yay is known to use -S for AUR packages."
  AUR_PARAM="-S"
elif command -v paru > /dev/null; then
  echo "Detected helper: paru"
  AUR_HELPER="paru"
  echo "paru is known to use -S for AUR packages."
  AUR_PARAM="-S"
elif command -v aura > /dev/null; then
  echo "Detected helper: aura"
  AUR_HELPER="aura"
  echo "aura is known to use -A for AUR packages."
  AUR_PARAM="-A"
fi

# Find where the script is located.
# Source: https://stackoverflow.com/a/246128
echo "Detecting where the script is located..."
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
echo "Detected path: $SCRIPT_DIR"

# Install packages from official repository.
echo "Installing requirements listed for official repositories using pacman..."
sudo pacman -S --needed --noconfirm $(cat $SCRIPT_DIR/assets/packages/arch/packages_official.txt) $(cat $SCRIPT_DIR/assets/packages/arch/packages_python.txt | grep ijson)

# Install packages from AUR.
echo "Installing requirements listed for AUR using $AUR_HELPER..."
$AUR_HELPER $AUR_PARAM --needed --noconfirm $(cat $SCRIPT_DIR/assets/packages/arch/packages_aur.txt) $(cat $SCRIPT_DIR/assets/packages/arch/packages_python.txt | sed '/ijson/d' )

echo "All done!"
