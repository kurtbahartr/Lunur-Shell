Version 0.4.2
https://github.com/dianaw353/Lunur-Shell/releases/tag/v0.4.2
------------------------------------------------------------

# Fixes
- Update maximum character width for notificatons.
- Fix lints and reformat in the context of importing components.
- Power Profile widget now properly reflects the current profile.
- Fix the way system tray icons are displayed.
- Fix calculator orders of operations in launcher.
- Fix `GTK_IS_ADJUSTMENT` errors.
- Improve the startup time for the `hyprsunset` QS tile.
- Fix scrolled windows appearing like they were being resized upon first interaction.
- Fix an issue where there would be multiple instances of the brightness service would be started. This also fixes the flickering OSD when adjusting brightness from the quick settings.

# Features
- The Bluetooth tile in the quick settings is now updated to reveal device list and allow interaction with other Bluetooth devices.
- The WiFi tile in the quick settings is now updated to reveal a list of WiFi networks and allow interaction with other WiFi networks. You can also authenticate while connecting to a new/unsaved network!

# Misc
- Migrate Python package management to `uv`.
- Remove unused imports in applicable components.
- Refactor `widget_settings` for easier readability.

Version 0.4.1
https://github.com/dianaw353/Lunur-Shell/releases/tag/v0.4.1
-------------------------------------------------------------

# Fixes
- Make dependency checks stricter.
- Don't escape out of the Python virtual environment.
- Add dependency checks where necessary.
- Menus no longer need ESC to close.
  - This means you can now click outside of the widget to close it.

# Features
- Add support for various calculations in launcher.
- Add audio mixer for volume control in the quick settings.
- Add slider for microphone to the quick settings.
- Add a new QS tile to control `hyprsunset`.

# Misc
- Get rid of the dependency for `setproctitle`.
- Drop update checking mechanism for the bar.
- Drop SCSS pre-compilation for smart scss compilation.
- Divide quick settings components into smaller parts.
- Remove obsolete instructions from the installation instructions.
- Change QS tile layout from 3x1 to 2x2.
- Lots of performance and stability improvements.

Version 0.4.0
https://github.com/dianaw353/Lunur-Shell/releases/tag/v0.4.0
-----------------------------------------------------------------------

# Features
- Refactor system tray to use revealer instead of popover.
- Add OSD for volume and brightness.
- Refactor the logic for slide to reveal animation.
- Implement a basic quick settings panel.
- Do some improvements regarding icon resolution.
- Add player popup for player widget.
- Add a flag for logging debug info.
- Make screen record and screenshot enableable.
- Add a view button to screenshot notifications.

# Fixes
- Fix the cases where text isn't being copied and clipboard doesn't consistently open respectively.
- Break description line if it gets too long in app launcher.
- Remove horizontal scrollbar for app launcher and keyboard shortcuts windows.
- Put shortcut descriptions in keyboard shortcuts window into their own lines.
- Record system audio instead of microphone when recording screen.
- The date and time component now updates instantly upon time zone change.
- Fix curves for when the bar is set to be at the bottom of the display.
- Fix the screenshot commands for them to work properly.

# Misc
- Change media backend from MPRIS to playerctl.
- Tweak padding for the shell components.
- Add artist name to the player widget.
- Update the installer script.
- Optimize power profiles widget for faster initialization. (The startup is now ~50x faster!)

Version 0.3.0
https://github.com/dianaw353/Lunur-Shell/releases/tag/v0.3.0
-----------------------------------------------------------------------

# Features
- Add Power menu options
- Add screenshot widget
- Add recorder widget

# Misc
- collapsible group style improvements

Version 0.2.1
https://github.com/dianaw353/Lunur-Shell/releases/tag/v0.2.1
-----------------------------------------------------------------------

# Fixes
- Make buttons inside collapsible group able to preform their action

Version 0.2.0
https://github.com/dianaw353/Lunur-Shell/releases/tag/v0.2.0
-----------------------------------------------------------------------

# Featues
- Add support to configure icon size and slide direction for mpris
- Add Collapsible groups

# Fixes
- Many system tray fixes
- Notifications widget dosent get cut off by the screen
- Network widget work with vpn 

# Misc
- Refactor notifications
- Added onto update script
- Update package dependency list
- Drop json5 dependency
- Few other tweaks
 
Version 0.1.0
https://github.com/dianaw353/Lunur-Shell/releases/tag/v0.1.0
-----------------------------------------------------------------------
- Initial release with CI.
