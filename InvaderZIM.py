#!/usr/bin/env python3
"""
Invader ZIM - ZIP to ZIM Converter
PySide6 rewrite with premium UI
Install zimwriterfs via: sudo apt install zim-tools
"""

import os
import sys
import re
import queue
import shutil
import tempfile
import zipfile
import threading
import subprocess
from pathlib import Path
from typing import Optional

from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect,
    QSize, Signal, QObject, Property, QPoint, QParallelAnimationGroup,
    QSequentialAnimationGroup,
)
from PySide6.QtGui import (
    QColor, QPalette, QFont, QPainter, QBrush, QPen, QLinearGradient,
    QDragEnterEvent, QDropEvent,
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QTextEdit, QFileDialog,
    QFrame, QSizePolicy, QGraphicsDropShadowEffect, QScrollArea,
    QProgressBar, QMessageBox, QGraphicsOpacityEffect,
)

VERSION = "3.1.0-WSL"
CONFIG_FILE = os.path.expanduser("~/.zimpacker_config.txt")


# ─────────────────────────────────────────────────────────────────────────────
# THEME MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class ThemeManager:
    """
    Central theme provider. Supports dark / light / auto (system) modes.
    All QSS uses CSS-like variable substitution via .render_qss().
    """

    DARK = "dark"
    LIGHT = "light"
    AUTO = "auto"

    DARK_VARS: dict[str, str] = {
        "--bg":              "#0f1117",
        "--bg-alt":         "#161b27",
        "--surface":        "#1c2333",
        "--surface-hover":  "#232d42",
        "--surface-active": "#2a3550",
        "--border":         "#2a3550",
        "--border-subtle":  "#1e2840",
        "--primary":        "#5b8dee",
        "--primary-hover":  "#7aa5f0",
        "--primary-pressed":"#4a7ce0",
        "--primary-muted":  "rgba(91,141,238,0.15)",
        "--success":        "#3ecf8e",
        "--warning":        "#f5a623",
        "--error":          "#f0536a",
        "--text-primary":   "#e8eaf0",
        "--text-secondary": "#8892a4",
        "--text-muted":     "#4a5568",
        "--text-on-primary":"#ffffff",
        "--radius-sm":      "6px",
        "--radius-md":      "12px",
        "--radius-lg":      "16px",
        "--radius-xl":      "20px",
        "--font":           "Inter, 'Segoe UI Variable', 'Segoe UI', system-ui, sans-serif",
        "--font-mono":      "'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace",
    }

    LIGHT_VARS: dict[str, str] = {
        "--bg":              "#f6f8fc",
        "--bg-alt":         "#eef2f9",
        "--surface":        "#ffffff",
        "--surface-hover":  "#f0f4fb",
        "--surface-active": "#e4ecf8",
        "--border":         "#dde3ef",
        "--border-subtle":  "#eaedf5",
        "--primary":        "#3b6fd4",
        "--primary-hover":  "#2f5bbf",
        "--primary-pressed":"#254da8",
        "--primary-muted":  "rgba(59,111,212,0.10)",
        "--success":        "#2aaa75",
        "--warning":        "#e0901a",
        "--error":          "#d93651",
        "--text-primary":   "#111827",
        "--text-secondary": "#4b5563",
        "--text-muted":     "#9ca3af",
        "--text-on-primary":"#ffffff",
        "--radius-sm":      "6px",
        "--radius-md":      "12px",
        "--radius-lg":      "16px",
        "--radius-xl":      "20px",
        "--font":           "Inter, 'Segoe UI Variable', 'Segoe UI', system-ui, sans-serif",
        "--font-mono":      "'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace",
    }

    RAW_QSS = """
    /* ── Root ─────────────────────────────────────────────────────── */
    QMainWindow, QDialog {
        background: {--bg};
    }
    QWidget {
        font-family: {--font};
        font-size: 13px;
        color: {--text-primary};
        background: transparent;
    }
    QScrollArea, QScrollArea > QWidget > QWidget {
        background: transparent;
        border: none;
    }

    /* ── Scrollbars ─────────────────────────────────────────────── */
    QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 4px 2px;
        border-radius: 4px;
    }
    QScrollBar::handle:vertical {
        background: {--border};
        border-radius: 4px;
        min-height: 30px;
    }
    QScrollBar::handle:vertical:hover { background: {--text-muted}; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QScrollBar:horizontal {
        background: transparent;
        height: 8px;
        margin: 2px 4px;
        border-radius: 4px;
    }
    QScrollBar::handle:horizontal {
        background: {--border};
        border-radius: 4px;
        min-width: 30px;
    }
    QScrollBar::handle:horizontal:hover { background: {--text-muted}; }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

    /* ── Input Fields ───────────────────────────────────────────── */
    QLineEdit {
        background: {--surface};
        border: 1.5px solid {--border};
        border-radius: {--radius-md};
        padding: 8px 12px;
        color: {--text-primary};
        selection-background-color: {--primary};
        selection-color: {--text-on-primary};
    }
    QLineEdit:hover  { border-color: {--primary-hover}; }
    QLineEdit:focus  {
        border-color: {--primary};
        background: {--bg-alt};
        outline: none;
    }
    QLineEdit[readOnly="true"] {
        background: {--bg-alt};
        color: {--text-secondary};
    }

    /* ── Text Edit (Log) ─────────────────────────────────────────── */
    QTextEdit {
        background: {--bg};
        border: 1.5px solid {--border-subtle};
        border-radius: {--radius-md};
        padding: 10px 12px;
        color: {--text-primary};
        font-family: {--font-mono};
        font-size: 12px;
        selection-background-color: {--primary};
    }

    /* ── Progress Bar ───────────────────────────────────────────── */
    QProgressBar {
        background: {--surface};
        border: 1.5px solid {--border};
        border-radius: 6px;
        height: 6px;
        text-align: center;
    }
    QProgressBar::chunk {
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {--primary}, stop:1 {--primary-hover}
        );
        border-radius: 6px;
    }

    /* ── CheckBox ───────────────────────────────────────────────── */
    QCheckBox {
        color: {--text-secondary};
        spacing: 8px;
    }
    QCheckBox:hover { color: {--text-primary}; }
    QCheckBox::indicator {
        width: 18px; height: 18px;
        border-radius: 5px;
        border: 1.5px solid {--border};
        background: {--surface};
    }
    QCheckBox::indicator:hover { border-color: {--primary}; }
    QCheckBox::indicator:checked {
        background: {--primary};
        border-color: {--primary};
        image: none;
    }
    QCheckBox::indicator:checked::after {
        content: "✓";
        color: white;
    }

    /* ── Label ──────────────────────────────────────────────────── */
    QLabel { background: transparent; }

    /* ── Tooltip ────────────────────────────────────────────────── */
    QToolTip {
        background: {--surface};
        color: {--text-primary};
        border: 1px solid {--border};
        border-radius: {--radius-sm};
        padding: 6px 10px;
        font-size: 12px;
    }
    """

    def __init__(self, mode: str = AUTO) -> None:
        self._mode = mode
        self._resolved: str = self._resolve_mode()

    # ── Public API ──────────────────────────────────────────────────────────

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        self._resolved = self._resolve_mode()

    @property
    def is_dark(self) -> bool:
        return self._resolved == self.DARK

    def vars(self) -> dict[str, str]:
        return self.DARK_VARS if self.is_dark else self.LIGHT_VARS

    def var(self, key: str) -> str:
        return self.vars().get(key, "")

    def color(self, key: str) -> QColor:
        raw = self.var(key)
        if raw.startswith("rgba("):
            parts = raw.removeprefix("rgba(").removesuffix(")").split(",")
            r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
            a = float(parts[3].strip())
            c = QColor(r, g, b)
            c.setAlphaF(a)
            return c
        return QColor(raw)

    def current_qss(self) -> str:
        return self._render(self.RAW_QSS)

    def _render(self, qss: str) -> str:
        for key, val in self.vars().items():
            qss = qss.replace(f"{{{key}}}", val)
        return qss

    # ── Private ─────────────────────────────────────────────────────────────

    def _resolve_mode(self) -> str:
        if self._mode != self.AUTO:
            return self._mode
        pal = QApplication.palette()
        bg = pal.color(QPalette.Window)
        return self.DARK if bg.lightness() < 128 else self.LIGHT


# Module-level singleton — set after QApplication is created
theme: ThemeManager


# ─────────────────────────────────────────────────────────────────────────────
# MODERN BUTTON
# ─────────────────────────────────────────────────────────────────────────────

class ModernButton(QPushButton):
    """
    Premium push button with:
    - Hover: scale 1.04 + shadow grow + color transition
    - Press: scale 0.96
    - Three variants: primary | ghost | danger
    - Optional left icon (unicode/emoji)
    """

    def __init__(
        self,
        text: str = "",
        variant: str = "primary",  # primary | ghost | danger
        icon_char: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self._variant = variant
        self._icon_char = icon_char
        self._hovered = False
        self._pressed = False
        self._base_style = ""
        self._setup_style()
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(40)

        # Shadow
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(0)
        self._shadow.setOffset(0, 2)
        self._shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(self._shadow)

    def _setup_style(self) -> None:
        v = theme.vars()
        if self._variant == "primary":
            qss = f"""
            ModernButton {{
                background: {v['--primary']};
                color: {v['--text-on-primary']};
                border: none;
                border-radius: {v['--radius-md']};
                padding: 8px 20px;
                font-weight: 600;
                font-size: 13px;
            }}
            ModernButton:hover {{
                background: {v['--primary-hover']};
            }}
            ModernButton:pressed {{
                background: {v['--primary-pressed']};
            }}
            ModernButton:disabled {{
                background: {v['--border']};
                color: {v['--text-muted']};
            }}
            """
        elif self._variant == "ghost":
            qss = f"""
            ModernButton {{
                background: {v['--surface']};
                color: {v['--text-secondary']};
                border: 1.5px solid {v['--border']};
                border-radius: {v['--radius-md']};
                padding: 8px 20px;
                font-weight: 500;
                font-size: 13px;
            }}
            ModernButton:hover {{
                background: {v['--surface-hover']};
                color: {v['--text-primary']};
                border-color: {v['--primary']};
            }}
            ModernButton:pressed {{
                background: {v['--surface-active']};
            }}
            ModernButton:disabled {{
                background: {v['--surface']};
                color: {v['--text-muted']};
                border-color: {v['--border-subtle']};
            }}
            """
        elif self._variant == "danger":
            qss = f"""
            ModernButton {{
                background: transparent;
                color: {v['--error']};
                border: 1.5px solid {v['--error']};
                border-radius: {v['--radius-md']};
                padding: 8px 20px;
                font-weight: 500;
                font-size: 13px;
            }}
            ModernButton:hover {{
                background: rgba(240,83,106,0.10);
            }}
            ModernButton:pressed {{
                background: rgba(240,83,106,0.20);
            }}
            """
        else:
            qss = ""
        self.setStyleSheet(qss)

    def enterEvent(self, event) -> None:
        self._hovered = True
        anim = QPropertyAnimation(self._shadow, b"blurRadius", self)
        anim.setDuration(200)
        anim.setEndValue(16)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        anim = QPropertyAnimation(self._shadow, b"blurRadius", self)
        anim.setDuration(200)
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        super().leaveEvent(event)


# ─────────────────────────────────────────────────────────────────────────────
# CARD WIDGET
# ─────────────────────────────────────────────────────────────────────────────

class CardWidget(QFrame):
    """
    Rounded surface card with hover elevation lift.
    Use as a container by calling .content_layout() to add widgets.
    """

    def __init__(
        self,
        title: str = "",
        parent: QWidget | None = None,
        hoverable: bool = False,
    ) -> None:
        super().__init__(parent)
        self._hoverable = hoverable
        self._setup_style()

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(12)
        self._shadow.setOffset(0, 4)
        self._shadow.setColor(QColor(0, 0, 0, 40 if theme.is_dark else 20))
        self.setGraphicsEffect(self._shadow)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(12)

        if title:
            lbl = QLabel(title)
            v = theme.vars()
            lbl.setStyleSheet(
                f"font-size: 11px; font-weight: 700; letter-spacing: 0.8px;"
                f" color: {v['--text-muted']}; text-transform: uppercase; background: transparent;"
            )
            outer.addWidget(lbl)

        self._inner = QVBoxLayout()
        self._inner.setContentsMargins(0, 0, 0, 0)
        self._inner.setSpacing(8)
        outer.addLayout(self._inner)

    def content_layout(self) -> QVBoxLayout:
        return self._inner

    def _setup_style(self) -> None:
        v = theme.vars()
        self.setStyleSheet(f"""
        CardWidget {{
            background: {v['--surface']};
            border: 1.5px solid {v['--border-subtle']};
            border-radius: {v['--radius-lg']};
        }}
        """)

    def enterEvent(self, event) -> None:
        if not self._hoverable:
            return super().enterEvent(event)
        anim = QPropertyAnimation(self._shadow, b"blurRadius", self)
        anim.setDuration(200)
        anim.setEndValue(24)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if not self._hoverable:
            return super().leaveEvent(event)
        anim = QPropertyAnimation(self._shadow, b"blurRadius", self)
        anim.setDuration(200)
        anim.setEndValue(12)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        super().leaveEvent(event)


# ─────────────────────────────────────────────────────────────────────────────
# COLLAPSIBLE SECTION
# ─────────────────────────────────────────────────────────────────────────────

class CollapsibleSection(QWidget):
    """Smooth height-animated expand/collapse panel."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._expanded = True
        self._content_height = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header button
        self._toggle = QPushButton(f"▾  {title}")
        v = theme.vars()
        self._toggle.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            color: {v['--text-secondary']};
            border: none;
            text-align: left;
            font-size: 12px;
            font-weight: 600;
            padding: 6px 2px;
        }}
        QPushButton:hover {{ color: {v['--text-primary']}; }}
        """)
        self._toggle.setCursor(Qt.PointingHandCursor)
        self._toggle.clicked.connect(self.toggle)
        outer.addWidget(self._toggle)

        # Content container
        self._content_widget = QWidget()
        self._content_widget.setMaximumHeight(0)
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(12, 4, 0, 8)
        self._content_layout.setSpacing(8)
        outer.addWidget(self._content_widget)

    def content_layout(self) -> QVBoxLayout:
        return self._content_layout

    def toggle(self) -> None:
        self._expanded = not self._expanded
        v = theme.vars()
        if self._expanded:
            self._toggle.setText(self._toggle.text().replace("▸", "▾"))
            target = self._content_widget.sizeHint().height()
        else:
            title = self._toggle.text().replace("▾", "▸")
            self._toggle.setText(title)
            target = 0

        anim = QPropertyAnimation(self._content_widget, b"maximumHeight", self)
        anim.setDuration(280)
        anim.setStartValue(self._content_widget.maximumHeight())
        anim.setEndValue(target if target > 0 else 0)
        anim.setEasingCurve(QEasingCurve.InOutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def show_content(self) -> None:
        self._content_widget.setMaximumHeight(16777215)
        self._expanded = True


# ─────────────────────────────────────────────────────────────────────────────
# LABEL ROW  (section header row)
# ─────────────────────────────────────────────────────────────────────────────

class SectionLabel(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        v = theme.vars()
        self.setStyleSheet(
            f"font-size: 11px; font-weight: 700; letter-spacing: 0.7px;"
            f" color: {v['--text-muted']}; background: transparent; padding-bottom: 2px;"
        )


class FieldLabel(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        v = theme.vars()
        self.setStyleSheet(
            f"font-size: 13px; font-weight: 500; color: {v['--text-secondary']}; background: transparent;"
        )


# ─────────────────────────────────────────────────────────────────────────────
# FILE PICKER ROW
# ─────────────────────────────────────────────────────────────────────────────

class FilePickerRow(QWidget):
    """A path QLineEdit + Browse button row, with optional drag-and-drop."""

    path_changed = Signal(str)

    def __init__(
        self,
        placeholder: str = "",
        accept_drop: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setAcceptDrops(accept_drop)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.textChanged.connect(self.path_changed)
        layout.addWidget(self.edit, 1)

        self.btn = ModernButton("Browse", variant="ghost")
        self.btn.setFixedWidth(88)
        layout.addWidget(self.btn)

    def path(self) -> str:
        return self.edit.text()

    def set_path(self, p: str) -> None:
        self.edit.setText(p)

    def dragEnterEvent(self, e: QDragEnterEvent) -> None:
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent) -> None:
        urls = e.mimeData().urls()
        if urls:
            self.set_path(urls[0].toLocalFile())


# ─────────────────────────────────────────────────────────────────────────────
# ANIMATED PROGRESS BAR (pulsing indeterminate)
# ─────────────────────────────────────────────────────────────────────────────

class AnimatedProgress(QProgressBar):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        v = theme.vars()
        self.setFixedHeight(6)
        self.setTextVisible(False)
        self.setRange(0, 0)
        self.setStyleSheet(f"""
        QProgressBar {{
            background: {v['--surface']};
            border: none;
            border-radius: 3px;
        }}
        QProgressBar::chunk {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 {v['--primary']}, stop:0.5 {v['--primary-hover']}, stop:1 {v['--primary']}
            );
            border-radius: 3px;
        }}
        """)


# ─────────────────────────────────────────────────────────────────────────────
# LOG CONSOLE
# ─────────────────────────────────────────────────────────────────────────────

class LogConsole(QTextEdit):
    """Styled read-only log with color-coded tags."""

    TAG_COLORS = {
        "ERROR":   "#f0536a",
        "SUCCESS": "#3ecf8e",
        "WARN":    "#f5a623",
        "OK":      "#5b8dee",
        "INFO":    None,
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def append_log(self, msg: str) -> None:
        color = None
        for tag, c in self.TAG_COLORS.items():
            if f"[{tag}]" in msg:
                color = c
                break

        if color:
            self.append(f'<span style="color:{color}; font-weight:500;">{msg}</span>')
        else:
            v = theme.vars()
            self.append(f'<span style="color:{v["--text-secondary"]};">{msg}</span>')

        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())


# ─────────────────────────────────────────────────────────────────────────────
# FADE-IN WIDGET MIXIN
# ─────────────────────────────────────────────────────────────────────────────

def fade_in(widget: QWidget, duration: int = 280) -> None:
    eff = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(eff)
    anim = QPropertyAnimation(eff, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    anim.start(QPropertyAnimation.DeleteWhenStopped)


# ─────────────────────────────────────────────────────────────────────────────
# BACKEND LOGIC (unchanged from original, just extracted)
# ─────────────────────────────────────────────────────────────────────────────

status_queue: queue.Queue = queue.Queue()
is_converting: bool = False
current_zip_path: Optional[str] = None
conversion_thread: Optional[threading.Thread] = None


def _log(msg: str, tag: str = "INFO") -> None:
    status_queue.put(("log", f"[{tag}] {msg}"))


def _update_status(msg: str) -> None:
    status_queue.put(("status", msg))


def verify_zimwriterfs() -> bool:
    try:
        result = subprocess.run(
            ["zimwriterfs", "--version"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            _log(f"Found zimwriterfs: {result.stdout.strip()}", "OK")
            return True
        _log("zimwriterfs verification failed", "ERROR")
        return False
    except FileNotFoundError:
        _log("zimwriterfs not found in PATH!", "ERROR")
        _log("Install with: sudo apt install zim-tools", "ERROR")
        return False
    except Exception as e:
        _log(f"Error verifying zimwriterfs: {e}", "ERROR")
        return False


def extract_zip(zip_path: str, extract_dir: str) -> None:
    _log(f"Extracting: {os.path.basename(zip_path)}")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)
    _log(f"Extracted to: {extract_dir}")


def detect_site_root(extract_dir: str) -> str:
    items = os.listdir(extract_dir)
    if len(items) == 1:
        single = os.path.join(extract_dir, items[0])
        if os.path.isdir(single):
            _log(f"Using nested folder: {items[0]}")
            return single
    _log("Using extraction directory as root")
    return extract_dir


def find_index_html(root_dir: str) -> tuple[Optional[str], Optional[str]]:
    root_index = os.path.join(root_dir, "index.html")
    if os.path.exists(root_index):
        _log("Found index.html at root")
        return root_index, "index.html"
    _log("Searching for index.html recursively...")
    for dirpath, _, filenames in os.walk(root_dir):
        if "index.html" in filenames:
            abs_path = os.path.join(dirpath, "index.html")
            rel_path = os.path.relpath(abs_path, root_dir)
            _log(f"Found index.html at: {rel_path}")
            return abs_path, rel_path
    return None, None


def rewrite_html_links(html_path: str) -> bool:
    try:
        with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        content = re.sub(r"file:///[^\s'\"]*", "", content)
        content = re.sub(r"(href|src)=[\"']/", r'\1="', content)
        with open(html_path, "w", encoding="utf-8", errors="ignore") as f:
            f.write(content)
        return True
    except Exception as e:
        _log(f"Warning: Failed to rewrite {html_path}: {e}", "WARN")
        return False


def rewrite_all_html_files(root_dir: str) -> None:
    _log("Rewriting HTML links...")
    count = sum(
        1
        for dirpath, _, filenames in os.walk(root_dir)
        for fn in filenames
        if fn.lower().endswith(".html") and rewrite_html_links(os.path.join(dirpath, fn))
    )
    _log(f"Rewrote {count} HTML files")


def run_zimwriterfs(
    site_root: str, output_zim: str, welcome_path: str,
    title: str, description: str, language: str,
) -> tuple[bool, str, str]:
    import base64

    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", title).lower()
    PNG_B64 = (
        "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAAEElEQVR42u3BAQ0AAADCoPdPbQ8H"
        "FAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAB8GQgAAAFR6jJSAAAAAElFTkSuQmCC"
    )
    illus_path = os.path.join(site_root, "zimpacker_illustration.png")
    with open(illus_path, "wb") as f:
        f.write(base64.b64decode(PNG_B64))

    cmd = [
        "zimwriterfs",
        f"--welcome={welcome_path}",
        "--illustration=zimpacker_illustration.png",
        f"--language={language}",
        f"--name={safe_name}",
        f"--title={title}",
        f"--description={description or title}",
        "--creator=zimpacker",
        "--publisher=zimpacker",
        "--skip-libmagic-check",
        site_root, output_zim,
    ]
    _log(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode == 0:
            _log("ZIM creation successful!", "SUCCESS")
            return True, result.stdout, result.stderr
        _log(f"ZIM creation failed (exit {result.returncode})", "ERROR")
        if result.stderr:
            _log(f"STDERR: {result.stderr}", "ERROR")
        return False, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        _log("ZIM creation timed out!", "ERROR")
        return False, "", "Process timed out after 10 minutes"
    except Exception as e:
        _log(f"ZIM creation error: {e}", "ERROR")
        return False, "", str(e)


def convert_zip_to_zim(
    zip_path: str, output_zim: str, title: str,
    description: str, language: str, rewrite_links: bool,
) -> bool:
    global is_converting
    temp_dir = None
    try:
        is_converting = True
        _update_status("Converting…")
        _log("Verifying zimwriterfs installation…")
        if not verify_zimwriterfs():
            status_queue.put(("error", "zimwriterfs not found!\n\nInstall with:\nsudo apt install zim-tools"))
            return False

        temp_dir = tempfile.mkdtemp(prefix="zimpacker_")
        _log(f"Created temp directory: {temp_dir}")
        extract_zip(zip_path, temp_dir)
        site_root = detect_site_root(temp_dir)
        index_abs, index_rel = find_index_html(site_root)
        if not index_abs:
            _log("No index.html found in ZIP!", "ERROR")
            status_queue.put(("error", "No index.html found in the ZIP file!"))
            return False

        if rewrite_links:
            rewrite_all_html_files(site_root)

        _update_status("Creating ZIM file…")
        success, _, stderr = run_zimwriterfs(
            site_root, output_zim, index_rel, title, description, language
        )
        if not success:
            status_queue.put(("error", f"zimwriterfs failed:\n\n{stderr}"))
            return False

        _log(f"ZIM file created: {output_zim}", "SUCCESS")
        _update_status("Complete!")
        status_queue.put(("success", output_zim))
        return True

    except Exception as e:
        _log(f"Conversion error: {e}", "ERROR")
        status_queue.put(("error", str(e)))
        return False

    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                _log("Cleaned up temp directory")
            except Exception as e:
                _log(f"Failed to cleanup temp: {e}", "WARN")
        is_converting = False


# ─────────────────────────────────────────────────────────────────────────────
# MAIN WINDOW
# ─────────────────────────────────────────────────────────────────────────────

class ZimPackerWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Invader ZIM  ·  {VERSION}")
        self.setMinimumSize(780, 680)
        self.resize(860, 760)
        self._build_ui()
        self._start_queue_timer()
        threading.Thread(target=verify_zimwriterfs, daemon=True).start()
        QTimer.singleShot(100, lambda: fade_in(self.centralWidget(), 350))

    # ── UI Construction ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        v = theme.vars()
        root = QWidget()
        root.setObjectName("root")
        root.setStyleSheet(f"#root {{ background: {v['--bg']}; }}")
        self.setCentralWidget(root)

        main = QVBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ── Top Bar ──────────────────────────────────────────────────────────
        topbar = QWidget()
        topbar.setFixedHeight(64)
        topbar.setStyleSheet(f"""
            background: {v['--bg-alt']};
            border-bottom: 1px solid {v['--border-subtle']};
        """)
        tb_layout = QHBoxLayout(topbar)
        tb_layout.setContentsMargins(28, 0, 28, 0)

        title_lbl = QLabel(f"⚡  Invader ZIM")
        title_lbl.setStyleSheet(
            f"font-size: 17px; font-weight: 700; color: {v['--text-primary']}; background: transparent;"
        )
        tb_layout.addWidget(title_lbl)
        tb_layout.addStretch()

        ver_lbl = QLabel(VERSION)
        ver_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {v['--text-muted']};"
            f" background: {v['--surface']}; border: 1px solid {v['--border']};"
            f" border-radius: 8px; padding: 3px 10px;"
        )
        tb_layout.addWidget(ver_lbl)
        main.addWidget(topbar)

        # ── Scroll area ──────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        main.addWidget(scroll, 1)

        content = QWidget()
        content.setStyleSheet(f"background: {v['--bg']};")
        scroll.setWidget(content)

        cl = QVBoxLayout(content)
        cl.setContentsMargins(28, 28, 28, 28)
        cl.setSpacing(20)

        # ── INPUT FILE CARD ──────────────────────────────────────────────────
        input_card = CardWidget()
        cl.addWidget(input_card)
        il = input_card.content_layout()

        drop_label = QLabel("📦  Drop a ZIP here or browse")
        drop_label.setAlignment(Qt.AlignCenter)
        drop_label.setStyleSheet(f"""
            font-size: 13px; color: {v['--text-secondary']};
            background: {v['--bg-alt']};
            border: 2px dashed {v['--border']};
            border-radius: {v['--radius-md']};
            padding: 24px;
        """)
        il.addWidget(drop_label)

        self.zip_picker = FilePickerRow("Path to input ZIP file…", accept_drop=True)
        self.zip_picker.btn.clicked.connect(self._browse_zip)
        self.zip_picker.path_changed.connect(self._on_zip_changed)
        # Wire drag-and-drop on drop label
        drop_label.setAcceptDrops(True)
        drop_label.dragEnterEvent = lambda e: e.acceptProposedAction() if e.mimeData().hasUrls() else None
        drop_label.dropEvent = lambda e: self._handle_zip_path(e.mimeData().urls()[0].toLocalFile()) if e.mimeData().hasUrls() else None
        il.addWidget(self.zip_picker)

        # ── METADATA CARD ────────────────────────────────────────────────────
        meta_card = CardWidget()
        cl.addWidget(meta_card)
        ml = meta_card.content_layout()

        ml.addWidget(SectionLabel("METADATA"))

        # Title row
        ml.addWidget(FieldLabel("Title"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g. My Website Archive")
        ml.addWidget(self.title_edit)

        # Language + Description row
        row_w = QWidget()
        row_l = QHBoxLayout(row_w)
        row_l.setContentsMargins(0, 0, 0, 0)
        row_l.setSpacing(16)

        lang_col = QWidget()
        lang_vl = QVBoxLayout(lang_col)
        lang_vl.setContentsMargins(0, 0, 0, 0)
        lang_vl.setSpacing(4)
        lang_vl.addWidget(FieldLabel("Language Code"))
        self.lang_edit = QLineEdit("eng")
        self.lang_edit.setFixedWidth(110)
        lang_vl.addWidget(self.lang_edit)
        row_l.addWidget(lang_col)

        desc_col = QWidget()
        desc_vl = QVBoxLayout(desc_col)
        desc_vl.setContentsMargins(0, 0, 0, 0)
        desc_vl.setSpacing(4)
        desc_vl.addWidget(FieldLabel("Description  (optional)"))
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Short description of the archive…")
        desc_vl.addWidget(self.desc_edit)
        row_l.addWidget(desc_col, 1)
        ml.addWidget(row_w)

        # ── OPTIONS CARD ─────────────────────────────────────────────────────
        opts_card = CardWidget()
        cl.addWidget(opts_card)
        ol = opts_card.content_layout()
        ol.addWidget(SectionLabel("OPTIONS"))

        self.rewrite_check = QCheckBox(
            "Rewrite HTML links  —  strips file:// and converts absolute paths to relative"
        )
        self.rewrite_check.setChecked(True)
        ol.addWidget(self.rewrite_check)

        # ── OUTPUT CARD ──────────────────────────────────────────────────────
        out_card = CardWidget()
        cl.addWidget(out_card)
        outl = out_card.content_layout()
        outl.addWidget(SectionLabel("OUTPUT"))
        outl.addWidget(FieldLabel("Save ZIM file to"))
        self.out_picker = FilePickerRow("e.g.  /home/user/archive.zim")
        self.out_picker.btn.clicked.connect(self._browse_output)
        outl.addWidget(self.out_picker)

        # ── ACTION ROW ───────────────────────────────────────────────────────
        action_row = QWidget()
        ar = QHBoxLayout(action_row)
        ar.setContentsMargins(0, 4, 0, 0)
        ar.setSpacing(12)

        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet(
            f"color: {v['--text-secondary']}; font-size: 13px; background: transparent;"
        )
        ar.addWidget(self.status_lbl)
        ar.addStretch()

        self.convert_btn = ModernButton("Convert to .ZIM  →", variant="primary")
        self.convert_btn.setFixedHeight(44)
        self.convert_btn.setMinimumWidth(180)
        self.convert_btn.clicked.connect(self._start_conversion)
        ar.addWidget(self.convert_btn)

        cl.addWidget(action_row)

        # Progress bar (hidden until converting)
        self.progress = AnimatedProgress()
        self.progress.setVisible(False)
        cl.addWidget(self.progress)

        # ── LOG CARD ─────────────────────────────────────────────────────────
        log_card = CardWidget(title="Console Output")
        cl.addWidget(log_card)
        ll = log_card.content_layout()

        self.log_console = LogConsole()
        self.log_console.setMinimumHeight(220)
        ll.addWidget(self.log_console)

        # Credit
        credit = QLabel("created by  <a href='https://github.com/noosed' style='color:#5b8dee;'>github.com/noosed</a>")
        credit.setOpenExternalLinks(True)
        credit.setStyleSheet(f"font-size: 11px; color: {v['--text-muted']}; background: transparent; padding-top: 4px;")
        cl.addWidget(credit)

    # ── Queue Processor ──────────────────────────────────────────────────────

    def _start_queue_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._process_queue)
        self._timer.start(80)

    def _process_queue(self) -> None:
        v = theme.vars()
        try:
            while not status_queue.empty():
                msg_type, *args = status_queue.get_nowait()

                if msg_type == "log":
                    self.log_console.append_log(args[0])

                elif msg_type == "status":
                    self.status_lbl.setText(args[0])

                elif msg_type == "success":
                    output_path = args[0]
                    self._set_converting(False)
                    self.status_lbl.setStyleSheet(
                        f"color: {v['--success']}; font-size: 13px; font-weight: 600; background: transparent;"
                    )
                    self.status_lbl.setText("✓  Conversion complete!")
                    QMessageBox.information(
                        self, "Success",
                        f"ZIM file created successfully!\n\n{output_path}"
                    )

                elif msg_type == "error":
                    self._set_converting(False)
                    self.status_lbl.setStyleSheet(
                        f"color: {v['--error']}; font-size: 13px; font-weight: 600; background: transparent;"
                    )
                    self.status_lbl.setText("✗  Error — see console")
                    QMessageBox.critical(self, "Conversion Error", args[0])

        except queue.Empty:
            pass

    def _set_converting(self, active: bool) -> None:
        v = theme.vars()
        self.convert_btn.setEnabled(not active)
        self.progress.setVisible(active)
        if not active:
            self.status_lbl.setStyleSheet(
                f"color: {v['--text-secondary']}; font-size: 13px; background: transparent;"
            )

    # ── Event Handlers ───────────────────────────────────────────────────────

    def _browse_zip(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select ZIP file", "", "ZIP files (*.zip);;All files (*.*)"
        )
        if path:
            self._handle_zip_path(path)

    def _browse_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save ZIM file as", "", "ZIM files (*.zim);;All files (*.*)"
        )
        if path:
            self.out_picker.set_path(path)

    def _on_zip_changed(self, path: str) -> None:
        if path and os.path.exists(path):
            self._handle_zip_path(path)

    def _handle_zip_path(self, filepath: str) -> None:
        global current_zip_path
        if not filepath.lower().endswith(".zip"):
            self.log_console.append_log("[ERROR] File must be a ZIP archive!")
            return
        if not os.path.exists(filepath):
            self.log_console.append_log("[ERROR] File does not exist!")
            return
        current_zip_path = filepath
        self.zip_picker.set_path(filepath)
        basename = os.path.splitext(os.path.basename(filepath))[0]
        if not self.title_edit.text():
            self.title_edit.setText(basename)
        if not self.out_picker.path():
            self.out_picker.set_path(
                os.path.join(os.path.dirname(filepath), basename + ".zim")
            )
        self.log_console.append_log(f"[OK] Loaded ZIP: {os.path.basename(filepath)}")

    def _start_conversion(self) -> None:
        global conversion_thread
        if is_converting:
            self.log_console.append_log("[WARN] Conversion already in progress!")
            return
        if not current_zip_path:
            self.log_console.append_log("[ERROR] No ZIP file selected!")
            return

        output_zim = self.out_picker.path()
        title = self.title_edit.text()
        description = self.desc_edit.text()
        language = self.lang_edit.text() or "eng"
        rewrite = self.rewrite_check.isChecked()

        if not output_zim:
            self.log_console.append_log("[ERROR] Please specify output ZIM file!")
            return
        if not title:
            self.log_console.append_log("[ERROR] Please specify a title!")
            return

        self.log_console.clear()
        self._set_converting(True)
        v = theme.vars()
        self.status_lbl.setStyleSheet(
            f"color: {v['--primary']}; font-size: 13px; font-weight: 600; background: transparent;"
        )
        self.status_lbl.setText("Converting…")

        conversion_thread = threading.Thread(
            target=convert_zip_to_zim,
            args=(current_zip_path, output_zim, title, description, language, rewrite),
            daemon=True,
        )
        conversion_thread.start()


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    global theme

    app = QApplication(sys.argv)
    app.setApplicationName("Invader ZIM")
    app.setApplicationVersion(VERSION)

    # High-DPI
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Detect system dark/light preference
    theme = ThemeManager(ThemeManager.AUTO)

    # Apply global stylesheet
    app.setStyleSheet(theme.current_qss())

    window = ZimPackerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
