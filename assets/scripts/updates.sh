#!/bin/bash

TERMINAL="kitty"  # Default terminal

# Detect Arch or Arch-based distros
DISTRO=""
if [[ -f /etc/os-release ]]; then
    source /etc/os-release
    if [[ "$ID" == "arch" || "$ID_LIKE" == *"arch"* ]]; then
        DISTRO="arch"
    fi
fi

if [[ -z "$DISTRO" ]]; then
    echo "Error: Unsupported distro."
    exit 1
fi

aur_helper="yay"
if command -v paru &>/dev/null; then
    aur_helper="paru"
fi

check_arch_updates() {
    local official_updates=0
    local aur_updates=0

    if command -v checkupdates &>/dev/null; then
        official_updates=$(checkupdates 2>/dev/null | wc -l)
    fi

    if command -v "$aur_helper" &>/dev/null; then
        aur_updates=$($aur_helper -Qum 2>/dev/null | wc -l)
    fi

    local total_updates=$((official_updates + aur_updates))

    echo
    echo "Scanning for updates..."
    echo

    echo "󰣇 Official updates available: $official_updates"
    echo "󰮯 AUR updates available: $aur_updates"
    echo

    if (( total_updates > 0 )); then
        echo "Running full system update..."
        echo
        $aur_helper -Syu --noconfirm
    else
        echo "✅ Your system is up to date."
    fi

    echo
    read -n 1 -p "Press any key to close..."
}

execute_in_terminal() {
    local command="$1"

    if [[ ! "$TERMINAL" =~ ^[a-zA-Z0-9._-]+$ ]]; then
        echo "Error: Terminal name contains invalid characters."
        exit 1
    fi

    if ! command -v "$TERMINAL" >/dev/null 2>&1; then
        echo "Error: Terminal '$TERMINAL' not found in PATH."
        exit 1
    fi

    case "$(basename "$TERMINAL")" in
        kitty)     "$TERMINAL" --title systemupdate sh -c "${command}" ;;
        alacritty) "$TERMINAL" --title systemupdate -e sh -c "${command}" ;;
        wezterm)   "$TERMINAL" start --title systemupdate -- sh -c "${command}" ;;
        *)         "$TERMINAL" sh -c "${command}" ;;
    esac
}

# Export function and variables for terminal shell
export -f check_arch_updates
export aur_helper

command='
figlet "System Updates"

check_arch_updates
'

execute_in_terminal "$command"
