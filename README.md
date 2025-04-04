# ImagePromptViewer

**Version:** 1.7.3.1-MASTER

## Overview
ImagePromptViewer is an intuitive tool designed for viewing and managing PNG and JPEG images, extracting embedded metadata (Prompt, Negative Prompt, Settings), and filtering your image collection based on comprehensive criteria.

---

## Main Features

### 📌 Top Bar
- **Options Menu:** Adjust UI scaling (0.0-2.0, requires restart).
- **Exit Button:** Close the application.
- **Always on Top:** Keep the window above other applications.
- **Help Button (?):** Open the User Guide window.

### 🎛️ Left Panel – Advanced Filters
- **Prompt Filter:** Refine images based on keyword inclusion/exclusion.
- **Date Filter:** Filter images by creation dates or specific periods.
- **File Size Filter:** Set minimum and maximum file size thresholds.
- **Action Buttons:**
  - **Apply Filter:** Execute filter settings.
  - **Clear:** Reset individual filters.
  - **Reset All:** Return all filters to default.

### 🛠️ Right Panel – Main Controls
- **Keyword Filter:** Filter images by keywords in filename, prompt, negative prompt, or settings.
- **Folder Management:**
  - Browse, select, view, or delete images.
  - "Delete immediately" option available.
- **Subfolder & Sorting:** Search subfolders and toggle sorting by creation date.
- **Highlighting:** Highlight special syntax like `<Lora>` or `(weights)`.

### 🖼️ Image Display & Navigation
- **Central Image Viewer:** Clickable area to enter fullscreen.
- **Drag & Drop Canvas:** Easily load image folders.
- **Navigation Controls:**
  - Back, Next, and Fullscreen with intuitive keyboard shortcuts.
- **Image Scaling:**
  - Manual slider (10%-100%).
  - Automatic scaling option available.

### 📝 Metadata Extraction
- Display and copy **Prompt**, **Negative Prompt**, and **Settings** metadata.

### 📂 Folder List
- Preview and manage filtered image thumbnails.

---

## 🚀 Fullscreen Mode
- Advanced viewing experience with image navigation, metadata visibility toggling, and deletion options.
- Quick shortcuts for efficient workflow.

---

## 🎯 Keyboard Shortcuts

### Main Window
- **Right Arrow:** Next image  
- **Left Arrow:** Previous image  
- **F11:** Exit fullscreen  
- **Delete:** Delete current image  
- **Mouse Wheel:** Navigate through images

### Fullscreen Mode
- **Esc / F11:** Close fullscreen  
- **Ctrl + Mouse Wheel:** Zoom image - comes later
- **P:** Toggle prompt visibility

---

## 📸 Screenshots
```markdown
![Screenshot1](url-to-screenshot-1)
![Screenshot2](url-to-screenshot-2)
```

---

## ⚠️ Known Issues
- Fullscreen view does not work with folders containing over 4000 image files (including subfolders). Use filters to reduce the number of files temporarily. This issue is under investigation—any solutions are welcome!
- There are still several design flaws being addressed progressively.
- Currently, only the last parentheses are captured for highlighting weights.
- Some extraction logics may include unintended text not related to the prompt.
- Window dragging may not function optimally on multi-monitor setups, especially beyond resolutions of 1920x1080.

---

## 🔮 Planned Improvements
- Customizable syntax highlighting settings.
- Improved highlighting capturing all parentheses.
- Enhanced logic processing for text extraction.
- Image zoom function in full screen mode
- Filtering out chunk snipes.

---

## 📌 Important Notice
If scaling does not fit your monitor, use the manual adjustment option available in the Options Menu!

---

## 💡 Tips
- Quickly load folders by dragging and dropping images.
- Combine multiple filters for powerful image management.
- Customize scaling for optimal visibility on your display.

---

## 🙌 Feedback & Contributions

Feel free to report any bugs or suggest improvements.  
If you have a better solution or idea, please share it—contributions are always welcome!

---

Enjoy using **ImagePromptViewer**! 🎉

