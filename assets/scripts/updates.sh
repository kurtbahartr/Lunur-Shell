#!/bin/bash

DISTRO=""
TERMINAL="$(echo "$TERM" | sed 's/^xterm-//')"

SHELL_LOG="$HOME/.lunur-shell.log"
SHELL_DIR="$HOME/.config/Lunur-Shell"

REPO="dianaw353/Lunur-Shell"
REPO_URL="https://github.com/$REPO.git"

MODE="stable"
REPO_BRANCH="main"

lunur_shell_packages="assets/packages/arch"

REMOTE_PKG_TMPDIR=""

system_official_updates=0
system_aur_updates=0

detect_distro() {
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        if [[ "$ID" == "arch" || "$ID_LIKE" == *"arch"* || "$ID" == "cachyos" ]]; then
            DISTRO="arch"
        fi
    fi
}

check_arch_updates() {
    local aur_helper="yay"
    if command -v paru &>/dev/null; then
        aur_helper="paru"
    fi

    figlet "System Updates"

    echo ""
    echo "Scanning for updates..."
    echo ""

    system_official_updates=$(checkupdates 2>/dev/null | wc -l)
    system_aur_updates=$($aur_helper -Qum 2>/dev/null | wc -l)

    echo ""
    echo "Official updates available: $system_official_updates"
    echo "AUR updates available: $system_aur_updates"
    echo ""

    local total=$((system_official_updates + system_aur_updates))
    if (( total == 0 )); then
        echo "No updates available."
    else
        echo "Updates are available."
    fi
    echo ""
}

check_lunur_shell() {
    figlet "Lunur_Ecosystem"

    if [[ ! -d "$SHELL_DIR" ]]; then
        echo ""
        echo "Lunur-Shell directory not found at $SHELL_DIR."
        echo "Please clone the repository first."
        read -n1 -rsp "Press any key to exit..."
        exit 1
    fi

    cd "$SHELL_DIR" || {
        echo "Failed to change directory to $SHELL_DIR."
        read -n1 -rsp "Press any key to exit..."
        exit 1
    }
}

arch_apply_system_updates() {
    echo "[System] Applying system updates..."

    local aur_helper="yay"
    if command -v paru &>/dev/null; then
        aur_helper="paru"
    fi

    sudo pacman -Syu --noconfirm
    $aur_helper -Syu --noconfirm

    echo "[System] Updates complete."
    echo ""
}

fetch_remote_package_list() {
    local branch_or_tag="$1"
    local file_path="$2"
    local dest_path="$3"
    local raw_url="https://raw.githubusercontent.com/$REPO/$branch_or_tag/$file_path"
    curl -sfL "$raw_url" -o "$dest_path" || echo "Warning: Could not fetch $file_path from $branch_or_tag"
}

print_remote_package_check_summary() {
    echo ""
    echo "Scanning package dependencies for Lunur Shell..."
    echo ""
}

count_missing_packages() {
    local count=0
    local full_path

    for list_file in packages_official.txt packages_aur.txt packages_python.txt; do
        full_path="$REMOTE_PKG_TMPDIR/$list_file"
        if [[ -f "$full_path" ]]; then
            while IFS= read -r pkg; do
                [[ -z "$pkg" || "$pkg" =~ ^# ]] && continue
                if ! pacman -Q "$pkg" &>/dev/null; then
                    ((count++))
                fi
            done < "$full_path"
        fi
    done

    echo "$count"
    return 0
}

arch_install_missing_packages_remote() {
    local aur_helper="yay"
    if command -v paru &>/dev/null; then
        aur_helper="paru"
    fi

    local any_missing=0

    install_missing_packages_remote() {
        local list_file="$1"
        local type="$2"
        local pkg_cmd="$3"

        local full_path="$REMOTE_PKG_TMPDIR/$list_file"
        if [[ -f "$full_path" ]]; then
            while IFS= read -r pkg; do
                [[ -z "$pkg" || "$pkg" =~ ^# ]] && continue
                if ! pacman -Q "$pkg" &>/dev/null; then
                    any_missing=1
                    $pkg_cmd "$pkg"
                fi
            done < "$full_path"
        fi
    }

    install_missing_packages_remote "packages_official.txt" "official" "sudo pacman -S --noconfirm"
    install_missing_packages_remote "packages_aur.txt" "AUR" "$aur_helper -S --noconfirm"
    install_missing_packages_remote "packages_python.txt" "Python (via AUR)" "$aur_helper -S --noconfirm"

    if (( any_missing == 0 )); then
        echo "No missing packages to install."
        echo ""
    else
        echo "Package installation complete."
        echo ""
    fi
}

apply_updates() {
    local updates_available=0
    local target_ref=""
    local local_version=""
    local repo_updates_available=0

    if [[ "$MODE" == "stable" ]]; then
        echo ""
        echo "Checking for latest stable release..."
        target_ref=$(curl -s "https://api.github.com/repos/$REPO/releases/latest" | grep -Po '"tag_name": "\K.*?(?=")')
        local_version_file=".latest_release"
        if [[ -f "$local_version_file" ]]; then
            local_version=$(cat "$local_version_file")
        fi

        if [[ "$local_version" != "$target_ref" ]]; then
            echo "New stable release available: $target_ref"
            repo_updates_available=1
        else
            echo "Already up to date (release $local_version)."
        fi
    elif [[ "$MODE" == "rolling" ]]; then
        target_ref="$REPO_BRANCH"
        echo ""
        echo "Checking rolling branch ($target_ref) for updates..."
        git fetch origin "$target_ref"
        LOCAL_HASH=$(git rev-parse HEAD)
        REMOTE_HASH=$(git rev-parse origin/"$target_ref")
        if [[ "$LOCAL_HASH" == "$REMOTE_HASH" ]]; then
            echo "Lunur-Shell is up to date (branch $target_ref)."
        else
            echo "Updates available on branch $target_ref."
            repo_updates_available=1
        fi
    else
        echo "Invalid mode: $MODE"
        exit 1
    fi

    REMOTE_PKG_TMPDIR=$(mktemp -d)
    fetch_remote_package_list "$target_ref" "$lunur_shell_packages/packages_official.txt" "$REMOTE_PKG_TMPDIR/packages_official.txt"
    fetch_remote_package_list "$target_ref" "$lunur_shell_packages/packages_aur.txt" "$REMOTE_PKG_TMPDIR/packages_aur.txt"
    fetch_remote_package_list "$target_ref" "$lunur_shell_packages/packages_python.txt" "$REMOTE_PKG_TMPDIR/packages_python.txt"

    print_remote_package_check_summary
    missing_count=$(count_missing_packages)
    echo "Number of new packages to install: $missing_count"

    if (( system_official_updates > 0 || system_aur_updates > 0 || repo_updates_available == 1 || missing_count > 0 )); then
        updates_available=1
    fi

    if (( updates_available == 0 )); then
        echo "No updates available. System packages and/or shell packages are up to date."
        rm -rf "$REMOTE_PKG_TMPDIR"
        return 0
    fi

    echo "Would you like to apply these updates? [y/N]"
    read -r -p "> " confirm

    case "$confirm" in
        [yY][eE][sS]|[yY])
            echo ""
            echo "Applying updates..."

            if (( system_official_updates > 0 || system_aur_updates > 0 )); then
                arch_apply_system_updates
            else
                echo "[System] No system updates to apply."
                echo ""
            fi

            echo "To safely update the shell it is required to temporarily kill the shell."
            pkill Lunur-Shell
             
            if (( repo_updates_available == 1 )); then
                if [[ "$MODE" == "stable" ]]; then
                    echo "Updating Lunur-Shell to latest stable release..."
                    tmp_dir=$(mktemp -d)
                    curl -sL "https://github.com/$REPO/archive/refs/tags/$target_ref.tar.gz" | tar xz -C "$tmp_dir"
                    rm -rf "$SHELL_DIR"
                    mv "$tmp_dir"/"$(echo "$REPO" | sed 's/.*\///')"-"$(echo "$target_ref" | sed 's/^v//')" "$SHELL_DIR"
                    echo "$target_ref" > "$SHELL_DIR/.latest_release"
                else
                    echo "Updating Lunur-Shell rolling branch..."
                    cd "$SHELL_DIR"
                    git reset --hard HEAD
                    git pull origin "$REPO_BRANCH"
                fi
            else
                echo "[Shell] Lunur-Shell is already up to date."
                echo ""
            fi

            if (( missing_count > 0 )); then
                arch_install_missing_packages_remote
            else
                echo "[Packages] No missing packages to install."
                echo ""
            fi

            echo "[Shell] Remember to reload the shell! If you're using Lunur-Dots, the keybind is Super+R."
            echo "All applicable updates have been applied."
            ;;
        *)
            echo "Update canceled by user."
            ;;
    esac

    rm -rf "$REMOTE_PKG_TMPDIR"
}

execute_in_new_terminal() {
    local term="$TERMINAL"

    if [[ ! "$term" =~ ^[a-zA-Z0-9._-]+$ ]]; then
        echo "Error: Terminal name contains invalid characters."
        exit 1
    fi

    if ! command -v "$term" &>/dev/null; then
        echo "Error: Terminal '$term' not found."
        exit 1
    fi

    local tmp_script
    tmp_script=$(mktemp)

    cat > "$tmp_script" <<EOF
#!/bin/bash
$(declare -f check_arch_updates)
$(declare -f check_lunur_shell)
$(declare -f arch_apply_system_updates)
$(declare -f fetch_remote_package_list)
$(declare -f print_remote_package_check_summary)
$(declare -f count_missing_packages)
$(declare -f arch_install_missing_packages_remote)
$(declare -f apply_updates)

MODE="$MODE"
SHELL_DIR="$SHELL_DIR"
REPO="$REPO"
REPO_BRANCH="$REPO_BRANCH"
lunur_shell_packages="$lunur_shell_packages"

check_arch_updates
check_lunur_shell
apply_updates

read -n1 -rsp "Press any key to exit..."
EOF

    chmod +x "$tmp_script"

    case "$(basename "$term")" in
        kitty)
            "$term" --title systemupdate sh -c "$tmp_script; rm -f $tmp_script"
            ;;
        alacritty)
            "$term" --title systemupdate -e sh -c "$tmp_script; rm -f $tmp_script"
            ;;
        wezterm)
            "$term" start --title systemupdate -- sh -c "$tmp_script; rm -f $tmp_script"
            ;;
        *)
            "$term" sh -c "$tmp_script; rm -f $tmp_script"
            ;;
    esac
}

USE_NEW_TERMINAL=0

while [[ $# -gt 0 ]]; do
    case $1 in
        stable)
            MODE="stable"
            shift
            ;;
        rolling)
            MODE="rolling"
            shift
            ;;
        --new-terminal)
            USE_NEW_TERMINAL=1
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [stable|rolling] [--new-terminal]"
            exit 0
            ;;
        *)
            echo "Invalid argument: $1"
            echo "Usage: $0 [stable|rolling] [--new-terminal]"
            exit 1
            ;;
    esac
done

if [[ -z "$DISTRO" ]]; then
    detect_distro
fi

if [[ "$DISTRO" != "arch" ]]; then
    echo "Error: Only Arch Linux and its derivatives are supported."
    exit 1
fi

if (( USE_NEW_TERMINAL )); then
    execute_in_new_terminal
else
    check_arch_updates
    check_lunur_shell
    apply_updates
    read -n1 -rsp "Press any key to exit..."
fi
