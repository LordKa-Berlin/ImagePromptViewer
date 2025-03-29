# ImagePromptViewer

**Version:** 1.0.36.3a  
**Codename:** Master8 Alpha5  
**License:** [CC BY-NC 4.0](LICENSE)

## Description

**ImagePromptViewer** is an advanced image viewer for `.png`, `.jpg`, and `.jpeg` files. It extracts and displays embedded prompt data (such as *prompt*, *negative prompt*, and *generation settings*) from Stable Diffusion outputs.

It supports both:
- PNG text chunks (e.g., `info['parameters']`)
- JPEG EXIF tags (`UserComment`, tag `37510`)

The program displays the extracted data in structured fields, and allows filtering, copying, and navigation through folders containing images.

---

## Features

- 🖼 **View Images** in a resizable interface or fullscreen mode
- 🧠 **Extract Prompt Data** from PNG and JPEG files automatically
- 🔍 **Filter Images** by filename, prompt, negative prompt, or settings
- 🗑 **Delete Images** safely (with or without confirmation)
- 🖱 **Mouse and Keyboard Support** (navigation, zoom, copy)
- 🧰 **Debug Info** window with OS, Python version, screen resolution
- 🎨 **Dark Mode UI** with dynamic scaling for high-DPI screens
- 🧲 **Drag & Drop Support**: Drop an image to load its folder instantly

---

## Installation

Make sure you have Python 3.8+ installed.  
Dependencies will be installed automatically on first run (e.g. `Pillow`, `tkinterdnd2`, `piexif`, etc.).

To run:

```bash
python imagepromptviewer.py
Or make it executable and launch directly:

bash
chmod +x imagepromptviewer.py
./imagepromptviewer.py
How It Works
Select or drop an image.

The containing folder is scanned (optionally including subfolders).

Embedded prompts and metadata are parsed and displayed.

Navigate through all images using keyboard, mouse, or preview table.

Apply filters to find specific prompts or keywords.

Supported Formats
.png — Reads info['parameters'] or fallback tags

.jpg / .jpeg — Reads EXIF tag 37510 (UserComment with UNICODE prefix)

Keyboard Shortcuts
Key	Action
→ / ←	Next / Previous image
Delete	Delete current image
F11 / Esc	Exit fullscreen mode
Mouse	Scroll to navigate
License
This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0) license.

See LICENSE for more information.

Author
Developed by LordKa, 2025
Feel free to use and improve the code non-commercially. Feedback welcome!
