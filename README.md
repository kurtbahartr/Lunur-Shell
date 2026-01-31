# Lunur-Shell


<div align=center>
  
![GitHub last commit](https://img.shields.io/github/last-commit/dianaw353/Lunur-Shell?style=for-the-badge&labelColor=101418&color=9ccbfb)
![GitHub Repo stars](https://img.shields.io/github/stars/dianaw353/Lunur-Shell?style=for-the-badge&labelColor=101418&color=b9c8da)
![GitHub repo size](https://img.shields.io/github/repo-size/dianaw353/Lunur-Shell?style=for-the-badge&labelColor=101418&color=d3bfe6)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/dianaw353/Lunur-Shell?style=for-the-badge&labelColor=101418&color=CBA6F7)

</div>

> [!WARNING]  
> This is in active development

## Screenshots

<table align="center">
  <tr>
    <td colspan="4"><img src="assets/screenshots/main.png"></td>
  </tr>
</table>

As of 8/3/25

## Installation

> [!NOTE]
> You need a functioning Hyprland installation.

Clone the repo:

```
  git clone https://github.com/dianaw353/Lunur-Shell.git ~/.config/Lunur-Shell
  cd ~/.config/Lunur-Shell/
```

### Option 1: Automated Installation

#### Step 1: Run the script

Run the following script

```
  ./install_requirements.sh
```

#### Step 2: Run Lunur-Shell

```
  uv run main.py
```

### Option 2: Manual Installation

#### Step 1: Install system packages

```
  yay -S --needed - < ~/.config/Lunur-Shell/assets/packages/arch/packages_official.txt
  yay -S --needed - < ~/.config/Lunur-Shell/assets/packages/arch/packages_aur.txt
```

#### Step 2: Run Lunur-Shell 

`uv` is a Python package and project manager in whitch it will download and install python dependencies and run the shell

```
  uv run main.py
```

## Roadmap

- [x] App Launcher
- [x] Workspaces
- [x] Window Title
- [x] Date/Time
- [x] Calender
- [x] Battery
- [x] Network Manager
- [x] Bluetooth Manager
- [x] Clipboard Manager
- [x] Power Manager
- [x] Power Menu
- [x] Color Picker
- [ ] QuickSettings (in progress)
- [x] Notifications
- [x] System Tray
- [x] Keybind Cheat Sheet
- [x] Screen Recorder (basic)
- [x] Screenshots (basic)
- [ ] OCR
- [ ] OSD (volume and brightness added, more to come soon)
- [x] Emoji Picker
- [ ] Theme Switcher
- [ ] Wallpaper Switcher
- [ ] Media Player (half done)
- [ ] Matugen theme (in progress)

## Sister Projects

- [Lunur-Dots](https://github.com/dianaw353/Lunur-Dots)
- [Lunur-Wallpaper](https://github.com/dianaw353/Lunur-Wallpapers)
