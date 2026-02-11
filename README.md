# InvaderZIM 👽
<center><img width="811" height="734" alt="image" src="https://github.com/user-attachments/assets/9477fd36-b92b-4f82-bf52-5101d8f9626f" /></center>

Convert HTML websites (stored as ZIP files) into ZIM archives for offline viewing. Perfect for archiving websites, documentation, or creating offline-readable content.

## What is this?

InvaderZIM is a simple GUI tool that takes a ZIP file containing a website (HTML, CSS, images, etc.) and converts it into a `.zim` file. ZIM files are compressed archives designed for storing content for offline use, commonly used by apps like Kiwix.

## Requirements

- **Linux** or **Windows with WSL** (Windows Subsystem for Linux)
- Python 3.6+
- `zimwriterfs` (installation instructions below)

## Windows Users: WSL Setup

If you're on Windows, you'll need to set up WSL first. Don't worry—it's easier than it sounds!

### 1. Install WSL

Open PowerShell as Administrator and run:

```powershell
wsl --install
```

Restart your computer when prompted.

### 2. Set up Ubuntu

After restart, Ubuntu will automatically open and ask you to create a username and password. Choose something you'll remember!

### 3. Install Python and required tools

In your Ubuntu terminal, run these commands one by one:

```bash
sudo apt update
sudo apt install python3 python3-tk zim-tools -y
```

### 4. Get InvaderZIM

```bash
cd ~
git clone https://github.com/noosed/InvaderZIM.git
cd InvaderZIM
```

### 5. Access your Windows files

Your Windows files are accessible at `/mnt/c/` in WSL. For example:
- `C:\Users\YourName\Downloads` becomes `/mnt/c/Users/YourName/Downloads`

## Linux Users: Installation

Just install the dependencies:

```bash
sudo apt update
sudo apt install python3 python3-tk zim-tools -y
```

Clone the repository:

```bash
git clone https://github.com/yourusername/InvaderZIM.git
cd InvaderZIM
```

## How to Use

### 1. Run the program

```bash
python3 InvaderZIM.py
```

A window will open with a simple interface.

### 2. Select your ZIP file

Click **Browse** next to "ZIP Archive" and select your website ZIP file.

The ZIP should contain your website files with an `index.html` somewhere inside.

### 3. Fill in the details

- **Title**: Name of your website (auto-filled from filename)
- **Language**: Language code (e.g., `eng` for English)
- **Description**: Short description of the content

### 4. Choose output location

Click **Browse** next to "Output ZIM File" to choose where to save the `.zim` file.

### 5. Click "Convert to .ZIM"

Watch the console log as your ZIM file is created. You'll get a popup when it's done!

## Tips

- The "Rewrite HTML links" option is enabled by default and recommended. It fixes absolute file paths that might break in the ZIM archive.
- Conversion time depends on the size of your website. Larger sites take longer.
- The console log shows detailed progress. Look for green "SUCCESS" messages!

## Viewing Your ZIM Files

Download [Kiwix](https://www.kiwix.org/) to open and browse your ZIM archives offline.

## Troubleshooting

**"zimwriterfs not found" error**
- Run: `sudo apt install zim-tools`

**Can't find my ZIP file in WSL (Windows users)**
- Remember: `C:\` becomes `/mnt/c/` in WSL
- Example: Browse to `/mnt/c/Users/YourName/Downloads`

**Program won't start**
- Make sure you installed `python3-tk`: `sudo apt install python3-tk`

## Created by

[github.com/noosed](https://github.com/noosed)

## License

Free to use and modify!
