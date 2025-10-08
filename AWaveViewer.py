"""
Advanced Verilog Waveform Viewer with Automatic Testbench Generation
Similar to ModelSim with full verification capabilities

Author: Shahrear Hossain Shawon
License: Algo Science Lab
Version: 1.0
"""

import sys
import os
import subprocess
import tempfile
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTreeWidget, QTreeWidgetItem, QPushButton, QFileDialog,
    QTextEdit, QLabel, QComboBox, QSpinBox, QLineEdit, QMessageBox,
    QGroupBox, QCheckBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QProgressBar, QStatusBar, QToolBar, QMenu, QDialog, QDialogButtonBox,
    QScrollArea, QFrame, QGraphicsDropShadowEffect, QSplashScreen, QSlider,
    QSizePolicy, QPlainTextEdit
)
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, Signal, QThread, QPropertyAnimation, QEasingCurve, QSize, QRect, QTime
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont, QAction, QPalette,
    QBrush, QPainterPath, QLinearGradient, QPixmap, QIcon, QRadialGradient,
    QSyntaxHighlighter, QTextCharFormat, QTextFormat
)


def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller
    This is critical for the logo to work in the built executable
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


class VerilogSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Verilog/SystemVerilog code"""
    
    def __init__(self, parent=None, theme_name="Dark Blue"):
        super().__init__(parent)
        self.theme_name = theme_name
        self.setup_highlighting_rules()
    
    def setup_highlighting_rules(self):
        """Setup syntax highlighting rules with theme colors"""
        self.highlighting_rules = []
        
        # Get theme colors
        colors = self.get_theme_colors(self.theme_name)
        
        # Keywords format
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(colors['keyword']))
        keyword_format.setFontWeight(QFont.Bold)
        
        # Verilog/SystemVerilog keywords
        keywords = [
            'module', 'endmodule', 'input', 'output', 'inout', 'wire', 'reg',
            'always', 'initial', 'begin', 'end', 'if', 'else', 'case', 'endcase',
            'for', 'while', 'assign', 'parameter', 'localparam', 'function',
            'endfunction', 'task', 'endtask', 'generate', 'endgenerate',
            'posedge', 'negedge', 'or', 'and', 'not', 'xor', 'default',
            # SystemVerilog keywords
            'logic', 'bit', 'byte', 'int', 'integer', 'time', 'real',
            'always_ff', 'always_comb', 'always_latch', 'unique', 'priority',
            'interface', 'endinterface', 'class', 'endclass', 'package',
            'endpackage', 'import', 'export', 'typedef', 'enum', 'struct',
            'union', 'virtual', 'extends', 'implements', 'pure', 'extern',
            'signed', 'unsigned', 'void', 'return', 'break', 'continue'
        ]
        
        for keyword in keywords:
            pattern = r'\b' + keyword + r'\b'
            self.highlighting_rules.append((re.compile(pattern), keyword_format))
        
        # Data types format
        datatype_format = QTextCharFormat()
        datatype_format.setForeground(QColor(colors['datatype']))
        datatype_format.setFontWeight(QFont.Bold)
        
        datatypes = ['wire', 'reg', 'logic', 'bit', 'byte', 'int', 'integer', 'real', 'time']
        for datatype in datatypes:
            pattern = r'\b' + datatype + r'\b'
            self.highlighting_rules.append((re.compile(pattern), datatype_format))
        
        # Numbers format
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(colors['number']))
        patterns = [
            r'\b[0-9]+\'[bB][01xXzZ_]+\b',  # Binary
            r'\b[0-9]+\'[hH][0-9a-fA-FxXzZ_]+\b',  # Hex
            r'\b[0-9]+\'[dD][0-9_]+\b',  # Decimal
            r'\b[0-9]+\b'  # Plain numbers
        ]
        for pattern in patterns:
            self.highlighting_rules.append((re.compile(pattern), number_format))
        
        # String format
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(colors['string']))
        self.highlighting_rules.append((re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        
        # Comment format - single line
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(colors['comment']))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((re.compile(r'//[^\n]*'), comment_format))
        
        # Preprocessor directives
        preprocessor_format = QTextCharFormat()
        preprocessor_format.setForeground(QColor(colors['preprocessor']))
        preprocessor_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((re.compile(r'`\w+'), preprocessor_format))
        
        # System tasks
        system_format = QTextCharFormat()
        system_format.setForeground(QColor(colors['system']))
        self.highlighting_rules.append((re.compile(r'\$\w+'), system_format))
        
        # Multi-line comment format
        self.comment_start_expression = re.compile(r'/\*')
        self.comment_end_expression = re.compile(r'\*/')
        self.multiline_comment_format = QTextCharFormat()
        self.multiline_comment_format.setForeground(QColor(colors['comment']))
        self.multiline_comment_format.setFontItalic(True)
    
    def get_theme_colors(self, theme_name):
        """Get color scheme for the theme"""
        themes = {
            'Dark Blue': {
                'keyword': '#569cd6',      # Blue
                'datatype': '#4ec9b0',     # Teal
                'number': '#b5cea8',       # Light green
                'string': '#ce9178',       # Orange
                'comment': '#6a9955',      # Green
                'preprocessor': '#c586c0', # Purple
                'system': '#dcdcaa'        # Yellow
            },
            'Monokai': {
                'keyword': '#f92672',      # Pink
                'datatype': '#66d9ef',     # Cyan
                'number': '#ae81ff',       # Purple
                'string': '#e6db74',       # Yellow
                'comment': '#75715e',      # Gray
                'preprocessor': '#a6e22e', # Green
                'system': '#fd971f'        # Orange
            },
            'Solarized Dark': {
                'keyword': '#268bd2',      # Blue
                'datatype': '#2aa198',     # Cyan
                'number': '#d33682',       # Magenta
                'string': '#859900',       # Green
                'comment': '#586e75',      # Gray
                'preprocessor': '#cb4b16', # Orange
                'system': '#b58900'        # Yellow
            },
            'Dracula': {
                'keyword': '#ff79c6',      # Pink
                'datatype': '#8be9fd',     # Cyan
                'number': '#bd93f9',       # Purple
                'string': '#f1fa8c',       # Yellow
                'comment': '#6272a4',      # Gray
                'preprocessor': '#50fa7b', # Green
                'system': '#ffb86c'        # Orange
            },
            'Nord': {
                'keyword': '#81a1c1',      # Blue
                'datatype': '#88c0d0',     # Cyan
                'number': '#b48ead',       # Purple
                'string': '#a3be8c',       # Green
                'comment': '#616e88',      # Gray
                'preprocessor': '#d08770', # Orange
                'system': '#ebcb8b'        # Yellow
            },
        }
        
        # Return theme or default to Dark Blue
        return themes.get(theme_name, themes['Dark Blue'])
    
    def highlightBlock(self, text):
        """Apply syntax highlighting to a block of text"""
        # Apply single-line rules
        for pattern, format in self.highlighting_rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - match.start()
                self.setFormat(start, length, format)
        
        # Handle multi-line comments
        self.setCurrentBlockState(0)
        start_index = 0
        
        if self.previousBlockState() != 1:
            start_match = self.comment_start_expression.search(text)
            start_index = start_match.start() if start_match else -1
        
        while start_index >= 0:
            end_match = self.comment_end_expression.search(text, start_index)
            
            if end_match:
                length = end_match.end() - start_index
                self.setFormat(start_index, length, self.multiline_comment_format)
                start_match = self.comment_start_expression.search(text, end_match.end())
                start_index = start_match.start() if start_match else -1
            else:
                self.setCurrentBlockState(1)
                length = len(text) - start_index
                self.setFormat(start_index, length, self.multiline_comment_format)
                break
    
    def update_theme(self, theme_name):
        """Update highlighting theme"""
        self.theme_name = theme_name
        self.setup_highlighting_rules()
        self.rehighlight()


class LineNumberArea(QWidget):
    """Widget to display line numbers for CodeEditor"""
    
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor
    
    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)
    
    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    """Professional code editor with line numbers and syntax highlighting"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create line number area
        self.line_number_area = LineNumberArea(self)
        
        # Connect signals
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        
        # Initial setup
        self.update_line_number_area_width(0)
        self.highlight_current_line()
        
        # Set font
        self.setFont(QFont("Consolas", 10))
        
        # Tab settings - use 4 spaces
        self.setTabStopDistance(40)  # 4 spaces * 10 pixels per character
    
    def line_number_area_width(self):
        """Calculate the width needed for line numbers"""
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space
    
    def update_line_number_area_width(self, _):
        """Update the width of line number area"""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)
    
    def update_line_number_area(self, rect, dy):
        """Update the line number area when scrolling"""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)
    
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), 
                                                 self.line_number_area_width(), cr.height()))
    
    def highlight_current_line(self):
        """Highlight the current line"""
        extra_selections = []
        
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            
            line_color = QColor(30, 41, 59)  # Dark blue-gray highlight
            
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        
        self.setExtraSelections(extra_selections)
    
    def line_number_area_paint_event(self, event):
        """Paint the line numbers"""
        painter = QPainter(self.line_number_area)
        
        # Background color for line number area
        painter.fillRect(event.rect(), QColor(20, 31, 49))
        
        # Get the first visible block
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        
        # Set up fonts and colors
        painter.setFont(self.font())
        
        # Paint line numbers
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                
                # Highlight current line number
                if self.textCursor().blockNumber() == block_number:
                    painter.setPen(QColor(0, 255, 100))  # Bright green for current line
                    painter.setFont(QFont("Consolas", 10, QFont.Bold))
                else:
                    painter.setPen(QColor(100, 116, 139))  # Gray for other lines
                    painter.setFont(QFont("Consolas", 10))
                
                painter.drawText(0, top, self.line_number_area.width() - 5, 
                               self.fontMetrics().height(),
                               Qt.AlignRight, number)
            
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1


class ThemeManager:
    """Manage 50 different transparent themes with opacity control"""
    
    def __init__(self):
        self.current_theme = "Deep Black Green"
        self.opacity = 0.95
        self.themes = self.get_all_themes()
    
    def get_all_themes(self):
        """Return all 50 beautiful themes"""
        return {
            # Deep Black Green (NEW DEFAULT)
            "Deep Black Green": {
                'primary': (0, 0, 0),
                'secondary': (10, 10, 10),
                'accent': (0, 255, 100),
                'text': (220, 220, 220),
                'highlight': (100, 255, 150)
            },
            # Dark Themes (1-15)
            "Dark Blue Ocean": {
                'primary': (15, 23, 42),
                'secondary': (30, 41, 59),
                'accent': (59, 130, 246),
                'text': (226, 232, 240),
                'highlight': (147, 197, 253)
            },
            "Midnight Purple": {
                'primary': (17, 17, 38),
                'secondary': (30, 30, 60),
                'accent': (147, 51, 234),
                'text': (229, 229, 246),
                'highlight': (192, 132, 252)
            },
            "Dark Emerald": {
                'primary': (6, 20, 15),
                'secondary': (20, 40, 30),
                'accent': (16, 185, 129),
                'text': (209, 250, 229),
                'highlight': (110, 231, 183)
            },
            "Carbon Black": {
                'primary': (10, 10, 10),
                'secondary': (25, 25, 25),
                'accent': (220, 220, 220),
                'text': (240, 240, 240),
                'highlight': (180, 180, 180)
            },
            "Deep Navy": {
                'primary': (8, 15, 30),
                'secondary': (15, 30, 50),
                'accent': (70, 130, 200),
                'text': (220, 230, 245),
                'highlight': (130, 170, 220)
            },
            "Volcanic Ash": {
                'primary': (25, 20, 20),
                'secondary': (40, 35, 35),
                'accent': (255, 100, 70),
                'text': (250, 240, 235),
                'highlight': (255, 150, 120)
            },
            "Forest Night": {
                'primary': (10, 20, 15),
                'secondary': (20, 35, 25),
                'accent': (80, 200, 120),
                'text': (230, 250, 235),
                'highlight': (130, 230, 165)
            },
            "Royal Purple": {
                'primary': (20, 10, 30),
                'secondary': (35, 20, 50),
                'accent': (160, 80, 240),
                'text': (240, 230, 250),
                'highlight': (200, 150, 255)
            },
            "Obsidian": {
                'primary': (5, 8, 12),
                'secondary': (15, 20, 28),
                'accent': (100, 150, 200),
                'text': (230, 235, 245),
                'highlight': (150, 180, 220)
            },
            "Crimson Shadow": {
                'primary': (25, 10, 15),
                'secondary': (40, 20, 25),
                'accent': (220, 50, 80),
                'text': (250, 235, 240),
                'highlight': (255, 100, 130)
            },
            "Deep Teal": {
                'primary': (10, 25, 28),
                'secondary': (20, 40, 45),
                'accent': (80, 200, 200),
                'text': (230, 250, 250),
                'highlight': (130, 230, 230)
            },
            "Slate Gray": {
                'primary': (30, 35, 40),
                'secondary': (45, 52, 60),
                'accent': (150, 170, 190),
                'text': (230, 235, 240),
                'highlight': (180, 200, 220)
            },
            "Chocolate Brown": {
                'primary': (25, 15, 10),
                'secondary': (40, 25, 15),
                'accent': (200, 140, 100),
                'text': (250, 240, 230),
                'highlight': (230, 180, 140)
            },
            "Electric Indigo": {
                'primary': (15, 10, 35),
                'secondary': (25, 18, 55),
                'accent': (130, 90, 255),
                'text': (240, 235, 255),
                'highlight': (180, 150, 255)
            },
            "Charcoal": {
                'primary': (20, 22, 25),
                'secondary': (35, 38, 42),
                'accent': (100, 110, 125),
                'text': (220, 225, 230),
                'highlight': (150, 160, 175)
            },
            
            # Blue Themes (16-25)
            "Azure Sky": {
                'primary': (40, 50, 80),
                'secondary': (55, 65, 100),
                'accent': (120, 180, 255),
                'text': (240, 245, 255),
                'highlight': (160, 200, 255)
            },
            "Cyan Dream": {
                'primary': (30, 50, 60),
                'secondary': (45, 70, 85),
                'accent': (100, 220, 255),
                'text': (235, 250, 255),
                'highlight': (150, 235, 255)
            },
            "Sapphire": {
                'primary': (20, 35, 70),
                'secondary': (35, 55, 95),
                'accent': (80, 140, 240),
                'text': (230, 240, 255),
                'highlight': (130, 180, 250)
            },
            "Ice Blue": {
                'primary': (45, 55, 70),
                'secondary': (60, 75, 95),
                'accent': (150, 220, 255),
                'text': (240, 248, 255),
                'highlight': (180, 230, 255)
            },
            "Ocean Breeze": {
                'primary': (30, 45, 55),
                'secondary': (45, 65, 80),
                'accent': (90, 200, 240),
                'text': (235, 248, 252),
                'highlight': (140, 220, 250)
            },
            "Steel Blue": {
                'primary': (35, 45, 60),
                'secondary': (50, 65, 85),
                'accent': (110, 160, 220),
                'text': (230, 240, 250),
                'highlight': (150, 190, 235)
            },
            "Cobalt": {
                'primary': (25, 40, 75),
                'secondary': (40, 60, 100),
                'accent': (70, 130, 240),
                'text': (225, 238, 255),
                'highlight': (120, 170, 250)
            },
            "Powder Blue": {
                'primary': (50, 60, 75),
                'secondary': (70, 85, 100),
                'accent': (130, 190, 235),
                'text': (240, 248, 255),
                'highlight': (170, 210, 245)
            },
            "Navy Mist": {
                'primary': (28, 40, 58),
                'secondary': (42, 58, 80),
                'accent': (90, 150, 210),
                'text': (228, 238, 250),
                'highlight': (135, 180, 230)
            },
            "Arctic Blue": {
                'primary': (42, 52, 65),
                'secondary': (58, 72, 88),
                'accent': (140, 210, 245),
                'text': (238, 246, 252),
                'highlight': (175, 225, 252)
            },
            
            # Green Themes (26-32)
            "Emerald Forest": {
                'primary': (20, 40, 30),
                'secondary': (35, 60, 48),
                'accent': (50, 200, 120),
                'text': (230, 250, 240),
                'highlight': (100, 230, 170)
            },
            "Mint Fresh": {
                'primary': (35, 55, 45),
                'secondary': (50, 75, 65),
                'accent': (120, 240, 180),
                'text': (240, 255, 248),
                'highlight': (160, 250, 210)
            },
            "Jade": {
                'primary': (25, 45, 40),
                'secondary': (40, 65, 58),
                'accent': (80, 220, 160),
                'text': (235, 252, 245),
                'highlight': (130, 240, 190)
            },
            "Lime Zest": {
                'primary': (40, 50, 30),
                'secondary': (58, 72, 45),
                'accent': (160, 240, 80),
                'text': (245, 255, 235),
                'highlight': (190, 250, 130)
            },
            "Pine": {
                'primary': (25, 35, 25),
                'secondary': (40, 55, 40),
                'accent': (90, 180, 90),
                'text': (235, 245, 235),
                'highlight': (140, 210, 140)
            },
            "Seafoam": {
                'primary': (35, 50, 48),
                'secondary': (52, 72, 70),
                'accent': (110, 230, 210),
                'text': (240, 252, 250),
                'highlight': (155, 245, 230)
            },
            "Olive": {
                'primary': (35, 40, 28),
                'secondary': (52, 60, 42),
                'accent': (150, 180, 90),
                'text': (242, 248, 235),
                'highlight': (185, 210, 135)
            },
            
            # Purple/Pink Themes (33-40)
            "Lavender": {
                'primary': (45, 40, 60),
                'secondary': (65, 58, 85),
                'accent': (180, 150, 240),
                'text': (248, 245, 255),
                'highlight': (210, 190, 250)
            },
            "Magenta Glow": {
                'primary': (40, 25, 45),
                'secondary': (60, 40, 68),
                'accent': (240, 100, 220),
                'text': (255, 240, 252),
                'highlight': (255, 150, 240)
            },
            "Amethyst": {
                'primary': (35, 25, 50),
                'secondary': (52, 40, 75),
                'accent': (160, 90, 230),
                'text': (245, 238, 255),
                'highlight': (195, 140, 250)
            },
            "Rose": {
                'primary': (50, 35, 40),
                'secondary': (72, 52, 60),
                'accent': (255, 140, 180),
                'text': (255, 245, 248),
                'highlight': (255, 180, 210)
            },
            "Plum": {
                'primary': (35, 25, 40),
                'secondary': (52, 40, 60),
                'accent': (200, 120, 200),
                'text': (250, 240, 250),
                'highlight': (230, 170, 230)
            },
            "Orchid": {
                'primary': (45, 35, 55),
                'secondary': (65, 52, 78),
                'accent': (220, 140, 255),
                'text': (252, 245, 255),
                'highlight': (240, 180, 255)
            },
            "Fuchsia": {
                'primary': (40, 20, 40),
                'secondary': (60, 35, 60),
                'accent': (255, 80, 220),
                'text': (255, 235, 250),
                'highlight': (255, 130, 240)
            },
            "Violet Mist": {
                'primary': (38, 30, 52),
                'secondary': (55, 45, 75),
                'accent': (170, 120, 240),
                'text': (245, 240, 255),
                'highlight': (200, 165, 250)
            },
            
            # Warm Themes (41-48)
            "Sunset Orange": {
                'primary': (45, 30, 20),
                'secondary': (68, 48, 35),
                'accent': (255, 150, 70),
                'text': (255, 245, 238),
                'highlight': (255, 180, 110)
            },
            "Coral Reef": {
                'primary': (48, 35, 35),
                'secondary': (70, 52, 52),
                'accent': (255, 130, 120),
                'text': (255, 248, 246),
                'highlight': (255, 170, 160)
            },
            "Amber": {
                'primary': (42, 35, 20),
                'secondary': (62, 52, 32),
                'accent': (255, 190, 50),
                'text': (255, 250, 235),
                'highlight': (255, 210, 100)
            },
            "Peach": {
                'primary': (52, 42, 38),
                'secondary': (75, 62, 55),
                'accent': (255, 180, 150),
                'text': (255, 250, 245),
                'highlight': (255, 200, 175)
            },
            "Copper": {
                'primary': (38, 28, 22),
                'secondary': (58, 45, 35),
                'accent': (220, 130, 80),
                'text': (250, 242, 235),
                'highlight': (240, 165, 120)
            },
            "Terracotta": {
                'primary': (42, 30, 25),
                'secondary': (62, 48, 40),
                'accent': (210, 110, 80),
                'text': (252, 245, 240),
                'highlight': (235, 145, 115)
            },
            "Cinnamon": {
                'primary': (38, 30, 25),
                'secondary': (58, 48, 40),
                'accent': (200, 120, 80),
                'text': (250, 245, 238),
                'highlight': (225, 155, 115)
            },
            "Bronze": {
                'primary': (35, 30, 20),
                'secondary': (52, 48, 32),
                'accent': (205, 150, 90),
                'text': (248, 245, 235),
                'highlight': (225, 175, 125)
            },
            
            # Special Themes (49-50)
            "Hacker Matrix": {
                'primary': (0, 8, 0),
                'secondary': (0, 20, 0),
                'accent': (0, 255, 65),
                'text': (180, 255, 180),
                'highlight': (100, 255, 150)
            },
            "Neon Cyberpunk": {
                'primary': (10, 5, 25),
                'secondary': (20, 12, 40),
                'accent': (255, 0, 255),
                'text': (0, 255, 255),
                'highlight': (255, 100, 255)
            }
        }
    
    def get_stylesheet(self, theme_name, opacity):
        """Generate stylesheet for the theme with opacity"""
        theme = self.themes.get(theme_name, self.themes["Dark Blue Ocean"])
        
        # Convert RGB to RGBA with opacity
        def rgba(rgb, alpha=None):
            if alpha is None:
                alpha = opacity
            return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha})"
        
        return f"""
            QMainWindow {{
                background-color: {rgba(theme['primary'])};
            }}
            
            QWidget {{
                background-color: {rgba(theme['primary'])};
                color: {rgba(theme['text'], 1.0)};
            }}
            
            QTextEdit, QTreeWidget, QTableWidget, QPlainTextEdit {{
                background-color: {rgba(theme['secondary'], opacity * 0.8)};
                color: {rgba(theme['text'], 1.0)};
                border: 1px solid {rgba(theme['accent'], opacity * 0.5)};
                border-radius: 5px;
                padding: 5px;
            }}
            
            QPushButton {{
                background-color: {rgba(theme['accent'], opacity * 0.8)};
                color: {rgba(theme['text'], 1.0)};
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            
            QPushButton:hover {{
                background-color: {rgba(theme['highlight'], opacity * 0.9)};
            }}
            
            QPushButton:pressed {{
                background-color: {rgba(theme['accent'], opacity * 0.6)};
            }}
            
            QGroupBox {{
                border: 2px solid {rgba(theme['accent'], opacity * 0.6)};
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
                padding-top: 15px;
            }}
            
            QGroupBox::title {{
                color: {rgba(theme['highlight'], 1.0)};
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            
            QTabWidget::pane {{
                border: 1px solid {rgba(theme['accent'], opacity * 0.5)};
                background: {rgba(theme['primary'])};
                border-radius: 5px;
            }}
            
            QTabBar::tab {{
                background: {rgba(theme['secondary'], opacity * 0.7)};
                color: {rgba(theme['text'], 0.8)};
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }}
            
            QTabBar::tab:selected {{
                background: {rgba(theme['accent'], opacity * 0.9)};
                color: {rgba(theme['text'], 1.0)};
            }}
            
            QMenuBar {{
                background-color: {rgba(theme['secondary'], opacity * 0.9)};
                color: {rgba(theme['text'], 1.0)};
            }}
            
            QMenuBar::item:selected {{
                background-color: {rgba(theme['accent'], opacity * 0.8)};
            }}
            
            QMenu {{
                background-color: {rgba(theme['secondary'], opacity * 0.95)};
                color: {rgba(theme['text'], 1.0)};
                border: 1px solid {rgba(theme['accent'], opacity * 0.6)};
            }}
            
            QMenu::item:selected {{
                background-color: {rgba(theme['accent'], opacity * 0.8)};
            }}
            
            QStatusBar {{
                background-color: {rgba(theme['secondary'], opacity * 0.9)};
                color: {rgba(theme['text'], 1.0)};
            }}
            
            QScrollBar:vertical {{
                background: {rgba(theme['secondary'], opacity * 0.5)};
                width: 12px;
                border-radius: 6px;
            }}
            
            QScrollBar::handle:vertical {{
                background: {rgba(theme['accent'], opacity * 0.7)};
                border-radius: 6px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background: {rgba(theme['highlight'], opacity * 0.8)};
            }}
            
            QScrollBar:horizontal {{
                background: {rgba(theme['secondary'], opacity * 0.5)};
                height: 12px;
                border-radius: 6px;
            }}
            
            QScrollBar::handle:horizontal {{
                background: {rgba(theme['accent'], opacity * 0.7)};
                border-radius: 6px;
            }}
            
            QSlider::groove:horizontal {{
                border: 1px solid {rgba(theme['accent'], opacity * 0.4)};
                height: 8px;
                background: {rgba(theme['secondary'], opacity * 0.6)};
                border-radius: 4px;
            }}
            
            QSlider::handle:horizontal {{
                background: {rgba(theme['accent'], opacity * 0.9)};
                border: 1px solid {rgba(theme['highlight'], opacity * 0.8)};
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }}
            
            QSpinBox, QComboBox {{
                background-color: {rgba(theme['secondary'], opacity * 0.8)};
                color: {rgba(theme['text'], 1.0)};
                border: 1px solid {rgba(theme['accent'], opacity * 0.5)};
                border-radius: 4px;
                padding: 5px;
            }}
            
            QLabel {{
                background-color: transparent;
                color: {rgba(theme['text'], 1.0)};
            }}
        """
    
    def get_theme_list(self):
        """Return list of all theme names"""
        return list(self.themes.keys())


class SplashScreen(QSplashScreen):
    """Glassmorphic professional splash screen - Algo Science Lab"""
    
    def __init__(self):
        # Modern glassmorphic splash dimensions
        pixmap = QPixmap(850, 550)
        super().__init__(pixmap)
        
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.progress = 0
        self.message = "Initializing..."
        self.animation_frame = 0
        self.fade_opacity = 0  # Smooth fade-in
        self.pulse_value = 0
        
        # Center the splash screen on the display
        self.center_on_screen()
        
        # Professional animation timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        self.timer.start(30)
    
    def center_on_screen(self):
        """Center the splash screen on the primary screen"""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
    def animate(self):
        """Smooth animations for glassmorphic effects"""
        self.animation_frame += 1
        if self.fade_opacity < 1.0:
            self.fade_opacity = min(1.0, self.fade_opacity + 0.03)
        
        # Smooth pulse for glow effects
        import math
        self.pulse_value = 0.5 + 0.5 * math.sin(self.animation_frame * 0.05)
        self.repaint()
        
    def paintEvent(self, event):
        """Glassmorphic professional splash screen with stunning details"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Apply fade-in opacity
        painter.setOpacity(self.fade_opacity)
        
        # === DEEP BLACK BACKGROUND ===
        painter.fillRect(self.rect(), QColor(0, 0, 0))
        
        # === ANIMATED BACKGROUND PARTICLES (BRIGHT GREEN) ===
        import math
        painter.setPen(Qt.NoPen)
        for i in range(40):
            angle = (self.animation_frame * 0.008 + i * 9) % 360
            radius = 120 + i * 6
            x = self.width() // 2 + int(radius * math.cos(math.radians(angle)))
            y = self.height() // 2 + int(radius * math.sin(math.radians(angle)))
            
            if 0 <= x < self.width() and 0 <= y < self.height():
                alpha = int(120 * (1 - i / 40))
                size = 2 + int(4 * (1 - i / 40))
                painter.setBrush(QColor(0, 255, 100, alpha))  # Bright green particles
                painter.drawEllipse(x - size//2, y - size//2, size, size)
        
        # === GLASSMORPHIC MAIN CARD (DARK WITH BRIGHT BORDER) ===
        card_margin = 40
        card_rect = self.rect().adjusted(card_margin, card_margin, -card_margin, -card_margin)
        
        # Glass background - very dark with subtle gradient
        glass_gradient = QLinearGradient(card_rect.topLeft(), card_rect.bottomRight())
        glass_gradient.setColorAt(0, QColor(20, 20, 20, 200))
        glass_gradient.setColorAt(0.5, QColor(15, 15, 15, 200))
        glass_gradient.setColorAt(1, QColor(10, 10, 10, 200))
        
        painter.setBrush(glass_gradient)
        painter.setPen(QPen(QColor(0, 255, 100, 120), 3))  # Bright green border
        painter.drawRoundedRect(card_rect, 20, 20)
        
        # Inner glow for glass effect
        for i in range(3):
            alpha = int((3 - i) * 30)
            painter.setPen(QPen(QColor(0, 255, 100, alpha), (3 - i) * 2))
            painter.drawRoundedRect(card_rect.adjusted(i, i, -i, -i), 20 - i, 20 - i)
        
        # === TOP GRADIENT BAR (ACCENT - BRIGHT GREEN) ===
        accent_height = 6
        accent_gradient = QLinearGradient(card_margin, card_margin, self.width() - card_margin, card_margin)
        accent_gradient.setColorAt(0, QColor(0, 255, 100))    # Bright green
        accent_gradient.setColorAt(0.3, QColor(50, 255, 150))  # Brighter
        accent_gradient.setColorAt(0.7, QColor(0, 200, 80))   # Medium green
        accent_gradient.setColorAt(1, QColor(0, 255, 100))     # Bright green
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(accent_gradient)
        painter.drawRoundedRect(card_margin, card_margin, self.width() - card_margin * 2, accent_height, 3, 3)
        
        # === LOGO SECTION WITH GLASSMORPHIC CIRCLE ===
        logo_y = 90
        center_x = self.width() // 2
        
        # Glassmorphic circle background for logo
        logo_circle_size = 140
        logo_circle_x = center_x - logo_circle_size // 2
        
        # Outer glow - BRIGHT GREEN
        for i in range(15, 0, -1):
            alpha = int(i * 3 * self.pulse_value)
            painter.setBrush(QColor(0, 255, 100, alpha))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(logo_circle_x - i, logo_y - i, logo_circle_size + i*2, logo_circle_size + i*2)
        
        # Glass circle - DARK with bright green gradient
        circle_gradient = QRadialGradient(center_x, logo_y + logo_circle_size // 2, logo_circle_size // 2)
        circle_gradient.setColorAt(0, QColor(30, 30, 30, 180))
        circle_gradient.setColorAt(0.7, QColor(20, 20, 20, 200))
        circle_gradient.setColorAt(1, QColor(10, 10, 10, 220))
        
        painter.setBrush(circle_gradient)
        painter.setPen(QPen(QColor(0, 255, 100, 150), 3))  # Bright green border
        painter.drawEllipse(logo_circle_x, logo_y, logo_circle_size, logo_circle_size)
        
        # Inner highlight - BRIGHT
        painter.setPen(QPen(QColor(100, 255, 150, 180), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(logo_circle_x + 10, logo_y + 10, logo_circle_size - 20, logo_circle_size - 20, 45 * 16, 120 * 16)
        
        # === WAVEFORM ICON (DIGITAL SIGNAL - BRIGHT GREEN) ===
        wave_pen = QPen(QColor(0, 255, 100), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(wave_pen)
        
        wave_start_x = logo_circle_x + 25
        wave_width = logo_circle_size - 50
        wave_y_center = logo_y + logo_circle_size // 2
        
        # Animated digital waveform
        wave_offset = (self.animation_frame % 60) * 1.5
        wave_path = QPainterPath()
        wave_path.moveTo(wave_start_x - wave_offset, wave_y_center + 20)
        
        for i in range(0, int(wave_width + wave_offset), 20):
            x_pos = wave_start_x + i - wave_offset
            if i % 40 < 20:
                wave_path.lineTo(x_pos, wave_y_center + 20)
                wave_path.lineTo(x_pos, wave_y_center - 20)
            else:
                wave_path.lineTo(x_pos, wave_y_center - 20)
                wave_path.lineTo(x_pos, wave_y_center + 20)
        
        painter.setClipRect(logo_circle_x + 20, logo_y + 20, logo_circle_size - 40, logo_circle_size - 40)
        painter.drawPath(wave_path)
        painter.setClipping(False)
        
        # Glow effect on waveform - VERY BRIGHT
        glow_pen = QPen(QColor(100, 255, 150, 180), 8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(glow_pen)
        painter.drawPath(wave_path)
        
        # === BRANDING TEXT SECTION - BRIGHT COLORS ===
        text_y = logo_y + logo_circle_size + 50
        
        # Organization name with glow
        painter.setPen(QColor(0, 0, 0, 100))
        painter.setFont(QFont("Arial", 13, QFont.Bold))
        painter.drawText(0, text_y + 1, self.width(), 20, Qt.AlignCenter, "ALGO SCIENCE LAB")
        
        painter.setPen(QColor(100, 255, 150))  # Bright green
        painter.setFont(QFont("Arial", 13, QFont.Bold))
        painter.drawText(0, text_y, self.width(), 20, Qt.AlignCenter, "ALGO SCIENCE LAB")
        
        # Decorative line
        line_y = text_y + 28
        line_width = 280
        line_x = center_x - line_width // 2
        
        line_gradient = QLinearGradient(line_x, line_y, line_x + line_width, line_y)
        line_gradient.setColorAt(0, QColor(0, 255, 100, 0))
        line_gradient.setColorAt(0.5, QColor(0, 255, 100, 255))
        line_gradient.setColorAt(1, QColor(0, 255, 100, 0))
        
        painter.setPen(QPen(QBrush(line_gradient), 2))
        painter.drawLine(line_x, line_y, line_x + line_width, line_y)
        
        # Product name (large, bold) with shadow
        product_y = line_y + 25
        painter.setPen(QColor(0, 0, 0, 120))
        painter.setFont(QFont("Arial", 44, QFont.Bold))
        painter.drawText(0, product_y + 2, self.width(), 50, Qt.AlignCenter, "AWaveViewer")
        
        painter.setPen(QColor(255, 255, 255))  # Pure white
        painter.setFont(QFont("Arial", 44, QFont.Bold))
        painter.drawText(0, product_y, self.width(), 50, Qt.AlignCenter, "AWaveViewer")
        
        # Tagline
        tagline_y = product_y + 55
        painter.setPen(QColor(200, 255, 200))  # Very light green
        painter.setFont(QFont("Arial", 12, QFont.Normal))
        painter.drawText(0, tagline_y, self.width(), 20, Qt.AlignCenter, 
                        "Professional Verilog Waveform Analyzer")
        
        # Version badge with glassmorphic style
        version_y = tagline_y + 30
        badge_width = 240
        badge_height = 28
        badge_x = center_x - badge_width // 2
        
        # Badge glass background
        badge_gradient = QLinearGradient(badge_x, version_y, badge_x + badge_width, version_y)
        badge_gradient.setColorAt(0, QColor(0, 255, 100, 80))
        badge_gradient.setColorAt(1, QColor(0, 200, 80, 80))
        
        painter.setBrush(badge_gradient)
        painter.setPen(QPen(QColor(100, 255, 150, 120), 1))
        painter.drawRoundedRect(badge_x, version_y, badge_width, badge_height, 14, 14)
        
        # Badge text
        painter.setPen(QColor(255, 255, 255))  # Pure white
        painter.setFont(QFont("Arial", 9, QFont.Bold))
        painter.drawText(badge_x, version_y, badge_width, badge_height, Qt.AlignCenter, 
                        "Version 1.0 • Professional Edition")
        
        # === GLASSMORPHIC PROGRESS BAR - BRIGHT GREEN ===
        progress_y = self.height() - 110
        bar_width = 550
        bar_height = 6
        bar_x = center_x - bar_width // 2
        
        # Progress bar glass background
        bar_bg_gradient = QLinearGradient(bar_x, progress_y, bar_x, progress_y + bar_height)
        bar_bg_gradient.setColorAt(0, QColor(50, 50, 50, 150))
        bar_bg_gradient.setColorAt(1, QColor(30, 30, 30, 150))
        
        painter.setBrush(bar_bg_gradient)
        painter.setPen(QPen(QColor(100, 255, 150, 80), 1))
        painter.drawRoundedRect(bar_x, progress_y, bar_width, bar_height, 3, 3)
        
        # Progress fill with gradient and glow
        if self.progress > 0:
            progress_width = int((self.progress / 100) * bar_width)
            
            progress_gradient = QLinearGradient(bar_x, progress_y, bar_x + progress_width, progress_y)
            progress_gradient.setColorAt(0, QColor(0, 255, 100))
            progress_gradient.setColorAt(0.5, QColor(50, 255, 150))
            progress_gradient.setColorAt(1, QColor(0, 200, 80))
            
            # Glow under progress
            for i in range(3, 0, -1):
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(0, 255, 100, 50 * i))
                painter.drawRoundedRect(bar_x - i, progress_y - i, progress_width + i*2, bar_height + i*2, 3, 3)
            
            painter.setBrush(progress_gradient)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(bar_x, progress_y, progress_width, bar_height, 3, 3)
            
            # Shine effect on progress
            shine_gradient = QLinearGradient(bar_x, progress_y, bar_x, progress_y + bar_height)
            shine_gradient.setColorAt(0, QColor(255, 255, 255, 80))
            shine_gradient.setColorAt(0.5, QColor(255, 255, 255, 0))
            
            painter.setBrush(shine_gradient)
            painter.drawRoundedRect(bar_x, progress_y, progress_width, bar_height // 2, 3, 3)
        
        # Loading message - BRIGHT TEXT
        message_y = progress_y + 22
        painter.setPen(QColor(0, 0, 0, 100))
        painter.setFont(QFont("Arial", 10, QFont.Normal))
        painter.drawText(0, message_y + 1, self.width(), 20, Qt.AlignCenter, self.message)
        
        painter.setPen(QColor(200, 255, 200))  # Very bright green
        painter.setFont(QFont("Arial", 10, QFont.Normal))
        painter.drawText(0, message_y, self.width(), 20, Qt.AlignCenter, self.message)
        
        # Copyright with subtle style - BRIGHT TEXT
        copyright_y = self.height() - 35
        painter.setPen(QColor(150, 255, 150))  # Bright green
        painter.setFont(QFont("Arial", 8, QFont.Normal))
        painter.drawText(0, copyright_y, self.width(), 15, Qt.AlignCenter, 
                        "© 2025 Algo Science Lab. All rights reserved.")
        
        # Outer glassmorphic border - BRIGHT GREEN
        painter.setPen(QPen(QColor(0, 255, 100, 100), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(0, 0, self.width() - 1, self.height() - 1, 15, 15)
    
    def set_progress(self, value, message=""):
        """Update progress and message"""
        self.progress = value
        if message:
            self.message = message
        self.repaint()
    
    def closeEvent(self, event):
        """Stop animation timer when closing"""
        self.timer.stop()
        super().closeEvent(event)


class WelcomeDialog(QDialog):
    """Glassmorphic professional welcome screen - Algo Science Lab"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to AWaveViewer")
        self.setFixedSize(900, 680)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.animation_frame = 0
        self.setup_ui()
        
        # Center the dialog on screen
        self.center_on_screen()
        
        # Professional shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)
        
        # Start animation for glassmorphic effects
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        self.timer.start(50)
    
    def center_on_screen(self):
        """Center the dialog on the primary screen"""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def animate(self):
        """Animate glassmorphic effects"""
        self.animation_frame += 1
        self.update()
    
    def paintEvent(self, event):
        """Custom paint for glassmorphic background"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Deep black background
        painter.fillRect(self.rect(), QColor(0, 0, 0))
        
        # Animated particles - BRIGHT GREEN
        import math
        painter.setPen(Qt.NoPen)
        for i in range(35):
            angle = (self.animation_frame * 0.5 + i * 10.3) % 360
            radius = 100 + i * 7
            x = self.width() // 2 + int(radius * math.cos(math.radians(angle)))
            y = self.height() // 2 + int(radius * math.sin(math.radians(angle)))
            
            if 0 <= x < self.width() and 0 <= y < self.height():
                alpha = int(100 * (1 - i / 35))
                size = 2 + int(3 * (1 - i / 35))
                painter.setBrush(QColor(0, 255, 100, alpha))  # Bright green
                painter.drawEllipse(x - size//2, y - size//2, size, size)
        
        # Glassmorphic border glow - BRIGHT GREEN
        for i in range(8, 0, -1):
            alpha = int(i * 12)
            painter.setPen(QPen(QColor(0, 255, 100, alpha), i * 2))  # Bright green glow
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(i, i, self.width() - i*2, self.height() - i*2, 20, 20)
        
        painter.setPen(QPen(QColor(0, 255, 100, 150), 2))  # Bright green border
        painter.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 18, 18)
        
        super().paintEvent(event)
    
    def setup_ui(self):
        """Professional and simple welcome screen"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Main container
        container = QFrame()
        container.setStyleSheet("QFrame { background: transparent; }")
        
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(60, 50, 60, 50)
        container_layout.setSpacing(0)
        
        # === HEADER SECTION ===
        # Organization label
        org_label = QLabel("🔬 ALGO SCIENCE LAB")
        org_label.setAlignment(Qt.AlignCenter)
        org_label.setStyleSheet("""
            color: rgb(0, 255, 100);
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 2px;
            font-family: 'Arial';
            background: transparent;
        """)
        container_layout.addWidget(org_label)
        container_layout.addSpacing(12)
        
        # Product name
        product_label = QLabel("AWaveViewer")
        product_label.setAlignment(Qt.AlignCenter)
        product_label.setStyleSheet("""
            color: rgb(255, 255, 255);
            font-size: 48px;
            font-weight: 800;
            font-family: 'Arial';
            background: transparent;
        """)
        container_layout.addWidget(product_label)
        container_layout.addSpacing(8)
        
        # Version
        version_label = QLabel("Version 1.0 Professional")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("""
            color: rgb(150, 255, 150);
            font-size: 11px;
            font-weight: 600;
            font-family: 'Arial';
            background: transparent;
        """)
        container_layout.addWidget(version_label)
        container_layout.addSpacing(6)
        
        # Tagline
        tagline_label = QLabel("Professional Verilog Waveform Analyzer & Verification Suite")
        tagline_label.setAlignment(Qt.AlignCenter)
        tagline_label.setStyleSheet("""
            color: rgb(180, 180, 180);
            font-size: 12px;
            font-weight: 400;
            font-family: 'Arial';
            background: transparent;
        """)
        container_layout.addWidget(tagline_label)
        
        # Separator line
        container_layout.addSpacing(35)
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background: rgba(0, 255, 100, 80);")
        container_layout.addWidget(separator)
        container_layout.addSpacing(30)
        
        # === FEATURES LIST - SIMPLE AND CLEAN ===
        features_data = [
            ("✓", "Smart Verilog Parser with automatic module analysis"),
            ("✓", "Built-in Testbench Generator for quick verification"),
            ("✓", "Integrated Simulator with Icarus Verilog support"),
            ("✓", "Professional Waveform Viewer for signal visualization"),
            ("✓", "50+ Customizable Themes with opacity control"),
            ("✓", "Syntax Highlighting with 5 color schemes"),
            ("✓", "Module Tree View with signal hierarchy"),
            ("✓", "VCD Export for external analysis tools"),
        ]
        
        # Features list container
        features_container = QWidget()
        features_container.setStyleSheet("background: transparent;")
        features_layout = QVBoxLayout(features_container)
        features_layout.setSpacing(12)
        features_layout.setContentsMargins(80, 0, 80, 0)
        
        for checkmark, feature_text in features_data:
            feature_row = QWidget()
            feature_row.setStyleSheet("background: transparent;")
            feature_row_layout = QHBoxLayout(feature_row)
            feature_row_layout.setContentsMargins(0, 0, 0, 0)
            feature_row_layout.setSpacing(15)
            
            # Checkmark
            check_label = QLabel(checkmark)
            check_label.setStyleSheet("""
                QLabel {
                    color: rgb(0, 255, 100);
                    font-size: 16px;
                    font-weight: 700;
                    font-family: 'Arial';
                    background: transparent;
                }
            """)
            check_label.setFixedWidth(20)
            feature_row_layout.addWidget(check_label)
            
            # Feature text
            feature_label = QLabel(feature_text)
            feature_label.setStyleSheet("""
                QLabel {
                    color: rgb(220, 220, 220);
                    font-size: 13px;
                    font-weight: 400;
                    font-family: 'Arial';
                    background: transparent;
                }
            """)
            feature_row_layout.addWidget(feature_label, 1)
            
            features_layout.addWidget(feature_row)
        
        container_layout.addWidget(features_container)
        container_layout.addSpacing(40)
        
        # === FOOTER INFO ===
        footer_container = QWidget()
        footer_container.setStyleSheet("background: transparent;")
        footer_layout = QVBoxLayout(footer_container)
        footer_layout.setSpacing(6)
        
        # Creator info
        creator_label = QLabel("Created by Shahrear Hossain Shawon")
        creator_label.setAlignment(Qt.AlignCenter)
        creator_label.setStyleSheet("""
            color: rgb(180, 180, 180);
            font-size: 11px;
            font-weight: 500;
            font-family: 'Arial';
            background: transparent;
        """)
        footer_layout.addWidget(creator_label)
        
        # Copyright
        copyright_label = QLabel("© 2025 Algo Science Lab • All rights reserved")
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("""
            color: rgb(120, 120, 120);
            font-size: 9px;
            font-weight: 400;
            font-family: 'Arial';
            background: transparent;
        """)
        footer_layout.addWidget(copyright_label)
        
        container_layout.addWidget(footer_container)
        container_layout.addSpacing(30)
        
        # === BUTTONS ===
        button_container = QWidget()
        button_container.setStyleSheet("background: transparent;")
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(15)
        button_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFixedSize(120, 40)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgb(180, 180, 180);
                border: 1px solid rgba(100, 100, 100, 150);
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
                font-family: 'Arial';
            }
            QPushButton:hover {
                color: rgb(220, 220, 220);
                border: 1px solid rgba(150, 150, 150, 200);
            }
            QPushButton:pressed {
                background: rgba(50, 50, 50, 100);
            }
        """)
        close_btn.clicked.connect(self.reject)
        button_layout.addWidget(close_btn)
        
        # Get Started button
        start_btn = QPushButton("Get Started")
        start_btn.setFixedSize(150, 40)
        start_btn.setCursor(Qt.PointingHandCursor)
        start_btn.setStyleSheet("""
            QPushButton {
                background: rgb(0, 255, 100);
                color: rgb(0, 0, 0);
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 700;
                font-family: 'Arial';
            }
            QPushButton:hover {
                background: rgb(50, 255, 150);
            }
            QPushButton:pressed {
                background: rgb(0, 200, 80);
            }
        """)
        start_btn.clicked.connect(self.accept)
        button_layout.addWidget(start_btn)
        
        button_layout.addStretch()
        container_layout.addWidget(button_container)
        
        layout.addWidget(container)
        layout.addWidget(container)


class VerilogSyntaxChecker:
    """Check Verilog syntax and validate code before testbench generation"""
    
    @staticmethod
    def check_syntax(verilog_code: str) -> tuple[bool, list[str]]:
        """
        Check Verilog syntax and return (is_valid, error_list)
        Supports Verilog-95, Verilog-2001, and SystemVerilog
        """
        errors = []
        warnings = []
        
        # Remove comments to avoid false positives
        code = VerilogSyntaxChecker._remove_comments(verilog_code)
        
        # Check 1: Module declaration
        if not re.search(r'\bmodule\s+\w+', code):
            errors.append("ERROR: No module declaration found")
        
        # Check 2: Module/endmodule matching
        module_count = len(re.findall(r'\bmodule\s+', code))
        endmodule_count = len(re.findall(r'\bendmodule\b', code))
        if module_count != endmodule_count:
            errors.append(f"ERROR: Module/endmodule mismatch (found {module_count} module(s) but {endmodule_count} endmodule(s))")
        
        # Check 3: Begin/end matching
        begin_count = len(re.findall(r'\bbegin\b', code))
        end_count = len(re.findall(r'\bend\b', code))
        if begin_count != end_count:
            warnings.append(f"WARNING: Begin/end mismatch (found {begin_count} begin(s) but {end_count} end(s))")
        
        # Check 4: Case/endcase matching
        case_count = len(re.findall(r'\bcase[xz]?\b', code))
        endcase_count = len(re.findall(r'\bendcase\b', code))
        if case_count != endcase_count:
            errors.append(f"ERROR: Case/endcase mismatch (found {case_count} case(s) but {endcase_count} endcase(s))")
        
        # Check 5: Function/endfunction matching
        function_count = len(re.findall(r'\bfunction\b', code))
        endfunction_count = len(re.findall(r'\bendfunction\b', code))
        if function_count != endfunction_count:
            errors.append(f"ERROR: Function/endfunction mismatch")
        
        # Check 6: Task/endtask matching
        task_count = len(re.findall(r'\btask\b', code))
        endtask_count = len(re.findall(r'\bendtask\b', code))
        if task_count != endtask_count:
            errors.append(f"ERROR: Task/endtask mismatch")
        
        # Check 7: Parentheses matching
        paren_balance = 0
        line_num = 0
        for line in code.split('\n'):
            line_num += 1
            for char in line:
                if char == '(':
                    paren_balance += 1
                elif char == ')':
                    paren_balance -= 1
                    if paren_balance < 0:
                        errors.append(f"ERROR: Unmatched closing parenthesis at line {line_num}")
                        break
        if paren_balance > 0:
            errors.append(f"ERROR: {paren_balance} unclosed parenthesis/parentheses")
        
        # Check 8: Bracket matching
        bracket_balance = 0
        line_num = 0
        for line in code.split('\n'):
            line_num += 1
            for char in line:
                if char == '[':
                    bracket_balance += 1
                elif char == ']':
                    bracket_balance -= 1
                    if bracket_balance < 0:
                        errors.append(f"ERROR: Unmatched closing bracket at line {line_num}")
                        break
        if bracket_balance > 0:
            errors.append(f"ERROR: {bracket_balance} unclosed bracket(s)")
        
        # Check 9: Invalid port declarations
        invalid_ports = re.findall(r'(input|output|inout)\s+[^\w\s\[\]]+', code)
        if invalid_ports:
            warnings.append(f"WARNING: Potentially invalid port declarations found")
        
        # Check 10: Semicolon after module ports (common error)
        if re.search(r'\bmodule\s+\w+\s*\([^)]*\)\s*;(?!\s*endmodule)', code):
            # This is valid for Verilog-95 style
            pass
        
        # Check 11: Multiple module declarations in same block
        if module_count > 1:
            warnings.append(f"INFO: Multiple modules found ({module_count}). Only the first will be used for testbench generation.")
        
        # Check 12: Empty module
        module_content = re.search(r'module\s+\w+.*?endmodule', code, re.DOTALL)
        if module_content:
            content = module_content.group(0)
            # Check if module has any ports or internal logic
            has_ports = bool(re.search(r'(input|output|inout)', content))
            has_logic = bool(re.search(r'(always|assign|initial|\w+\s+\w+\s*\()', content))
            
            if not has_ports and not has_logic:
                warnings.append("WARNING: Module appears to be empty (no ports or logic found)")
        
        # Check 13: Common syntax errors
        # Missing semicolons (rough check)
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line and not line.startswith('//'):
                # Check for statements that should end with semicolon
                if re.match(r'(input|output|inout|wire|reg|parameter|assign|integer|real)\s+', line):
                    if not line.endswith((';', ',', ')', '(', 'begin', 'end')):
                        if i < len(lines) and not lines[i].strip().startswith((')', ',')):
                            warnings.append(f"WARNING: Line {i} might be missing semicolon: {line[:50]}")
        
        # Combine errors and warnings
        all_messages = errors + warnings
        is_valid = len(errors) == 0
        
        return is_valid, all_messages
    
    @staticmethod
    def _remove_comments(code: str) -> str:
        """Remove single-line and multi-line comments from Verilog code"""
        # Remove single-line comments
        code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
        # Remove multi-line comments
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        return code
    
    @staticmethod
    def get_verilog_version(verilog_code: str) -> str:
        """Detect Verilog version based on syntax features"""
        # SystemVerilog indicators
        if re.search(r'\b(logic|always_ff|always_comb|always_latch|interface|class|package)\b', verilog_code):
            return "SystemVerilog"
        
        # Verilog-2001 indicators
        if re.search(r'\b(localparam|generate|signed|unsigned)\b', verilog_code) or \
           re.search(r'@\(\*\)', verilog_code):  # @(*) sensitivity list
            return "Verilog-2001"
        
        # Default to Verilog-95
        return "Verilog-95"


class VerilogParser:
    """Parse Verilog files to extract module information"""
    
    @staticmethod
    def parse_module(verilog_code: str) -> Dict[str, Any]:
        """Extract module information from Verilog code"""
        module_info = {
            'name': '',
            'inputs': [],
            'outputs': [],
            'inouts': [],
            'parameters': [],
            'regs': [],
            'wires': []
        }
        
        # Extract module name
        module_match = re.search(r'module\s+(\w+)', verilog_code)
        if module_match:
            module_info['name'] = module_match.group(1)
        
        # Extract parameters
        param_pattern = r'parameter\s+(?:\[.*?\]\s+)?(\w+)\s*=\s*([^;,]+)'
        for match in re.finditer(param_pattern, verilog_code):
            module_info['parameters'].append({
                'name': match.group(1),
                'value': match.group(2).strip()
            })
        
        # Extract ports - improved regex to avoid false matches
        # Remove comments first to avoid parsing commented code
        code_no_comments = re.sub(r'//.*?$', '', verilog_code, flags=re.MULTILINE)
        code_no_comments = re.sub(r'/\*.*?\*/', '', code_no_comments, flags=re.DOTALL)
        
        port_patterns = [
            (r'input\s+(?:wire\s+)?(?:\[(\d+):(\d+)\]\s+)?(\w+)\s*[,;)]', 'inputs'),
            (r'output\s+(?:reg|wire\s+)?(?:\[(\d+):(\d+)\]\s+)?(\w+)\s*[,;)]', 'outputs'),
            (r'inout\s+(?:\[(\d+):(\d+)\]\s+)?(\w+)\s*[,;)]', 'inouts')
        ]
        
        for pattern, port_type in port_patterns:
            for match in re.finditer(pattern, code_no_comments):
                port_name = match.group(3)
                # Skip if already added (avoid duplicates)
                if any(p['name'] == port_name for p in module_info[port_type]):
                    continue
                    
                if match.group(1) and match.group(2):
                    width = int(match.group(1)) - int(match.group(2)) + 1
                    module_info[port_type].append({
                        'name': port_name,
                        'width': width,
                        'msb': int(match.group(1)),
                        'lsb': int(match.group(2))
                    })
                else:
                    module_info[port_type].append({
                        'name': port_name,
                        'width': 1,
                        'msb': 0,
                        'lsb': 0
                    })
        
        # Extract internal signals (wires and regs) - avoid parsing comments
        wire_pattern = r'wire\s+(?:\[(\d+):(\d+)\]\s+)?(\w+)\s*[,;]'
        for match in re.finditer(wire_pattern, code_no_comments):
            signal_name = match.group(3)
            # Skip if it's already a port or already added
            if any(signal_name == p['name'] for p in module_info['inputs'] + module_info['outputs'] + module_info['wires']):
                continue
                
            if match.group(1) and match.group(2):
                width = int(match.group(1)) - int(match.group(2)) + 1
                module_info['wires'].append({
                    'name': signal_name,
                    'width': width
                })
            else:
                module_info['wires'].append({
                    'name': signal_name,
                    'width': 1
                })
        
        reg_pattern = r'reg\s+(?:\[(\d+):(\d+)\]\s+)?(\w+)\s*[,;]'
        for match in re.finditer(reg_pattern, code_no_comments):
            signal_name = match.group(3)
            # Skip if it's already a port or already added
            if any(signal_name == p['name'] for p in module_info['outputs'] + module_info['regs']):
                continue
                
            if match.group(1) and match.group(2):
                width = int(match.group(1)) - int(match.group(2)) + 1
                module_info['regs'].append({
                    'name': signal_name,
                    'width': width
                })
            else:
                module_info['regs'].append({
                    'name': signal_name,
                    'width': 1
                })
        
        return module_info


class TestbenchGenerator:
    """Generate automatic testbench for Verilog modules"""
    
    @staticmethod
    def generate_testbench(module_info: Dict[str, Any], test_vectors: int = 100) -> str:
        """Generate comprehensive testbench"""
        module_name = module_info['name']
        tb_name = f"{module_name}_tb"
        
        tb_code = f"""// Automatic Testbench for {module_name}
// Generated by AWaveViewer
//
// IMPORTANT: When using this testbench:
// 1. Save this as a SEPARATE file (e.g., {module_name}_tb.v)
// 2. Keep your module in another file (e.g., {module_name}.v)
// 3. Compile both: iverilog -o sim {module_name}.v {module_name}_tb.v
//
// OR if combining in one file, put the MODULE DEFINITION FIRST,
// then the TESTBENCH second (module must be defined before use)
//
`timescale 1ns/1ps

module {tb_name};

    // Parameters
"""
        
        # Add parameters
        for param in module_info['parameters']:
            tb_code += f"    parameter {param['name']} = {param['value']};\n"
        
        tb_code += "\n    // Inputs\n"
        for inp in module_info['inputs']:
            if inp['width'] > 1:
                tb_code += f"    reg [{inp['msb']}:{inp['lsb']}] {inp['name']};\n"
            else:
                tb_code += f"    reg {inp['name']};\n"
        
        tb_code += "\n    // Outputs\n"
        for out in module_info['outputs']:
            if out['width'] > 1:
                tb_code += f"    wire [{out['msb']}:{out['lsb']}] {out['name']};\n"
            else:
                tb_code += f"    wire {out['name']};\n"
        
        tb_code += "\n    // Inouts\n"
        for inout in module_info['inouts']:
            if inout['width'] > 1:
                tb_code += f"    wire [{inout['msb']}:{inout['lsb']}] {inout['name']};\n"
            else:
                tb_code += f"    wire {inout['name']};\n"
        
        # Instantiate DUT
        tb_code += f"\n    // Instantiate the Unit Under Test (UUT)\n"
        tb_code += f"    {module_name} "
        
        if module_info['parameters']:
            tb_code += "#(\n"
            param_list = [f"        .{p['name']}({p['name']})" for p in module_info['parameters']]
            tb_code += ",\n".join(param_list)
            tb_code += "\n    ) "
        
        tb_code += "uut (\n"
        
        all_ports = module_info['inputs'] + module_info['outputs'] + module_info['inouts']
        port_list = [f"        .{p['name']}({p['name']})" for p in all_ports]
        tb_code += ",\n".join(port_list)
        tb_code += "\n    );\n\n"
        
        # Clock generation (if clock signal exists)
        clock_signals = [inp for inp in module_info['inputs'] if 'clk' in inp['name'].lower() or 'clock' in inp['name'].lower()]
        if clock_signals:
            clk_name = clock_signals[0]['name']
            tb_code += f"""    // Clock generation
    initial begin
        {clk_name} = 0;
        forever #5 {clk_name} = ~{clk_name};  // 100MHz clock
    end
"""
        
        # Reset generation
        reset_signals = [inp for inp in module_info['inputs'] if 'rst' in inp['name'].lower() or 'reset' in inp['name'].lower()]
        if reset_signals:
            rst_name = reset_signals[0]['name']
            tb_code += f"""
    // Reset generation
    initial begin
        {rst_name} = 1;
        #20 {rst_name} = 0;
        #10 {rst_name} = 1;
    end
"""
        
        # Test stimulus
        tb_code += f"""
    // Test stimulus
    integer i;
    initial begin
        // Initialize inputs
"""
        for inp in module_info['inputs']:
            if inp['name'] not in [s['name'] for s in clock_signals + reset_signals]:
                tb_code += f"        {inp['name']} = 0;\n"
        
        tb_code += f"""
        // Wait for reset
        #50;
        
        // Apply test vectors
        for (i = 0; i < {test_vectors}; i = i + 1) begin
"""
        
        for inp in module_info['inputs']:
            if inp['name'] not in [s['name'] for s in clock_signals + reset_signals]:
                if inp['width'] > 1:
                    tb_code += f"            {inp['name']} = $random % (1 << {inp['width']});\n"
                else:
                    tb_code += f"            {inp['name']} = $random % 2;\n"
        
        tb_code += """            #10;
        end
        
        // Finish simulation
        #100;
        $display("Simulation completed successfully");
        $finish;
    end
    
    // Monitor signals
    initial begin
        $monitor("Time=%0t", $time"""
        
        for inp in module_info['inputs']:
            tb_code += f', " {inp["name"]}=%b", {inp["name"]}'
        for out in module_info['outputs']:
            tb_code += f', " {out["name"]}=%b", {out["name"]}'
        
        tb_code += """);
    end
    
    // VCD dump for waveform viewing
    initial begin
        $dumpfile("wave.vcd");
        $dumpvars(0, """ + tb_name + """);
    end

endmodule
"""
        
        return tb_code


class VCDParser:
    """Parse VCD (Value Change Dump) files"""
    
    def __init__(self):
        self.timescale = 1
        self.signals = {}
        self.changes = []
        self.scope_hierarchy = []
        
    def parse(self, vcd_file: str) -> Tuple[Dict, List]:
        """Parse VCD file and return signals and value changes"""
        if not os.path.exists(vcd_file):
            return {}, []
        
        with open(vcd_file, 'r') as f:
            lines = f.readlines()
        
        in_header = True
        current_time = 0
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            if line.startswith('$timescale'):
                # Parse timescale
                match = re.search(r'(\d+)\s*(\w+)', line)
                if match:
                    scale_value = int(match.group(1))
                    scale_unit = match.group(2)
                    unit_map = {'s': 1e0, 'ms': 1e-3, 'us': 1e-6, 'ns': 1e-9, 'ps': 1e-12, 'fs': 1e-15}
                    self.timescale = scale_value * unit_map.get(scale_unit, 1e-9)
            
            elif line.startswith('$scope'):
                parts = line.split()
                if len(parts) >= 3:
                    self.scope_hierarchy.append(parts[2])
            
            elif line.startswith('$upscope'):
                if self.scope_hierarchy:
                    self.scope_hierarchy.pop()
            
            elif line.startswith('$var'):
                # Parse variable declaration
                parts = line.split()
                if len(parts) >= 5:
                    var_type = parts[1]
                    width = int(parts[2])
                    identifier = parts[3]
                    signal_name = parts[4]
                    
                    full_name = '.'.join(self.scope_hierarchy + [signal_name])
                    
                    self.signals[identifier] = {
                        'name': signal_name,
                        'full_name': full_name,
                        'width': width,
                        'type': var_type,
                        'values': []
                    }
                    # Debug: Print parsed signal
                    print(f"DEBUG: Registered signal '{signal_name}' with identifier '{identifier}'")
            
            elif line.startswith('$enddefinitions'):
                in_header = False
            
            elif not in_header:
                if line.startswith('#'):
                    # Time marker
                    current_time = int(line[1:])
                
                elif line[0] in '01xzXZ':
                    # Single bit value change
                    value = line[0]
                    identifier = line[1:].strip()  # Strip whitespace from identifier
                    
                    # Debug: Print each value change
                    print(f"DEBUG: Time {current_time}: value '{value}' for identifier '{identifier}'")
                    
                    if identifier in self.signals:
                        self.signals[identifier]['values'].append((current_time, value))
                        self.changes.append((current_time, identifier, value))
                        print(f"  -> Stored for signal '{self.signals[identifier]['name']}'")
                    else:
                        # Debug: Print unmatched identifiers
                        print(f"  -> ERROR: Identifier '{identifier}' not found! Available: {list(self.signals.keys())}")
                
                elif line[0] == 'b':
                    # Multi-bit value change
                    parts = line.split()
                    if len(parts) >= 2:
                        value = parts[0][1:]  # Remove 'b' prefix
                        identifier = parts[1]
                        
                        if identifier in self.signals:
                            self.signals[identifier]['values'].append((current_time, value))
                            self.changes.append((current_time, identifier, value))
        
        return self.signals, self.changes


class WaveformWidget(QWidget):
    """Custom widget to display waveforms"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.signals = {}
        self.visible_signals = []
        self.time_scale = 10  # pixels per time unit
        self.time_offset = 0
        self.max_time = 1000
        self.grid_enabled = True
        self.cursor_time = None
        self.marker_times = []
        
        self.setMinimumHeight(400)
        self.setMouseTracking(True)
        
        # Colors - more organized palette
        self.bg_color = QColor(15, 23, 42)
        self.grid_color = QColor(51, 65, 85)
        self.grid_major_color = QColor(71, 85, 105)
        self.signal_high = QColor(34, 197, 94)  # Green
        self.signal_low = QColor(100, 116, 139)  # Gray
        self.signal_x = QColor(239, 68, 68)  # Red
        self.signal_z = QColor(251, 191, 36)  # Yellow
        self.signal_bus = QColor(59, 130, 246)  # Blue
        self.text_color = QColor(226, 232, 240)
        self.cursor_color = QColor(251, 191, 36, 180)  # Yellow with transparency
        self.marker_color = QColor(236, 72, 153, 180)  # Pink with transparency
        self.name_bg = QColor(30, 41, 59)
        self.name_bg_alt = QColor(20, 31, 49)
        
    def set_signals(self, signals: Dict, visible_signals: List[str]):
        """Set signals to display"""
        self.signals = signals
        self.visible_signals = visible_signals
        
        # Calculate max time
        self.max_time = 0
        for sig_id in visible_signals:
            if sig_id in signals and signals[sig_id]['values']:
                last_time = signals[sig_id]['values'][-1][0]
                self.max_time = max(self.max_time, last_time)
        
        # Calculate and set widget dimensions based on visible signals and time
        signal_height = 70
        signal_spacing = 5
        total_height = len(visible_signals) * (signal_height + signal_spacing) + 50
        
        # Set minimum height to ensure all signals are visible
        self.setMinimumHeight(max(400, total_height))
        
        # Set minimum width based on time scale to enable horizontal scrolling
        name_width = 200
        total_width = name_width + int(self.max_time * self.time_scale) + 100
        self.setMinimumWidth(max(800, total_width))
        
        self.update()
    
    def paintEvent(self, event):
        """Paint waveforms with legend"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), self.bg_color)
        
        # Draw legend in top-right corner
        self.draw_legend(painter)
        
        if not self.visible_signals:
            painter.setPen(self.text_color)
            painter.drawText(self.rect(), Qt.AlignCenter, "No signals to display")
            return
        
        # Calculate layout
        signal_height = 70
        signal_spacing = 5
        name_width = 250
        wave_x_start = name_width + 15
        wave_width = self.width() - wave_x_start - 20
        
        # Draw time grid
        if self.grid_enabled:
            # Minor grid lines
            painter.setPen(QPen(self.grid_color, 1, Qt.DotLine))
            time_step = max(1, int(50 / self.time_scale))
            for t in range(0, int(self.max_time), time_step):
                x = wave_x_start + int((t - self.time_offset) * self.time_scale)
                if wave_x_start <= x <= wave_x_start + wave_width:
                    painter.drawLine(x, 0, x, self.height())
            
            # Major grid lines
            painter.setPen(QPen(self.grid_major_color, 1))
            major_step = max(1, int(200 / self.time_scale))
            for t in range(0, int(self.max_time), major_step):
                x = wave_x_start + int((t - self.time_offset) * self.time_scale)
                if wave_x_start <= x <= wave_x_start + wave_width:
                    painter.drawLine(x, 0, x, self.height())
                    # Draw time labels
                    painter.setPen(self.text_color)
                    painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
                    painter.drawText(x + 3, 15, f"{t}ns")
                    painter.setPen(QPen(self.grid_major_color, 1))
        
        # Draw signals
        y_pos = 35
        signal_index = 0
        for sig_id in self.visible_signals:
            if sig_id not in self.signals:
                continue
            
            signal = self.signals[sig_id]
            
            # Alternating background colors for signal rows
            bg_color = self.name_bg if signal_index % 2 == 0 else self.name_bg_alt
            painter.fillRect(0, y_pos, name_width, signal_height, bg_color)
            
            # Draw signal name with better styling
            painter.setPen(self.text_color)
            painter.setFont(QFont("Segoe UI", 11, QFont.Bold))
            
            # Draw icon based on signal type
            icon = "[BUS]" if signal['width'] > 1 else "[BIT]"
            painter.drawText(10, y_pos + 25, icon)
            
            # Draw signal name
            signal_name = signal['name']
            if len(signal_name) > 25:
                signal_name = signal_name[:22] + "..."
            painter.drawText(35, y_pos + 25, signal_name)
            
            # Draw width info for buses
            if signal['width'] > 1:
                painter.setFont(QFont("Segoe UI", 9))
                painter.setPen(QColor(148, 163, 184))
                painter.drawText(35, y_pos + 45, f"[{signal['width']-1}:0]")
            
            # Draw separator line with gradient
            gradient = QLinearGradient(0, y_pos + signal_height, self.width(), y_pos + signal_height)
            gradient.setColorAt(0, QColor(51, 65, 85, 50))
            gradient.setColorAt(0.5, QColor(71, 85, 105, 100))
            gradient.setColorAt(1, QColor(51, 65, 85, 50))
            painter.setPen(QPen(QBrush(gradient), 2))
            painter.drawLine(0, y_pos + signal_height, self.width(), y_pos + signal_height)
            
            # Draw waveform
            self.draw_waveform(painter, signal, wave_x_start, y_pos, wave_width, signal_height)
            
            y_pos += signal_height + signal_spacing
            signal_index += 1
        
        # Draw cursor
        if self.cursor_time is not None:
            x = wave_x_start + int((self.cursor_time - self.time_offset) * self.time_scale)
            if wave_x_start <= x <= wave_x_start + wave_width:
                # Draw cursor line with glow effect
                for i in range(3, 0, -1):
                    alpha = int(i * 30)
                    painter.setPen(QPen(QColor(251, 191, 36, alpha), i * 2))
                    painter.drawLine(x, 0, x, self.height())
                
                painter.setPen(QPen(self.cursor_color, 2))
                painter.drawLine(x, 0, x, self.height())
                
                # Draw cursor time label with background
                label_text = f"[T] {self.cursor_time}ns"
                painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
                label_width = 100
                label_height = 25
                label_x = min(x + 5, self.width() - label_width - 5)
                label_y = 5
                
                # Label background
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(251, 191, 36, 200))
                painter.drawRoundedRect(label_x, label_y, label_width, label_height, 5, 5)
                
                # Label text
                painter.setPen(QColor(15, 23, 42))
                painter.drawText(label_x, label_y, label_width, label_height, 
                               Qt.AlignCenter, label_text)
        
        # Draw markers
        for marker_time in self.marker_times:
            x = wave_x_start + int((marker_time - self.time_offset) * self.time_scale)
            if wave_x_start <= x <= wave_x_start + wave_width:
                # Draw marker with glow
                painter.setPen(QPen(self.marker_color, 2, Qt.DashLine))
                painter.drawLine(x, 0, x, self.height())
                
                # Draw marker label
                painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(236, 72, 153, 200))
                painter.drawEllipse(x - 8, 3, 16, 16)
                
                painter.setPen(Qt.white)
                painter.drawText(x - 8, 3, 16, 16, Qt.AlignCenter, "M")
    
    def draw_waveform(self, painter: QPainter, signal: Dict, x_start: int, y_start: int, width: int, height: int):
        """Draw individual waveform"""
        if not signal['values']:
            return
        
        wave_height = height - 10
        y_mid = y_start + height // 2
        y_high = y_start + 5
        y_low = y_start + height - 5
        
        painter.setClipRect(x_start, y_start, width, height)
        
        if signal['width'] == 1:
            # Single-bit signal with clear value labels
            prev_value = None
            prev_time = 0
            prev_x = x_start
            
            # Draw initial state from time 0 if first transition is not at time 0
            if signal['values'] and signal['values'][0][0] > 0:
                initial_value = 'x'  # Unknown before first transition
                first_time = signal['values'][0][0]
                first_x = x_start + int((first_time - self.time_offset) * self.time_scale)
                
                # Draw initial unknown state
                painter.setPen(QPen(self.signal_x, 2))
                painter.drawLine(x_start, y_mid, first_x, y_mid)
                
                # Draw hatched pattern for X
                painter.setPen(QPen(self.signal_x, 1, Qt.DashLine))
                hatch_y_top = y_mid - 15
                hatch_y_bot = y_mid + 15
                painter.drawLine(x_start, hatch_y_top, first_x, hatch_y_bot)
                painter.drawLine(x_start, hatch_y_bot, first_x, hatch_y_top)
            
            for time, value in signal['values']:
                x = x_start + int((time - self.time_offset) * self.time_scale)
                
                if prev_value is not None:
                    segment_width = x - prev_x
                    
                    # Draw previous state with standard lines
                    if prev_value == '1':
                        # HIGH state - green line at top
                        painter.setPen(QPen(self.signal_high, 2))
                        painter.drawLine(prev_x, y_high, x, y_high)
                        
                        # Draw "1" label if segment is wide enough
                        if segment_width > 35:
                            self.draw_value_label(painter, prev_x, x, y_high, "1", self.signal_high)
                    
                    elif prev_value == '0':
                        # LOW state - gray line at bottom
                        painter.setPen(QPen(self.signal_low, 2))
                        painter.drawLine(prev_x, y_low, x, y_low)
                        
                        # Draw "0" label if segment is wide enough
                        if segment_width > 35:
                            self.draw_value_label(painter, prev_x, x, y_low, "0", self.signal_low)
                    
                    elif prev_value in 'xX':
                        # UNKNOWN state - red hatched pattern in middle
                        painter.setPen(QPen(self.signal_x, 2))
                        painter.drawLine(prev_x, y_mid, x, y_mid)
                        
                        # Draw hatched pattern for X
                        painter.setPen(QPen(self.signal_x, 1, Qt.DashLine))
                        hatch_y_top = y_mid - 15
                        hatch_y_bot = y_mid + 15
                        painter.drawLine(prev_x, hatch_y_top, x, hatch_y_bot)
                        painter.drawLine(prev_x, hatch_y_bot, x, hatch_y_top)
                        
                        # Draw "X" label if segment is wide enough
                        if segment_width > 35:
                            self.draw_value_label(painter, prev_x, x, y_mid, "X", self.signal_x)
                    
                    elif prev_value in 'zZ':
                        # HIGH-Z state - yellow dashed line in middle
                        painter.setPen(QPen(self.signal_z, 2, Qt.DashLine))
                        painter.drawLine(prev_x, y_mid, x, y_mid)
                        
                        # Draw "Z" label if segment is wide enough
                        if segment_width > 35:
                            self.draw_value_label(painter, prev_x, x, y_mid, "Z", self.signal_z)
                    
                    # Draw transition edge with glow effect
                    if value == '1':
                        # Transition to HIGH
                        painter.setPen(QPen(self.signal_high, 2))
                        painter.drawLine(x, y_low, x, y_high)
                        # Add glow
                        painter.setPen(QPen(QColor(34, 197, 94, 80), 6))
                        painter.drawLine(x, y_low, x, y_high)
                    elif value == '0':
                        # Transition to LOW
                        painter.setPen(QPen(self.signal_low, 2))
                        painter.drawLine(x, y_high, x, y_low)
                        # Add glow
                        painter.setPen(QPen(QColor(100, 116, 139, 80), 6))
                        painter.drawLine(x, y_high, x, y_low)
                    elif value in 'xX':
                        # Transition to X
                        painter.setPen(QPen(self.signal_x, 2))
                        painter.drawLine(x, y_high, x, y_mid)
                        painter.drawLine(x, y_low, x, y_mid)
                    elif value in 'zZ':
                        # Transition to Z
                        painter.setPen(QPen(self.signal_z, 2, Qt.DashLine))
                        painter.drawLine(x, y_high, x, y_mid)
                        painter.drawLine(x, y_low, x, y_mid)
                
                prev_value = value
                prev_time = time
                prev_x = x
            
            # Draw to end with value label
            if prev_value is not None:
                end_x = x_start + int((self.max_time - self.time_offset) * self.time_scale)
                segment_width = end_x - prev_x
                
                if prev_value == '1':
                    painter.setPen(QPen(self.signal_high, 2))
                    painter.drawLine(prev_x, y_high, end_x, y_high)
                    if segment_width > 35:
                        self.draw_value_label(painter, prev_x, end_x, y_high, "1", self.signal_high)
                elif prev_value == '0':
                    painter.setPen(QPen(self.signal_low, 2))
                    painter.drawLine(prev_x, y_low, end_x, y_low)
                    if segment_width > 35:
                        self.draw_value_label(painter, prev_x, end_x, y_low, "0", self.signal_low)
                elif prev_value in 'xX':
                    painter.setPen(QPen(self.signal_x, 2))
                    painter.drawLine(prev_x, y_mid, end_x, y_mid)
                    # Hatched pattern
                    painter.setPen(QPen(self.signal_x, 1, Qt.DashLine))
                    hatch_y_top = y_mid - 15
                    hatch_y_bot = y_mid + 15
                    painter.drawLine(prev_x, hatch_y_top, end_x, hatch_y_bot)
                    painter.drawLine(prev_x, hatch_y_bot, end_x, hatch_y_top)
                    if segment_width > 35:
                        self.draw_value_label(painter, prev_x, end_x, y_mid, "X", self.signal_x)
                elif prev_value in 'zZ':
                    painter.setPen(QPen(self.signal_z, 2, Qt.DashLine))
                    painter.drawLine(prev_x, y_mid, end_x, y_mid)
                    if segment_width > 35:
                        self.draw_value_label(painter, prev_x, end_x, y_mid, "Z", self.signal_z)
        
        else:
            # Multi-bit signal (bus) - enhanced with X/Z support
            prev_time = 0
            prev_x = x_start
            prev_value = None
            
            # Draw initial state from time 0 if first transition is not at time 0
            if signal['values'] and signal['values'][0][0] > 0:
                initial_value = 'x' * signal['width']  # Unknown before first transition
                first_time = signal['values'][0][0]
                first_x = x_start + int((first_time - self.time_offset) * self.time_scale)
                
                # Draw initial unknown state trapezoid
                bus_gradient = QLinearGradient(x_start, y_high, first_x, y_low)
                bus_gradient.setColorAt(0, QColor(239, 68, 68, 180))  # Red for unknown
                bus_gradient.setColorAt(1, QColor(239, 68, 68, 120))
                
                painter.setPen(QPen(self.signal_x, 2))
                painter.setBrush(bus_gradient)
                
                path = QPainterPath()
                path.moveTo(x_start, y_mid)
                path.lineTo(x_start + 8, y_high)
                path.lineTo(first_x - 8, y_high)
                path.lineTo(first_x, y_mid)
                path.lineTo(first_x - 8, y_low)
                path.lineTo(x_start + 8, y_low)
                path.closeSubpath()
                painter.drawPath(path)
            
            for time, value in signal['values']:
                x = x_start + int((time - self.time_offset) * self.time_scale)
                segment_width = x - prev_x
                
                # Skip drawing if this is the first value (already drawn above or will be drawn)
                if prev_value is None:
                    prev_value = value
                    prev_time = time
                    prev_x = x
                    continue
                
                # Determine color based on value content
                has_x = 'x' in str(value).lower()
                has_z = 'z' in str(value).lower()
                
                if has_x:
                    # Bus contains X values - red gradient
                    bus_gradient = QLinearGradient(prev_x, y_high, x, y_low)
                    bus_gradient.setColorAt(0, QColor(239, 68, 68, 180))  # Red
                    bus_gradient.setColorAt(1, QColor(239, 68, 68, 120))
                    pen_color = self.signal_x
                elif has_z:
                    # Bus contains Z values - yellow gradient
                    bus_gradient = QLinearGradient(prev_x, y_high, x, y_low)
                    bus_gradient.setColorAt(0, QColor(251, 191, 36, 180))  # Yellow
                    bus_gradient.setColorAt(1, QColor(251, 191, 36, 120))
                    pen_color = self.signal_z
                else:
                    # Normal bus - blue gradient
                    bus_gradient = QLinearGradient(prev_x, y_high, x, y_low)
                    bus_gradient.setColorAt(0, QColor(59, 130, 246, 180))
                    bus_gradient.setColorAt(1, QColor(59, 130, 246, 120))
                    pen_color = self.signal_bus
                
                painter.setPen(QPen(pen_color, 2))
                painter.setBrush(bus_gradient)
                
                # Draw trapezoid
                path = QPainterPath()
                path.moveTo(prev_x, y_mid)
                path.lineTo(prev_x + 8, y_high)
                path.lineTo(x - 8, y_high)
                path.lineTo(x, y_mid)
                path.lineTo(x - 8, y_low)
                path.lineTo(prev_x + 8, y_low)
                path.closeSubpath()
                
                painter.drawPath(path)
                
                # Draw value text with background
                if segment_width > 40:  # Only show value if there's enough space
                    text_x = (prev_x + x) // 2
                    
                    # Format value for display
                    try:
                        if has_x:
                            display_text = f"X ({value[:8]}...)" if len(value) > 8 else f"X"
                            text_color = QColor(255, 100, 100)
                        elif has_z:
                            display_text = f"Z ({value[:8]}...)" if len(value) > 8 else f"Z"
                            text_color = QColor(255, 220, 100)
                        else:
                            # Convert binary to hex for normal values
                            hex_val = hex(int(value, 2))[2:].upper()
                            # Also show decimal for small values
                            dec_val = int(value, 2)
                            if signal['width'] <= 8:
                                display_text = f"0x{hex_val} ({dec_val})"
                            else:
                                display_text = f"0x{hex_val}"
                            text_color = QColor(186, 230, 253)
                    except:
                        display_text = value[:10] + "..." if len(value) > 10 else value
                        text_color = QColor(255, 255, 255)
                    
                    # Draw text background with glow
                    painter.setFont(QFont("Consolas", 9, QFont.Bold))
                    text_rect = painter.fontMetrics().boundingRect(display_text)
                    text_bg_width = min(text_rect.width() + 12, segment_width - 20)
                    text_bg_height = text_rect.height() + 6
                    
                    # Glow effect
                    for i in range(2, 0, -1):
                        painter.setPen(Qt.NoPen)
                        painter.setBrush(QColor(pen_color.red(), pen_color.green(), pen_color.blue(), 30 * i))
                        painter.drawRoundedRect(text_x - text_bg_width//2 - i, y_mid - text_bg_height//2 - i,
                                              text_bg_width + i*2, text_bg_height + i*2, 4, 4)
                    
                    # Solid background
                    painter.setBrush(QColor(15, 23, 42, 230))
                    painter.setPen(QPen(pen_color, 1))
                    painter.drawRoundedRect(text_x - text_bg_width//2, y_mid - text_bg_height//2,
                                          text_bg_width, text_bg_height, 4, 4)
                    
                    # Draw text
                    painter.setPen(text_color)
                    painter.drawText(text_x - text_bg_width//2, y_mid - text_bg_height//2,
                                   text_bg_width, text_bg_height,
                                   Qt.AlignCenter, display_text)
                
                prev_time = time
                prev_x = x
                prev_value = value
            
            # Draw last segment to end of timeline
            if prev_value is not None:
                end_x = x_start + int((self.max_time - self.time_offset) * self.time_scale)
                segment_width = end_x - prev_x
                
                if segment_width > 0:
                    # Determine color based on last value content
                    has_x = 'x' in str(prev_value).lower()
                    has_z = 'z' in str(prev_value).lower()
                    
                    if has_x:
                        bus_gradient = QLinearGradient(prev_x, y_high, end_x, y_low)
                        bus_gradient.setColorAt(0, QColor(239, 68, 68, 180))
                        bus_gradient.setColorAt(1, QColor(239, 68, 68, 120))
                        pen_color = self.signal_x
                    elif has_z:
                        bus_gradient = QLinearGradient(prev_x, y_high, end_x, y_low)
                        bus_gradient.setColorAt(0, QColor(251, 191, 36, 180))
                        bus_gradient.setColorAt(1, QColor(251, 191, 36, 120))
                        pen_color = self.signal_z
                    else:
                        bus_gradient = QLinearGradient(prev_x, y_high, end_x, y_low)
                        bus_gradient.setColorAt(0, QColor(59, 130, 246, 180))
                        bus_gradient.setColorAt(1, QColor(59, 130, 246, 120))
                        pen_color = self.signal_bus
                    
                    painter.setPen(QPen(pen_color, 2))
                    painter.setBrush(bus_gradient)
                    
                    # Draw final trapezoid
                    path = QPainterPath()
                    path.moveTo(prev_x, y_mid)
                    path.lineTo(prev_x + 8, y_high)
                    path.lineTo(end_x - 8, y_high)
                    path.lineTo(end_x, y_mid)
                    path.lineTo(end_x - 8, y_low)
                    path.lineTo(prev_x + 8, y_low)
                    path.closeSubpath()
                    painter.drawPath(path)
                    
                    # Draw value text if space permits
                    if segment_width > 40:
                        text_x = (prev_x + end_x) // 2
                        
                        try:
                            if has_x:
                                display_text = "X"
                                text_color = QColor(255, 100, 100)
                            elif has_z:
                                display_text = "Z"
                                text_color = QColor(255, 220, 100)
                            else:
                                hex_val = hex(int(prev_value, 2))[2:].upper()
                                dec_val = int(prev_value, 2)
                                if signal['width'] <= 8:
                                    display_text = f"0x{hex_val} ({dec_val})"
                                else:
                                    display_text = f"0x{hex_val}"
                                text_color = QColor(186, 230, 253)
                        except:
                            display_text = str(prev_value)[:10]
                            text_color = QColor(255, 255, 255)
                        
                        painter.setFont(QFont("Consolas", 9, QFont.Bold))
                        text_rect = painter.fontMetrics().boundingRect(display_text)
                        text_bg_width = min(text_rect.width() + 12, segment_width - 20)
                        text_bg_height = text_rect.height() + 6
                        
                        # Background
                        painter.setBrush(QColor(15, 23, 42, 230))
                        painter.setPen(QPen(pen_color, 1))
                        painter.drawRoundedRect(text_x - text_bg_width//2, y_mid - text_bg_height//2,
                                              text_bg_width, text_bg_height, 4, 4)
                        
                        # Text
                        painter.setPen(text_color)
                        painter.drawText(text_x - text_bg_width//2, y_mid - text_bg_height//2,
                                       text_bg_width, text_bg_height,
                                       Qt.AlignCenter, display_text)
        
        painter.setClipping(False)
    
    def draw_legend(self, painter: QPainter):
        """Draw legend showing signal state colors and meanings"""
        legend_x = self.width() - 180
        legend_y = 10
        legend_width = 170
        legend_height = 140
        
        # Legend background with border
        painter.setPen(QPen(QColor(71, 85, 105), 2))
        painter.setBrush(QColor(20, 31, 49, 230))
        painter.drawRoundedRect(legend_x, legend_y, legend_width, legend_height, 8, 8)
        
        # Legend title
        painter.setPen(QColor(226, 232, 240))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.drawText(legend_x + 10, legend_y + 20, "Signal States")
        
        # Draw legend items
        item_y = legend_y + 35
        item_height = 22
        
        legend_items = [
            ("1", "Logic HIGH", self.signal_high),
            ("0", "Logic LOW", self.signal_low),
            ("X", "Unknown", self.signal_x),
            ("Z", "High-Z", self.signal_z),
        ]
        
        painter.setFont(QFont("Consolas", 9, QFont.Bold))
        
        for label, description, color in legend_items:
            # Draw colored box with value label
            box_x = legend_x + 15
            box_width = 30
            box_height = 18
            
            painter.setPen(QPen(color, 2))
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 80))
            painter.drawRoundedRect(box_x, item_y, box_width, box_height, 3, 3)
            
            # Draw label in box
            painter.setPen(color)
            painter.drawText(box_x, item_y, box_width, box_height, Qt.AlignCenter, label)
            
            # Draw description
            painter.setPen(QColor(200, 200, 200))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(box_x + box_width + 10, item_y + 13, description)
            painter.setFont(QFont("Consolas", 9, QFont.Bold))
            
            item_y += item_height
    
    def draw_value_label(self, painter: QPainter, x_start: int, x_end: int, y_pos: int, 
                         label: str, color: QColor):
        """Draw value label (1, 0, X, Z) on the waveform - Clean and standard"""
        text_x = (x_start + x_end) // 2
        segment_width = x_end - x_start
        
        # Only draw if segment is wide enough
        if segment_width < 30:
            return
        
        # Use standard font for clean appearance
        painter.setFont(QFont("Consolas", 8, QFont.Bold))
        text_rect = painter.fontMetrics().boundingRect(label)
        
        # Compact label background
        bg_width = text_rect.width() + 8
        bg_height = text_rect.height() + 4
        bg_x = text_x - bg_width // 2
        bg_y = y_pos - bg_height // 2
        
        # Simple subtle glow
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(color.red(), color.green(), color.blue(), 60))
        painter.drawRoundedRect(bg_x - 2, bg_y - 2, bg_width + 4, bg_height + 4, 2, 2)
        
        # Clean background
        painter.setBrush(QColor(20, 20, 30, 220))
        painter.setPen(QPen(color, 1))
        painter.drawRoundedRect(bg_x, bg_y, bg_width, bg_height, 2, 2)
        
        # Draw clean text
        painter.setPen(color)
        painter.drawText(bg_x, bg_y, bg_width, bg_height, Qt.AlignCenter, label)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for cursor and show signal values"""
        name_width = 200
        wave_x_start = name_width + 10
        
        if event.pos().x() >= wave_x_start:
            x_offset = event.pos().x() - wave_x_start
            self.cursor_time = int(x_offset / self.time_scale + self.time_offset)
            
            # Build tooltip showing all signal values at cursor time
            if self.visible_signals and self.signals:
                tooltip_text = f"Time: {self.cursor_time} ns\n"
                tooltip_text += "─" * 30 + "\n"
                
                for sig_id in self.visible_signals:
                    if sig_id in self.signals:
                        sig = self.signals[sig_id]
                        value = self.get_value_at_time(sig, self.cursor_time)
                        sig_name = sig['name'][:20]  # Truncate long names
                        
                        # Format value display
                        if sig['width'] == 1:
                            # Single bit - show 0, 1, X, Z
                            if value == '1':
                                value_display = f"1 (HIGH)"
                            elif value == '0':
                                value_display = f"0 (LOW)"
                            elif value in 'xX':
                                value_display = f"X (UNKNOWN)"
                            elif value in 'zZ':
                                value_display = f"Z (HIGH-Z)"
                            else:
                                value_display = str(value)
                        else:
                            # Multi-bit - show hex and decimal
                            try:
                                if 'x' not in str(value).lower() and 'z' not in str(value).lower():
                                    hex_val = hex(int(value, 2))[2:].upper()
                                    dec_val = int(value, 2)
                                    value_display = f"0x{hex_val} ({dec_val})"
                                else:
                                    value_display = str(value)
                            except:
                                value_display = str(value)
                        
                        tooltip_text += f"{sig_name}: {value_display}\n"
                
                self.setToolTip(tooltip_text)
            
            self.update()
    
    def get_value_at_time(self, signal, time):
        """Get signal value at specific time"""
        if not signal['values']:
            return 'X'
        
        # Find value at or before this time
        value = signal['values'][0][1]
        for t, v in signal['values']:
            if t <= time:
                value = v
            else:
                break
        
        return str(value)
    
    def mousePressEvent(self, event):
        """Handle mouse click for markers"""
        if event.button() == Qt.RightButton and self.cursor_time is not None:
            if self.cursor_time not in self.marker_times:
                self.marker_times.append(self.cursor_time)
                self.marker_times.sort()
                self.update()
    
    def wheelEvent(self, event):
        """Handle zoom with mouse wheel"""
        delta = event.angleDelta().y()
        if delta > 0:
            self.time_scale *= 1.2
        else:
            self.time_scale /= 1.2
        
        self.time_scale = max(0.1, min(100, self.time_scale))
        self.update()


class SimulationThread(QThread):
    """Thread for running simulation"""
    
    finished = Signal(bool, str)
    progress = Signal(str)
    
    def __init__(self, verilog_file: str, testbench_file: str, output_dir: str, module_info: Dict):
        super().__init__()
        self.verilog_file = verilog_file
        self.testbench_file = testbench_file
        self.output_dir = output_dir
        self.module_info = module_info
    
    def check_iverilog(self):
        """Check if Icarus Verilog is installed"""
        try:
            result = subprocess.run(['iverilog', '-V'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def run(self):
        """Run simulation - try Icarus Verilog, fallback to built-in generator"""
        try:
            # Check if iverilog is available
            self.progress.emit("Checking for Icarus Verilog...")
            
            if self.check_iverilog():
                # Use Icarus Verilog
                self.run_iverilog_simulation()
            else:
                # Use built-in VCD generator
                self.progress.emit("Icarus Verilog not found. Using built-in VCD generator...")
                self.generate_sample_vcd()
            
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")
    
    def run_iverilog_simulation(self):
        """Run actual Icarus Verilog simulation"""
        try:
            # Compile
            self.progress.emit("Compiling Verilog files...")
            compile_cmd = [
                'iverilog',
                '-o', os.path.join(self.output_dir, 'simulation.vvp'),
                '-g2012',  # SystemVerilog 2012
                self.verilog_file,
                self.testbench_file
            ]
            
            result = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                self.progress.emit("Compilation failed, using built-in generator...")
                self.generate_sample_vcd()
                return
            
            # Simulate
            self.progress.emit("Running simulation...")
            sim_cmd = [
                'vvp',
                os.path.join(self.output_dir, 'simulation.vvp')
            ]
            
            result = subprocess.run(sim_cmd, capture_output=True, text=True, cwd=self.output_dir, timeout=60)
            if result.returncode != 0:
                self.progress.emit("Simulation failed, using built-in generator...")
                self.generate_sample_vcd()
                return
            
            self.progress.emit("Simulation completed successfully!")
            self.finished.emit(True, result.stdout)
            
        except subprocess.TimeoutExpired:
            self.progress.emit("Simulation timeout, using built-in generator...")
            self.generate_sample_vcd()
        except Exception as e:
            self.progress.emit(f"Simulation error: {str(e)}, using built-in generator...")
            self.generate_sample_vcd()
    
    def generate_sample_vcd(self):
        """Generate sample VCD file for demonstration"""
        import random
        
        self.progress.emit("Generating sample waveform data...")
        
        vcd_content = "$date\n"
        vcd_content += "   October 1, 2025\n"
        vcd_content += "$end\n"
        vcd_content += "$version\n"
        vcd_content += "   AWaveViewer Built-in Generator\n"
        vcd_content += "$end\n"
        vcd_content += "$timescale 1ns $end\n"
        
        # Add scope
        module_name = self.module_info.get('name', 'testbench')
        vcd_content += f"$scope module {module_name}_tb $end\n"
        vcd_content += f"$scope module uut $end\n"
        
        # Add variables
        var_id = 33  # Start with '!'
        signal_map = {}
        
        # Add inputs
        for inp in self.module_info.get('inputs', []):
            sig_id = chr(var_id)
            var_id += 1
            # Convert width to int for calculations
            width_int = int(inp['width']) if inp['width'] else 1
            signal_map[inp['name']] = {'id': sig_id, 'width': width_int, 'type': 'input'}
            vcd_content += f"$var wire {width_int} {sig_id} {inp['name']} $end\n"
        
        # Add outputs
        for out in self.module_info.get('outputs', []):
            sig_id = chr(var_id)
            var_id += 1
            # Convert width to int for calculations
            width_int = int(out['width']) if out['width'] else 1
            signal_map[out['name']] = {'id': sig_id, 'width': width_int, 'type': 'output'}
            vcd_content += f"$var wire {width_int} {sig_id} {out['name']} $end\n"
        
        vcd_content += "$upscope $end\n"
        vcd_content += "$upscope $end\n"
        vcd_content += "$enddefinitions $end\n"
        
        # Generate initial values
        vcd_content += "#0\n"
        vcd_content += "$dumpvars\n"
        for sig_name, sig_info in signal_map.items():
            if sig_info['width'] == 1:
                vcd_content += f"0{sig_info['id']}\n"
            else:
                vcd_content += f"b{'0' * sig_info['width']} {sig_info['id']}\n"
        vcd_content += "$end\n"
        
        # Generate waveform data
        current_values = {name: 0 for name in signal_map.keys()}
        
        # Find clock signal
        clock_signals = [name for name in signal_map.keys() if 'clk' in name.lower() or 'clock' in name.lower()]
        reset_signals = [name for name in signal_map.keys() if 'rst' in name.lower() or 'reset' in name.lower()]
        
        # Generate time steps
        for t in range(0, 1000, 5):
            vcd_content += f"#{t}\n"
            
            # Toggle clock
            if clock_signals:
                clk_name = clock_signals[0]
                current_values[clk_name] = 1 - current_values[clk_name]
                vcd_content += f"{current_values[clk_name]}{signal_map[clk_name]['id']}\n"
            
            # Handle reset
            if reset_signals and t < 50:
                rst_name = reset_signals[0]
                current_values[rst_name] = 1 if t < 20 else 0
                vcd_content += f"{current_values[rst_name]}{signal_map[rst_name]['id']}\n"
            
            # Random changes for other signals (every 20ns)
            if t % 20 == 0 and t > 50:
                for sig_name, sig_info in signal_map.items():
                    if sig_name not in clock_signals + reset_signals:
                        if random.random() > 0.7:  # 30% chance of change
                            if sig_info['width'] == 1:
                                current_values[sig_name] = random.randint(0, 1)
                                vcd_content += f"{current_values[sig_name]}{sig_info['id']}\n"
                            else:
                                max_val = (1 << sig_info['width']) - 1
                                current_values[sig_name] = random.randint(0, max_val)
                                bin_val = bin(current_values[sig_name])[2:].zfill(sig_info['width'])
                                vcd_content += f"b{bin_val} {sig_info['id']}\n"
        
        # Write VCD file
        vcd_path = os.path.join(self.output_dir, 'wave.vcd')
        with open(vcd_path, 'w') as f:
            f.write(vcd_content)
        
        output_msg = f"Built-in VCD generator completed\n"
        output_msg += f"Generated waveform for module: {module_name}\n"
        output_msg += f"Signals: {len(signal_map)}\n"
        output_msg += f"Time range: 0-1000ns\n"
        output_msg += f"\nNote: This is sample data. Install Icarus Verilog for actual simulation.\n"
        
        self.progress.emit("Sample VCD generated successfully!")
        self.finished.emit(True, output_msg)


class AWaveViewer(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AWaveViewer Professional - Verilog Waveform Viewer | Algo Science Lab")
        
        # Set application icon using resource_path for PyInstaller compatibility
        icon_path = resource_path('logo.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.setGeometry(100, 100, 1600, 900)
        self.setMinimumSize(1200, 700)
        
        self.verilog_file = None
        self.module_info = None
        self.testbench_code = None
        self.vcd_file = None
        self.temp_dir = tempfile.mkdtemp()
        
        # Initialize theme manager
        self.theme_manager = ThemeManager()
        self.current_theme = "Deep Black Green"
        self.current_opacity = 0.95
        
        # Syntax highlighter (will be set after editor is created)
        self.syntax_highlighter = None
        
        self.setup_ui()
        self.apply_themed_style()
        
        # Set initial status message
        self.statusBar.showMessage("Ready | AWaveViewer Professional Edition", 3000)
    
    def setup_ui(self):
        """Setup organized user interface with tabs"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Toolbar
        self.create_toolbar()
        
        # Create tab widget for organized sections
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setDocumentMode(True)
        
        # Tab 1: Design & Testbench
        design_tab = self.create_design_tab()
        self.tab_widget.addTab(design_tab, "[Design & Testbench]")
        
        # Tab 2: Simulation
        simulation_tab = self.create_simulation_tab()
        self.tab_widget.addTab(simulation_tab, "[Simulation]")
        
        # Tab 3: Waveform Viewer
        waveform_tab = self.create_waveform_tab()
        self.tab_widget.addTab(waveform_tab, "[Waveform Viewer]")
        
        main_layout.addWidget(self.tab_widget)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
    
    def create_design_tab(self):
        """Create design and testbench tab"""
        design_widget = QWidget()
        design_layout = QVBoxLayout(design_widget)
        design_layout.setContentsMargins(10, 10, 10, 10)
        design_layout.setSpacing(10)
        
        # Top section: Code editors
        code_splitter = QSplitter(Qt.Horizontal)
        
        # Verilog code editor
        verilog_container = QWidget()
        verilog_main_layout = QVBoxLayout(verilog_container)
        verilog_main_layout.setContentsMargins(0, 0, 0, 0)
        verilog_main_layout.setSpacing(5)
        
        verilog_group = QGroupBox(">> Verilog Source Code")
        verilog_layout = QVBoxLayout()
        verilog_layout.setSpacing(8)
        
        self.verilog_editor = CodeEditor()
        self.verilog_editor.setPlaceholderText("Load or paste your Verilog code here...")
        verilog_layout.addWidget(self.verilog_editor)
        
        # Add syntax highlighter to Verilog editor
        self.syntax_highlighter = VerilogSyntaxHighlighter(self.verilog_editor.document(), "Dark Blue")
        
        verilog_buttons = QHBoxLayout()
        verilog_buttons.setSpacing(10)
        
        self.load_btn = QPushButton("[ ] Load Verilog File")
        self.load_btn.setMinimumHeight(40)
        self.load_btn.clicked.connect(self.load_verilog_file)
        
        self.parse_btn = QPushButton("[*] Parse Module")
        self.parse_btn.setMinimumHeight(40)
        self.parse_btn.clicked.connect(self.parse_verilog)
        
        self.check_syntax_btn = QPushButton("[Check] Syntax Check")
        self.check_syntax_btn.setMinimumHeight(40)
        self.check_syntax_btn.clicked.connect(self.check_verilog_syntax)
        
        verilog_buttons.addWidget(self.load_btn)
        verilog_buttons.addWidget(self.parse_btn)
        verilog_buttons.addWidget(self.check_syntax_btn)
        verilog_layout.addLayout(verilog_buttons)
        
        verilog_group.setLayout(verilog_layout)
        verilog_main_layout.addWidget(verilog_group)
        
        code_splitter.addWidget(verilog_container)
        
        # Testbench editor
        tb_container = QWidget()
        tb_main_layout = QVBoxLayout(tb_container)
        tb_main_layout.setContentsMargins(0, 0, 0, 0)
        tb_main_layout.setSpacing(5)
        
        tb_group = QGroupBox(">> Automatic Testbench")
        tb_layout = QVBoxLayout()
        tb_layout.setSpacing(8)
        
        self.tb_editor = CodeEditor()
        self.tb_editor.setPlaceholderText("Testbench will be generated here...")
        self.tb_editor.setReadOnly(True)
        tb_layout.addWidget(self.tb_editor)
        
        # Add syntax highlighter to testbench editor
        self.tb_syntax_highlighter = VerilogSyntaxHighlighter(self.tb_editor.document(), "Dark Blue")
        
        tb_controls = QHBoxLayout()
        tb_controls.setSpacing(10)
        
        self.gen_tb_btn = QPushButton("[+] Generate Testbench")
        self.gen_tb_btn.setMinimumHeight(40)
        self.gen_tb_btn.clicked.connect(self.generate_testbench)
        self.gen_tb_btn.setEnabled(False)
        
        tb_controls.addWidget(self.gen_tb_btn)
        
        tb_vectors_layout = QHBoxLayout()
        tb_vectors_layout.setSpacing(5)
        self.test_vectors_label = QLabel("Test Vectors:")
        self.test_vectors_spin = QSpinBox()
        self.test_vectors_spin.setRange(10, 10000)
        self.test_vectors_spin.setValue(100)
        self.test_vectors_spin.setMinimumWidth(100)
        tb_vectors_layout.addWidget(self.test_vectors_label)
        tb_vectors_layout.addWidget(self.test_vectors_spin)
        
        tb_controls.addLayout(tb_vectors_layout)
        tb_controls.addStretch()
        
        tb_layout.addLayout(tb_controls)
        
        tb_group.setLayout(tb_layout)
        tb_main_layout.addWidget(tb_group)
        
        code_splitter.addWidget(tb_container)
        
        # Set equal sizes
        code_splitter.setSizes([500, 500])
        
        design_layout.addWidget(code_splitter, 1)
        
        return design_widget
    
    def create_simulation_tab(self):
        """Create simulation tab"""
        sim_widget = QWidget()
        sim_layout = QVBoxLayout(sim_widget)
        sim_layout.setContentsMargins(10, 10, 10, 10)
        sim_layout.setSpacing(10)
        
        # Module information section
        info_group = QGroupBox(">> Module Information")
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        
        self.info_tree = QTreeWidget()
        self.info_tree.setHeaderLabels(["Signal", "Type", "Width", "Details"])
        self.info_tree.setColumnWidth(0, 250)
        self.info_tree.setColumnWidth(1, 120)
        self.info_tree.setColumnWidth(2, 80)
        self.info_tree.setAlternatingRowColors(True)
        info_layout.addWidget(self.info_tree)
        
        info_group.setLayout(info_layout)
        sim_layout.addWidget(info_group, 2)
        
        # Simulation control section
        sim_control_group = QGroupBox("▶️ Simulation Control")
        sim_control_layout = QVBoxLayout()
        sim_control_layout.setSpacing(10)
        
        # Run button
        self.run_sim_btn = QPushButton("▶️ Run Simulation")
        self.run_sim_btn.setMinimumHeight(50)
        self.run_sim_btn.clicked.connect(self.run_simulation)
        self.run_sim_btn.setEnabled(False)
        self.run_sim_btn.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: bold;
            }
        """)
        sim_control_layout.addWidget(self.run_sim_btn)
        
        # Progress bar
        self.sim_progress = QProgressBar()
        self.sim_progress.setVisible(False)
        self.sim_progress.setMinimumHeight(30)
        self.sim_progress.setTextVisible(True)
        sim_control_layout.addWidget(self.sim_progress)
        
        # Output section
        output_label = QLabel("📄 Simulation Output:")
        output_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        sim_control_layout.addWidget(output_label)
        
        self.sim_output = QTextEdit()
        self.sim_output.setReadOnly(True)
        self.sim_output.setFont(QFont("Consolas", 9))
        self.sim_output.setPlaceholderText("Simulation output will appear here...")
        sim_control_layout.addWidget(self.sim_output)
        
        sim_control_group.setLayout(sim_control_layout)
        sim_layout.addWidget(sim_control_group, 1)
        
        return sim_widget
    
    def create_waveform_tab(self):
        """Create enhanced waveform viewer tab with verification features"""
        wave_widget = QWidget()
        wave_layout = QVBoxLayout(wave_widget)
        wave_layout.setContentsMargins(10, 10, 10, 10)
        wave_layout.setSpacing(10)
        
        # === ENHANCED WAVEFORM CONTROLS ===
        controls_group = QGroupBox("🎛️ Waveform Controls & Analysis")
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(8)
        
        # First row - File and zoom controls
        controls_row1 = QHBoxLayout()
        controls_row1.setSpacing(10)
        
        self.load_vcd_btn = QPushButton("📂 Load VCD")
        self.load_vcd_btn.setMinimumHeight(40)
        self.load_vcd_btn.clicked.connect(self.load_vcd_file)
        
        self.zoom_in_btn = QPushButton("[+] Zoom In")
        self.zoom_in_btn.setMinimumHeight(40)
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        
        self.zoom_out_btn = QPushButton("[-] Zoom Out")
        self.zoom_out_btn.setMinimumHeight(40)
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        
        self.fit_btn = QPushButton("📏 Fit All")
        self.fit_btn.setMinimumHeight(40)
        self.fit_btn.clicked.connect(self.fit_all)
        
        self.grid_check = QCheckBox("🔲 Grid")
        self.grid_check.setChecked(True)
        self.grid_check.stateChanged.connect(self.toggle_grid)
        
        controls_row1.addWidget(self.load_vcd_btn)
        controls_row1.addWidget(self.zoom_in_btn)
        controls_row1.addWidget(self.zoom_out_btn)
        controls_row1.addWidget(self.fit_btn)
        controls_row1.addWidget(self.grid_check)
        controls_row1.addStretch()
        
        # Second row - Verification and comparison tools
        controls_row2 = QHBoxLayout()
        controls_row2.setSpacing(10)
        
        self.add_marker_btn = QPushButton("📍 Add Marker")
        self.add_marker_btn.setMinimumHeight(35)
        self.add_marker_btn.clicked.connect(self.add_marker)
        self.add_marker_btn.setToolTip("Add marker at cursor position")
        
        self.clear_markers_btn = QPushButton("🗑️ Clear Markers")
        self.clear_markers_btn.setMinimumHeight(35)
        self.clear_markers_btn.clicked.connect(self.clear_markers)
        
        self.measure_btn = QPushButton("📏 Measure")
        self.measure_btn.setMinimumHeight(35)
        self.measure_btn.setCheckable(True)
        self.measure_btn.clicked.connect(self.toggle_measure_mode)
        self.measure_btn.setToolTip("Measure time between two points")
        
        self.compare_btn = QPushButton("⚖️ Compare Signals")
        self.compare_btn.setMinimumHeight(35)
        self.compare_btn.clicked.connect(self.compare_signals)
        self.compare_btn.setToolTip("Compare selected signals for verification")
        
        self.verify_btn = QPushButton("✓ Auto Verify")
        self.verify_btn.setMinimumHeight(35)
        self.verify_btn.clicked.connect(self.auto_verify_logic)
        self.verify_btn.setToolTip("Automatically verify logic patterns")
        
        self.export_btn = QPushButton("💾 Export")
        self.export_btn.setMinimumHeight(35)
        self.export_btn.clicked.connect(self.export_waveform)
        self.export_btn.setToolTip("Export waveform as image or data")
        
        self.inspect_btn = QPushButton("🔍 Inspect Values")
        self.inspect_btn.setMinimumHeight(35)
        self.inspect_btn.clicked.connect(self.inspect_values_at_cursor)
        self.inspect_btn.setToolTip("Show detailed signal values at cursor position")
        
        controls_row2.addWidget(self.add_marker_btn)
        controls_row2.addWidget(self.clear_markers_btn)
        controls_row2.addWidget(self.measure_btn)
        controls_row2.addWidget(self.compare_btn)
        controls_row2.addWidget(self.verify_btn)
        controls_row2.addWidget(self.export_btn)
        controls_row2.addWidget(self.inspect_btn)
        controls_row2.addStretch()
        
        controls_layout.addLayout(controls_row1)
        controls_layout.addLayout(controls_row2)
        
        controls_group.setLayout(controls_layout)
        wave_layout.addWidget(controls_group)
        
        # === MAIN DISPLAY AREA WITH 3 PANELS ===
        main_splitter = QSplitter(Qt.Horizontal)
        
        # === LEFT PANEL: HIERARCHICAL SIGNAL TREE ===
        left_panel = QWidget()
        left_panel_layout = QVBoxLayout(left_panel)
        left_panel_layout.setContentsMargins(5, 5, 5, 5)
        left_panel_layout.setSpacing(5)
        
        signal_header = QLabel("🌳 Signal Hierarchy")
        signal_header.setStyleSheet("font-weight: bold; font-size: 13px; color: rgb(0, 255, 100);")
        left_panel_layout.addWidget(signal_header)
        
        # Search bar for signals
        search_layout = QHBoxLayout()
        self.signal_search = QLineEdit()
        self.signal_search.setPlaceholderText("🔍 Search signals...")
        self.signal_search.textChanged.connect(self.filter_signals)
        self.signal_search.setMinimumHeight(30)
        search_layout.addWidget(self.signal_search)
        left_panel_layout.addLayout(search_layout)
        
        # Signal tree control buttons
        signal_btn_layout = QHBoxLayout()
        signal_btn_layout.setSpacing(5)
        
        self.expand_all_btn = QPushButton("[+] Expand")
        self.expand_all_btn.setMaximumHeight(28)
        self.expand_all_btn.clicked.connect(self.expand_all_signals)
        signal_btn_layout.addWidget(self.expand_all_btn)
        
        self.collapse_all_btn = QPushButton("[-] Collapse")
        self.collapse_all_btn.setMaximumHeight(28)
        self.collapse_all_btn.clicked.connect(self.collapse_all_signals)
        signal_btn_layout.addWidget(self.collapse_all_btn)
        
        self.select_all_btn = QPushButton("☑ Select All")
        self.select_all_btn.setMaximumHeight(28)
        self.select_all_btn.clicked.connect(self.select_all_signals)
        signal_btn_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("☐ Clear")
        self.deselect_all_btn.setMaximumHeight(28)
        self.deselect_all_btn.clicked.connect(self.deselect_all_signals)
        signal_btn_layout.addWidget(self.deselect_all_btn)
        
        left_panel_layout.addLayout(signal_btn_layout)
        
        # Enhanced hierarchical signal tree
        self.signal_list = QTreeWidget()
        self.signal_list.setHeaderLabels(["Signal", "Type", "Width", "Value"])
        self.signal_list.setColumnWidth(0, 220)
        self.signal_list.setColumnWidth(1, 70)
        self.signal_list.setColumnWidth(2, 60)
        self.signal_list.setColumnWidth(3, 90)
        self.signal_list.setMaximumWidth(480)
        self.signal_list.setMinimumWidth(400)
        self.signal_list.setAlternatingRowColors(True)
        self.signal_list.itemChanged.connect(self.signal_selection_changed)
        self.signal_list.itemDoubleClicked.connect(self.signal_double_clicked)
        left_panel_layout.addWidget(self.signal_list)
        
        # Signal statistics
        stats_label = QLabel("📊 Statistics:")
        stats_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        left_panel_layout.addWidget(stats_label)
        
        self.signal_stats = QTextEdit()
        self.signal_stats.setReadOnly(True)
        self.signal_stats.setMaximumHeight(120)
        self.signal_stats.setPlaceholderText("Select signals to view statistics...")
        self.signal_stats.setStyleSheet("font-size: 10px; font-family: Consolas;")
        left_panel_layout.addWidget(self.signal_stats)
        
        main_splitter.addWidget(left_panel)
        
        # === CENTER PANEL: WAVEFORM DISPLAY ===
        center_panel = QWidget()
        center_panel_layout = QVBoxLayout(center_panel)
        center_panel_layout.setContentsMargins(5, 5, 5, 5)
        center_panel_layout.setSpacing(5)
        
        waveform_header = QLabel("📈 Waveform Display")
        waveform_header.setStyleSheet("font-weight: bold; font-size: 13px; color: rgb(0, 255, 100);")
        center_panel_layout.addWidget(waveform_header)
        
        # Time and cursor info bar
        info_bar = QHBoxLayout()
        info_bar.setSpacing(15)
        
        self.time_info = QLabel("⏱️ Time: 0 ns")
        self.time_info.setStyleSheet("font-weight: bold; color: rgb(251, 191, 36);")
        info_bar.addWidget(self.time_info)
        
        self.cursor_info = QLabel("📍 Cursor: -- ns")
        self.cursor_info.setStyleSheet("font-weight: bold; color: rgb(251, 191, 36);")
        info_bar.addWidget(self.cursor_info)
        
        self.delta_info = QLabel("Δ Delta: -- ns")
        self.delta_info.setStyleSheet("font-weight: bold; color: rgb(236, 72, 153);")
        info_bar.addWidget(self.delta_info)
        
        info_bar.addStretch()
        center_panel_layout.addLayout(info_bar)
        
        # Waveform scroll area with both scrollbars
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.waveform_widget = WaveformWidget()
        scroll_area.setWidget(self.waveform_widget)
        center_panel_layout.addWidget(scroll_area)
        
        main_splitter.addWidget(center_panel)
        
        # === RIGHT PANEL: VERIFICATION & ANALYSIS WITH SCROLLBAR ===
        right_panel = QWidget()
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setContentsMargins(5, 5, 5, 5)
        right_panel_layout.setSpacing(5)
        
        analysis_header = QLabel("🔍 Analysis & Verification")
        analysis_header.setStyleSheet("font-weight: bold; font-size: 13px; color: rgb(0, 255, 100);")
        right_panel_layout.addWidget(analysis_header)
        
        # Create scrollable area for all analysis widgets
        scroll_container = QScrollArea()
        scroll_container.setWidgetResizable(True)
        scroll_container.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_container.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Container widget for scrollable content
        scroll_content = QWidget()
        scroll_content_layout = QVBoxLayout(scroll_content)
        scroll_content_layout.setSpacing(8)
        scroll_content_layout.setContentsMargins(5, 5, 5, 5)
        
        # === MARKERS LIST ===
        markers_group = QGroupBox("📍 Markers")
        markers_layout = QVBoxLayout()
        markers_layout.setSpacing(5)
        
        self.markers_list = QTreeWidget()
        self.markers_list.setHeaderLabels(["Time (ns)", "Label"])
        self.markers_list.setMinimumHeight(120)
        self.markers_list.setMaximumHeight(180)
        self.markers_list.setAlternatingRowColors(True)
        self.markers_list.itemDoubleClicked.connect(self.jump_to_marker)
        markers_layout.addWidget(self.markers_list)
        
        markers_btn_layout = QHBoxLayout()
        self.delete_marker_btn = QPushButton("🗑️ Delete")
        self.delete_marker_btn.setMaximumHeight(28)
        self.delete_marker_btn.clicked.connect(self.delete_selected_marker)
        markers_btn_layout.addWidget(self.delete_marker_btn)
        
        self.rename_marker_btn = QPushButton("✏️ Rename")
        self.rename_marker_btn.setMaximumHeight(28)
        self.rename_marker_btn.clicked.connect(self.rename_marker)
        markers_btn_layout.addWidget(self.rename_marker_btn)
        markers_layout.addLayout(markers_btn_layout)
        
        markers_group.setLayout(markers_layout)
        scroll_content_layout.addWidget(markers_group)
        
        # === LOGIC ANALYSIS PANEL ===
        logic_group = QGroupBox("🔬 Logic Analysis")
        logic_layout = QVBoxLayout()
        logic_layout.setSpacing(5)
        
        # Logic detection button
        self.analyze_logic_btn = QPushButton("🔍 Analyze Logic Relations")
        self.analyze_logic_btn.setMinimumHeight(32)
        self.analyze_logic_btn.clicked.connect(self.analyze_logic_relations)
        self.analyze_logic_btn.setStyleSheet("""
            QPushButton {
                background-color: rgb(59, 130, 246);
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgb(96, 165, 250);
            }
        """)
        logic_layout.addWidget(self.analyze_logic_btn)
        
        # Detected gates display
        gates_label = QLabel("Detected Logic:")
        gates_label.setStyleSheet("font-size: 10px; font-weight: bold;")
        logic_layout.addWidget(gates_label)
        
        self.detected_gates = QTextEdit()
        self.detected_gates.setReadOnly(True)
        self.detected_gates.setMinimumHeight(80)
        self.detected_gates.setMaximumHeight(120)
        self.detected_gates.setPlaceholderText("Click 'Analyze' to detect logic gates...")
        self.detected_gates.setStyleSheet("font-size: 9px; font-family: Consolas;")
        logic_layout.addWidget(self.detected_gates)
        
        # Truth table display
        truth_label = QLabel("Truth Table:")
        truth_label.setStyleSheet("font-size: 10px; font-weight: bold;")
        logic_layout.addWidget(truth_label)
        
        self.truth_table = QTreeWidget()
        self.truth_table.setHeaderLabels(["Inputs", "→", "Output", "Logic"])
        self.truth_table.setColumnWidth(0, 80)
        self.truth_table.setColumnWidth(1, 20)
        self.truth_table.setColumnWidth(2, 50)
        self.truth_table.setColumnWidth(3, 70)
        self.truth_table.setMinimumHeight(150)
        self.truth_table.setMaximumHeight(250)
        self.truth_table.setAlternatingRowColors(True)
        logic_layout.addWidget(self.truth_table)
        
        logic_group.setLayout(logic_layout)
        scroll_content_layout.addWidget(logic_group)
        
        # === VERIFICATION RESULTS ===
        verify_group = QGroupBox("✓ Verification Results")
        verify_layout = QVBoxLayout()
        verify_layout.setSpacing(5)
        
        self.verify_results = QTextEdit()
        self.verify_results.setReadOnly(True)
        self.verify_results.setMinimumHeight(150)
        self.verify_results.setMaximumHeight(250)
        self.verify_results.setPlaceholderText("Verification results will appear here...\n\n• Compare signals\n• Check logic patterns\n• Verify timing")
        self.verify_results.setStyleSheet("font-size: 10px; font-family: Consolas;")
        verify_layout.addWidget(self.verify_results)
        
        verify_group.setLayout(verify_layout)
        scroll_content_layout.addWidget(verify_group)
        
        # === SIGNAL COMPARISON ===
        compare_group = QGroupBox("⚖️ Signal Comparison")
        compare_layout = QVBoxLayout()
        compare_layout.setSpacing(5)
        
        self.compare_table = QTreeWidget()
        self.compare_table.setHeaderLabels(["Property", "Signal A", "Signal B"])
        self.compare_table.setColumnWidth(0, 100)
        self.compare_table.setColumnWidth(1, 80)
        self.compare_table.setColumnWidth(2, 80)
        self.compare_table.setMinimumHeight(150)
        self.compare_table.setMaximumHeight(250)
        self.compare_table.setAlternatingRowColors(True)
        compare_layout.addWidget(self.compare_table)
        
        compare_group.setLayout(compare_layout)
        scroll_content_layout.addWidget(compare_group)
        
        scroll_content_layout.addStretch()
        
        # Set scroll content and add to scroll area
        scroll_container.setWidget(scroll_content)
        right_panel_layout.addWidget(scroll_container)
        
        main_splitter.addWidget(right_panel)
        
        # Set splitter sizes (left: signal tree, center: waveform, right: analysis)
        main_splitter.setSizes([380, 800, 340])
        
        wave_layout.addWidget(main_splitter, 1)
        
        return wave_widget
    
    def create_toolbar(self):
        """Create gorgeous professional toolbar with enhanced visual effects"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(28, 28))
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)
        
        # Add gorgeous gradient effect to toolbar
        toolbar.setStyleSheet("""
            QToolBar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(30, 41, 59, 0.95),
                    stop:0.5 rgba(15, 23, 42, 0.98),
                    stop:1 rgba(30, 41, 59, 0.95));
                border: none;
                border-bottom: 3px solid;
                border-image: linear-gradient(90deg, 
                    #3b82f6 0%, #8b5cf6 25%, #ec4899 50%, #8b5cf6 75%, #3b82f6 100%) 1;
                spacing: 12px;
                padding: 10px;
            }
            QToolButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(59, 130, 246, 0.2),
                    stop:1 rgba(139, 92, 246, 0.2));
                color: #f1f5f9;
                border: 2px solid transparent;
                border-radius: 8px;
                padding: 10px 14px;
                font-weight: bold;
                font-size: 13px;
            }
            QToolButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(59, 130, 246, 0.5),
                    stop:1 rgba(139, 92, 246, 0.5));
                border: 2px solid rgba(147, 197, 253, 0.7);
                color: #ffffff;
            }
            QToolButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #8b5cf6);
                border: 2px solid #60a5fa;
            }
            QToolBar::separator {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(59, 130, 246, 0.3),
                    stop:0.5 rgba(236, 72, 153, 0.5),
                    stop:1 rgba(139, 92, 246, 0.3));
                width: 3px;
                margin: 10px 8px;
                border-radius: 2px;
            }
            QLabel {
                color: #93c5fd;
                font-weight: bold;
                font-size: 12px;
            }
            QComboBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(30, 41, 59, 0.9),
                    stop:1 rgba(15, 23, 42, 0.9));
                color: #f1f5f9;
                border: 2px solid rgba(59, 130, 246, 0.5);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QComboBox:hover {
                border: 2px solid rgba(147, 197, 253, 0.8);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(59, 130, 246, 0.3),
                    stop:1 rgba(139, 92, 246, 0.3));
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 7px solid #93c5fd;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: rgba(30, 41, 59, 0.98);
                color: #f1f5f9;
                selection-background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #8b5cf6);
                border: 2px solid #3b82f6;
                border-radius: 6px;
                padding: 4px;
            }
            QSlider::groove:horizontal {
                border: 2px solid rgba(59, 130, 246, 0.4);
                height: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(30, 41, 59, 0.8),
                    stop:1 rgba(15, 23, 42, 0.8));
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #60a5fa,
                    stop:0.5 #8b5cf6,
                    stop:1 #ec4899);
                border: 2px solid #93c5fd;
                width: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #93c5fd,
                    stop:0.5 #a78bfa,
                    stop:1 #f472b6);
                border: 3px solid #bfdbfe;
            }
        """)
        
        # File menu with gorgeous styling
        file_menu = self.menuBar().addMenu("📁 &File")
        
        # Open Verilog action
        open_action = QAction("📄 Open Verilog", self)
        open_action.setShortcut("Ctrl+O")
        open_action.setStatusTip("Open Verilog source file (.v, .sv)")
        open_action.triggered.connect(self.load_verilog_file)
        file_menu.addAction(open_action)
        toolbar.addAction(open_action)
        
        file_menu.addSeparator()
        
        # Load Testbench action (in File menu too)
        load_tb_file_action = QAction("📥 Load Testbench", self)
        load_tb_file_action.setShortcut("Ctrl+Shift+O")
        load_tb_file_action.setStatusTip("Load existing testbench file (.v, .sv)")
        load_tb_file_action.triggered.connect(self.load_testbench)
        file_menu.addAction(load_tb_file_action)
        
        # Save Testbench action
        save_tb_action = QAction("💾 Save Testbench", self)
        save_tb_action.setShortcut("Ctrl+S")
        save_tb_action.setStatusTip("Save generated testbench to file")
        save_tb_action.triggered.connect(self.save_testbench)
        file_menu.addAction(save_tb_action)
        toolbar.addAction(save_tb_action)
        
        file_menu.addSeparator()
        
        # Exit action with gorgeous icon
        exit_action = QAction("🚪 Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit AWaveViewer")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        toolbar.addSeparator()
        
        # Edit menu with stunning icon
        edit_menu = self.menuBar().addMenu("✏️ &Edit")
        
        # Parse action
        parse_action = QAction("🔍 Parse Module", self)
        parse_action.setShortcut("Ctrl+P")
        parse_action.setStatusTip("Parse Verilog module structure")
        parse_action.triggered.connect(self.parse_verilog)
        edit_menu.addAction(parse_action)
        toolbar.addAction(parse_action)
        
        # Syntax Check action
        syntax_check_action = QAction("✓ Syntax Check", self)
        syntax_check_action.setShortcut("Ctrl+K")
        syntax_check_action.setStatusTip("Validate Verilog syntax (Verilog-95/2001/SystemVerilog)")
        syntax_check_action.triggered.connect(self.check_verilog_syntax)
        edit_menu.addAction(syntax_check_action)
        toolbar.addAction(syntax_check_action)
        
        # Generate TB action
        gen_tb_action = QAction("⚡ Generate Testbench", self)
        gen_tb_action.setShortcut("Ctrl+G")
        gen_tb_action.setStatusTip("Generate comprehensive automatic testbench")
        gen_tb_action.triggered.connect(self.generate_testbench)
        edit_menu.addAction(gen_tb_action)
        toolbar.addAction(gen_tb_action)
        
        # Upload/Load Testbench action
        load_tb_action = QAction("📤 Load Testbench", self)
        load_tb_action.setShortcut("Ctrl+Shift+T")
        load_tb_action.setStatusTip("Upload and load your own Verilog testbench file")
        load_tb_action.triggered.connect(self.load_testbench)
        edit_menu.addAction(load_tb_action)
        toolbar.addAction(load_tb_action)
        
        toolbar.addSeparator()
        
        # Simulation menu with gorgeous icon
        sim_menu = self.menuBar().addMenu("🎬 &Simulation")
        
        # Run simulation action
        run_action = QAction("▶️ Run Simulation", self)
        run_action.setShortcut("F5")
        run_action.setStatusTip("Execute simulation and generate waveform data")
        run_action.triggered.connect(self.run_simulation)
        sim_menu.addAction(run_action)
        toolbar.addAction(run_action)
        
        # Load VCD action
        load_vcd_action = QAction("📊 Load VCD", self)
        load_vcd_action.setShortcut("Ctrl+L")
        load_vcd_action.setStatusTip("Load VCD waveform file for visualization")
        load_vcd_action.triggered.connect(self.load_vcd_file)
        sim_menu.addAction(load_vcd_action)
        
        toolbar.addSeparator()
        
        # View menu with elegant icon
        view_menu = self.menuBar().addMenu("👁️ &View")
        
        # Zoom actions with beautiful icons
        zoom_in_action = QAction("🔎 Zoom In", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.setStatusTip("Expand waveform time scale")
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)
        toolbar.addAction(zoom_in_action)
        
        zoom_out_action = QAction("🔍 Zoom Out", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.setStatusTip("Compress waveform time scale")
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)
        toolbar.addAction(zoom_out_action)
        
        fit_action = QAction("📏 Fit All", self)
        fit_action.setShortcut("Ctrl+F")
        fit_action.setStatusTip("Auto-fit all waveforms to window")
        fit_action.triggered.connect(self.fit_all)
        view_menu.addAction(fit_action)
        toolbar.addAction(fit_action)
        
        view_menu.addSeparator()
        
        # Grid toggle
        grid_action = QAction("🔲 Toggle Grid", self)
        grid_action.setCheckable(True)
        grid_action.setChecked(True)
        grid_action.setStatusTip("Show/hide grid")
        grid_action.triggered.connect(lambda: self.toggle_grid(Qt.Checked if grid_action.isChecked() else Qt.Unchecked))
        view_menu.addAction(grid_action)
        
        view_menu.addSeparator()
        
        # Theme submenu with all 50 themes
        theme_submenu = view_menu.addMenu("🎨 Themes")
        theme_submenu.setStatusTip("Select from 50 gorgeous themes")
        
        # Add all themes to submenu
        for theme_name in self.theme_manager.get_theme_list():
            theme_action = QAction(theme_name, self)
            theme_action.triggered.connect(lambda checked, t=theme_name: self.change_theme(t))
            theme_submenu.addAction(theme_action)
        
        # Add spacer to push theme controls to the right side of toolbar
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        toolbar.addWidget(spacer)
        
        toolbar.addSeparator()
        
        # Theme controls with enhanced visibility
        theme_label = QLabel("  🎨 Theme: ")
        theme_label.setStyleSheet("""
            QLabel {
                color: #60a5fa;
                font-weight: bold;
                font-size: 13px;
                padding: 0px 5px;
            }
        """)
        toolbar.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(self.theme_manager.get_theme_list())
        self.theme_combo.setCurrentText(self.current_theme)
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        self.theme_combo.setMinimumWidth(200)
        self.theme_combo.setMaximumWidth(250)
        self.theme_combo.setToolTip("Select from 50 gorgeous themes")
        toolbar.addWidget(self.theme_combo)
        
        toolbar.addSeparator()
        
        opacity_label = QLabel("  💧 Opacity: ")
        opacity_label.setStyleSheet("""
            QLabel {
                color: #60a5fa;
                font-weight: bold;
                font-size: 13px;
                padding: 0px 5px;
            }
        """)
        toolbar.addWidget(opacity_label)
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(50)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(int(self.current_opacity * 100))
        self.opacity_slider.valueChanged.connect(self.change_opacity)
        self.opacity_slider.setFixedWidth(140)
        self.opacity_slider.setToolTip("Adjust theme transparency (50-100%)")
        toolbar.addWidget(self.opacity_slider)
        
        self.opacity_label = QLabel(f"{int(self.current_opacity * 100)}%")
        self.opacity_label.setMinimumWidth(40)
        self.opacity_label.setAlignment(Qt.AlignCenter)
        self.opacity_label.setStyleSheet("""
            QLabel {
                color: #93c5fd;
                font-weight: bold;
                font-size: 13px;
                background: rgba(59, 130, 246, 0.2);
                border: 1px solid rgba(59, 130, 246, 0.4);
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)
        toolbar.addWidget(self.opacity_label)
        
        toolbar.addSeparator()
        
        # Help menu
        help_menu = self.menuBar().addMenu("&Help")
        
        # Welcome action
        welcome_action = QAction("🏠 Welcome Screen", self)
        welcome_action.setStatusTip("Show welcome screen")
        welcome_action.triggered.connect(self.show_welcome_screen)
        help_menu.addAction(welcome_action)
        
        help_menu.addSeparator()
        
        # About action
        about_action = QAction("ℹ️ About", self)
        about_action.setShortcut("F1")
        about_action.setStatusTip("About AWaveViewer")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        toolbar.addAction(about_action)
    
    def apply_dark_theme(self):
        """Apply stunning modern professional theme"""
        modern_stylesheet = """
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0a0e1a, stop:0.5 #0f172a, stop:1 #1e293b);
            }
            
            QWidget {
                background-color: transparent;
                color: #e2e8f0;
                font-family: 'Segoe UI';
            }
            
            QTextEdit, QTreeWidget, QListWidget, QPlainTextEdit {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e293b, stop:1 #0f172a);
                color: #f1f5f9;
                border: 2px solid transparent;
                border-radius: 8px;
                padding: 8px;
                selection-background-color: #3b82f6;
            }
            
            QTextEdit:focus, QTreeWidget:focus, QListWidget:focus, QPlainTextEdit:focus {
                border: 2px solid #3b82f6;
                box-shadow: 0 0 20px rgba(59, 130, 246, 0.4);
            }
            
            QGroupBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(30, 41, 59, 0.8), stop:1 rgba(15, 23, 42, 0.6));
                border: 2px solid;
                border-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:0.5 #8b5cf6, stop:1 #3b82f6);
                border-radius: 12px;
                margin-top: 18px;
                padding-top: 15px;
                font-weight: bold;
                font-size: 14px;
            }
            
            QGroupBox::title {
                color: #93c5fd;
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 20px;
                padding: 0 12px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(59, 130, 246, 0.3),
                    stop:0.5 rgba(139, 92, 246, 0.3),
                    stop:1 rgba(59, 130, 246, 0.3));
                border-radius: 4px;
            }
            
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3b82f6, stop:1 #2563eb);
                color: white;
                border: 2px solid rgba(59, 130, 246, 0.5);
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                min-height: 32px;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #60a5fa, stop:0.5 #8b5cf6, stop:1 #3b82f6);
                border: 2px solid rgba(96, 165, 250, 0.8);
            }
            
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1d4ed8, stop:1 #1e40af);
                border: 2px solid rgba(29, 78, 216, 1);
            }
            
            QPushButton:disabled {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #334155, stop:1 #1e293b);
                color: #64748b;
                border: 2px solid rgba(51, 65, 85, 0.5);
            }
            
            QMenuBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e293b, stop:1 #0f172a);
                color: #f1f5f9;
                border-bottom: 2px solid;
                border-image: linear-gradient(to right, #3b82f6, #8b5cf6, #3b82f6) 1;
                padding: 6px;
                font-size: 13px;
            }
            
            QMenuBar::item {
                background-color: transparent;
                padding: 8px 16px;
                border-radius: 6px;
                margin: 2px;
            }
            
            QMenuBar::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(59, 130, 246, 0.3),
                    stop:1 rgba(139, 92, 246, 0.3));
                border: 1px solid rgba(96, 165, 250, 0.5);
            }
            
            QMenuBar::item:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #8b5cf6);
            }
            
            QMenu {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e293b, stop:1 #0f172a);
                color: #f1f5f9;
                border: 2px solid #3b82f6;
                border-radius: 8px;
                padding: 8px;
            }
            
            QMenu::item {
                padding: 10px 40px 10px 25px;
                border-radius: 6px;
                margin: 2px;
            }
            
            QMenu::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #8b5cf6);
            }
            
            QMenu::separator {
                height: 2px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 transparent, stop:0.5 #3b82f6, stop:1 transparent);
                margin: 8px 15px;
            }
            
            QToolBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e293b, stop:1 #0f172a);
                border: none;
                border-bottom: 2px solid;
                border-image: linear-gradient(to right, #3b82f6, #8b5cf6, #3b82f6) 1;
                spacing: 10px;
                padding: 8px;
            }
            
            QToolBar::separator {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 transparent, stop:0.5 #3b82f6, stop:1 transparent);
                width: 2px;
                margin: 8px 5px;
            }
            
            QToolButton {
                background-color: transparent;
                color: #f1f5f9;
                border: 2px solid transparent;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            
            QToolButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(59, 130, 246, 0.3),
                    stop:1 rgba(139, 92, 246, 0.3));
                border: 2px solid rgba(96, 165, 250, 0.5);
            }
            
            QToolButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #8b5cf6);
                border: 2px solid #60a5fa;
            }
            
            QStatusBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0f172a, stop:1 #0a0e1a);
                color: #94a3b8;
                border-top: 2px solid;
                border-image: linear-gradient(to right, #3b82f6, #8b5cf6, #3b82f6) 1;
                padding: 6px;
                font-weight: 600;
            }
            
            QScrollBar:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1e293b, stop:1 #0f172a);
                width: 14px;
                border-radius: 7px;
                margin: 2px;
            }
            
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #475569, stop:1 #3b82f6);
                border-radius: 7px;
                min-height: 30px;
                border: 1px solid rgba(59, 130, 246, 0.3);
            }
            
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #64748b, stop:1 #60a5fa);
            }
            
            QScrollBar:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e293b, stop:1 #0f172a);
                height: 14px;
                border-radius: 7px;
                margin: 2px;
            }
            
            QScrollBar::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #475569, stop:1 #3b82f6);
                border-radius: 7px;
                min-width: 30px;
                border: 1px solid rgba(59, 130, 246, 0.3);
            }
            
            QScrollBar::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #64748b, stop:1 #60a5fa);
            }
            
            QScrollBar::add-line, QScrollBar::sub-line {
                border: none;
                background: none;
            }
            
            QSplitter::handle {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 transparent, stop:0.5 #3b82f6, stop:1 transparent);
            }
            
            QSplitter::handle:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 transparent, stop:0.5 #60a5fa, stop:1 transparent);
            }
            
            QCheckBox {
                color: #f1f5f9;
                spacing: 10px;
                font-weight: 600;
            }
            
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #475569;
                border-radius: 6px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e293b, stop:1 #0f172a);
            }
            
            QCheckBox::indicator:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #3b82f6, stop:1 #8b5cf6);
                border-color: #60a5fa;
                image: url(none);
            }
            
            QCheckBox::indicator:hover {
                border-color: #60a5fa;
                border-width: 2px;
            }
            
            QSpinBox, QLineEdit, QComboBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e293b, stop:1 #0f172a);
                color: #f1f5f9;
                border: 2px solid #334155;
                border-radius: 6px;
                padding: 8px;
                min-height: 28px;
                font-weight: 600;
            }
            
            QSpinBox:focus, QLineEdit:focus, QComboBox:focus {
                border: 2px solid #3b82f6;
            }
            
            QProgressBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e293b, stop:1 #0f172a);
                border: 2px solid #334155;
                border-radius: 6px;
                text-align: center;
                color: #f1f5f9;
                height: 24px;
                font-weight: bold;
            }
            
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:0.5 #8b5cf6, stop:1 #ec4899);
                border-radius: 4px;
            }
            
            QTabWidget::pane {
                border: 2px solid;
                border-image: linear-gradient(to right, #3b82f6, #8b5cf6, #3b82f6) 1;
                border-radius: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e293b, stop:1 #0f172a);
                margin-top: 5px;
            }
            
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e293b, stop:1 #0f172a);
                color: #94a3b8;
                border: 2px solid #334155;
                border-bottom: none;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                padding: 12px 24px;
                margin-right: 4px;
                font-weight: bold;
                font-size: 13px;
                min-width: 150px;
            }
            
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #3b82f6, stop:0.5 #8b5cf6, stop:1 #3b82f6);
                color: white;
                border: 2px solid #60a5fa;
                border-bottom: none;
            }
            
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #334155, stop:1 #1e293b);
                border-color: #475569;
            }
            
            QLabel {
                color: #e2e8f0;
            }
            
            QTreeWidget::item:selected {
                background-color: #3b82f6;
                color: white;
            }
            
            QTreeWidget::item:hover {
                background-color: #334155;
            }
            
            QTextEdit, QPlainTextEdit {
                line-height: 1.4;
            }
            
            QTextEdit[readOnly="true"], QPlainTextEdit[readOnly="true"] {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(30, 41, 59, 0.5), stop:1 rgba(15, 23, 42, 0.5));
            }
        """
        self.setStyleSheet(modern_stylesheet)
    
    def load_verilog_file(self):
        """Load Verilog file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Verilog File",
            "",
            "Verilog Files (*.v *.sv);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                self.verilog_editor.setPlainText(content)
                self.verilog_file = file_path
                self.statusBar.showMessage(f"Loaded: {file_path}")
                self.parse_verilog()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")
    
    def parse_verilog(self):
        """Parse Verilog code"""
        code = self.verilog_editor.toPlainText()
        if not code.strip():
            QMessageBox.warning(self, "Warning", "No Verilog code to parse")
            return
        
        try:
            parser = VerilogParser()
            self.module_info = parser.parse_module(code)
            
            if not self.module_info['name']:
                QMessageBox.warning(self, "Warning", "No module found in Verilog code")
                return
            
            self.display_module_info()
            self.gen_tb_btn.setEnabled(True)
            self.statusBar.showMessage(f"Parsed module: {self.module_info['name']}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to parse Verilog:\n{str(e)}")
    
    def display_module_info(self):
        """Display module information in tree"""
        self.info_tree.clear()
        
        if not self.module_info:
            return
        
        # Module name
        module_item = QTreeWidgetItem([self.module_info['name'], "Module", "", ""])
        module_item.setFont(0, QFont("Courier New", 10, QFont.Bold))
        self.info_tree.addTopLevelItem(module_item)
        
        # Parameters
        if self.module_info['parameters']:
            param_parent = QTreeWidgetItem(["Parameters", "", "", ""])
            param_parent.setFont(0, QFont("Courier New", 10, QFont.Bold))
            for param in self.module_info['parameters']:
                param_item = QTreeWidgetItem([
                    param['name'],
                    "Parameter",
                    "",
                    f"= {param['value']}"
                ])
                param_parent.addChild(param_item)
            self.info_tree.addTopLevelItem(param_parent)
            param_parent.setExpanded(True)
        
        # Inputs
        if self.module_info['inputs']:
            input_parent = QTreeWidgetItem(["Inputs", "", "", ""])
            input_parent.setFont(0, QFont("Courier New", 10, QFont.Bold))
            for inp in self.module_info['inputs']:
                # Convert width to int for comparison, default to 1 if conversion fails
                try:
                    width_int = int(inp['width']) if inp['width'] else 1
                except (ValueError, TypeError):
                    width_int = 1
                
                width_str = f"{inp['width']}" if width_int > 1 else "1"
                
                # Check if msb and lsb exist in the dict
                if 'msb' in inp and 'lsb' in inp and width_int > 1:
                    range_str = f"[{inp['msb']}:{inp['lsb']}]"
                elif width_int > 1:
                    range_str = f"[{width_int-1}:0]"
                else:
                    range_str = ""
                
                inp_item = QTreeWidgetItem([
                    inp['name'],
                    "Input",
                    width_str,
                    range_str
                ])
                input_parent.addChild(inp_item)
            self.info_tree.addTopLevelItem(input_parent)
            input_parent.setExpanded(True)
        
        # Outputs
        if self.module_info['outputs']:
            output_parent = QTreeWidgetItem(["Outputs", "", "", ""])
            output_parent.setFont(0, QFont("Courier New", 10, QFont.Bold))
            for out in self.module_info['outputs']:
                # Convert width to int for comparison, default to 1 if conversion fails
                try:
                    width_int = int(out['width']) if out['width'] else 1
                except (ValueError, TypeError):
                    width_int = 1
                
                width_str = f"{out['width']}" if width_int > 1 else "1"
                
                # Check if msb and lsb exist in the dict
                if 'msb' in out and 'lsb' in out and width_int > 1:
                    range_str = f"[{out['msb']}:{out['lsb']}]"
                elif width_int > 1:
                    range_str = f"[{width_int-1}:0]"
                else:
                    range_str = ""
                
                out_item = QTreeWidgetItem([
                    out['name'],
                    "Output",
                    width_str,
                    range_str
                ])
                output_parent.addChild(out_item)
            self.info_tree.addTopLevelItem(output_parent)
            output_parent.setExpanded(True)
    
    def generate_testbench(self):
        """Generate testbench with syntax checking"""
        if not self.module_info:
            QMessageBox.warning(self, "Warning", "Parse Verilog module first")
            return
        
        # Get Verilog code from editor
        verilog_code = self.verilog_editor.toPlainText()
        
        if not verilog_code.strip():
            QMessageBox.warning(self, "Warning", "No Verilog code to check")
            return
        
        try:
            # Step 1: Check syntax before generating testbench
            self.statusBar.showMessage("Checking Verilog syntax...")
            checker = VerilogSyntaxChecker()
            is_valid, messages = checker.check_syntax(verilog_code)
            
            # Detect Verilog version
            verilog_version = checker.get_verilog_version(verilog_code)
            
            # Display syntax check results
            if messages:
                message_text = f"Verilog Version Detected: {verilog_version}\n\n"
                message_text += "Syntax Check Results:\n"
                message_text += "=" * 50 + "\n"
                for msg in messages:
                    message_text += f"{msg}\n"
                message_text += "=" * 50 + "\n\n"
                
                if is_valid:
                    message_text += "Status: PASSED (with warnings)\n\n"
                    message_text += "Continue with testbench generation?"
                    
                    reply = QMessageBox.question(
                        self, 
                        "Syntax Check - Warnings Found",
                        message_text,
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.No:
                        self.statusBar.showMessage("Testbench generation cancelled")
                        return
                else:
                    message_text += "Status: FAILED\n\n"
                    message_text += "Please fix the errors before generating testbench."
                    
                    QMessageBox.critical(
                        self,
                        "Syntax Check Failed",
                        message_text
                    )
                    self.statusBar.showMessage("Syntax check failed - fix errors first")
                    return
            else:
                # No errors or warnings
                info_msg = f"Verilog Version: {verilog_version}\nSyntax Check: PASSED\n\nNo errors or warnings found!"
                QMessageBox.information(self, "Syntax Check Passed", info_msg)
            
            # Step 2: Generate testbench
            self.statusBar.showMessage("Generating testbench...")
            generator = TestbenchGenerator()
            test_vectors = self.test_vectors_spin.value()
            self.testbench_code = generator.generate_testbench(self.module_info, test_vectors)
            self.tb_editor.setPlainText(self.testbench_code)
            self.run_sim_btn.setEnabled(True)
            self.statusBar.showMessage(f"Testbench generated successfully ({verilog_version})")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate testbench:\n{str(e)}")
            self.statusBar.showMessage("Testbench generation failed")
    
    def check_verilog_syntax(self):
        """Check Verilog syntax independently"""
        verilog_code = self.verilog_editor.toPlainText()
        
        if not verilog_code.strip():
            QMessageBox.warning(self, "Warning", "No Verilog code to check")
            return
        
        try:
            self.statusBar.showMessage("Checking Verilog syntax...")
            
            # Perform syntax check
            checker = VerilogSyntaxChecker()
            is_valid, messages = checker.check_syntax(verilog_code)
            
            # Detect Verilog version
            verilog_version = checker.get_verilog_version(verilog_code)
            
            # Prepare result message
            result_title = "Syntax Check Results"
            result_text = f"Verilog Version Detected: {verilog_version}\n"
            result_text += f"Code Length: {len(verilog_code)} characters\n"
            result_text += f"Lines of Code: {len(verilog_code.splitlines())}\n\n"
            
            if messages:
                result_text += "Issues Found:\n"
                result_text += "=" * 60 + "\n"
                for i, msg in enumerate(messages, 1):
                    result_text += f"{i}. {msg}\n"
                result_text += "=" * 60 + "\n\n"
                
                if is_valid:
                    result_text += "Overall Status: PASSED (with warnings)\n"
                    result_text += "\nThe code has some warnings but is syntactically valid.\n"
                    result_text += "You can proceed with testbench generation."
                    QMessageBox.information(self, result_title, result_text)
                    self.statusBar.showMessage(f"Syntax check passed with {len(messages)} warning(s)")
                else:
                    error_count = sum(1 for msg in messages if msg.startswith("ERROR"))
                    result_text += f"Overall Status: FAILED ({error_count} error(s))\n"
                    result_text += "\nPlease fix the errors before proceeding."
                    QMessageBox.critical(self, result_title, result_text)
                    self.statusBar.showMessage(f"Syntax check failed with {error_count} error(s)")
            else:
                result_text += "Issues Found: None\n\n"
                result_text += "Overall Status: PASSED\n"
                result_text += "\nYour Verilog code is syntactically correct!\n"
                result_text += "No errors or warnings detected.\n"
                result_text += f"\nSupported Version: {verilog_version}"
                QMessageBox.information(self, result_title, result_text)
                self.statusBar.showMessage(f"Syntax check passed - {verilog_version}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Syntax check failed:\n{str(e)}")
            self.statusBar.showMessage("Syntax check error")
    
    def save_testbench(self):
        """Save testbench to file"""
        if not self.testbench_code:
            QMessageBox.warning(self, "Warning", "No testbench to save")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Testbench",
            f"{self.module_info['name']}_tb.v",
            "Verilog Files (*.v);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(self.testbench_code)
                QMessageBox.information(self, "Success", "Testbench saved successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save testbench:\n{str(e)}")
    
    def extract_module_info_from_testbench(self, testbench_content):
        """Extract module information from testbench instantiation"""
        try:
            module_info = {
                'name': '',
                'parameters': [],
                'inputs': [],
                'outputs': [],
                'inouts': []
            }
            
            # Find module instantiation pattern: module_name #(...) instance_name (...)
            # or: module_name instance_name (...)
            instantiation_pattern = r'(\w+)\s*(?:#\s*\([^)]*\))?\s+(\w+)\s*\((.*?)\);'
            matches = re.finditer(instantiation_pattern, testbench_content, re.DOTALL)
            
            for match in matches:
                try:
                    module_name = match.group(1)
                    instance_name = match.group(2)
                    port_connections = match.group(3)
                    
                    # Skip testbench module itself and common keywords
                    if module_name in ['module', 'initial', 'always', 'assign', 'reg', 'wire', 'integer']:
                        continue
                    
                    # This is likely our DUT
                    module_info['name'] = module_name
                    
                    # Parse port connections to determine inputs/outputs
                    # Format: .port_name(signal_name)
                    port_pattern = r'\.\s*(\w+)\s*\(\s*(\w+)\s*\)'
                    port_matches = re.finditer(port_pattern, port_connections)
                    
                    for port_match in port_matches:
                        try:
                            port_name = port_match.group(1)
                            signal_name = port_match.group(2)
                            
                            # Try to determine port direction from testbench signals
                            # Look for signal declarations: reg signal_name or wire signal_name
                            if re.search(rf'\breg\s+.*\b{signal_name}\b', testbench_content):
                                # It's driven by testbench (reg), so it's an input to DUT
                                module_info['inputs'].append({
                                    'name': port_name,
                                    'width': str(self._extract_signal_width(testbench_content, signal_name)),
                                    'type': 'input'
                                })
                            elif re.search(rf'\bwire\s+.*\b{signal_name}\b', testbench_content):
                                # It's a wire (output from DUT)
                                module_info['outputs'].append({
                                    'name': port_name,
                                    'width': str(self._extract_signal_width(testbench_content, signal_name)),
                                    'type': 'output'
                                })
                            else:
                                # Default: assume input if we can't determine
                                module_info['inputs'].append({
                                    'name': port_name,
                                    'width': '1',
                                    'type': 'input'
                                })
                        except Exception as port_error:
                            print(f"Error parsing port: {port_error}")
                            continue
                    
                    # We found our DUT, break
                    if module_info['name']:
                        break
                except Exception as match_error:
                    print(f"Error processing match: {match_error}")
                    continue
            
            return module_info
            
        except Exception as e:
            print(f"Error extracting module info from testbench: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_signal_width(self, testbench_content, signal_name):
        """Extract signal width from declaration"""
        try:
            # Look for: reg [7:0] signal_name or wire [WIDTH-1:0] signal_name
            width_pattern = rf'(?:reg|wire)\s*\[([^\]]+)\]\s*{signal_name}\b'
            match = re.search(width_pattern, testbench_content)
            if match:
                width_expr = match.group(1)
                # Try to extract just the upper bound
                if ':' in width_expr:
                    upper = width_expr.split(':')[0].strip()
                    lower = width_expr.split(':')[1].strip()
                    
                    # Try to evaluate numeric expressions
                    try:
                        # Check if both are pure integers
                        upper_val = None
                        lower_val = None
                        
                        # Try to convert upper bound
                        try:
                            upper_val = int(upper)
                        except ValueError:
                            # Try eval for simple expressions like "8-1"
                            try:
                                result = eval(upper, {"__builtins__": {}}, {})
                                if isinstance(result, (int, float)):
                                    upper_val = int(result)
                            except:
                                pass
                        
                        # Try to convert lower bound
                        try:
                            lower_val = int(lower)
                        except ValueError:
                            try:
                                result = eval(lower, {"__builtins__": {}}, {})
                                if isinstance(result, (int, float)):
                                    lower_val = int(result)
                            except:
                                pass
                        
                        # Calculate width if we got both values
                        if upper_val is not None and lower_val is not None:
                            width = abs(upper_val - lower_val) + 1
                            return str(width)
                        else:
                            # Return the expression as-is if we can't evaluate
                            return width_expr
                    except Exception as eval_err:
                        # If evaluation fails, return the expression
                        return width_expr
                else:
                    # Single value like [7]
                    try:
                        val = int(width_expr)
                        return str(val + 1)  # [7] means 8 bits
                    except:
                        return width_expr
            else:
                # No width specified, assume 1-bit
                return '1'
        except Exception as e:
            # On any error, return default
            return '1'
    
    def load_testbench(self):
        """Load existing testbench file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Testbench",
            "",
            "Verilog Files (*.v *.sv);;SystemVerilog Files (*.sv);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            # Read the testbench file
            with open(file_path, 'r') as f:
                testbench_content = f.read()
            
            if not testbench_content.strip():
                QMessageBox.warning(self, "Warning", "The testbench file is empty")
                return
            
            # Perform syntax check on the loaded testbench
            self.statusBar.showMessage("Checking testbench syntax...")
            checker = VerilogSyntaxChecker()
            is_valid, messages = checker.check_syntax(testbench_content)
            verilog_version = checker.get_verilog_version(testbench_content)
            
            # Display syntax check results
            result_text = f"Loaded Testbench: {Path(file_path).name}\n"
            result_text += f"Verilog Version: {verilog_version}\n"
            result_text += f"Size: {len(testbench_content)} characters\n"
            result_text += f"Lines: {len(testbench_content.splitlines())}\n\n"
            
            if messages:
                result_text += "Syntax Check Results:\n"
                result_text += "=" * 50 + "\n"
                for msg in messages[:10]:  # Show first 10 messages
                    result_text += f"• {msg}\n"
                if len(messages) > 10:
                    result_text += f"... and {len(messages) - 10} more\n"
                result_text += "=" * 50 + "\n\n"
                
                if is_valid:
                    result_text += "Status: ✓ VALID (with warnings)\n\n"
                    result_text += "Load this testbench?"
                    reply = QMessageBox.question(
                        self,
                        "Testbench Loaded - Warnings",
                        result_text,
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    if reply == QMessageBox.No:
                        self.statusBar.showMessage("Testbench loading cancelled")
                        return
                else:
                    result_text += "Status: ✗ INVALID\n\n"
                    result_text += "The testbench has syntax errors.\nLoad anyway?"
                    reply = QMessageBox.warning(
                        self,
                        "Testbench Syntax Errors",
                        result_text,
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        self.statusBar.showMessage("Testbench loading cancelled due to errors")
                        return
            else:
                result_text += "Syntax Check: ✓ PASSED\n\n"
                result_text += "The testbench is syntactically correct!"
                QMessageBox.information(self, "Testbench Valid", result_text)
            
            # Load the testbench (use tb_editor, not testbench_editor)
            self.testbench_code = testbench_content
            self.tb_editor.setPlainText(testbench_content)
            self.tb_editor.setReadOnly(False)  # Allow editing of loaded testbench
            
            # Automatically extract module information from testbench
            self.statusBar.showMessage("Extracting module information from testbench...")
            extracted_module_info = None
            module_extracted = False
            extraction_status = "⚠ Module info extraction disabled"
            
            try:
                extracted_module_info = self.extract_module_info_from_testbench(testbench_content)
            except Exception as extract_err:
                print(f"Error during module extraction: {extract_err}")
                import traceback
                traceback.print_exc()
                extracted_module_info = None
            
            if extracted_module_info and extracted_module_info['name']:
                self.module_info = extracted_module_info
                self.display_module_info()
                self.gen_tb_btn.setEnabled(True)
                module_extracted = True
                extraction_status = f"✓ Module '{extracted_module_info['name']}' extracted"
            else:
                module_extracted = False
                extraction_status = "⚠ Could not auto-extract module info"
            
            # Extract module name from testbench if possible
            module_match = re.search(r'module\s+(\w+)', testbench_content)
            if module_match:
                tb_module_name = module_match.group(1)
                self.statusBar.showMessage(f"Testbench '{tb_module_name}' loaded - {extraction_status}")
            else:
                self.statusBar.showMessage(f"Testbench loaded - {extraction_status}")
            
            # Show success message with file info
            info_msg = f"✓ Testbench Loaded Successfully!\n\n"
            info_msg += f"File: {Path(file_path).name}\n"
            info_msg += f"Path: {file_path}\n"
            info_msg += f"Version: {verilog_version}\n"
            info_msg += f"Lines: {len(testbench_content.splitlines())}\n\n"
            
            if module_extracted:
                info_msg += f"🎯 Module Information Extracted:\n"
                info_msg += f"   Module: {extracted_module_info['name']}\n"
                info_msg += f"   Inputs: {len(extracted_module_info['inputs'])}\n"
                info_msg += f"   Outputs: {len(extracted_module_info['outputs'])}\n"
                if extracted_module_info['inouts']:
                    info_msg += f"   Inouts: {len(extracted_module_info['inouts'])}\n"
                info_msg += "\n"
            else:
                info_msg += "⚠ Module info not auto-extracted\n"
                info_msg += "   (You can manually parse Verilog if needed)\n\n"
            
            # Check if Verilog source is loaded
            has_verilog = self.verilog_editor.toPlainText().strip() != ""
            
            info_msg += "You can now:\n"
            info_msg += "• Edit the testbench in the editor\n"
            
            if has_verilog:
                info_msg += "• Run simulation (F5) - DUT loaded ✓\n"
            else:
                info_msg += "• Run simulation (F5) - will prompt for DUT file\n"
                info_msg += "• Load DUT Verilog file (Ctrl+O) for simulation\n"
            
            info_msg += "• Save modifications\n"
            if module_extracted:
                info_msg += "• View module structure in the tree\n"
            
            if not has_verilog and module_extracted:
                info_msg += f"\n💡 Tip: Load '{extracted_module_info['name']}.v' to run simulation"
            
            QMessageBox.information(self, "Testbench Loaded", info_msg)
            
        except Exception as e:
            # Show detailed error information
            import traceback
            error_details = traceback.format_exc()
            
            QMessageBox.critical(
                self,
                "Error Loading Testbench",
                f"Failed to load testbench file:\n\n{str(e)}\n\nFile: {file_path}\n\nDetails:\n{error_details[:500]}"
            )
            self.statusBar.showMessage("Failed to load testbench")
            print(f"Full error trace:\n{error_details}")
    
    def run_simulation(self):
        """Run simulation"""
        if not self.testbench_code:
            QMessageBox.warning(self, "Warning", "No testbench available. Generate or load a testbench first.")
            return
        
        # Get Verilog content from editor
        verilog_content = self.verilog_editor.toPlainText()
        
        # Check if testbench file contains the DUT module (self-contained testbench)
        testbench_has_dut = False
        dut_module_name = None
        
        # Look for DUT instantiation to find module name
        instantiation_match = re.search(r'(\w+)\s+(?:uut|dut|u1|inst|i_\w+)\s*\(', self.testbench_code)
        if instantiation_match:
            dut_module_name = instantiation_match.group(1)
            # Check if this module is defined in the testbench file
            if re.search(rf'module\s+{dut_module_name}\s*[\(;]', self.testbench_code):
                testbench_has_dut = True
                self.statusBar.showMessage(f"Detected self-contained testbench with DUT module '{dut_module_name}'")
        
        # Check if we have Verilog source code OR if testbench is self-contained
        if (not verilog_content or not verilog_content.strip()) and not testbench_has_dut:
            # Ask user with more options
            reply = QMessageBox.question(
                self,
                "No Verilog Source",
                "No Verilog source code loaded in the editor.\n\n"
                "Options:\n"
                "1. If your testbench includes the DUT module → Click 'No' to use testbench only\n"
                "2. If DUT is in a separate file → Click 'Yes' to load it\n\n"
                "Would you like to load a separate DUT Verilog file?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No  # Default to No (use testbench only)
            )
            
            if reply == QMessageBox.Yes:
                # Open file dialog to load Verilog source
                file_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Load DUT Verilog Source",
                    "",
                    "Verilog Files (*.v *.sv);;SystemVerilog Files (*.sv);;All Files (*.*)"
                )
                
                if file_path:
                    try:
                        with open(file_path, 'r') as f:
                            verilog_content = f.read()
                        self.verilog_editor.setPlainText(verilog_content)
                        self.statusBar.showMessage(f"Loaded DUT from {Path(file_path).name}")
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Failed to load Verilog file:\n{str(e)}")
                        return
                else:
                    # User cancelled, try to use testbench only
                    self.statusBar.showMessage("No DUT loaded - attempting to use self-contained testbench")
                    verilog_content = ""
                    testbench_has_dut = True  # Assume testbench has DUT
            else:
                # User chose to use testbench only
                self.statusBar.showMessage("Using self-contained testbench for simulation")
                verilog_content = ""
                testbench_has_dut = True
        
        # Create a minimal module_info if not present or incomplete
        if not self.module_info or not self.module_info.get('name'):
            # Try to extract module name from testbench
            module_match = re.search(r'(\w+)\s+(?:uut|dut|u1|inst|i_\w+)\s*\(', self.testbench_code)
            if module_match:
                module_name = module_match.group(1)
            elif verilog_content:
                # Try to get from verilog source
                module_match = re.search(r'module\s+(\w+)', verilog_content)
                module_name = module_match.group(1) if module_match else "design"
            else:
                # Try to find first module in testbench (that's not the testbench itself)
                all_modules = re.findall(r'module\s+(\w+)', self.testbench_code)
                # Filter out testbench modules (usually contain 'tb' or 'test')
                dut_modules = [m for m in all_modules if 'tb' not in m.lower() and 'test' not in m.lower()]
                module_name = dut_modules[0] if dut_modules else (all_modules[0] if all_modules else "design")
            
            # Create minimal module info for simulation
            self.module_info = {
                'name': module_name,
                'parameters': [],
                'inputs': [],
                'outputs': [],
                'inouts': []
            }
            self.statusBar.showMessage(f"Running simulation for module '{module_name}'...")
        
        # Save files to temp directory
        verilog_temp = os.path.join(self.temp_dir, "design.v")
        testbench_temp = os.path.join(self.temp_dir, "testbench.v")
        
        try:
            # If testbench is self-contained, write it as both files
            if testbench_has_dut and (not verilog_content or not verilog_content.strip()):
                # Write testbench content to both files
                # This works because the testbench file contains both the DUT and the testbench
                with open(verilog_temp, 'w') as f:
                    f.write(self.testbench_code)
                with open(testbench_temp, 'w') as f:
                    f.write(self.testbench_code)
                self.statusBar.showMessage("Using self-contained testbench (DUT included in testbench file)")
            else:
                # Write separate DUT and testbench files
                with open(verilog_temp, 'w') as f:
                    f.write(verilog_content)
                with open(testbench_temp, 'w') as f:
                    f.write(self.testbench_code)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save simulation files:\n{str(e)}")
            return
        
        # Run simulation in thread
        self.sim_progress.setVisible(True)
        self.sim_progress.setRange(0, 0)  # Indeterminate
        self.run_sim_btn.setEnabled(False)
        self.sim_output.clear()
        
        self.statusBar.showMessage("Running simulation...")
        
        self.sim_thread = SimulationThread(verilog_temp, testbench_temp, self.temp_dir, self.module_info)
        self.sim_thread.progress.connect(self.on_simulation_progress)
        self.sim_thread.finished.connect(self.on_simulation_finished)
        self.sim_thread.start()
    
    def on_simulation_progress(self, message: str):
        """Handle simulation progress"""
        self.sim_output.append(message)
        self.statusBar.showMessage(message)
    
    def on_simulation_finished(self, success: bool, message: str):
        """Handle simulation completion"""
        self.sim_progress.setVisible(False)
        self.run_sim_btn.setEnabled(True)
        self.sim_output.append("\n" + message)
        
        if success:
            self.statusBar.showMessage("Simulation completed successfully")
            vcd_path = os.path.join(self.temp_dir, "wave.vcd")
            if os.path.exists(vcd_path):
                self.load_vcd(vcd_path)
        else:
            self.statusBar.showMessage("Simulation failed")
            QMessageBox.critical(self, "Simulation Error", message)
    
    def load_vcd_file(self):
        """Load VCD file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open VCD File",
            "",
            "VCD Files (*.vcd);;All Files (*.*)"
        )
        
        if file_path:
            self.load_vcd(file_path)
    
    def load_vcd(self, file_path: str):
        """Load and parse VCD file"""
        try:
            parser = VCDParser()
            signals, changes = parser.parse(file_path)
            
            if not signals:
                QMessageBox.warning(self, "Warning", "No signals found in VCD file")
                return
            
            self.vcd_file = file_path
            self.populate_signal_list(signals)
            self.statusBar.showMessage(f"Loaded VCD: {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load VCD:\n{str(e)}")
    
    def populate_signal_list(self, signals: Dict):
        """Populate signal list"""
        self.signal_list.clear()
        self.signal_list.blockSignals(True)
        
        # Group signals by hierarchy
        hierarchy = {}
        for sig_id, sig_data in signals.items():
            parts = sig_data['full_name'].split('.')
            current = hierarchy
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            if '_signals' not in current:
                current['_signals'] = []
            current['_signals'].append((sig_id, sig_data))
        
        def add_hierarchy(parent_item, hier_dict):
            for key, value in hier_dict.items():
                if key == '_signals':
                    for sig_id, sig_data in value:
                        # Create item with all columns populated
                        sig_name = sig_data['name']
                        sig_type = sig_data.get('type', 'wire')
                        sig_width = str(sig_data.get('width', 1))
                        sig_value = sig_data.get('values', [])[-1][1] if sig_data.get('values') else '--'
                        
                        sig_item = QTreeWidgetItem([sig_name, sig_type, sig_width, str(sig_value)])
                        sig_item.setFlags(sig_item.flags() | Qt.ItemIsUserCheckable)
                        sig_item.setCheckState(0, Qt.Unchecked)
                        sig_item.setData(0, Qt.UserRole, sig_id)
                        parent_item.addChild(sig_item)
                else:
                    scope_item = QTreeWidgetItem([key, '', '', ''])
                    scope_item.setFont(0, QFont("Courier New", 10, QFont.Bold))
                    parent_item.addChild(scope_item)
                    add_hierarchy(scope_item, value)
                    scope_item.setExpanded(True)
        
        root = QTreeWidgetItem(["All Signals", "", "", ""])
        root.setFont(0, QFont("Courier New", 10, QFont.Bold))
        self.signal_list.addTopLevelItem(root)
        add_hierarchy(root, hierarchy)
        root.setExpanded(True)
        
        self.signal_list.blockSignals(False)
        self.signals_dict = signals
    
    def signal_selection_changed(self, item: QTreeWidgetItem, column: int):
        """Handle signal selection change"""
        if not hasattr(self, 'signals_dict'):
            return
        
        visible_signals = []
        
        def collect_checked(parent_item):
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                sig_id = child.data(0, Qt.UserRole)
                if sig_id and child.checkState(0) == Qt.Checked:
                    visible_signals.append(sig_id)
                collect_checked(child)
        
        collect_checked(self.signal_list.topLevelItem(0))
        
        # Update status bar with signal count
        total_signals = len(self.signals_dict) if hasattr(self, 'signals_dict') else 0
        self.statusBar.showMessage(f"Displaying {len(visible_signals)} of {total_signals} signals")
        
        self.waveform_widget.set_signals(self.signals_dict, visible_signals)
    
    def select_all_signals(self):
        """Select all signals in the tree"""
        if not hasattr(self, 'signals_dict'):
            return
        
        self.signal_list.blockSignals(True)
        
        def check_all(parent_item):
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                if child.flags() & Qt.ItemIsUserCheckable:
                    child.setCheckState(0, Qt.Checked)
                check_all(child)
        
        if self.signal_list.topLevelItemCount() > 0:
            check_all(self.signal_list.topLevelItem(0))
        
        self.signal_list.blockSignals(False)
        
        # Manually trigger the selection changed
        if self.signal_list.topLevelItemCount() > 0:
            self.signal_selection_changed(self.signal_list.topLevelItem(0), 0)
    
    def deselect_all_signals(self):
        """Deselect all signals in the tree"""
        if not hasattr(self, 'signals_dict'):
            return
        
        self.signal_list.blockSignals(True)
        
        def uncheck_all(parent_item):
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                if child.flags() & Qt.ItemIsUserCheckable:
                    child.setCheckState(0, Qt.Unchecked)
                uncheck_all(child)
        
        if self.signal_list.topLevelItemCount() > 0:
            uncheck_all(self.signal_list.topLevelItem(0))
        
        self.signal_list.blockSignals(False)
        
        # Manually trigger the selection changed
        if self.signal_list.topLevelItemCount() > 0:
            self.signal_selection_changed(self.signal_list.topLevelItem(0), 0)
    
    def zoom_in(self):
        """Zoom in waveform"""
        self.waveform_widget.time_scale *= 1.5
        self.waveform_widget.update()
    
    def zoom_out(self):
        """Zoom out waveform"""
        self.waveform_widget.time_scale /= 1.5
        self.waveform_widget.update()
    
    def fit_all(self):
        """Fit all waveforms"""
        if self.waveform_widget.max_time > 0:
            available_width = self.waveform_widget.width() - 230
            self.waveform_widget.time_scale = available_width / self.waveform_widget.max_time
            self.waveform_widget.time_offset = 0
            self.waveform_widget.update()
    
    def toggle_grid(self, state):
        """Toggle grid display"""
        self.waveform_widget.grid_enabled = (state == Qt.Checked)
        self.waveform_widget.update()
    
    # === NEW ENHANCED WAVEFORM METHODS ===
    
    def filter_signals(self, text):
        """Filter signals based on search text"""
        if not hasattr(self, 'signals_dict'):
            return
        
        search_text = text.lower()
        
        def filter_item(item):
            """Recursively filter tree items"""
            item_text = item.text(0).lower()
            matches = search_text in item_text
            
            # Check children
            child_matches = False
            for i in range(item.childCount()):
                child = item.child(i)
                if filter_item(child):
                    child_matches = True
            
            # Show item if it matches or any child matches
            visible = matches or child_matches or not search_text
            item.setHidden(not visible)
            
            return visible
        
        # Filter all top-level items
        for i in range(self.signal_list.topLevelItemCount()):
            filter_item(self.signal_list.topLevelItem(i))
    
    def expand_all_signals(self):
        """Expand all items in signal tree"""
        self.signal_list.expandAll()
    
    def collapse_all_signals(self):
        """Collapse all items in signal tree"""
        self.signal_list.collapseAll()
    
    def signal_double_clicked(self, item, column):
        """Handle double-click on signal to show details"""
        if not hasattr(self, 'signals_dict'):
            return
        
        signal_id = item.data(0, Qt.UserRole)
        if signal_id and signal_id in self.signals_dict:
            signal = self.signals_dict[signal_id]
            
            # Calculate and display signal statistics
            stats_text = f"=== {signal['name']} ===\n\n"
            stats_text += f"Full Path: {signal['full_name']}\n"
            stats_text += f"Type: {signal['type']}\n"
            stats_text += f"Width: {signal['width']} bit(s)\n"
            stats_text += f"Value Changes: {len(signal['values'])}\n\n"
            
            if signal['values']:
                first_time, first_val = signal['values'][0]
                last_time, last_val = signal['values'][-1]
                stats_text += f"First Change: {first_time} ns → {first_val}\n"
                stats_text += f"Last Change: {last_time} ns → {last_val}\n\n"
                
                # Calculate toggle count for single-bit signals
                if signal['width'] == 1:
                    toggle_count = 0
                    for i in range(1, len(signal['values'])):
                        if signal['values'][i][1] != signal['values'][i-1][1]:
                            toggle_count += 1
                    stats_text += f"Toggle Count: {toggle_count}\n"
                    
                    # Calculate frequency if it's a clock-like signal
                    if toggle_count > 2:
                        time_span = last_time - first_time
                        if time_span > 0:
                            freq_mhz = (toggle_count / 2) / (time_span / 1000.0)
                            stats_text += f"Approx Frequency: {freq_mhz:.2f} MHz\n"
                            period_ns = (time_span / (toggle_count / 2)) if toggle_count > 0 else 0
                            stats_text += f"Approx Period: {period_ns:.2f} ns\n"
            
            self.signal_stats.setText(stats_text)
    
    def add_marker(self):
        """Add marker at current cursor position"""
        if not hasattr(self, 'waveform_widget') or self.waveform_widget.cursor_time is None:
            QMessageBox.information(self, "Add Marker", 
                                   "Please move the cursor to a position on the waveform first.")
            return
        
        cursor_time = self.waveform_widget.cursor_time
        
        # Get marker label from user
        from PySide6.QtWidgets import QInputDialog
        label, ok = QInputDialog.getText(self, "Add Marker", 
                                         f"Enter label for marker at {cursor_time} ns:",
                                         text=f"Marker_{len(self.waveform_widget.marker_times) + 1}")
        
        if ok and label:
            # Add to waveform widget
            if cursor_time not in self.waveform_widget.marker_times:
                self.waveform_widget.marker_times.append(cursor_time)
                self.waveform_widget.marker_times.sort()
                self.waveform_widget.update()
            
            # Add to markers list
            marker_item = QTreeWidgetItem([str(cursor_time), label])
            marker_item.setData(0, Qt.UserRole, cursor_time)
            self.markers_list.addTopLevelItem(marker_item)
            self.markers_list.sortItems(0, Qt.AscendingOrder)
    
    def clear_markers(self):
        """Clear all markers"""
        reply = QMessageBox.question(self, "Clear Markers",
                                     "Are you sure you want to clear all markers?",
                                     QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.waveform_widget.marker_times.clear()
            self.waveform_widget.update()
            self.markers_list.clear()
    
    def delete_selected_marker(self):
        """Delete selected marker"""
        current_item = self.markers_list.currentItem()
        if not current_item:
            return
        
        marker_time = current_item.data(0, Qt.UserRole)
        if marker_time in self.waveform_widget.marker_times:
            self.waveform_widget.marker_times.remove(marker_time)
            self.waveform_widget.update()
        
        self.markers_list.takeTopLevelItem(self.markers_list.indexOfTopLevelItem(current_item))
    
    def rename_marker(self):
        """Rename selected marker"""
        current_item = self.markers_list.currentItem()
        if not current_item:
            return
        
        from PySide6.QtWidgets import QInputDialog
        old_label = current_item.text(1)
        new_label, ok = QInputDialog.getText(self, "Rename Marker",
                                            "Enter new label:",
                                            text=old_label)
        
        if ok and new_label:
            current_item.setText(1, new_label)
    
    def jump_to_marker(self, item, column):
        """Jump to marker position in waveform"""
        marker_time = item.data(0, Qt.UserRole)
        if marker_time is not None:
            self.waveform_widget.cursor_time = marker_time
            # Center the view on marker
            view_width = self.waveform_widget.width() - 230
            center_time = marker_time - (view_width / (2 * self.waveform_widget.time_scale))
            self.waveform_widget.time_offset = max(0, center_time)
            self.waveform_widget.update()
    
    def toggle_measure_mode(self, checked):
        """Toggle measurement mode"""
        if checked:
            self.statusBar.showMessage("Measurement mode: Click two points to measure time difference", 0)
            self.measure_btn.setStyleSheet("background-color: rgb(251, 191, 36);")
        else:
            self.statusBar.showMessage("Measurement mode disabled", 2000)
            self.measure_btn.setStyleSheet("")
    
    def compare_signals(self):
        """Compare two selected signals"""
        # Get checked signals
        checked_signals = []
        
        def collect_checked(parent_item):
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                if child.checkState(0) == Qt.Checked:
                    sig_id = child.data(0, Qt.UserRole)
                    if sig_id and sig_id in self.signals_dict:
                        checked_signals.append((sig_id, child.text(0)))
                collect_checked(child)
        
        if self.signal_list.topLevelItemCount() > 0:
            collect_checked(self.signal_list.topLevelItem(0))
        
        if len(checked_signals) < 2:
            QMessageBox.information(self, "Compare Signals",
                                   "Please select at least 2 signals to compare.")
            return
        
        if len(checked_signals) > 2:
            QMessageBox.information(self, "Compare Signals",
                                   f"Selected {len(checked_signals)} signals. Comparing first two: {checked_signals[0][1]} vs {checked_signals[1][1]}")
        
        # Compare first two signals
        sig_a_id, sig_a_name = checked_signals[0]
        sig_b_id, sig_b_name = checked_signals[1]
        
        sig_a = self.signals_dict[sig_a_id]
        sig_b = self.signals_dict[sig_b_id]
        
        # Clear and populate comparison table
        self.compare_table.clear()
        
        # Add comparison data
        items = [
            ("Signal Name", sig_a_name, sig_b_name),
            ("Type", sig_a['type'], sig_b['type']),
            ("Width", f"{sig_a['width']} bit(s)", f"{sig_b['width']} bit(s)"),
            ("Changes", str(len(sig_a['values'])), str(len(sig_b['values']))),
        ]
        
        if sig_a['values'] and sig_b['values']:
            items.extend([
                ("First Change", f"{sig_a['values'][0][0]} ns", f"{sig_b['values'][0][0]} ns"),
                ("Last Change", f"{sig_a['values'][-1][0]} ns", f"{sig_b['values'][-1][0]} ns"),
            ])
        
        for prop, val_a, val_b in items:
            item = QTreeWidgetItem([prop, val_a, val_b])
            # Highlight differences
            if val_a != val_b:
                item.setForeground(0, QColor(251, 191, 36))  # Yellow for different values
            self.compare_table.addTopLevelItem(item)
        
        self.compare_table.expandAll()
        
        # Add to verification results
        result_text = f"\n=== Signal Comparison ===\n"
        result_text += f"Signal A: {sig_a_name}\n"
        result_text += f"Signal B: {sig_b_name}\n"
        result_text += f"Width Match: {'✓ Yes' if sig_a['width'] == sig_b['width'] else '✗ No'}\n"
        result_text += f"Change Count: {len(sig_a['values'])} vs {len(sig_b['values'])}\n"
        
        self.verify_results.append(result_text)
    
    def auto_verify_logic(self):
        """Automatically verify common logic patterns"""
        if not hasattr(self, 'signals_dict') or not self.signals_dict:
            QMessageBox.information(self, "Auto Verify",
                                   "No signals loaded. Please run simulation first.")
            return
        
        result_text = "\n=== AUTO VERIFICATION ===\n"
        result_text += f"Timestamp: {QTime.currentTime().toString()}\n\n"
        
        # Check for clock signals
        clock_signals = []
        for sig_id, signal in self.signals_dict.items():
            name_lower = signal['name'].lower()
            if 'clk' in name_lower or 'clock' in name_lower:
                if signal['width'] == 1 and len(signal['values']) > 2:
                    clock_signals.append(signal['name'])
        
        if clock_signals:
            result_text += f"✓ Found {len(clock_signals)} clock signal(s): {', '.join(clock_signals)}\n"
        else:
            result_text += "⚠ No clock signals detected\n"
        
        # Check for reset signals
        reset_signals = []
        for sig_id, signal in self.signals_dict.items():
            name_lower = signal['name'].lower()
            if 'rst' in name_lower or 'reset' in name_lower:
                reset_signals.append(signal['name'])
        
        if reset_signals:
            result_text += f"✓ Found {len(reset_signals)} reset signal(s): {', '.join(reset_signals)}\n"
        else:
            result_text += "⚠ No reset signals detected\n"
        
        # Check signal activity
        active_signals = 0
        inactive_signals = 0
        for sig_id, signal in self.signals_dict.items():
            if len(signal['values']) > 1:
                active_signals += 1
            else:
                inactive_signals += 1
        
        result_text += f"\n📊 Signal Activity:\n"
        result_text += f"  Active signals: {active_signals}\n"
        result_text += f"  Inactive signals: {inactive_signals}\n"
        
        # Check for X/Z values
        unknown_signals = []
        for sig_id, signal in self.signals_dict.items():
            for time, value in signal['values']:
                if 'x' in str(value).lower() or 'z' in str(value).lower():
                    unknown_signals.append(signal['name'])
                    break
        
        if unknown_signals:
            result_text += f"\n⚠ Signals with X/Z values: {len(unknown_signals)}\n"
            result_text += f"  {', '.join(unknown_signals[:5])}\n"
        else:
            result_text += f"\n✓ No X/Z values detected (all signals valid)\n"
        
        result_text += "\n=== VERIFICATION COMPLETE ===\n"
        
        self.verify_results.setText(result_text)
        QMessageBox.information(self, "Auto Verify", "Verification complete. Check results panel.")
    
    def analyze_logic_relations(self):
        """Analyze logic relationships between signals and generate truth tables"""
        if not hasattr(self, 'signals_dict') or not self.signals_dict:
            QMessageBox.information(self, "Logic Analysis",
                                   "No signals loaded. Please run simulation first.")
            return
        
        # Get all checked (visible) signals
        checked_signals = []
        
        def collect_checked(parent_item):
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                if child.checkState(0) == Qt.Checked:
                    sig_id = child.data(0, Qt.UserRole)
                    if sig_id and sig_id in self.signals_dict:
                        checked_signals.append((sig_id, self.signals_dict[sig_id]))
                collect_checked(child)
        
        if self.signal_list.topLevelItemCount() > 0:
            collect_checked(self.signal_list.topLevelItem(0))
        
        if len(checked_signals) < 2:
            QMessageBox.information(self, "Logic Analysis",
                                   "Please select at least 2 signals (inputs and output).\n\n"
                                   "Example: Select input_a, input_b, and output for AND gate analysis.")
            return
        
        # Separate signals into potential inputs and outputs
        # Usually output signals have more dependencies
        single_bit_signals = [(sid, sig) for sid, sig in checked_signals if sig['width'] == 1]
        
        if len(single_bit_signals) < 2:
            QMessageBox.information(self, "Logic Analysis",
                                   "Logic analysis requires at least 2 single-bit signals.\n"
                                   "Multi-bit (bus) signals are not supported for truth table analysis.")
            return
        
        # Analyze logic relationships
        result_text = "=== LOGIC ANALYSIS ===\n\n"
        
        # Assume last signal is output, rest are inputs (user can select differently)
        if len(single_bit_signals) <= 4:  # Maximum 3 inputs + 1 output for reasonable truth table
            self.analyze_combinational_logic(single_bit_signals)
        else:
            result_text += "⚠ Too many signals selected (max 4 for truth table)\n"
            result_text += f"Selected: {len(single_bit_signals)} signals\n"
            result_text += "Please select 2-4 signals for analysis\n"
            self.detected_gates.setText(result_text)
    
    def analyze_combinational_logic(self, signals):
        """Analyze combinational logic and generate truth table"""
        # Clear truth table
        self.truth_table.clear()
        
        # Try different combinations of inputs/outputs
        num_signals = len(signals)
        
        # Most common: last signal is output, rest are inputs
        inputs = signals[:-1]
        output = signals[-1]
        
        result_text = f"╔════════════════════════════════════════╗\n"
        result_text += f"║      LOGIC GATE ANALYSIS              ║\n"
        result_text += f"╚════════════════════════════════════════╝\n\n"
        
        result_text += f"📊 Configuration: {len(inputs)} INPUT(S) → 1 OUTPUT\n\n"
        
        result_text += f"📥 INPUTS ({len(inputs)}):\n"
        for idx, (sid, sig) in enumerate(inputs, 1):
            full_name = sig['full_name']
            result_text += f"   [{idx}] {sig['name']}\n"
            result_text += f"       Path: {full_name}\n"
        
        result_text += f"\n📤 OUTPUT:\n"
        out_full = output[1]['full_name']
        result_text += f"   [→] {output[1]['name']}\n"
        result_text += f"       Path: {out_full}\n\n"
        
        result_text += "─" * 45 + "\n\n"
        
        # Collect all unique input combinations from waveform
        time_points = set()
        for sid, sig in inputs + [output]:
            for time, value in sig['values']:
                time_points.add(time)
        
        time_points = sorted(time_points)
        
        # Sample values at each time point
        logic_samples = []
        for time in time_points:
            sample = {'time': time, 'inputs': [], 'output': None}
            
            # Get input values at this time
            for sid, sig in inputs:
                value = self.get_signal_value_at_time(sig, time)
                sample['inputs'].append(value)
            
            # Get output value at this time
            output_value = self.get_signal_value_at_time(output[1], time)
            sample['output'] = output_value
            
            # Only include samples with valid values (not X or Z)
            if all(v in ['0', '1'] for v in sample['inputs']) and sample['output'] in ['0', '1']:
                logic_samples.append(sample)
        
        if not logic_samples:
            result_text += "⚠ No valid logic samples found\n"
            result_text += "Signals may contain X/Z values or not be synchronized\n"
            self.detected_gates.setText(result_text)
            return
        
        # Build truth table from unique combinations
        truth_table_data = {}
        for sample in logic_samples:
            input_tuple = tuple(sample['inputs'])
            output_val = sample['output']
            
            if input_tuple not in truth_table_data:
                truth_table_data[input_tuple] = []
            truth_table_data[input_tuple].append(output_val)
        
        # Consolidate truth table (most common output for each input combination)
        truth_table = {}
        for input_combo, outputs in truth_table_data.items():
            # Take most common output value
            most_common = max(set(outputs), key=outputs.count)
            truth_table[input_combo] = most_common
        
        # Display truth table
        result_text += f"📋 TRUTH TABLE ({len(truth_table)} combinations):\n"
        result_text += "╔" + "═" * 43 + "╗\n"
        
        # Header
        input_names = [sig[1]['name'][:8] for sig in inputs]
        output_name = output[1]['name'][:8]
        header = "║ " + " │ ".join(f"{name:^6}" for name in input_names)
        header += f" ║ {output_name:^6} ║\n"
        result_text += header
        result_text += "╠" + "═" * 43 + "╣\n"
        
        # Sort truth table by input values for readability
        sorted_combos = sorted(truth_table.keys())
        
        for input_combo in sorted_combos:
            output_val = truth_table[input_combo]
            row = "║ " + " │ ".join(f"  {v}   " for v in input_combo)
            row += f" ║   {output_val}    ║\n"
            result_text += row
            
            # Add to tree widget
            inputs_str = " ".join(input_combo)
            output_str = output_val
            
            item = QTreeWidgetItem([inputs_str, "→", output_str, ""])
            
            # Color code: Green for 1, Gray for 0
            if output_val == '1':
                item.setForeground(2, QColor(0, 255, 100))
            else:
                item.setForeground(2, QColor(150, 150, 150))
            
            self.truth_table.addTopLevelItem(item)
        
        result_text += "╚" + "═" * 43 + "╝\n\n"
        
        # Detect logic gate type
        gate_type = self.detect_gate_type(truth_table, len(inputs))
        result_text += f"🔍 DETECTED LOGIC: {gate_type}\n"
        result_text += "─" * 45 + "\n\n"
        
        # Add gate type to truth table
        for i in range(self.truth_table.topLevelItemCount()):
            item = self.truth_table.topLevelItem(i)
            item.setText(3, gate_type)
            item.setForeground(3, QColor(251, 191, 36))
        
        # Verification
        result_text += self.verify_gate_logic(gate_type, truth_table, len(inputs))
        
        self.detected_gates.setText(result_text)
        
        # Show success message
        QMessageBox.information(self, "Logic Analysis Complete",
                               f"✓ Detected: {gate_type}\n\n"
                               f"Found {len(truth_table)} unique input combinations\n\n"
                               f"Module Path:\n{out_full}\n\n"
                               f"Check Logic Analysis panel for complete truth table")
    
    def get_signal_value_at_time(self, signal, time):
        """Get signal value at specific time"""
        if not signal['values']:
            return 'X'
        
        # Find value at or before this time
        value = signal['values'][0][1]  # Start with first value
        for t, v in signal['values']:
            if t <= time:
                value = v
            else:
                break
        
        return str(value)
    
    def detect_gate_type(self, truth_table, num_inputs):
        """Detect logic gate type from truth table"""
        if num_inputs == 1:
            # Single input - check for NOT
            input_0 = truth_table.get(('0',), None)
            input_1 = truth_table.get(('1',), None)
            
            if input_0 == '1' and input_1 == '0':
                return "NOT Gate"
            elif input_0 == '0' and input_1 == '1':
                return "BUFFER"
            else:
                return "Unknown"
        
        elif num_inputs == 2:
            # Two inputs - check for AND, OR, XOR, NAND, NOR, XNOR
            out_00 = truth_table.get(('0', '0'), 'X')
            out_01 = truth_table.get(('0', '1'), 'X')
            out_10 = truth_table.get(('1', '0'), 'X')
            out_11 = truth_table.get(('1', '1'), 'X')
            
            # AND: only 1,1 = 1
            if out_00 == '0' and out_01 == '0' and out_10 == '0' and out_11 == '1':
                return "AND Gate"
            
            # OR: any input 1 = 1
            elif out_00 == '0' and out_01 == '1' and out_10 == '1' and out_11 == '1':
                return "OR Gate"
            
            # XOR: different inputs = 1
            elif out_00 == '0' and out_01 == '1' and out_10 == '1' and out_11 == '0':
                return "XOR Gate"
            
            # NAND: inverted AND
            elif out_00 == '1' and out_01 == '1' and out_10 == '1' and out_11 == '0':
                return "NAND Gate"
            
            # NOR: inverted OR
            elif out_00 == '1' and out_01 == '0' and out_10 == '0' and out_11 == '0':
                return "NOR Gate"
            
            # XNOR: inverted XOR
            elif out_00 == '1' and out_01 == '0' and out_10 == '0' and out_11 == '1':
                return "XNOR Gate"
            
            else:
                return "Custom Logic"
        
        elif num_inputs == 3:
            # Three inputs - check for basic gates
            ones_count = sum(1 for out in truth_table.values() if out == '1')
            
            if ones_count == 1:
                # Check if it's AND (all 1s = 1)
                if truth_table.get(('1', '1', '1'), '0') == '1':
                    return "3-input AND"
            elif ones_count == 7:
                # Check if it's OR (any 1 = 1)
                if truth_table.get(('0', '0', '0'), '1') == '0':
                    return "3-input OR"
            elif ones_count == 4:
                return "3-input XOR/Complex"
            
            return "3-input Logic"
        
        else:
            return f"{num_inputs}-input Logic"
    
    def verify_gate_logic(self, gate_type, truth_table, num_inputs):
        """Verify if gate follows expected logic"""
        result = "VERIFICATION:\n"
        
        if "AND" in gate_type and "NAND" not in gate_type:
            result += "✓ AND Gate Rules (Correct Logic):\n"
            result += "  • 0 AND 0 = 0 ✓\n"
            result += "  • 0 AND 1 = 0 ✓\n"
            result += "  • 1 AND 0 = 0 ✓\n"
            result += "  • 1 AND 1 = 1 ✓\n"
            result += "  • Output = 1 ONLY when ALL inputs = 1\n"
            result += "  • Output = 0 if ANY input = 0\n"
            
            # Verify actual truth table matches
            errors = []
            if num_inputs == 2:
                expected = {
                    ('0', '0'): '0',
                    ('0', '1'): '0',
                    ('1', '0'): '0',
                    ('1', '1'): '1'
                }
                for inputs, expected_out in expected.items():
                    actual_out = truth_table.get(inputs, 'X')
                    if actual_out != expected_out:
                        errors.append(f"  ✗ Error: {inputs[0]} AND {inputs[1]} should be {expected_out}, got {actual_out}")
                
                if not errors:
                    result += "  ✓ ALL COMBINATIONS VERIFIED CORRECT!\n"
                else:
                    result += "\n".join(errors) + "\n"
            else:
                # Multi-input AND
                all_ones = tuple(['1'] * num_inputs)
                if truth_table.get(all_ones, '0') == '1':
                    result += f"  ✓ Correct: All {num_inputs} inputs = 1 → Output = 1\n"
                else:
                    result += f"  ✗ Error: All {num_inputs} inputs = 1 should → Output = 1\n"
        
        elif "OR" in gate_type and "NOR" not in gate_type and "XOR" not in gate_type:
            result += "✓ OR Gate Rules (Correct Logic):\n"
            result += "  • 0 OR 0 = 0 ✓\n"
            result += "  • 0 OR 1 = 1 ✓\n"
            result += "  • 1 OR 0 = 1 ✓\n"
            result += "  • 1 OR 1 = 1 ✓\n"
            result += "  • Output = 1 when ANY input = 1\n"
            result += "  • Output = 0 only when ALL inputs = 0\n"
            
            # Verify
            if num_inputs == 2:
                expected = {
                    ('0', '0'): '0',
                    ('0', '1'): '1',
                    ('1', '0'): '1',
                    ('1', '1'): '1'
                }
                errors = []
                for inputs, expected_out in expected.items():
                    actual_out = truth_table.get(inputs, 'X')
                    if actual_out != expected_out:
                        errors.append(f"  ✗ Error: {inputs[0]} OR {inputs[1]} should be {expected_out}, got {actual_out}")
                
                if not errors:
                    result += "  ✓ ALL COMBINATIONS VERIFIED CORRECT!\n"
                else:
                    result += "\n".join(errors) + "\n"
            else:
                all_zeros = tuple(['0'] * num_inputs)
                if truth_table.get(all_zeros, '1') == '0':
                    result += f"  ✓ Correct: All {num_inputs} inputs = 0 → Output = 0\n"
                else:
                    result += f"  ✗ Error: All {num_inputs} inputs = 0 should → Output = 0\n"
        
        elif "XOR" in gate_type and "XNOR" not in gate_type:
            result += "✓ XOR Gate Rules (Correct Logic):\n"
            result += "  • 0 XOR 0 = 0 ✓\n"
            result += "  • 0 XOR 1 = 1 ✓\n"
            result += "  • 1 XOR 0 = 1 ✓\n"
            result += "  • 1 XOR 1 = 0 ✓\n"
            result += "  • Output = 1 when inputs are DIFFERENT\n"
            result += "  • Output = 0 when inputs are SAME\n"
            
            if num_inputs == 2:
                expected = {
                    ('0', '0'): '0',
                    ('0', '1'): '1',
                    ('1', '0'): '1',
                    ('1', '1'): '0'
                }
                errors = []
                for inputs, expected_out in expected.items():
                    actual_out = truth_table.get(inputs, 'X')
                    if actual_out != expected_out:
                        errors.append(f"  ✗ Error: {inputs[0]} XOR {inputs[1]} should be {expected_out}, got {actual_out}")
                
                if not errors:
                    result += "  ✓ ALL COMBINATIONS VERIFIED CORRECT!\n"
                else:
                    result += "\n".join(errors) + "\n"
        
        elif "NOT" in gate_type:
            result += "✓ NOT Gate Rules (Correct Logic):\n"
            result += "  • NOT 0 = 1 ✓\n"
            result += "  • NOT 1 = 0 ✓\n"
            result += "  • Output = opposite of input\n"
            
            expected = {('0',): '1', ('1',): '0'}
            errors = []
            for inputs, expected_out in expected.items():
                actual_out = truth_table.get(inputs, 'X')
                if actual_out != expected_out:
                    errors.append(f"  ✗ Error: NOT {inputs[0]} should be {expected_out}, got {actual_out}")
            
            if not errors:
                result += "  ✓ ALL COMBINATIONS VERIFIED CORRECT!\n"
            else:
                result += "\n".join(errors) + "\n"
        
        elif "NAND" in gate_type:
            result += "✓ NAND Gate Rules (Correct Logic):\n"
            result += "  • 0 NAND 0 = 1 ✓\n"
            result += "  • 0 NAND 1 = 1 ✓\n"
            result += "  • 1 NAND 0 = 1 ✓\n"
            result += "  • 1 NAND 1 = 0 ✓\n"
            result += "  • Output = 0 only when ALL inputs = 1\n"
            result += "  • Inverted AND gate\n"
            
            if num_inputs == 2:
                expected = {
                    ('0', '0'): '1',
                    ('0', '1'): '1',
                    ('1', '0'): '1',
                    ('1', '1'): '0'
                }
                errors = []
                for inputs, expected_out in expected.items():
                    actual_out = truth_table.get(inputs, 'X')
                    if actual_out != expected_out:
                        errors.append(f"  ✗ Error: {inputs[0]} NAND {inputs[1]} should be {expected_out}, got {actual_out}")
                
                if not errors:
                    result += "  ✓ ALL COMBINATIONS VERIFIED CORRECT!\n"
                else:
                    result += "\n".join(errors) + "\n"
        
        elif "NOR" in gate_type:
            result += "✓ NOR Gate Rules (Correct Logic):\n"
            result += "  • 0 NOR 0 = 1 ✓\n"
            result += "  • 0 NOR 1 = 0 ✓\n"
            result += "  • 1 NOR 0 = 0 ✓\n"
            result += "  • 1 NOR 1 = 0 ✓\n"
            result += "  • Output = 1 only when ALL inputs = 0\n"
            result += "  • Inverted OR gate\n"
            
            if num_inputs == 2:
                expected = {
                    ('0', '0'): '1',
                    ('0', '1'): '0',
                    ('1', '0'): '0',
                    ('1', '1'): '0'
                }
                errors = []
                for inputs, expected_out in expected.items():
                    actual_out = truth_table.get(inputs, 'X')
                    if actual_out != expected_out:
                        errors.append(f"  ✗ Error: {inputs[0]} NOR {inputs[1]} should be {expected_out}, got {actual_out}")
                
                if not errors:
                    result += "  ✓ ALL COMBINATIONS VERIFIED CORRECT!\n"
                else:
                    result += "\n".join(errors) + "\n"
        
        else:
            result += "ℹ Custom logic detected\n"
            result += "  Check truth table for behavior\n"
        
        return result
    
    # === END LOGIC ANALYSIS ===
    
    def inspect_values_at_cursor(self):
        """Show detailed signal values at cursor position for debugging"""
        if not hasattr(self, 'waveform_widget') or self.waveform_widget.cursor_time is None:
            QMessageBox.information(self, "Inspect Values",
                                   "Please move the mouse over the waveform to position the cursor.")
            return
        
        if not hasattr(self, 'signals_dict') or not self.signals_dict:
            QMessageBox.information(self, "Inspect Values",
                                   "No signals loaded. Please load a VCD file first.")
            return
        
        cursor_time = self.waveform_widget.cursor_time
        visible_signals = self.waveform_widget.visible_signals
        
        if not visible_signals:
            QMessageBox.information(self, "Inspect Values",
                                   "No signals selected. Please check some signals to display.")
            return
        
        # Build detailed inspection report
        report = f"╔{'═' * 58}╗\n"
        report += f"║{'SIGNAL VALUE INSPECTION':^58}║\n"
        report += f"╠{'═' * 58}╣\n"
        report += f"║ Time: {cursor_time} ns{' ' * (50 - len(str(cursor_time)))}║\n"
        report += f"╠{'═' * 58}╣\n\n"
        
        # Collect values for all visible signals
        for idx, sig_id in enumerate(visible_signals, 1):
            if sig_id in self.signals_dict:
                sig = self.signals_dict[sig_id]
                value = self.get_signal_value_at_time(sig, cursor_time)
                
                report += f"[{idx}] {sig['name']}\n"
                report += f"    Path: {sig['full_name']}\n"
                report += f"    Type: {sig['type']}, Width: {sig['width']} bit(s)\n"
                
                # Format value
                if sig['width'] == 1:
                    if value == '1':
                        report += f"    Value: 1 (HIGH) ✓\n"
                    elif value == '0':
                        report += f"    Value: 0 (LOW)\n"
                    elif value in 'xX':
                        report += f"    Value: X (UNKNOWN) ⚠\n"
                    elif value in 'zZ':
                        report += f"    Value: Z (HIGH-IMPEDANCE) ⚠\n"
                    else:
                        report += f"    Value: {value}\n"
                else:
                    # Multi-bit
                    try:
                        if 'x' not in str(value).lower() and 'z' not in str(value).lower():
                            hex_val = hex(int(value, 2))[2:].upper()
                            dec_val = int(value, 2)
                            bin_val = value
                            report += f"    Binary: {bin_val}\n"
                            report += f"    Hex: 0x{hex_val}\n"
                            report += f"    Decimal: {dec_val}\n"
                        else:
                            report += f"    Value: {value} (contains X/Z)\n"
                    except:
                        report += f"    Value: {value}\n"
                
                report += "\n"
        
        report += "─" * 60 + "\n"
        report += "💡 TIP: Move cursor over waveform to change inspection time\n"
        report += "💡 Use hover tooltip for quick value preview\n"
        
        # Show in message box with monospace font
        msg = QMessageBox(self)
        msg.setWindowTitle("🔍 Signal Value Inspection")
        msg.setText(report)
        msg.setStyleSheet("QLabel { font-family: 'Consolas', 'Courier New', monospace; font-size: 10pt; }")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()
    
    def export_waveform(self):
        """Export waveform as image or data"""
        from PySide6.QtWidgets import QFileDialog
        
        file_filter = "PNG Image (*.png);;PDF Document (*.pdf);;CSV Data (*.csv)"
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Export Waveform", "", file_filter)
        
        if not file_path:
            return
        
        if "PNG" in selected_filter:
            # Export as PNG image
            pixmap = self.waveform_widget.grab()
            if pixmap.save(file_path, "PNG"):
                QMessageBox.information(self, "Export", f"Waveform exported to:\n{file_path}")
            else:
                QMessageBox.warning(self, "Export", "Failed to export waveform.")
        
        elif "PDF" in selected_filter:
            # Export as PDF
            from PySide6.QtPrintSupport import QPrinter
            from PySide6.QtGui import QPainter
            
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            
            painter = QPainter(printer)
            self.waveform_widget.render(painter)
            painter.end()
            
            QMessageBox.information(self, "Export", f"Waveform exported to:\n{file_path}")
        
        elif "CSV" in selected_filter:
            # Export signal data as CSV
            if not hasattr(self, 'signals_dict') or not self.signals_dict:
                QMessageBox.warning(self, "Export", "No signal data to export.")
                return
            
            try:
                with open(file_path, 'w') as f:
                    # Write header
                    f.write("Time (ns),Signal,Value\n")
                    
                    # Write all signal changes
                    all_changes = []
                    for sig_id, signal in self.signals_dict.items():
                        for time, value in signal['values']:
                            all_changes.append((time, signal['name'], value))
                    
                    # Sort by time
                    all_changes.sort(key=lambda x: x[0])
                    
                    # Write data
                    for time, name, value in all_changes:
                        f.write(f"{time},{name},{value}\n")
                
                QMessageBox.information(self, "Export", f"Signal data exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.warning(self, "Export", f"Failed to export data:\n{str(e)}")
    
    # === END NEW METHODS ===
    
    def change_theme(self, theme_name):
        """Change application theme"""
        self.current_theme = theme_name
        self.apply_themed_style()
        
        # Update syntax highlighter theme (map to highlighter theme names)
        highlighter_theme_map = {
            "Dark Blue Ocean": "Dark Blue",
            "Midnight Purple": "Dracula",
            "Volcanic Ash": "Monokai",
            "Deep Teal": "Solarized Dark",
            "Arctic Blue": "Nord",
        }
        
        highlighter_theme = highlighter_theme_map.get(theme_name, "Dark Blue")
        if self.syntax_highlighter:
            self.syntax_highlighter.update_theme(highlighter_theme)
        
        self.statusBar.showMessage(f"Theme changed to: {theme_name}", 2000)
    
    def change_opacity(self, value):
        """Change theme opacity"""
        self.current_opacity = value / 100.0
        self.opacity_label.setText(f"{value}%")
        self.apply_themed_style()
        self.statusBar.showMessage(f"Opacity: {value}%", 1000)
    
    def apply_themed_style(self):
        """Apply current theme and opacity"""
        stylesheet = self.theme_manager.get_stylesheet(self.current_theme, self.current_opacity)
        self.setStyleSheet(stylesheet)
    
    def show_welcome_screen(self):
        """Show welcome screen"""
        welcome = WelcomeDialog(self)
        welcome.exec()
    
    def show_about(self):
        """Show professional about dialog"""
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("About AWaveViewer")
        about_dialog.setFixedSize(500, 400)
        about_dialog.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        
        layout = QVBoxLayout(about_dialog)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("AWaveViewer")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: #60a5fa;
                font-size: 28px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
        """)
        layout.addWidget(title)
        
        # Version
        version = QLabel("Version 1.0 Professional Edition")
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("""
            QLabel {
                color: #bae6fd;
                font-size: 13px;
                font-family: 'Segoe UI';
            }
        """)
        layout.addWidget(version)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #475569; max-height: 2px;")
        layout.addWidget(separator)
        
        # Description
        desc = QLabel(
            "A comprehensive Verilog simulation and waveform viewing tool\n"
            "with automatic testbench generation and full verification capabilities."
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                font-size: 11px;
                font-family: 'Segoe UI';
                line-height: 1.5;
            }
        """)
        layout.addWidget(desc)
        
        # Author info frame
        author_frame = QFrame()
        author_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(59, 130, 246, 0.1);
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        author_layout = QVBoxLayout(author_frame)
        author_layout.setSpacing(8)
        
        author_label = QLabel("[Author] Author")
        author_label.setStyleSheet("color: #60a5fa; font-weight: bold; font-size: 12px;")
        author_layout.addWidget(author_label)
        
        author_name = QLabel("Shahrear Hossain Shawon")
        author_name.setStyleSheet("color: #bae6fd; font-size: 13px; font-weight: bold;")
        author_layout.addWidget(author_name)
        
        license_label = QLabel("[Org] License")
        license_label.setStyleSheet("color: #60a5fa; font-weight: bold; font-size: 12px; margin-top: 10px;")
        author_layout.addWidget(license_label)
        
        license_name = QLabel("Algo Science Lab")
        license_name.setStyleSheet("color: #bae6fd; font-size: 13px; font-weight: bold;")
        author_layout.addWidget(license_name)
        
        layout.addWidget(author_frame)
        
        # Copyright
        copyright_label = QLabel("© 2025 Algo Science Lab. All Rights Reserved.")
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 10px;
                font-family: 'Segoe UI';
                margin-top: 10px;
            }
        """)
        layout.addWidget(copyright_label)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(35)
        close_btn.clicked.connect(about_dialog.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #8b5cf6);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563eb, stop:1 #7c3aed);
            }
        """)
        layout.addWidget(close_btn)
        
        about_dialog.exec()
    
    def closeEvent(self, event):
        """Clean up on close"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AWaveViewer")
    app.setApplicationDisplayName("AWaveViewer Professional")
    app.setOrganizationName("Algo Science Lab")
    app.setOrganizationDomain("algosciencelab.com")
    
    # Show splash screen
    splash = SplashScreen()
    splash.show()
    app.processEvents()
    
    # Simulate loading process with 10 second total duration
    loading_steps = [
        (10, "Initializing AWaveViewer..."),
        (20, "Loading core modules..."),
        (30, "Setting up Verilog parser..."),
        (40, "Initializing testbench generator..."),
        (50, "Configuring simulation engine..."),
        (60, "Loading waveform renderer..."),
        (70, "Setting up signal analyzer..."),
        (80, "Preparing VCD parser..."),
        (90, "Finalizing interface..."),
        (100, "Starting application...")
    ]
    
    for i, (progress, message) in enumerate(loading_steps):
        delay = int((i + 1) * 1000)  # Spread across 10 seconds
        QTimer.singleShot(delay, lambda p=progress, m=message: splash.set_progress(p, m))
    
    # Wait for splash to finish (10 seconds)
    QTimer.singleShot(10000, splash.close)
    
    # Show welcome dialog after splash
    def show_welcome():
        welcome = WelcomeDialog()
        if welcome.exec() == QDialog.Accepted:
            viewer = AWaveViewer()
            viewer.show()
        else:
            sys.exit(0)
    
    QTimer.singleShot(10100, show_welcome)
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
