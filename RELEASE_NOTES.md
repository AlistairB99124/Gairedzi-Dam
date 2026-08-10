# Release Notes

## Unreleased

Client-facing improvements:
- Improved `update.bat` for ZIP-downloaded folders by adding incremental patch updates after a one-time baseline refresh.
- Added automatic fallback to full ZIP refresh when incremental patch update cannot be applied.

## 1.2.0 (2026-08-02)

Client-facing improvements:
- Added Setup and Run separation on Windows.
- Added automatic Elmer installation fallback from official binaries when winget does not provide Elmer.
- Added update.bat support for both git clones and ZIP-downloaded folders.
- Added stronger failure checks so missing outputs are reported explicitly.

Technical build:
- build metadata: 1.2.0+2026-08-02
- branch: main

## 1.1.x (2026-08-02)

- Initial one-click Windows launcher flow.
- Iterative fixes for Python detection, venv recovery, and Elmer path discovery.
