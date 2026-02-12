#!/usr/bin/env python3
"""
Install zimwriterfs via apt or zim-tools
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import os
import sys
import threading
import zipfile
import shutil
import tempfile
import subprocess
import queue
import re
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import os
import sys
import threading
import zipfile
import shutil
import tempfile
import subprocess
import queue
import re
from pathlib import Path
from typing import Optional

VERSION = "3.1.0-WSL"
CONFIG_FILE = os.path.expanduser("~/.zimpacker_config.txt")

current_zip_path: Optional[str] = None
conversion_thread: Optional[threading.Thread] = None
status_queue = queue.Queue()
is_converting = False


def log(msg, tag="INFO"):
    """Thread-safe logging"""
    status_queue.put(("log", f"[{tag}] {msg}"))


def update_status(msg):
    """Update status label"""
    status_queue.put(("status", msg))


def verify_zimwriterfs():
    """Verify zimwriterfs is available"""
    try:
        result = subprocess.run(
            ["zimwriterfs", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            log(f"Found zimwriterfs: {version}", "OK")
            return True
        else:
            log("zimwriterfs verification failed", "ERROR")
            return False
    except FileNotFoundError:
        log("zimwriterfs not found in PATH!", "ERROR")
        log("Install with: sudo apt install zim-tools", "ERROR")
        return False
    except Exception as e:
        log(f"Error verifying zimwriterfs: {e}", "ERROR")
        return False


def extract_zip(zip_path, extract_dir):
    """Extract ZIP file to directory"""
    log(f"Extracting: {os.path.basename(zip_path)}")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    log(f"Extracted to: {extract_dir}")


def detect_site_root(extract_dir):
    """
    Detect the actual website root directory.
    If ZIP contains a single top-level folder, use that.
    """
    items = os.listdir(extract_dir)
    if len(items) == 1:
        single_item = os.path.join(extract_dir, items[0])
        if os.path.isdir(single_item):
            log(f"Using nested folder: {items[0]}")
            return single_item

    log("Using extraction directory as root")
    return extract_dir


def find_index_html(root_dir):
    """
    Find index.html in the site root.
    Returns (absolute_path, relative_path_from_root)
    """
    # First check root
    root_index = os.path.join(root_dir, "index.html")
    if os.path.exists(root_index):
        log("Found index.html at root")
        return root_index, "index.html"

    # Search recursively
    log("Searching for index.html recursively...")
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if "index.html" in filenames:
            abs_path = os.path.join(dirpath, "index.html")
            rel_path = os.path.relpath(abs_path, root_dir)
            log(f"Found index.html at: {rel_path}")
            return abs_path, rel_path

    return None, None


def rewrite_html_links(html_path):
    """Rewrite links in HTML file to be relative"""
    try:
        with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Remove file:/// protocols
        content = re.sub(r'file:///[^\s\'"]*', '', content)

        # Convert absolute paths to relative
        content = re.sub(r'(href|src)=["\']/', r'\1="', content)

        with open(html_path, 'w', encoding='utf-8', errors='ignore') as f:
            f.write(content)

        return True
    except Exception as e:
        log(f"Warning: Failed to rewrite {html_path}: {e}", "WARN")
        return False


def rewrite_all_html_files(root_dir):
    """Rewrite all HTML files in the site"""
    log("Rewriting HTML links...")
    count = 0
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.lower().endswith('.html'):
                html_path = os.path.join(dirpath, filename)
                if rewrite_html_links(html_path):
                    count += 1
    log(f"Rewrote {count} HTML files")


def run_zimwriterfs(site_root, output_zim, welcome_path, title, description, language):
    """
    Run zimwriterfs to create ZIM file.
    Returns (success, stdout, stderr)
    
    Mandatory args: welcome, illustration, language, name, title, description, creator, publisher
    """
    import base64
    
    # Generate safe name from title
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', title).lower()
    
    # Actual 48x48 transparent PNG
    png_48x48_b64 = "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAAEElEQVR42u3BAQ0AAADCoPdPbQ8HFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB8GQgAAAFR6jJSAAAAAElFTkSuQmCC"
    
    illustration_path = os.path.join(site_root, "zimpacker_illustration.png")
    
    with open(illustration_path, 'wb') as f:
        f.write(base64.b64decode(png_48x48_b64))
    
    illustration_rel = "zimpacker_illustration.png"
    log(f"Created illustration: {illustration_rel}")
    
    # ALL mandatory arguments plus skip-libmagic-check
    cmd = [
        "zimwriterfs",
        f"--welcome={welcome_path}",
        f"--illustration={illustration_rel}",
        f"--language={language}",
        f"--name={safe_name}",
        f"--title={title}",
        f"--description={description if description else title}",
        f"--creator=zimpacker",
        f"--publisher=zimpacker",
        "--skip-libmagic-check",  # Skip magic file requirement
        site_root,
        output_zim
    ]

    log(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode == 0:
            log("ZIM creation successful!", "SUCCESS")
            return True, result.stdout, result.stderr
        else:
            log(f"ZIM creation failed (exit code {result.returncode})", "ERROR")
            if result.stderr:
                log(f"STDERR: {result.stderr}", "ERROR")
            return False, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        log("ZIM creation timed out!", "ERROR")
        return False, "", "Process timed out after 10 minutes"
    except Exception as e:
        log(f"ZIM creation error: {e}", "ERROR")
        return False, "", str(e)


def convert_zip_to_zim(zip_path, output_zim, title, description, language, rewrite_links):
    """Main conversion pipeline"""
    global is_converting

    temp_dir = None
    try:
        is_converting = True
        update_status("Converting...")

        # Verify zimwriterfs
        log("Verifying zimwriterfs installation...")
        if not verify_zimwriterfs():
            status_queue.put(("error", "zimwriterfs not found!\n\nInstall with:\nsudo apt install zim-tools"))
            return False

        # Create temp directory
        temp_dir = tempfile.mkdtemp(prefix="zimpacker_")
        log(f"Created temp directory: {temp_dir}")

        # Extract ZIP
        extract_zip(zip_path, temp_dir)

        # Detect site root
        site_root = detect_site_root(temp_dir)

        # Find index.html
        index_abs, index_rel = find_index_html(site_root)
        if not index_abs:
            log("ERROR: No index.html found in ZIP!", "ERROR")
            status_queue.put(("error", "No index.html found in the ZIP file!"))
            return False

        # Rewrite links if enabled
        if rewrite_links:
            rewrite_all_html_files(site_root)

        # Run zimwriterfs
        update_status("Creating ZIM file...")
        success, stdout, stderr = run_zimwriterfs(
            site_root, output_zim, index_rel, title, description, language
        )

        if not success:
            status_queue.put(("error", f"zimwriterfs failed:\n\n{stderr}"))
            return False

        # Success
        log(f"ZIM file created: {output_zim}", "SUCCESS")
        update_status("Complete!")
        status_queue.put(("success", output_zim))
        return True

    except Exception as e:
        log(f"Conversion error: {e}", "ERROR")
        status_queue.put(("error", str(e)))
        return False

    finally:
        # Cleanup temp directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                log("Cleaned up temp directory")
            except Exception as e:
                log(f"Failed to cleanup temp: {e}", "WARN")

        is_converting = False


class ZimPackerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Invader ZIM {VERSION}")
        self.root.geometry("800x700")
        self.root.resizable(True, True)

        # Variables
        self.zip_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.title_var = tk.StringVar()
        self.language_var = tk.StringVar(value="eng")
        self.description_var = tk.StringVar()
        self.rewrite_var = tk.BooleanVar(value=True)

        self.setup_ui()
        self.start_queue_processor()

        # Verify zimwriterfs on startup
        threading.Thread(target=verify_zimwriterfs, daemon=True).start()

    def setup_ui(self):
        """Setup the GUI layout"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        row = 0

        # Title
        title_label = ttk.Label(main_frame, text=f"Invader ZIM {VERSION}",
                                font=("Arial", 16, "bold"))
        title_label.grid(row=row, column=0, columnspan=3, pady=(0, 5))
        row += 1

        subtitle_label = ttk.Label(main_frame,
                                   text="Convert website ZIPs to ZIM format",
                                   foreground="gray")
        subtitle_label.grid(row=row, column=0, columnspan=3, pady=(0, 15))
        row += 1

        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        row += 1

        # ZIP Input
        ttk.Label(main_frame, text="Input ZIP File:",
                  font=("Arial", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=5)
        row += 1

        ttk.Entry(main_frame, textvariable=self.zip_path, width=60).grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(main_frame, text="Browse", command=self.browse_zip).grid(
            row=row, column=2, sticky=tk.E)
        row += 1

        # Metadata section
        ttk.Label(main_frame, text="Metadata:",
                  font=("Arial", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=(15, 5))
        row += 1

        # Title
        ttk.Label(main_frame, text="Title:").grid(row=row, column=0, sticky=tk.W)
        ttk.Entry(main_frame, textvariable=self.title_var, width=60).grid(
            row=row, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        row += 1

        # Language
        ttk.Label(main_frame, text="Language:").grid(row=row, column=0, sticky=tk.W)
        ttk.Entry(main_frame, textvariable=self.language_var, width=10).grid(
            row=row, column=1, sticky=tk.W, pady=2)
        row += 1

        # Description
        ttk.Label(main_frame, text="Description:").grid(row=row, column=0, sticky=tk.W)
        ttk.Entry(main_frame, textvariable=self.description_var, width=60).grid(
            row=row, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        row += 1

        # Options
        ttk.Label(main_frame, text="Options:",
                  font=("Arial", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=(15, 5))
        row += 1

        ttk.Checkbutton(main_frame, text="Rewrite HTML links (remove file:// and absolute paths)",
                        variable=self.rewrite_var).grid(
            row=row, column=0, columnspan=3, sticky=tk.W)
        row += 1

        # Output
        ttk.Label(main_frame, text="Output ZIM File:",
                  font=("Arial", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=(15, 5))
        row += 1

        ttk.Entry(main_frame, textvariable=self.output_path, width=60).grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(main_frame, text="Browse", command=self.browse_output).grid(
            row=row, column=2, sticky=tk.E)
        row += 1

        # Convert button
        self.convert_btn = ttk.Button(main_frame, text="Convert to .ZIM",
                                      command=self.start_conversion)
        self.convert_btn.grid(row=row, column=0, columnspan=3, pady=20)
        row += 1

        # Status
        self.status_label = ttk.Label(main_frame, text="Ready",
                                      foreground="blue", font=("Arial", 10))
        self.status_label.grid(row=row, column=0, columnspan=3, pady=5)
        row += 1

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        row += 1

        # Log area
        ttk.Label(main_frame, text="Console Log:",
                  font=("Arial", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=(10, 5))
        row += 1

        self.log_text = scrolledtext.ScrolledText(main_frame, height=15,
                                                  state='disabled', wrap='word')
        self.log_text.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.rowconfigure(row, weight=1)
        row += 1

        # Configure tags for colored log messages
        self.log_text.tag_config("ERROR", foreground="red")
        self.log_text.tag_config("SUCCESS", foreground="green")
        self.log_text.tag_config("WARN", foreground="orange")
        self.log_text.tag_config("OK", foreground="blue")
        
        # Credit at bottom left
        row += 1
        credit_label = ttk.Label(main_frame, text="created by github.com/noosed", 
                                foreground="gray", font=("Arial", 8))
        credit_label.grid(row=row, column=0, sticky=tk.W, pady=(5, 0))

    def browse_zip(self):
        """Open file dialog to select ZIP"""
        filepath = filedialog.askopenfilename(
            title="Select ZIP file",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]
        )

        if filepath:
            self.handle_zip_selection(filepath)

    def browse_output(self):
        """Open file dialog to select output ZIM"""
        filepath = filedialog.asksaveasfilename(
            title="Save ZIM file as",
            defaultextension=".zim",
            filetypes=[("ZIM files", "*.zim"), ("All files", "*.*")]
        )

        if filepath:
            self.output_path.set(filepath)

    def handle_zip_selection(self, filepath):
        """Handle ZIP file selection"""
        global current_zip_path

        if not filepath.lower().endswith('.zip'):
            self.log_message("Error: File must be a ZIP archive!", "ERROR")
            return

        if not os.path.exists(filepath):
            self.log_message("Error: File does not exist!", "ERROR")
            return

        current_zip_path = filepath
        self.zip_path.set(filepath)

        # Auto-populate title from filename
        basename = os.path.splitext(os.path.basename(filepath))[0]
        if not self.title_var.get():
            self.title_var.set(basename)

        # Auto-populate output ZIM path
        if not self.output_path.get():
            output_dir = os.path.dirname(filepath)
            output_path = os.path.join(output_dir, basename + ".zim")
            self.output_path.set(output_path)

        self.log_message(f"Loaded ZIP: {os.path.basename(filepath)}", "OK")

    def start_conversion(self):
        """Start conversion in background thread"""
        global conversion_thread

        if is_converting:
            self.log_message("Conversion already in progress!", "WARN")
            return

        if not current_zip_path:
            self.log_message("No ZIP file selected!", "ERROR")
            return

        output_zim = self.output_path.get()
        title = self.title_var.get()
        description = self.description_var.get()
        language = self.language_var.get()
        rewrite = self.rewrite_var.get()

        if not output_zim:
            self.log_message("Please specify output ZIM file!", "ERROR")
            return

        if not title:
            self.log_message("Please specify a title!", "ERROR")
            return

        # Clear log
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')

        # Start conversion thread
        conversion_thread = threading.Thread(
            target=convert_zip_to_zim,
            args=(current_zip_path, output_zim, title, description, language, rewrite),
            daemon=True
        )
        conversion_thread.start()

        # Update UI
        self.convert_btn.config(state='disabled')
        self.progress.start(10)

    def log_message(self, msg, tag="INFO"):
        """Add message to log"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, msg + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def start_queue_processor(self):
        """Start processing status queue"""
        self.process_queue()

    def process_queue(self):
        """Process status messages from worker thread"""
        try:
            while not status_queue.empty():
                msg_type, *args = status_queue.get_nowait()

                if msg_type == "log":
                    msg = args[0]
                    # Extract tag from message
                    tag = "INFO"
                    for possible_tag in ["ERROR", "SUCCESS", "WARN", "OK"]:
                        if f"[{possible_tag}]" in msg:
                            tag = possible_tag
                            break
                    self.log_message(msg, tag)

                elif msg_type == "status":
                    msg = args[0]
                    self.status_label.config(text=msg)

                elif msg_type == "success":
                    output_path = args[0]
                    self.convert_btn.config(state='normal')
                    self.progress.stop()
                    self.status_label.config(text="Complete!", foreground="green")
                    messagebox.showinfo("Success",
                                        f"ZIM file created successfully!\n\n{output_path}")

                elif msg_type == "error":
                    error_msg = args[0]
                    self.convert_btn.config(state='normal')
                    self.progress.stop()
                    self.status_label.config(text="Error!", foreground="red")
                    messagebox.showerror("Conversion Error", error_msg)

        except queue.Empty:
            pass

        # Schedule next check
        self.root.after(100, self.process_queue)


def main():
    root = tk.Tk()
    app = ZimPackerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
