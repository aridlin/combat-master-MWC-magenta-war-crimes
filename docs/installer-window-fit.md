# Small-screen installer patch (v0.1.9-preview)

The old 1180×1400 startup window could be centered above a short monitor. The installer now limits its initial size to the current monitor and usable desktop area, leaves room for native window decorations, and positions its top inside that area. When the preferred size does not fit, the installer now asks the window manager to maximize it. This lets the desktop account for actual title-bar decorations and panels instead of relying only on a position requested before the window is managed. Large displays retain the preferred size. Existing vertical scrolling and manual resizing remain available.

Windows uses the cursor monitor and its taskbar-excluding work area, with DPI-aware client sizing and a final outer-window clamp. Linux uses the cursor monitor reported by Xinerama and intersects it with the current desktop work area; without those extensions it uses the X screen bounds with decoration margins. The bundled FT library is unchanged.

This is a frontend-only update to v0.1.8-preview. Public packages retain the exact previous backend, source assets and configuration. The frontend also includes the current source model-review status descriptions. Existing game assets, installer selections and backups are unchanged.

For an existing portable installer, close it and replace only `MWC-Installer` (Linux) or `MWC-Installer.exe` (Windows) with the matching file from the patch archive. Keep all other files and the existing state directory. Alternatively extract the complete updated package to a new directory. Revert by restoring the previous executable.

Validation: both targets compiled. The actual Linux GUI ran under Openbox with native decorations on isolated 1024×600 and 1280×720 desktops. The complete outer frame fitted each display, including its 21-pixel title bar, and the existing scrollbar exposed the installation controls. Screenshots were reviewed. The Windows executable opened maximized at both sizes under Wine; its reported outer rectangle includes four pixels of off-screen border. Native Windows and a physical KDE desktop were not tested for this hotfix. An isolated KWin virtual-output attempt failed in Xwayland DMA-BUF import before the app opened, so it supplies no acceptance evidence. See [the recorded results](installer-window-hotfix-verification.json).

Download the complete packages or the executable-only `MWC-Installer-window-fix.zip` from [v0.1.9-preview](https://github.com/aridlin/combat-master-MWC-magenta-war-crimes/releases/tag/v0.1.9-preview).
