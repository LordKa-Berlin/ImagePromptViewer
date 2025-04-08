---
```markdown
# ImagePromptViewer

**Version**: 1.8.0.0  
**Release Date**: 2025-04-08  
**Internal Designation**: Master9 Stable  
**Author**: LordKa-Berlin  

---

## Overview

`ImagePromptViewer` is a Python-based tool to display and manage image files (PNG and JPEG) that have embedded **prompt data**—typically generated by **AI tools** such as **Stable Diffusion**, **AUTOMATIC1111**, or **Forge**.

It reads embedded text data (prompt, negative prompt, generation settings) and shows this information alongside each image. A fullscreen mode is included and supports prompt viewing, syntax highlighting for LoRAs and weights, and various filter options.

This is a **stable release** — tested, reliable, and ready for public use.

---

## Important Note about AI-Generated Prompts

If you have an **AI-generated image** whose prompt cannot yet be read by ImagePromptViewer, feel free to **send the image** along with **information about the tool or generator used** to:

📧 **lordkaberlin@gmail.com**

ImagePromptViewer is still in its early development phase — more AI tools and formats will be supported in future updates.

---

## Main Features

- **Image Display**: View PNG and JPEG images with adjustable preview sizes.
- **Metadata Extraction**:
  - PNG: From `info['parameters']`, or `prompt`, `description`, etc.
  - JPEG: EXIF tag `UserComment` (with support for various encodings).
- **Prompt Parsing**: Prompt, Negative Prompt, and Settings are shown separately.
- **Filter Options**: Filter by Prompt, Filename, Negative Prompt, Settings, File Date, and File Size.
- **Fullscreen Mode**: Includes metadata display, copy/delete options.
- **Syntax Highlighting**: Highlights weights and LoRA syntax in the prompt display.
- **Folder Navigation**: Load folders and subfolders. History for recently opened folders is supported.
- **Image Deletion**: Moves files to recycle bin or deletes them directly.

---

## Screenshots

### 🖼️ Main Window  
![Main Window](screenshots/imagepromptviewer-mainscreen.png)

### 🖼️ Fullscreen Mode  
![Fullscreen Mode](screenshots/imagepromptviewer-fullscreen.png)

### 🖼️ UI Scaling  
![UI Scaling](screenshots/User-Interface-Scaling.png)

---

## Installation

### Requirements

- **Python** 3.7+
- **OS**: Windows, macOS, Linux

### Install Dependencies
```bash
pip install tkinterdnd2 Pillow screeninfo send2trash piexif
```

### Start the Program
```bash
python ImagePromptViewer-1.8.0.0.py
```

---

## Detailed Features

### Prompt Parsing
- Supports parsing embedded prompt blocks.
- Extracts prompt, negative prompt, and settings.

### Filters
- Prompt filters: Match all / any / exclude keywords.
- Filename, Negative Prompt, and Settings filters.
- File size and file date filters.
- Visual filter indicator when filters are active.

### Fullscreen
- Displays large image with prompt overlay.
- Supports file deletion, copying filename/path, navigation.
- Scroll support for long prompt texts.

---

## Known Limitations

- Date filters such as "between two dates" are still in progress.
- Handling of huge image folders (>4000 images) may affect performance.
- Some AI tools might still use unknown formats.

---

## Contribution and Feedback

We welcome contributions and suggestions!

- Report bugs via [GitHub Issues](https://github.com/LordKa-Berlin/ImagePromptViewer/issues)
- Email feedback: **lordkaberlin@gmail.com**

---

*Developed by LordKa-Berlin*  
*Licensed under Attribution-NonCommercial 4.0 International (see LICENSE.md)*
```

---
