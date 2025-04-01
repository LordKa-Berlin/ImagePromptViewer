# ImagePromptViewer (Preview Version)

**Version**: 1.4.0.d4 (Development Branch: `entwicklung`)  
**Date**: 2025-04-01  
**Internal Designation**: Master8 Alpha10  
**Author**: LordKa-Berlin  

---

## Note: This is a Preview Version
This version of `ImagePromptViewer` is currently in the development branch `entwicklung` and represents a preview release. It is not yet fully stable or feature-complete. Some functionalities are still in progress, and there are known limitations (see [Known Issues](#known-issues)). Feedback and bug reports are welcome!

---

## Overview
`ImagePromptViewer` is a Python-based tool for viewing and managing image files (PNG and JPEG). It extracts metadata from images—specifically text chunks such as Prompt, Negative Prompt, and Settings—and provides a user-friendly GUI with advanced filtering options. It was designed to efficiently analyze and organize AI-generated images (e.g., from Stable Diffusion).

### Main Features
- **Image Display**: Dynamic display of PNG and JPEG images with scalable previews.
- **Metadata Extraction**: 
  - PNG: From `info['parameters']` or fallback keys (`prompt`, `metadata`, `description`).
  - JPEG: From EXIF tag 37510 (`UserComment`) with support for UNICODE decoding.
- **Filtering**: Advanced filters for Prompt, Filename, Negative Prompt, Settings, File Date, and File Size.
- **Fullscreen Mode**: Display of the current image with metadata and control options.
- **Folder Management**: Supports loading folders and subfolders with history functionality.
- **Deletion**: Moves images to the recycle bin with an optional immediate delete feature.

---

## Installation

### Prerequisites
- **Python**: Version 3.7 or higher
- **Operating System**: Windows, macOS, or Linux

### Dependencies
The script automatically installs missing Python libraries. Required packages:
- `tkinterdnd2` (Drag-and-Drop)
- `Pillow` (Image Processing)
- `screeninfo` (Monitor Resolution)
- `send2trash` (Recycle Bin Functionality)
- `piexif` (EXIF Data Processing)

Install manually with:
```bash
pip install tkinterdnd2 Pillow screeninfo send2trash piexif
