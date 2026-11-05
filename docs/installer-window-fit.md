# Small-screen installer patch (v0.1.4-preview)

The old 1180×1400 startup window could be centered above a short monitor. The installer now limits its initial size to the current monitor and usable desktop area, leaves room for native window decorations, and positions its top inside that area. Large displays retain the preferred size. Existing vertical scrolling and manual resizing remain available.

Windows uses the cursor monitor and its taskbar-excluding work area, with DPI-aware client sizing and a final outer-window clamp. Linux uses the cursor monitor reported by Xinerama and intersects it with the current desktop work area; without those extensions it uses the X screen bounds with decoration margins. The bundled FT library is unchanged.

This is a frontend-only update to v0.1.3-preview. Public packages retain the exact previous backend, source assets and configuration; experimental hand-weight work is not included. Existing game assets, installer selections and backups are unchanged.

For an existing portable installer, close it and replace only `MWC-Installer` (Linux) or `MWC-Installer.exe` (Windows) with the matching file from the patch archive. Keep all other files and the existing state directory. Alternatively extract the complete updated package to a new directory. Revert by restoring the previous executable.

Validation: both targets compiled. The Linux GUI was opened and measured on isolated 1024×600, 1280×720, 1366×768, 1920×1080 at 144 DPI, and 3840×2160 displays, with simulated top panels. Window bounds remained within the usable area; screenshots and the existing scrollbar were checked. Windows native testing is recorded separately in the release notes; compilation alone is not native Windows validation.
