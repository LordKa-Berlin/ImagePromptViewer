
---

# ImagePromptViewer - User Guide (Version 1.7.3.0-MASTER)

## Overview

This program allows you to view PNG and JPEG images, extract embedded metadata (Prompt, Negative Prompt, Settings), filter images based on various criteria, and manage them with navigation and deletion options. Below is a detailed guide to its features.

---

## Main Window Features

### 1. Top Bar Buttons
- **Options**: Opens a window to adjust the UI scaling factor (0.0-2.0). Requires a restart to apply changes.
- **Exit**: Closes the program.
- **?**: Opens this help window.
- **Always on Top Checkbox**: Keeps the window on top of others when checked.

### 2. Left Panel - Filter Settings

#### Prompt Filter
- **All words must match**: Filters images where all entered keywords are in the Prompt.
- **Any word**: Filters images with at least one keyword in the Prompt.
- **Exclude word**: Excludes images with any of the keywords in the Prompt.
- **None of the words**: Filters images with none of the keywords in the Prompt.

#### Date Filter
- **Checkboxes**: Filter by creation date (e.g., "Created this week", "Within 1 year").
- **Not older than (days)**: Enter days to filter images newer than that period.
- **Older than (days)**: Enter days to filter images older than that period.
- **Between dates (YYYY-MM-DD)**: Enter start and end dates to filter images within that range.

#### File Size (KB)
- **Min**: Enter minimum file size in KB.
- **Max**: Enter maximum file size in KB.

#### Buttons
- **Apply Filter**: Applies all filter settings from this panel.
- **Clear**: Resets filter inputs in this panel.
- **Reset All**: Clears all filters and resets to default settings.

### 3. Right Panel - Main Controls

#### Filter Section
- **Filter Button**: Applies the keyword filter entered in the text field.
- **Text Field**: Enter keywords (comma-separated) to filter images.
- **Clear Button**: Clears the keyword filter.
- **Whole Word Checkbox**: Filters for exact word matches only.
- **Checkboxes ("Filename", "Prompt", "Negative Prompt", "Settings")**: Select which fields to search for keywords.

#### Folder Section
- **Folder path Dropdown**: Select or enter a folder path (history saved).
- **Select folder Button**: Opens a dialog to choose a folder.
- **Select image Button**: Opens a dialog to select a specific image.
- **View image Button**: Opens the current image in your default viewer.
- **Delete image Button**: Moves the current image to the recycle bin.
- **Delete immediately Checkbox**: Skips confirmation when deleting if checked.

#### Subfolder Section
- **Search subfolders Checkbox**: Includes subfolders when loading images.
- **ASC/DESC Button**: Toggles sort order (ascending/descending) by creation date.
- **Lora highlight Checkbox**: Highlights text between `< >` in white.
- **Weighting highlight Checkbox**: Highlights text between `( )` in light blue.

### 4. Image Display
- **Central Area**: Shows the current image. Click to open fullscreen mode.
- **"Drop Image Here" Canvas**: Drag and drop an image to load its folder.

### 5. Navigation and Scaling
- **Back Button**: Shows the previous image (Shortcut: Left Arrow).
- **Fullscreen Button**: Opens the current image in fullscreen (Shortcut: F11 to close).
- **Next Button**: Shows the next image (Shortcut: Right Arrow).
- **Image Scaling Slider**: Adjusts image size (10-100%). Disabled when "Default" is checked.
- **Default Checkbox**: Uses automatic scaling based on monitor size if checked.

### 6. Text Fields
- **Prompt, Negative Prompt, Settings**: Display extracted metadata from the image.
- **copy Prompt, copy Negative, copy Settings Buttons**: Copy the respective text to the clipboard.

### 7. Folder List
- **Load folder list Button**: Shows/hides a preview list of filtered images with thumbnails.

#### Shortcuts (Main Window)
- **Right Arrow**: Next image  
- **Left Arrow**: Previous image  
- **F11**: Close fullscreen mode  
- **Delete**: Delete current image (with confirmation unless "delete immediately" is checked)  
- **Mouse Wheel on Image**: Navigate forward (scroll down) or backward (scroll up)

---

## Fullscreen Mode Features

### 1. Top Buttons
- **Delete image**: Deletes the current image (with confirmation unless "delete immediately" is checked).
- **delete immediately Checkbox**: Skips confirmation when deleting if checked.
- **Close**: Exits fullscreen mode (Shortcut: Esc or F11).
- **View image**: Opens the image in your default viewer.
- **Copy image name**: Copies the filename to the clipboard.
- **Copy image path**: Copies the full path to the clipboard.

### 2. Right Panel
- **Hide prompt Button (or "P" key)**: Toggles visibility of Prompt, Negative Prompt, and Settings.
- **Text Fields**: Display Prompt, Negative Prompt, and Settings with copy buttons.

### 3. Image Area
- **Click**: Closes fullscreen mode.
- **Mouse Wheel**: Navigate forward (scroll down) or backward (scroll up).

#### Shortcuts (Fullscreen Mode)
- **Esc or F11**: Close fullscreen  
- **Right Arrow**: Next image  
- **Left Arrow**: Previous image  
- **Ctrl + Mouse Wheel**: Zoom in/out  
- **Delete**: Delete current image  
- **P**: Toggle Prompt visibility

---

## Tips
- **Drag and drop** an image to quickly load its folder.
- Use **filters** to narrow down large image collections (all criteria are combined with AND logic).
- Adjust **scaling in Options** for better readability on high-resolution monitors.

---

Enjoy using ImagePromptViewer!

---