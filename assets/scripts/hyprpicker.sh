#!/bin/bash

# --- Globals ---
NOTIFY=true

# --- Dependency Check ---
check_dependencies() {
    local required=("hyprpicker" "wl-paste" "notify-send")
    local missing=()

    for cmd in "${required[@]}"; do
        if ! command -v "$cmd" &>/dev/null; then
            missing+=("$cmd")
        fi
    done

    if [ "${#missing[@]}" -ne 0 ]; then
        echo "Missing dependencies: ${missing[*]}"
        $NOTIFY && notify-send "HyprPicker Error" "Missing: ${missing[*]}"
        exit 1
    fi
}

send_notification() {
    local label="$1"
    local color_display="$2"

    $NOTIFY || return

    # Send notification
    notify-send -a "Hyprpicker" "$label" "$color_display"
}

# --- Picker Functions ---
pick_rgb() {
    hyprpicker -a -n -f rgb >/dev/null && sleep 0.1
    rgb_raw=$(wl-paste | tr -d '[:space:]')
    color="rgb(${rgb_raw})"
    send_notification "RGB color picked" "$color"
}

pick_hex() {
    hyprpicker -a -n -f hex >/dev/null && sleep 0.1
    color=$(wl-paste | tr -d '[:space:]')
    send_notification "HEX color picked" "$color"
}

pick_hsv() {
    hsv_raw=$(hyprpicker -n -f hsv | tr -d '[:space:]')
    echo -n "$hsv_raw" | wl-copy -n
    local formatted="hsv(${hsv_raw})"
    send_notification "HSV color picked" "$formatted"
}

# --- Usage Help ---
usage() {
    echo "Usage: $0 [--no-notify | -q] [-rgb|-hex|-hsv]"
    echo "  -q | --no-notify   Disable desktop notifications"
    echo "  -rgb               Pick color in RGB format"
    echo "  -hex               Pick color in HEX format"
    echo "  -hsv               Pick color in HSV format"
    exit 1
}

# --- Entry Point ---
main() {
    local mode=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -q|--no-notify)
                NOTIFY=false
                shift
                ;;
            -rgb|-hex|-hsv)
                mode="$1"
                shift
                ;;
            *)
                usage
                ;;
        esac
    done

    if [[ -z "$mode" ]]; then
        usage
    fi

    check_dependencies

    case "$mode" in
        -rgb) pick_rgb ;;
        -hex) pick_hex ;;
        -hsv) pick_hsv ;;
    esac
}

main "$@"

