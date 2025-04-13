#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مكونات واجهة المستخدم الرسومية للتطبيق
"""
import os
import sys
import logging
import webbrowser
from typing import Dict, List, Any, Optional, Union, Callable
from pathlib import Path
from datetime import datetime
from PySide6.QtGui import QTextFormat  # إضافة استيراد QTextFormat
from PySide6.QtWidgets import QDialogButtonBox, QProgressDialog  # إضافة استيرادات مفقودة

from PySide6.QtCore import (
    Qt, QSize, QTimer, Signal, Slot, QObject, QThread, QPoint, QRect, QEvent,
    QModelIndex, QSortFilterProxyModel, QAbstractItemModel, QItemSelectionModel
)
from PySide6.QtGui import (
    QFont, QFontMetrics, QIcon, QPixmap, QColor, QPainter, QPen, QAction,
    QSyntaxHighlighter, QTextCharFormat, QTextCursor, QKeySequence, QPalette,
    QBrush, QLinearGradient, QTextDocument, QStandardItemModel, QStandardItem,
    QTextOption, QPainterPath, QTextBlockFormat, QTextListFormat, QValidator
)
from PySide6.QtWidgets import (
    QWidget, QMainWindow, QTabWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFormLayout, QLabel, QPushButton, QLineEdit, QTextEdit, QPlainTextEdit,
    QTreeView, QListView, QTableView, QComboBox, QCheckBox, QRadioButton,
    QSpinBox, QDoubleSpinBox, QSlider, QScrollArea, QSplitter, QFrame,
    QGroupBox, QFileDialog, QMessageBox, QDialog, QToolBar, QToolButton,
    QStatusBar, QApplication, QMenu, QSizePolicy, QProgressBar, QStyle,
    QMenuBar, QDockWidget, QToolTip, QHeaderView, QStyleFactory, QTabBar
)

from project_model import Project, CodeFile, CodeEntity
from utils import get_icon_path
from analyzer import CodeAnalyzer

logger = logging.getLogger("CodeAnalyzer.UI")

# ===== المكونات المساعدة =====

class SyntaxHighlighter(QSyntaxHighlighter):
    """مُبرِز بناء الجملة للشفرة البرمجية"""
    
    def __init__(self, document: QTextDocument, language: str = "python"):
        """
        تهيئة مبرز بناء الجملة
        
        Args:
            document: مستند النص
            language: لغة البرمجة
        """
        super().__init__(document)
        self.language = language.lower()
        self.highlighting_rules = []
        self.formats = {}
        
        self._setup_formats()
        self._setup_rules()
    
    def _setup_formats(self):
        """إعداد تنسيقات النص"""
        # كلمات مفتاحية
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))
        keyword_format.setFontWeight(QFont.Bold)
        self.formats["keyword"] = keyword_format
        
        # التعليقات
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#608B4E"))
        comment_format.setFontItalic(True)
        self.formats["comment"] = comment_format
        
        # سلاسل النصوص
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))
        self.formats["string"] = string_format
        
        # الكلاسات والدوال
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#DCDCAA"))
        self.formats["function"] = function_format
        
        class_format = QTextCharFormat()
        class_format.setForeground(QColor("#4EC9B0"))
        class_format.setFontWeight(QFont.Bold)
        self.formats["class"] = class_format
        
        # الثوابت والأرقام
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8"))
        self.formats["number"] = number_format
        
        # المتغيرات الخاصة
        self_format = QTextCharFormat()
        self_format.setForeground(QColor("#569CD6"))
        self_format.setFontWeight(QFont.Bold)
        self.formats["self"] = self_format
        
        # العمليات والرموز
        operator_format = QTextCharFormat()
        operator_format.setForeground(QColor("#D4D4D4"))
        self.formats["operator"] = operator_format
        
        # الإضافات الخاصة بالذكاء الاصطناعي
        ai_format = QTextCharFormat()
        ai_format.setForeground(QColor("#C586C0"))
        ai_format.setFontWeight(QFont.Bold)
        self.formats["ai"] = ai_format
    
    def _setup_rules(self):
        """إعداد قواعد التبريز حسب اللغة"""
        self.highlighting_rules = []
        
        if self.language == "python":
            # الكلمات المفتاحية في Python
            keywords = [
                "and", "as", "assert", "break", "class", "continue", "def",
                "del", "elif", "else", "except", "exec", "finally", "for",
                "from", "global", "if", "import", "in", "is", "lambda", "not",
                "or", "pass", "print", "raise", "return", "try", "while", "with",
                "yield", "async", "await", "nonlocal", "True", "False", "None"
            ]
            
            # أسماء دوال مرتبطة بالذكاء الاصطناعي
            ai_keywords = [
                r"\bopenai\b", r"\bclaude\b", r"\bgpt\b", r"\bllm\b", 
                r"\banthropic\b", r"\bchat\b", r"\bgrok\b", r"\bai\b", 
                r"\bmodel\b", r"\bgenerate\b", r"\bembedding\b", r"\bprompt\b",
                r"\bCompletion\b", r"\bChatCompletion\b"
            ]
            
            # إضافة قواعد الكلمات المفتاحية
            for word in keywords:
                pattern = r"\b" + word + r"\b"
                rule = (pattern, self.formats["keyword"])
                self.highlighting_rules.append(rule)
            
            # إضافة قواعد الذكاء الاصطناعي
            for pattern in ai_keywords:
                rule = (pattern, self.formats["ai"])
                self.highlighting_rules.append(rule)
            
            # الفئات والدوال
            self.highlighting_rules.append((r"\bclass\s+(\w+)", self.formats["class"]))
            self.highlighting_rules.append((r"\bdef\s+(\w+)\s*\(", self.formats["function"]))
            
            # التعليقات
            self.highlighting_rules.append((r"#[^\n]*", self.formats["comment"]))
            
            # سلاسل النصوص
            self.highlighting_rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', self.formats["string"]))
            self.highlighting_rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", self.formats["string"]))
            
            # سلاسل النصوص متعددة الأسطر
            self.highlighting_rules.append((r'""".*?"""', self.formats["string"]))
            self.highlighting_rules.append((r"'''.*?'''", self.formats["string"]))
            
            # الأرقام
            self.highlighting_rules.append((r"\b[0-9]+\b", self.formats["number"]))
            
            # كلمة self
            self.highlighting_rules.append((r"\bself\b", self.formats["self"]))
            
            # العمليات
            operators = [
                "=", "+", "-", "*", "/", "//", "%", "**", "+=", "-=", "*=", "/=",
                "//=", "%=", "**=", "&=", "|=", "^=", ">>=", "<<=", "==", "!=",
                ">", "<", ">=", "<=", "&", "|", "^", "~", "<<", ">>"
            ]
            for op in operators:
                if op in ["*", "+", "|", "&", "^"]:  # تجنب الرموز التي قد تكون جزءًا من تعبيرات عادية
                    pattern = r"\s\\" + op + r"\s"
                else:
                    pattern = r"\s" + op + r"\s"
                rule = (pattern, self.formats["operator"])
                self.highlighting_rules.append(rule)
        
        elif self.language in ["javascript", "typescript", "react"]:
            # الكلمات المفتاحية في JavaScript/TypeScript
            keywords = [
                "break", "case", "catch", "class", "const", "continue", "debugger",
                "default", "delete", "do", "else", "export", "extends", "false",
                "finally", "for", "function", "if", "import", "in", "instanceof",
                "new", "null", "return", "super", "switch", "this", "throw", "true",
                "try", "typeof", "var", "void", "while", "with", "let", "yield",
                "async", "await", "of", "static", "get", "set", "interface", "type",
                "implements", "enum", "package", "private", "protected", "public",
                "readonly", "as", "any", "boolean", "number", "string", "undefined"
            ]
            
            # إضافة قواعد الكلمات المفتاحية
            for word in keywords:
                pattern = r"\b" + word + r"\b"
                rule = (pattern, self.formats["keyword"])
                self.highlighting_rules.append(rule)
            
            # إضافة كلمات مفتاحية للذكاء الاصطناعي
            ai_keywords = [
                r"\bopenai\b", r"\bclaude\b", r"\bgpt\b", r"\bllm\b", 
                r"\banthropic\b", r"\bchat\b", r"\bgrok\b", r"\bai\b", 
                r"\bmodel\b", r"\bgenerate\b", r"\bembedding\b", r"\bprompt\b",
                r"\bCompletion\b", r"\bChatCompletion\b"
            ]
            
            for pattern in ai_keywords:
                rule = (pattern, self.formats["ai"])
                self.highlighting_rules.append(rule)
            
            # الدوال والفئات
            self.highlighting_rules.append((r"\bclass\s+(\w+)", self.formats["class"]))
            self.highlighting_rules.append((r"\bfunction\s+(\w+)\s*\(", self.formats["function"]))
            self.highlighting_rules.append((r"\bconst\s+(\w+)\s*=\s*\(", self.formats["function"]))
            self.highlighting_rules.append((r"\blet\s+(\w+)\s*=\s*\(", self.formats["function"]))
            self.highlighting_rules.append((r"\bvar\s+(\w+)\s*=\s*\(", self.formats["function"]))
            
            # React Hooks
            self.highlighting_rules.append((r"\buse[A-Z]\w*\b", self.formats["function"]))
            
            # التعليقات
            self.highlighting_rules.append((r"//[^\n]*", self.formats["comment"]))
            self.highlighting_rules.append((r"/\*.*?\*/", self.formats["comment"]))
            
            # سلاسل النصوص
            self.highlighting_rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', self.formats["string"]))
            self.highlighting_rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", self.formats["string"]))
            self.highlighting_rules.append((r"`[^`\\]*(\\.[^`\\]*)*`", self.formats["string"]))
            
            # الأرقام
            self.highlighting_rules.append((r"\b[0-9]+\b", self.formats["number"]))
            
            # كلمة this
            self.highlighting_rules.append((r"\bthis\b", self.formats["self"]))
    
    def highlightBlock(self, text: str):
        """
        تطبيق تبريز بناء الجملة على كتلة نصية
        
        Args:
            text: النص المراد تبريزه
        """
        import re
        
        # تطبيق قواعد التبريز
        for pattern, format_obj in self.highlighting_rules:
            matches = re.finditer(pattern, text)
            for match in matches:
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, format_obj)
        
        # معالجة سلاسل النصوص متعددة الأسطر
        if self.language == "python":
            self.highlightPythonMultilineStrings(text)
    
    def highlightPythonMultilineStrings(self, text: str):
        """
        تبريز سلاسل النصوص متعددة الأسطر في Python
        
        Args:
            text: النص المراد تبريزه
        """
        # حالة السلسلة النصية
        self.setCurrentBlockState(0)
        
        # التعامل مع سلاسل ثلاث علامات اقتباس
        startPos = 0
        if self.previousBlockState() != 1:
            startPos = text.find('"""')
        
        while startPos >= 0:
            endPos = text.find('"""', startPos + 3)
            if endPos == -1:
                self.setCurrentBlockState(1)
                length = len(text) - startPos
            else:
                length = endPos - startPos + 3
            
            self.setFormat(startPos, length, self.formats["string"])
            startPos = text.find('"""', startPos + length)
        
        # التعامل مع سلاسل ثلاث علامات اقتباس مفردة
        startPos = 0
        if self.previousBlockState() != 2:
            startPos = text.find("'''")
        
        while startPos >= 0:
            endPos = text.find("'''", startPos + 3)
            if endPos == -1:
                self.setCurrentBlockState(2)
                length = len(text) - startPos
            else:
                length = endPos - startPos + 3
            
            self.setFormat(startPos, length, self.formats["string"])
            startPos = text.find("'''", startPos + length)


class CodeEditor(QPlainTextEdit):
    """محرر الشفرة البرمجية"""
    
    def __init__(self, parent=None, language="python"):
        """
        تهيئة محرر الشفرة
        
        Args:
            parent: العنصر الأب
            language: لغة البرمجة
        """
        super().__init__(parent)
        self.language = language
        self.line_numbers = LineNumberArea(self)
        self.file_path = None
        self.current_file = None
        self.original_content = ""
        self.issue_markers = []  # علامات المشاكل في الشفرة
        
        # إعداد المحرر
        self._setup_editor()
        
        # توصيل الإشارات
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        
        # تطبيق العرض الأولي
        self.update_line_number_area_width(0)
        self.highlight_current_line()
    
    def _setup_editor(self):
        """إعداد محرر الشفرة"""
        # تعيين خط ثابت العرض
        font = QFont("Courier New")
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(10)
        self.setFont(font)
        
        # تعيين عرض علامة التبويب
        metrics = QFontMetrics(font)
        self.setTabStopDistance(4 * metrics.horizontalAdvance(' '))
        
        # تعيين خيارات النص
        document = self.document()
        options = document.defaultTextOption()
        options.setFlags(QTextOption.ShowTabsAndSpaces | QTextOption.AddSpaceForLineAndParagraphSeparators)
        document.setDefaultTextOption(options)
        
        # إنشاء مبرز بناء الجملة
        self.highlighter = SyntaxHighlighter(document, self.language)
        
        # تعيين عرض الهامش
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)
        
        # تفعيل دعم التراجع/الإعادة
        self.setUndoRedoEnabled(True)
        
        # تفعيل لف الأسطر الطويلة
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        
        # ضبط سياسة الحجم
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    
    def load_file(self, file_path: str, code_file: CodeFile = None):
        """
        تحميل ملف في المحرر
        
        Args:
            file_path: مسار الملف
            code_file: كائن CodeFile (اختياري)
        """
        self.file_path = file_path
        self.current_file = code_file
        
        try:
            if code_file and code_file.content:
                content = code_file.content
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            self.setPlainText(content)
            self.original_content = content
            
            # تحديد اللغة بناءً على امتداد الملف أو كائن CodeFile
            if code_file and code_file.language:
                self.language = code_file.language
            else:
                ext = os.path.splitext(file_path)[1].lower()
                if ext in ['.py']:
                    self.language = 'python'
                elif ext in ['.js', '.jsx']:
                    self.language = 'javascript'
                elif ext in ['.ts', '.tsx']:
                    self.language = 'typescript'
                elif ext in ['.html', '.htm']:
                    self.language = 'html'
                elif ext in ['.css']:
                    self.language = 'css'
                elif ext in ['.php']:
                    self.language = 'php'
                elif ext in ['.dart']:
                    self.language = 'dart'
                else:
                    self.language = 'text'
            
            # إعادة تهيئة المبرز
            self.highlighter = SyntaxHighlighter(self.document(), self.language)
            
            # إضافة علامات المشاكل إذا كان هناك كائن CodeFile
            if code_file:
                self.add_issue_markers(code_file.issues)
            
            return True
        except Exception as e:
            logger.error(f"فشل تحميل الملف {file_path}: {str(e)}")
            return False
    
    def save_file(self):
        """
        حفظ الملف الحالي
        
        Returns:
            bool: نجاح الحفظ
        """
        if not self.file_path:
            return False
        
        try:
            content = self.toPlainText()
            
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.original_content = content
            
            # تحديث كائن CodeFile إذا كان موجوداً
            if self.current_file:
                self.current_file.save_content(content)
            
            return True
        except Exception as e:
            logger.error(f"فشل حفظ الملف {self.file_path}: {str(e)}")
            return False
    
    def is_modified(self):
        """
        التحقق ما إذا كان المحتوى قد تم تعديله
        
        Returns:
            bool: حالة التعديل
        """
        return self.toPlainText() != self.original_content
    
    def add_issue_markers(self, issues: List[Dict[str, Any]]):
        """
        إضافة علامات للمشاكل في الشفرة
        
        Args:
            issues: قائمة المشاكل
        """
        self.issue_markers = []
        
        for issue in issues:
            line_number = issue.get('line', 0)
            severity = issue.get('severity', 'medium')
            message = issue.get('message', '')
            
            if line_number > 0:
                self.issue_markers.append({
                    'line': line_number,
                    'severity': severity,
                    'message': message
                })
        
        # تحديث المحرر
        self.update()
    
    def get_line_number_for_block(self, block):
        """
        الحصول على رقم السطر لكتلة معينة
        
        Args:
            block: كتلة النص
            
        Returns:
            int: رقم السطر
        """
        if not block.isValid():
            return -1
        
        block_number = block.blockNumber()
        return block_number + 1
    
    def line_number_area_width(self):
        """
        حساب عرض منطقة أرقام الأسطر
        
        Returns:
            int: العرض بالبكسل
        """
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        
        space = 15 + self.fontMetrics().horizontalAdvance('9') * digits
        return space
    
    def update_line_number_area_width(self, new_block_count):
        """
        تحديث عرض منطقة أرقام الأسطر
        
        Args:
            new_block_count: عدد الكتل الجديد
        """
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)
    
    def update_line_number_area(self, rect, dy):
        """
        تحديث منطقة أرقام الأسطر
        
        Args:
            rect: المستطيل المتأثر
            dy: التغيير العمودي
        """
        if dy:
            self.line_numbers.scroll(0, dy)
        else:
            self.line_numbers.update(0, rect.y(), self.line_numbers.width(), rect.height())
        
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)
    
    def resizeEvent(self, event):
        """
        معالجة حدث تغيير الحجم
        
        Args:
            event: حدث تغيير الحجم
        """
        super().resizeEvent(event)
        
        cr = self.contentsRect()
        self.line_numbers.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))
    
    def highlight_current_line(self):
        """تمييز السطر الحالي"""
        extra_selections = []
        
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            
            line_color = QColor(Qt.yellow).lighter(180)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            
            extra_selections.append(selection)
        
        # إضافة علامات للمشاكل
        for marker in self.issue_markers:
            line = marker['line'] - 1  # تعديل الفهرس ليبدأ من 0
            severity = marker['severity']
            
            if line < 0 or line >= self.blockCount():
                continue
            
            # اختيار لون حسب الخطورة
            if severity.lower() == 'high':
                color = QColor(Qt.red).lighter(170)
            elif severity.lower() == 'medium':
                color = QColor(Qt.yellow).lighter(170)
            else:
                color = QColor(Qt.cyan).lighter(170)
            
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            
            cursor = QTextCursor(self.document().findBlockByNumber(line))
            selection.cursor = cursor
            
            extra_selections.append(selection)
        
        self.setExtraSelections(extra_selections)
    
    def paintEvent(self, event):
        """
        معالجة حدث الرسم
        
        Args:
            event: حدث الرسم
        """
        super().paintEvent(event)
        
        # رسم علامات إضافية هنا إذا لزم الأمر
    
    def line_number_area_paint_event(self, event):
        """
        رسم منطقة أرقام الأسطر
        
        Args:
            event: حدث الرسم
        """
        painter = QPainter(self.line_numbers)
        painter.fillRect(event.rect(), QColor(Qt.lightGray).lighter(120))
        
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(Qt.black)
                painter.drawText(0, top, self.line_numbers.width() - 5, self.fontMetrics().height(),
                                Qt.AlignRight, number)
                
                # رسم علامات للمشاكل
                for marker in self.issue_markers:
                    if marker['line'] == block_number + 1:
                        severity = marker['severity'].lower()
                        
                        if severity == 'high':
                            color = QColor(Qt.red)
                        elif severity == 'medium':
                            color = QColor(Qt.yellow).darker(130)
                        else:
                            color = QColor(Qt.cyan).darker(130)
                        
                        painter.setPen(color)
                        painter.setBrush(color)
                        painter.drawEllipse(5, top + self.fontMetrics().height() // 2 - 3, 6, 6)
                        break
            
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1
    
    def goto_line(self, line_number: int):
        """
        الانتقال إلى سطر محدد
        
        Args:
            line_number: رقم السطر
        """
        if line_number < 1:
            return
        
        # الحصول على كتلة النص المطلوبة
        block = self.document().findBlockByLineNumber(line_number - 1)
        if not block.isValid():
            return
        
        # إنشاء مؤشر عند بداية الكتلة
        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.StartOfBlock)
        
        # تعيين المؤشر الحالي
        self.setTextCursor(cursor)
        
        # التأكد من أن السطر مرئي
        self.centerCursor()
        
        # تحديد الكتلة بأكملها
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)
        
        # تمييز السطر
        self.highlight_current_line()
    
    def goto_entity(self, entity: CodeEntity):
        """
        الانتقال إلى كيان برمجي
        
        Args:
            entity: الكيان البرمجي
        """
        if not entity:
            return
        
        self.goto_line(entity.start_line)


class LineNumberArea(QWidget):
    """منطقة عرض أرقام الأسطر في محرر الشفرة"""
    
    def __init__(self, editor):
        """
        تهيئة منطقة أرقام الأسطر
        
        Args:
            editor: محرر الشفرة المرتبط
        """
        super().__init__(editor)
        self.editor = editor
    
    def sizeHint(self):
        """
        تلميح الحجم
        
        Returns:
            QSize: الحجم المقترح
        """
        return QSize(self.editor.line_number_area_width(), 0)
    
    def paintEvent(self, event):
        """
        معالجة حدث الرسم
        
        Args:
            event: حدث الرسم
        """
        self.editor.line_number_area_paint_event(event)

# ===== نموذج البيانات لعرض الشجرة =====

class ProjectTreeModel(QStandardItemModel):
    """نموذج بيانات شجرة المشروع"""
    
    def __init__(self, parent=None):
        """
        تهيئة نموذج شجرة المشروع
        
        Args:
            parent: العنصر الأب
        """
        super().__init__(parent)
        self.setHorizontalHeaderLabels(["اسم العنصر", "النوع", "المسار"])
        self.project = None
        self.directory_icons = {}
        self.file_icons = {}
        self._load_icons()
    
    def _load_icons(self):
        """تحميل الأيقونات للأنواع المختلفة من العناصر"""
        # أيقونات المجلدات
        self.directory_icons = {
            "default": self.get_icon("folder"),
            "src": self.get_icon("folder-src"),
            "lib": self.get_icon("folder-lib"),
            "test": self.get_icon("folder-test"),
            "docs": self.get_icon("folder-docs"),
            "assets": self.get_icon("folder-assets"),
            "config": self.get_icon("folder-config")
        }
        
        # أيقونات الملفات
        self.file_icons = {
            "default": self.get_icon("file"),
            "python": self.get_icon("file-python"),
            "javascript": self.get_icon("file-js"),
            "react": self.get_icon("file-react"),
            "typescript": self.get_icon("file-ts"),
            "html": self.get_icon("file-html"),
            "css": self.get_icon("file-css"),
            "json": self.get_icon("file-json"),
            "dart": self.get_icon("file-dart"),
            "php": self.get_icon("file-php"),
            "markdown": self.get_icon("file-md"),
            "text": self.get_icon("file-text"),
            "image": self.get_icon("file-image"),
            "api": self.get_icon("file-api")
        }
    
    def get_icon(self, name: str) -> QIcon:
        """
        الحصول على أيقونة
        
        Args:
            name: اسم الأيقونة
            
        Returns:
            QIcon: الأيقونة
        """
        icon_path = get_icon_path(name)
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        return QIcon()
    
    def set_project(self, project: Project):
        """
        تعيين المشروع للنموذج
        
        Args:
            project: المشروع
        """
        self.project = project
        self.clear()
        self.setHorizontalHeaderLabels(["اسم العنصر", "النوع", "المسار"])
        
        if not project:
            return
        
        # الحصول على هيكل المشروع
        structure = project.get_project_structure()
        
        # إنشاء العنصر الجذري
        root_item = QStandardItem(structure["name"])
        root_item.setIcon(self.directory_icons.get("default"))
        root_item.setData(structure["name"], Qt.UserRole)
        root_item.setData("directory", Qt.UserRole + 1)
        root_item.setData(project.root_dir, Qt.UserRole + 2)
        
        # إضافة الوصف
        type_item = QStandardItem("مجلد المشروع")
        path_item = QStandardItem(project.root_dir)
        
        # إضافة للنموذج
        self.appendRow([root_item, type_item, path_item])
        
        # بناء الشجرة
        self._build_tree(structure["children"], root_item, project.root_dir)
    
    def _build_tree(self, children: List[Dict[str, Any]], parent_item: QStandardItem, parent_path: str):
        """
        بناء شجرة الملفات
        
        Args:
            children: قائمة العناصر الفرعية
            parent_item: العنصر الأب
            parent_path: مسار المجلد الأب
        """
        # ترتيب العناصر: المجلدات أولاً ثم الملفات
        folders = [c for c in children if c["type"] == "directory"]
        files = [c for c in children if c["type"] == "file"]
        
        # فرز المجلدات والملفات
        folders.sort(key=lambda x: x["name"])
        files.sort(key=lambda x: x["name"])
        
        # إضافة المجلدات
        for folder in folders:
            folder_name = folder["name"]
            folder_path = os.path.join(parent_path, folder_name)
            
            # إنشاء عنصر المجلد
            item = QStandardItem(folder_name)
            
            # تعيين الأيقونة المناسبة
            icon_key = folder_name.lower()
            if icon_key in self.directory_icons:
                item.setIcon(self.directory_icons[icon_key])
            else:
                item.setIcon(self.directory_icons["default"])
            
            # تخزين البيانات
            item.setData(folder_name, Qt.UserRole)
            item.setData("directory", Qt.UserRole + 1)
            item.setData(folder_path, Qt.UserRole + 2)
            
            # إضافة الوصف
            type_item = QStandardItem("مجلد")
            path_item = QStandardItem(folder_path)
            
            # إضافة للنموذج
            parent_item.appendRow([item, type_item, path_item])
            
            # بناء العناصر الفرعية
            if "children" in folder:
                self._build_tree(folder["children"], item, folder_path)
        
        # إضافة الملفات
        for file in files:
            file_name = file["name"]
            file_path = os.path.join(parent_path, file_name)
            language = file.get("language", "")
            
            # إنشاء عنصر الملف
            item = QStandardItem(file_name)
            
            # تعيين الأيقونة المناسبة
            ext = os.path.splitext(file_name)[1].lower()
            icon_key = None
            
            if language:
                icon_key = language
            elif ext in ['.py']:
                icon_key = "python"
            elif ext in ['.js', '.jsx']:
                icon_key = "javascript"
            elif ext in ['.ts', '.tsx']:
                icon_key = "typescript"
            elif ext in ['.html', '.htm']:
                icon_key = "html"
            elif ext in ['.css']:
                icon_key = "css"
            elif ext in ['.json']:
                icon_key = "json"
            elif ext in ['.md', '.markdown']:
                icon_key = "markdown"
            elif ext in ['.txt']:
                icon_key = "text"
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg']:
                icon_key = "image"
            elif ext in ['.php']:
                icon_key = "php"
            elif ext in ['.dart']:
                icon_key = "dart"
            
            # كشف ملفات API
            if "api" in file_name.lower() or language == "ai_javascript":
                icon_key = "api"
            
            if icon_key in self.file_icons:
                item.setIcon(self.file_icons[icon_key])
            else:
                item.setIcon(self.file_icons["default"])
            
            # تخزين البيانات
            item.setData(file_name, Qt.UserRole)
            item.setData("file", Qt.UserRole + 1)
            item.setData(file_path, Qt.UserRole + 2)
            item.setData(language, Qt.UserRole + 3)
            
            # إضافة الوصف
            entity_count = file.get("entity_count", 0)
            if language:
                type_item = QStandardItem(f"ملف {language} ({entity_count} كيان)")
            else:
                type_item = QStandardItem(f"ملف ({entity_count} كيان)")
            
            path_item = QStandardItem(file_path)
            
            # إضافة للنموذج
            parent_item.appendRow([item, type_item, path_item])
    
    def get_file_path(self, index: QModelIndex) -> str:
        """
        الحصول على مسار الملف للفهرس
        
        Args:
            index: فهرس العنصر
            
        Returns:
            str: مسار الملف
        """
        if not index.isValid():
            return ""
        
        item = self.itemFromIndex(index)
        if not item:
            return ""
        
        return item.data(Qt.UserRole + 2)
    
    def is_file(self, index: QModelIndex) -> bool:
        """
        التحقق ما إذا كان العنصر ملفاً
        
        Args:
            index: فهرس العنصر
            
        Returns:
            bool: هل هو ملف
        """
        if not index.isValid():
            return False
        
        item = self.itemFromIndex(index)
        if not item:
            return False
        
        return item.data(Qt.UserRole + 1) == "file"
    
    def is_directory(self, index: QModelIndex) -> bool:
        """
        التحقق ما إذا كان العنصر مجلداً
        
        Args:
            index: فهرس العنصر
            
        Returns:
            bool: هل هو مجلد
        """
        if not index.isValid():
            return False
        
        item = self.itemFromIndex(index)
        if not item:
            return False
        
        return item.data(Qt.UserRole + 1) == "directory"
    
    def get_language(self, index: QModelIndex) -> str:
        """
        الحصول على لغة الملف
        
        Args:
            index: فهرس العنصر
            
        Returns:
            str: لغة البرمجة
        """
        if not index.isValid() or not self.is_file(index):
            return ""
        
        item = self.itemFromIndex(index)
        if not item:
            return ""
        
        return item.data(Qt.UserRole + 3) or ""


class EntityTreeModel(QStandardItemModel):
    """نموذج بيانات شجرة الكيانات البرمجية"""
    
    def __init__(self, parent=None):
        """
        تهيئة نموذج شجرة الكيانات
        
        Args:
            parent: العنصر الأب
        """
        super().__init__(parent)
        self.setHorizontalHeaderLabels(["اسم الكيان", "النوع", "السطر"])
        self.code_file = None
        self.entity_icons = {}
        self._load_icons()
    
    def _load_icons(self):
        """تحميل الأيقونات للأنواع المختلفة من الكيانات"""
        self.entity_icons = {
            "class": self.get_icon("class"),
            "function": self.get_icon("function"),
            "method": self.get_icon("method"),
            "variable": self.get_icon("variable"),
            "property": self.get_icon("property"),
            "constant": self.get_icon("constant"),
            "component": self.get_icon("component"),
            "widget": self.get_icon("widget"),
            "controller": self.get_icon("controller"),
            "model": self.get_icon("model"),
            "default": self.get_icon("entity")
        }
    
    def get_icon(self, name: str) -> QIcon:
        """
        الحصول على أيقونة
        
        Args:
            name: اسم الأيقونة
            
        Returns:
            QIcon: الأيقونة
        """
        icon_path = get_icon_path(name)
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        return QIcon()
    
    def set_code_file(self, code_file: CodeFile):
        """
        تعيين ملف الشفرة للنموذج
        
        Args:
            code_file: ملف الشفرة
        """
        self.code_file = code_file
        self.clear()
        self.setHorizontalHeaderLabels(["اسم الكيان", "النوع", "السطر"])
        
        if not code_file:
            return
        
        # فرز الكيانات حسب نوعها ثم اسمها
        entities = sorted(code_file.entities, key=lambda e: (e.type, e.name))
        
        for entity in entities:
            self._add_entity(entity)
    
    def _add_entity(self, entity: CodeEntity, parent_item=None):
        """
        إضافة كيان إلى النموذج
        
        Args:
            entity: الكيان البرمجي
            parent_item: العنصر الأب (اختياري)
        """
        # إنشاء عنصر الكيان
        item = QStandardItem(entity.name)
        
        # تعيين الأيقونة المناسبة
        icon_key = entity.type
        item.setIcon(self.entity_icons.get(icon_key, self.entity_icons["default"]))
        
        # تخزين البيانات
        item.setData(entity.name, Qt.UserRole)
        item.setData(entity.type, Qt.UserRole + 1)
        item.setData(entity.start_line, Qt.UserRole + 2)
        item.setData(entity.file_path, Qt.UserRole + 3)
        item.setData(entity, Qt.UserRole + 4)  # تخزين الكيان نفسه
        
        # إضافة الخصائص المخصصة
        for prop_name, prop_value in entity.properties.items():
            item.setData(prop_value, Qt.UserRole + 10 + hash(prop_name) % 100)
        
        # تحديد لون خاص للكيانات المرتبطة بالذكاء الاصطناعي
        if entity.properties.get("is_ai_related") or "ai" in entity.name.lower() or "gpt" in entity.name.lower() or "claude" in entity.name.lower() or "grok" in entity.name.lower():
            item.setForeground(QBrush(QColor("#C586C0")))
            item.setData(True, Qt.UserRole + 5)  # كيان متعلق بالذكاء الاصطناعي
        
        # إضافة الوصف
        type_item = QStandardItem(self._get_entity_type_display(entity))
        line_item = QStandardItem(str(entity.start_line))
        
        # إضافة للنموذج
        row = [item, type_item, line_item]
        
        if parent_item:
            parent_item.appendRow(row)
            parent = parent_item
        else:
            self.appendRow(row)
            parent = self.invisibleRootItem()
        
        # إضافة العناصر الفرعية بترتيب
        children = sorted(entity.children, key=lambda e: (e.type, e.name))
        for child in children:
            self._add_entity(child, item)
    
    def _get_entity_type_display(self, entity: CodeEntity) -> str:
        """
        الحصول على عرض نوع الكيان
        
        Args:
            entity: الكيان البرمجي
            
        Returns:
            str: العرض النصي للنوع
        """
        # ترجمة أنواع الكيانات إلى العربية
        type_map = {
            "class": "صنف",
            "function": "دالة",
            "method": "طريقة",
            "variable": "متغير",
            "property": "خاصية",
            "constant": "ثابت",
            "component": "مكون",
            "widget": "أداة واجهة",
            "controller": "متحكم",
            "model": "نموذج"
        }
        
        base_type = type_map.get(entity.type, entity.type)
        
        # إضافة معلومات إضافية حسب الخصائص
        if entity.properties.get("is_constructor"):
            return f"{base_type} (مُنشئ)"
        elif entity.properties.get("is_magic_method"):
            return f"{base_type} (خاصة)"
        elif entity.properties.get("is_react_component"):
            return f"{base_type} (React)"
        elif entity.properties.get("is_react_hook"):
            return f"{base_type} (Hook)"
        elif entity.properties.get("is_build_method"):
            return f"{base_type} (build)"
        elif entity.properties.get("is_resource_method"):
            return f"{base_type} (resource)"
        elif entity.properties.get("is_model_property"):
            return f"{base_type} (model)"
        elif entity.properties.get("is_ai_related"):
            return f"{base_type} (AI)"
        elif entity.properties.get("is_sensitive"):
            return f"{base_type} (حساس)"
        
        return base_type
    
    def get_entity(self, index: QModelIndex) -> Optional[CodeEntity]:
        """
        الحصول على الكيان للفهرس
        
        Args:
            index: فهرس العنصر
            
        Returns:
            Optional[CodeEntity]: الكيان البرمجي
        """
        if not index.isValid():
            return None
        
        item = self.itemFromIndex(index)
        if not item:
            return None
        
        return item.data(Qt.UserRole + 4)


class IssueTableModel(QStandardItemModel):
    """نموذج بيانات جدول القضايا"""
    
    # ألوان حسب مستوى الخطورة
    SEVERITY_COLORS = {
        "high": QColor("#FF6B6B"),
        "medium": QColor("#FFD166"),
        "low": QColor("#06D6A0"),
        "info": QColor("#118AB2")
    }
    
    def __init__(self, parent=None):
        """
        تهيئة نموذج جدول القضايا
        
        Args:
            parent: العنصر الأب
        """
        super().__init__(parent)
        self.setHorizontalHeaderLabels([
            "الملف", "السطر", "الخطورة", "الرسالة", "التوصية", "المصدر"
        ])
        self.project = None
        self.issues = []
    
    def set_project(self, project: Project):
        """
        تعيين المشروع للنموذج
        
        Args:
            project: المشروع
        """
        self.project = project
        self.update_issues()
    
    def update_issues(self):
        """تحديث قائمة القضايا"""
        self.clear()
        self.setHorizontalHeaderLabels([
            "الملف", "السطر", "الخطورة", "الرسالة", "التوصية", "المصدر"
        ])
        
        if not self.project:
            return
        
        # جمع القضايا من المشروع
        self.issues = self.project.issues.copy()
        
        # جمع القضايا من الملفات
        for file_path, code_file in self.project.files.items():
            for issue in code_file.issues:
                if issue not in self.issues:
                    self.issues.append(issue)
        
        # فرز القضايا حسب الخطورة ثم الملف
        self.issues.sort(key=lambda x: (
            self._severity_sort_key(x.get('severity', 'medium')),
            x.get('file_path', ''),
            x.get('line', 0)
        ))
        
        # إضافة للنموذج
        for issue in self.issues:
            file_path = issue.get('file_path', '')
            line = issue.get('line', 0)
            severity = issue.get('severity', 'medium')
            message = issue.get('message', '')
            recommendation = issue.get('recommendation', '')
            source = issue.get('source', 'manual')
            
            file_item = QStandardItem(os.path.basename(file_path))
            file_item.setData(file_path, Qt.UserRole)
            file_item.setData(issue, Qt.UserRole + 1)
            
            line_item = QStandardItem(str(line))
            line_item.setData(line, Qt.UserRole)
            
            severity_item = QStandardItem(self._get_severity_display(severity))
            severity_item.setData(severity, Qt.UserRole)
            
            color = self.SEVERITY_COLORS.get(severity.lower(), QColor(Qt.gray))
            severity_item.setForeground(QBrush(color))
            
            message_item = QStandardItem(message)
            recommendation_item = QStandardItem(recommendation)
            source_item = QStandardItem(source)
            
            self.appendRow([
                file_item, line_item, severity_item,
                message_item, recommendation_item, source_item
            ])
    
    def _severity_sort_key(self, severity: str) -> int:
        """
        مفتاح فرز للخطورة
        
        Args:
            severity: مستوى الخطورة
            
        Returns:
            int: رقم للفرز
        """
        severity = severity.lower()
        if severity == 'high':
            return 0
        elif severity == 'medium':
            return 1
        elif severity == 'low':
            return 2
        else:
            return 3
    
    def _get_severity_display(self, severity: str) -> str:
        """
        الحصول على عرض مستوى الخطورة
        
        Args:
            severity: مستوى الخطورة
            
        Returns:
            str: العرض النصي
        """
        severity = severity.lower()
        if severity == 'high':
            return "مرتفعة"
        elif severity == 'medium':
            return "متوسطة"
        elif severity == 'low':
            return "منخفضة"
        else:
            return "معلومات"
    
    def get_issue(self, index: QModelIndex) -> Optional[Dict[str, Any]]:
        """
        الحصول على القضية للفهرس
        
        Args:
            index: فهرس العنصر
            
        Returns:
            Optional[Dict[str, Any]]: القضية
        """
        if not index.isValid():
            return None
        
        item = self.itemFromIndex(index.sibling(index.row(), 0))
        if not item:
            return None
        
        return item.data(Qt.UserRole + 1)

# ===== المكونات الرئيسية للواجهة =====

class ProjectExplorer(QWidget):
    """مستكشف المشروع"""
    
    # الإشارات
    file_selected = Signal(str, object)  # مسار الملف، كائن CodeFile
    
    def __init__(self, parent=None):
        """
        تهيئة مستكشف المشروع
        
        Args:
            parent: العنصر الأب
        """
        super().__init__(parent)
        self.project = None
        self.model = ProjectTreeModel()
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        # القائمة العلوية
        toolbar = QToolBar()
        
        # زر تحديث
        refresh_action = QAction(QIcon(get_icon_path("refresh")), "تحديث", self)
        refresh_action.triggered.connect(self.refresh)
        toolbar.addAction(refresh_action)
        
        # حقل البحث
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("بحث...")
        self.search_field.textChanged.connect(self._filter_changed)
        toolbar.addWidget(self.search_field)
        
        # شجرة المشروع
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.proxy_model)
        self.tree_view.setHeaderHidden(False)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setAnimated(True)
        self.tree_view.setSelectionMode(QTreeView.SingleSelection)
        self.tree_view.clicked.connect(self._item_clicked)
        self.tree_view.doubleClicked.connect(self._item_double_clicked)
        
        # إعداد عرض العمود
        header = self.tree_view.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        # ضبط التخطيط
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(toolbar)
        layout.addWidget(self.tree_view)
        
        self.setLayout(layout)
    
    def set_project(self, project: Project):
        """
        تعيين المشروع
        
        Args:
            project: المشروع
        """
        self.project = project
        self.model.set_project(project)
        
        # توسيع العنصر الجذري
        if project:
            root_index = self.model.index(0, 0)
            self.tree_view.expand(self.proxy_model.mapFromSource(root_index))
    
    def refresh(self):
        """تحديث عرض المشروع"""
        if self.project:
            self.model.set_project(self.project)
    
    def _filter_changed(self, text: str):
        """
        معالجة تغيير نص البحث
        
        Args:
            text: نص البحث
        """
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterRegExp(text)
    
    def _item_clicked(self, index: QModelIndex):
        """
        معالجة النقر على عنصر
        
        Args:
            index: فهرس العنصر
        """
        source_index = self.proxy_model.mapToSource(index)
        
        # التحقق إذا كان العنصر ملفاً
        if self.model.is_file(source_index):
            file_path = self.model.get_file_path(source_index)
            
            if self.project and file_path:
                # البحث عن ملف الشفرة المقابل
                for rel_path, code_file in self.project.files.items():
                    if code_file.file_path == file_path:
                        # إطلاق إشارة بتحديد الملف
                        self.file_selected.emit(file_path, code_file)
                        break
    
    def _item_double_clicked(self, index: QModelIndex):
        """
        معالجة النقر المزدوج على عنصر
        
        Args:
            index: فهرس العنصر
        """
        source_index = self.proxy_model.mapToSource(index)
        
        # إذا كان العنصر مجلداً، قم بفتحه/إغلاقه
        if self.model.is_directory(source_index):
            if self.tree_view.isExpanded(index):
                self.tree_view.collapse(index)
            else:
                self.tree_view.expand(index)
        elif self.model.is_file(source_index):
            # للملفات، نفس سلوك النقر الفردي
            self._item_clicked(index)


class EntityExplorer(QWidget):
    """مستكشف الكيانات البرمجية"""
    
    # الإشارات
    entity_selected = Signal(object)  # كائن CodeEntity
    
    def __init__(self, parent=None):
        """
        تهيئة مستكشف الكيانات
        
        Args:
            parent: العنصر الأب
        """
        super().__init__(parent)
        self.code_file = None
        self.model = EntityTreeModel()
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        # القائمة العلوية
        toolbar = QToolBar()
        
        # أزرار الفرز
        sort_name_action = QAction(QIcon(get_icon_path("sort-name")), "فرز حسب الاسم", self)
        sort_name_action.triggered.connect(lambda: self._sort_items(0))
        toolbar.addAction(sort_name_action)
        
        sort_type_action = QAction(QIcon(get_icon_path("sort-type")), "فرز حسب النوع", self)
        sort_type_action.triggered.connect(lambda: self._sort_items(1))
        toolbar.addAction(sort_type_action)
        
        sort_line_action = QAction(QIcon(get_icon_path("sort-line")), "فرز حسب السطر", self)
        sort_line_action.triggered.connect(lambda: self._sort_items(2))
        toolbar.addAction(sort_line_action)
        
        # حقل البحث
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("بحث...")
        self.search_field.textChanged.connect(self._filter_changed)
        toolbar.addWidget(self.search_field)
        
        # شجرة الكيانات
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.proxy_model)
        self.tree_view.setHeaderHidden(False)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setAnimated(True)
        self.tree_view.setSelectionMode(QTreeView.SingleSelection)
        self.tree_view.clicked.connect(self._item_clicked)
        
        # إعداد عرض العمود
        header = self.tree_view.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        # ضبط التخطيط
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(toolbar)
        layout.addWidget(self.tree_view)
        
        self.setLayout(layout)
    
    def set_code_file(self, code_file: CodeFile):
        """
        تعيين ملف الشفرة
        
        Args:
            code_file: ملف الشفرة
        """
        self.code_file = code_file
        self.model.set_code_file(code_file)
        
        # توسيع جميع العناصر الجذرية
        for i in range(self.model.rowCount()):
            index = self.model.index(i, 0)
            self.tree_view.expand(self.proxy_model.mapFromSource(index))
    
    def _sort_items(self, column: int):
        """
        فرز العناصر
        
        Args:
            column: رقم العمود
        """
        self.proxy_model.sort(column)
    
    def _filter_changed(self, text: str):
        """
        معالجة تغيير نص البحث
        
        Args:
            text: نص البحث
        """
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterRegExp(text)
    
    def _item_clicked(self, index: QModelIndex):
        """
        معالجة النقر على عنصر
        
        Args:
            index: فهرس العنصر
        """
        source_index = self.proxy_model.mapToSource(index)
        entity = self.model.get_entity(source_index)
        
        if entity:
            self.entity_selected.emit(entity)


class IssueViewer(QWidget):
    """عارض قضايا الشفرة"""
    
    # الإشارات
    issue_selected = Signal(Dict[str, Any])  # القضية المحددة
    
    def __init__(self, parent=None):
        """
        تهيئة عارض القضايا
        
        Args:
            parent: العنصر الأب
        """
        super().__init__(parent)
        self.project = None
        self.model = IssueTableModel()
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        # القائمة العلوية
        toolbar = QToolBar()
        
        # زر تحديث
        refresh_action = QAction(QIcon(get_icon_path("refresh")), "تحديث", self)
        refresh_action.triggered.connect(self.refresh)
        toolbar.addAction(refresh_action)
        
        # تصفية حسب الخطورة
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("الكل", "all")
        self.filter_combo.addItem("مرتفعة", "high")
        self.filter_combo.addItem("متوسطة", "medium")
        self.filter_combo.addItem("منخفضة", "low")
        self.filter_combo.addItem("معلومات", "info")
        self.filter_combo.currentIndexChanged.connect(self._filter_severity_changed)
        toolbar.addWidget(QLabel("الخطورة:"))
        toolbar.addWidget(self.filter_combo)
        
        # حقل البحث
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("بحث...")
        self.search_field.textChanged.connect(self._filter_text_changed)
        toolbar.addWidget(self.search_field)
        
        # جدول القضايا
        self.table_view = QTableView()
        self.table_view.setModel(self.proxy_model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setSortingEnabled(True)
        self.table_view.clicked.connect(self._item_clicked)
        
        # إعداد أحجام الأعمدة
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # الملف
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # السطر
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # الخطورة
        header.setSectionResizeMode(3, QHeaderView.Stretch)          # الرسالة
        header.setSectionResizeMode(4, QHeaderView.Stretch)          # التوصية
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # المصدر
        
        # نص عند عدم وجود قضايا
        self.empty_label = QLabel("لا توجد قضايا في المشروع")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setVisible(False)
        
        # ضبط التخطيط
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(toolbar)
        layout.addWidget(self.table_view)
        layout.addWidget(self.empty_label)
        
        self.setLayout(layout)
    
    def set_project(self, project: Project):
        """
        تعيين المشروع
        
        Args:
            project: المشروع
        """
        self.project = project
        self.model.set_project(project)
        
        # التحقق من وجود قضايا
        has_issues = project and len(self.model.issues) > 0
        self.table_view.setVisible(has_issues)
        self.empty_label.setVisible(not has_issues)
    
    def refresh(self):
        """تحديث عرض القضايا"""
        if self.project:
            self.model.update_issues()
            
            # التحقق من وجود قضايا
            has_issues = len(self.model.issues) > 0
            self.table_view.setVisible(has_issues)
            self.empty_label.setVisible(not has_issues)
    
    def _filter_severity_changed(self, index: int):
        """
        معالجة تغيير تصفية الخطورة
        
        Args:
            index: فهرس العنصر المحدد
        """
        severity = self.filter_combo.currentData()
        
        if severity == "all":
            # إزالة التصفية
            self.proxy_model.setFilterFixedString("")
        else:
            # تطبيق التصفية على عمود الخطورة
            self.proxy_model.setFilterKeyColumn(2)
            self.proxy_model.setFilterFixedString(severity)
    
    def _filter_text_changed(self, text: str):
        """
        معالجة تغيير نص البحث
        
        Args:
            text: نص البحث
        """
        self.proxy_model.setFilterKeyColumn(3)  # عمود الرسالة
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterFixedString(text)
    
    def _item_clicked(self, index: QModelIndex):
        """
        معالجة النقر على عنصر
        
        Args:
            index: فهرس العنصر
        """
        source_index = self.proxy_model.mapToSource(index)
        row = source_index.row()
        file_index = self.model.index(row, 0)
        issue = self.model.get_issue(file_index)
        
        if issue:
            self.issue_selected.emit(issue)


class AIAnalysisPanel(QWidget):
    """لوحة تحليل الذكاء الاصطناعي"""
    
    # الإشارات
    analysis_requested = Signal(str, object)  # نوع التحليل، نص التعليمات
    fix_requested = Signal(str, object)  # نص المحتوى، نص التعليمات
    
    def __init__(self, parent=None):
        """
        تهيئة لوحة التحليل
        
        Args:
            parent: العنصر الأب
        """
        super().__init__(parent)
        self.current_file = None
        self.current_content = None
        self.current_selection = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        # نوع التحليل
        self.analysis_type_label = QLabel("نوع التحليل:")
        self.analysis_type_combo = QComboBox()
        self.analysis_type_combo.addItems([
            "تحليل الجودة",
            "اكتشاف الأخطاء",
            "فحص الأمان",
            "تحسين الأداء",
            "تحسين التصميم",
            "تحسين الشفرة البرمجية",
            "التحليل الشامل"
        ])
        
        # مزود الذكاء الاصطناعي
        self.provider_label = QLabel("مزود الذكاء الاصطناعي:")
        self.provider_combo = QComboBox()
        self.provider_combo.addItems([
            "الافتراضي",
            "OpenAI GPT-4",
            "Claude Haiku",
            "Claude Sonnet",
            "Grok-3-Beta",
            "DeepSeek"
        ])
        
        # تعليمات التحليل
        self.instructions_label = QLabel("تعليمات إضافية:")
        self.instructions_text = QPlainTextEdit()
        self.instructions_text.setPlaceholderText("أدخل تعليمات إضافية للذكاء الاصطناعي (اختياري)")
        self.instructions_text.setMaximumHeight(100)
        
        # زر بدء التحليل
        self.analyze_button = QPushButton("بدء التحليل")
        self.analyze_button.clicked.connect(self._request_analysis)
        
        # نص إرشادي
        self.help_text = QLabel(
            "قم بتحديد نوع التحليل المطلوب والمزود المفضل. "
            "يمكنك إضافة تعليمات خاصة للمساعدة في توجيه التحليل."
        )
        self.help_text.setWordWrap(True)
        self.help_text.setStyleSheet("color: #666;")
        
        # قسم تحسين الشفرة
        self.code_fix_group = QGroupBox("تحسين الشفرة البرمجية")
        
        fix_layout = QVBoxLayout()
        
        # تعليمات التحسين
        self.fix_instructions_label = QLabel("تعليمات التحسين:")
        self.fix_instructions_text = QPlainTextEdit()
        self.fix_instructions_text.setPlaceholderText("وصف المشكلة أو التحسين المطلوب")
        self.fix_instructions_text.setMaximumHeight(100)
        
        # زر بدء التحسين
        self.fix_button = QPushButton("تحسين الشفرة")
        self.fix_button.clicked.connect(self._request_fix)
        
        fix_layout.addWidget(self.fix_instructions_label)
        fix_layout.addWidget(self.fix_instructions_text)
        fix_layout.addWidget(self.fix_button)
        
        self.code_fix_group.setLayout(fix_layout)
        
        # القسم العلوي للتخطيط الرئيسي
        top_layout = QGridLayout()
        top_layout.addWidget(self.analysis_type_label, 0, 0)
        top_layout.addWidget(self.analysis_type_combo, 0, 1)
        top_layout.addWidget(self.provider_label, 1, 0)
        top_layout.addWidget(self.provider_combo, 1, 1)
        
        # التخطيط الرئيسي
        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.instructions_label)
        main_layout.addWidget(self.instructions_text)
        main_layout.addWidget(self.analyze_button)
        main_layout.addWidget(self.help_text)
        main_layout.addWidget(self.code_fix_group)
        
        self.setLayout(main_layout)
    
    def set_current_file(self, file_path: str, file_content: str, code_file: CodeFile = None):
        """
        تعيين الملف الحالي
        
        Args:
            file_path: مسار الملف
            file_content: محتوى الملف
            code_file: كائن CodeFile (اختياري)
        """
        self.current_file = file_path
        self.current_content = file_content
        self.current_selection = None
        
        # تفعيل/تعطيل الأزرار بناءً على توفر الملف
        enabled = bool(file_path and file_content)
        self.analyze_button.setEnabled(enabled)
        self.fix_button.setEnabled(enabled)
        
        # تعيين نص إرشادي مناسب
        if not enabled:
            self.help_text.setText("افتح ملفاً أولاً لبدء التحليل")
        else:
            language = "غير معروفة"
            if code_file and code_file.language:
                language = code_file.language
            
            self.help_text.setText(
                f"الملف: {os.path.basename(file_path)}\n"
                f"اللغة: {language}\n"
                "قم بتحديد نوع التحليل المطلوب والمزود المفضل."
            )
    
    def set_current_selection(self, selection: str):
        """
        تعيين النص المحدد حالياً
        
        Args:
            selection: النص المحدد
        """
        self.current_selection = selection
    
    def _request_analysis(self):
        """طلب تحليل الذكاء الاصطناعي"""
        if not self.current_file or not self.current_content:
            QMessageBox.warning(self, "تنبيه", "افتح ملفاً أولاً لبدء التحليل")
            return
        
        # جمع البيانات
        analysis_type = self.analysis_type_combo.currentText()
        provider = self.provider_combo.currentText()
        instructions = self.instructions_text.toPlainText()
        
        # إنشاء التعليمات
        content_to_analyze = self.current_selection or self.current_content
        file_ext = os.path.splitext(self.current_file)[1]
        
        prompt = f"""
        قم بتحليل الشفرة البرمجية التالية وتحديد المشاكل والتحسينات المحتملة.
        
        نوع التحليل: {analysis_type}
        امتداد الملف: {file_ext}
        
        تعليمات إضافية: {instructions}
        
        الشفرة:
        ```
        {content_to_analyze}
        ```
        
        قدم تحليلاً مفصلاً يتضمن:
        1. ملخص عام للشفرة
        2. قائمة بالمشاكل المكتشفة (مع أرقام الأسطر)
        3. اقتراحات للتحسين
        4. أمثلة على كيفية تنفيذ التحسينات المقترحة
        
        ملاحظة: قدم الرد باللغة العربية.
        """
        
        # إطلاق إشارة التحليل
        self.analysis_requested.emit(analysis_type, prompt)
    
    def _request_fix(self):
        """طلب تحسين الشفرة"""
        if not self.current_file or not self.current_content:
            QMessageBox.warning(self, "تنبيه", "افتح ملفاً أولاً لبدء التحسين")
            return
        
        # جمع البيانات
        provider = self.provider_combo.currentText()
        instructions = self.fix_instructions_text.toPlainText()
        
        if not instructions:
            QMessageBox.warning(self, "تنبيه", "أدخل تعليمات للتحسين أولاً")
            return
        
        # إنشاء التعليمات
        content_to_fix = self.current_selection or self.current_content
        file_ext = os.path.splitext(self.current_file)[1]
        
        prompt = f"""
        قم بتحسين الشفرة البرمجية التالية حسب التعليمات المرفقة.
        
        تعليمات التحسين: {instructions}
        امتداد الملف: {file_ext}
        
        الشفرة الأصلية:
        ```
        {content_to_fix}
        ```
        
        قم بإنشاء نسخة محسنة من الشفرة مع مراعاة:
        1. الحفاظ على الوظائف الأساسية
        2. تنفيذ التحسينات المطلوبة
        3. اتباع أفضل الممارسات البرمجية
        
        قدم الشفرة المحسنة داخل علامات "```" مع شرح موجز للتغييرات.
        
        ملاحظة: قدم الرد باللغة العربية.
        """
        
        # إطلاق إشارة التحسين
        self.fix_requested.emit(content_to_fix, prompt)


class SettingsDialog(QDialog):
    """مربع حوار الإعدادات"""
    
    settings_updated = Signal(dict)  # إشارة لتحديث الإعدادات
    
    def __init__(self, parent=None, current_settings=None):
        """
        تهيئة مربع حوار الإعدادات
        
        Args:
            parent: العنصر الأب
            current_settings: الإعدادات الحالية
        """
        super().__init__(parent)
        self.current_settings = current_settings or {}
        
        self.setWindowTitle("إعدادات التطبيق")
        self.setMinimumWidth(450)
        
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        tab_widget = QTabWidget()
        
        # علامة تبويب الذكاء الاصطناعي
        ai_tab = QWidget()
        ai_layout = QVBoxLayout()
        
        # مجموعة إعدادات OpenAI
        openai_group = QGroupBox("إعدادات OpenAI")
        openai_layout = QFormLayout()
        
        self.openai_key_field = QLineEdit()
        self.openai_key_field.setEchoMode(QLineEdit.Password)
        self.openai_key_field.setPlaceholderText("أدخل مفتاح API الخاص بك")
        
        self.openai_model_combo = QComboBox()
        self.openai_model_combo.addItems([
            "gpt-4-0125-preview",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo"
        ])
        
        openai_layout.addRow("مفتاح API:", self.openai_key_field)
        openai_layout.addRow("النموذج:", self.openai_model_combo)
        openai_group.setLayout(openai_layout)
        
        # مجموعة إعدادات Anthropic (Claude)
        claude_group = QGroupBox("إعدادات Anthropic (Claude)")
        claude_layout = QFormLayout()
        
        self.claude_key_field = QLineEdit()
        self.claude_key_field.setEchoMode(QLineEdit.Password)
        self.claude_key_field.setPlaceholderText("أدخل مفتاح API الخاص بك")
        
        self.claude_model_combo = QComboBox()
        self.claude_model_combo.addItems([
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ])
        
        claude_layout.addRow("مفتاح API:", self.claude_key_field)
        claude_layout.addRow("النموذج:", self.claude_model_combo)
        claude_group.setLayout(claude_layout)
        
        # مجموعة إعدادات DeepSeek
        deepseek_group = QGroupBox("إعدادات DeepSeek")
        deepseek_layout = QFormLayout()
        
        self.deepseek_key_field = QLineEdit()
        self.deepseek_key_field.setEchoMode(QLineEdit.Password)
        self.deepseek_key_field.setPlaceholderText("أدخل مفتاح API الخاص بك")
        
        self.deepseek_model_combo = QComboBox()
        self.deepseek_model_combo.addItems([
            "deepseek-chat",
            "deepseek-coder"
        ])
        
        deepseek_layout.addRow("مفتاح API:", self.deepseek_key_field)
        deepseek_layout.addRow("النموذج:", self.deepseek_model_combo)
        deepseek_group.setLayout(deepseek_layout)
        
        # مجموعة إعدادات Grok
        grok_group = QGroupBox("إعدادات Grok")
        grok_layout = QFormLayout()
        
        self.grok_key_field = QLineEdit()
        self.grok_key_field.setEchoMode(QLineEdit.Password)
        self.grok_key_field.setPlaceholderText("أدخل مفتاح API الخاص بك")
        
        self.grok_model_combo = QComboBox()
        self.grok_model_combo.addItems([
            "grok-3-beta"
        ])
        
        grok_layout.addRow("مفتاح API:", self.grok_key_field)
        grok_layout.addRow("النموذج:", self.grok_model_combo)
        grok_group.setLayout(grok_layout)
        
        # المزود الافتراضي
        default_provider_layout = QFormLayout()
        self.default_provider_combo = QComboBox()
        self.default_provider_combo.addItems([
            "OpenAI",
            "Claude",
            "DeepSeek",
            "Grok"
        ])
        default_provider_layout.addRow("المزود الافتراضي:", self.default_provider_combo)
        
        # إضافة المجموعات إلى تخطيط علامة التبويب
        ai_layout.addLayout(default_provider_layout)
        ai_layout.addWidget(openai_group)
        ai_layout.addWidget(claude_group)
        ai_layout.addWidget(grok_group)
        ai_layout.addWidget(deepseek_group)
        ai_tab.setLayout(ai_layout)
        
        # علامة تبويب الواجهة
        ui_tab = QWidget()
        ui_layout = QVBoxLayout()
        
        # إعدادات اللغة
        language_group = QGroupBox("اللغة")
        language_layout = QFormLayout()
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(["العربية", "English"])
        
        language_layout.addRow("لغة الواجهة:", self.language_combo)
        language_group.setLayout(language_layout)
        
        # إعدادات السمة
        theme_group = QGroupBox("السمة")
        theme_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["فاتح", "داكن", "النظام"])
        
        theme_layout.addRow("سمة التطبيق:", self.theme_combo)
        theme_group.setLayout(theme_layout)
        
        # إعدادات المحرر
        editor_group = QGroupBox("المحرر")
        editor_layout = QFormLayout()
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(10)
        
        self.tab_width_spin = QSpinBox()
        self.tab_width_spin.setRange(2, 8)
        self.tab_width_spin.setValue(4)
        
        self.wrap_checkbox = QCheckBox("تفعيل")
        
        editor_layout.addRow("حجم الخط:", self.font_size_spin)
        editor_layout.addRow("عرض Tab:", self.tab_width_spin)
        editor_layout.addRow("لف الأسطر:", self.wrap_checkbox)
        editor_group.setLayout(editor_layout)
        
        # إضافة المجموعات إلى تخطيط علامة التبويب
        ui_layout.addWidget(language_group)
        ui_layout.addWidget(theme_group)
        ui_layout.addWidget(editor_group)
        ui_tab.setLayout(ui_layout)
        
        # إضافة علامات التبويب
        tab_widget.addTab(ai_tab, "الذكاء الاصطناعي")
        tab_widget.addTab(ui_tab, "الواجهة")
        
        # أزرار مربع الحوار
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # التخطيط الرئيسي
        main_layout = QVBoxLayout()
        main_layout.addWidget(tab_widget)
        main_layout.addWidget(button_box)
        
        self.setLayout(main_layout)
    
    def _load_settings(self):
        """تحميل الإعدادات الحالية"""
        # إعدادات الذكاء الاصطناعي
        ai_settings = self.current_settings.get("ai", {})
        
        # OpenAI
        openai = ai_settings.get("openai", {})
        self.openai_key_field.setText(openai.get("api_key", ""))
        
        openai_model = openai.get("model", "gpt-4-turbo")
        index = self.openai_model_combo.findText(openai_model)
        if index >= 0:
            self.openai_model_combo.setCurrentIndex(index)
        
        # Claude
        claude = ai_settings.get("claude", {})
        self.claude_key_field.setText(claude.get("api_key", ""))
        
        claude_model = claude.get("model", "claude-3-haiku-20240307")
        index = self.claude_model_combo.findText(claude_model)
        if index >= 0:
            self.claude_model_combo.setCurrentIndex(index)
        
        # DeepSeek
        deepseek = ai_settings.get("deepseek", {})
        self.deepseek_key_field.setText(deepseek.get("api_key", ""))
        
        deepseek_model = deepseek.get("model", "deepseek-chat")
        index = self.deepseek_model_combo.findText(deepseek_model)
        if index >= 0:
            self.deepseek_model_combo.setCurrentIndex(index)
        
        # Grok
        grok = ai_settings.get("grok", {})
        self.grok_key_field.setText(grok.get("api_key", ""))
        
        grok_model = grok.get("model", "grok-3-beta")
        index = self.grok_model_combo.findText(grok_model)
        if index >= 0:
            self.grok_model_combo.setCurrentIndex(index)
        
        # المزود الافتراضي
        default_provider = ai_settings.get("default_provider", "OpenAI")
        index = self.default_provider_combo.findText(default_provider)
        if index >= 0:
            self.default_provider_combo.setCurrentIndex(index)
        
        # إعدادات الواجهة
        ui_settings = self.current_settings.get("ui", {})
        
        # اللغة
        language = ui_settings.get("language", "العربية")
        index = self.language_combo.findText(language)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
        
        # السمة
        theme = ui_settings.get("theme", "فاتح")
        index = self.theme_combo.findText(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        
        # المحرر
        editor = ui_settings.get("editor", {})
        self.font_size_spin.setValue(editor.get("font_size", 10))
        self.tab_width_spin.setValue(editor.get("tab_width", 4))
        self.wrap_checkbox.setChecked(editor.get("wrap_lines", False))
    
    def get_settings(self):
        """
        الحصول على الإعدادات من الحقول
        
        Returns:
            dict: الإعدادات
        """
        settings = {
            "ai": {
                "default_provider": self.default_provider_combo.currentText(),
                "openai": {
                    "api_key": self.openai_key_field.text(),
                    "model": self.openai_model_combo.currentText()
                },
                "claude": {
                    "api_key": self.claude_key_field.text(),
                    "model": self.claude_model_combo.currentText()
                },
                "deepseek": {
                    "api_key": self.deepseek_key_field.text(),
                    "model": self.deepseek_model_combo.currentText()
                },
                "grok": {
                    "api_key": self.grok_key_field.text(),
                    "model": self.grok_model_combo.currentText()
                }
            },
            "ui": {
                "language": self.language_combo.currentText(),
                "theme": self.theme_combo.currentText(),
                "editor": {
                    "font_size": self.font_size_spin.value(),
                    "tab_width": self.tab_width_spin.value(),
                    "wrap_lines": self.wrap_checkbox.isChecked()
                }
            }
        }
        
        return settings
    
    def accept(self):
        """قبول التغييرات وإغلاق مربع الحوار"""
        settings = self.get_settings()
        self.settings_updated.emit(settings)
        super().accept()


class AIResponseViewer(QWidget):
    """عارض استجابة الذكاء الاصطناعي"""
    
    code_snippet_selected = Signal(str)  # إشارة لتحديد مقطع شفرة
    
    def __init__(self, parent=None):
        """
        تهيئة عارض الاستجابة
        
        Args:
            parent: العنصر الأب
        """
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        # منطقة النص
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        
        # شريط الأدوات
        toolbar = QToolBar()
        
        clear_action = QAction(QIcon(get_icon_path("clear")), "مسح", self)
        clear_action.triggered.connect(self.clear_content)
        toolbar.addAction(clear_action)
        
        copy_action = QAction(QIcon(get_icon_path("copy")), "نسخ", self)
        copy_action.triggered.connect(self._copy_content)
        toolbar.addAction(copy_action)
        
        save_action = QAction(QIcon(get_icon_path("save")), "حفظ", self)
        save_action.triggered.connect(self._save_content)
        toolbar.addAction(save_action)
        
        # التخطيط
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(toolbar)
        layout.addWidget(self.text_edit)
        
        self.setLayout(layout)
    
    def set_content(self, text: str):
        """
        تعيين محتوى النص
        
        Args:
            text: النص
        """
        # تحويل النص إلى HTML:
        # 1. التعامل مع مقاطع الشفرة
        text = self._format_code_blocks(text)
        
        # 2. تحويل العناوين
        text = self._format_headings(text)
        
        # 3. تحويل القوائم
        text = self._format_lists(text)
        
        # 4. تحويل الروابط
        text = self._format_links(text)
        
        # 5. تحويل النص العريض والمائل
        text = self._format_emphasis(text)
        
        # تعيين HTML في عنصر التحرير
        self.text_edit.setHtml(text)
    
    def _format_code_blocks(self, text: str) -> str:
        """
        تنسيق مقاطع الشفرة
        
        Args:
            text: النص الأصلي
            
        Returns:
            str: النص المنسق
        """
        import re
        
        # تحديد مقاطع الشفرة بين علامات اقتباس ثلاثية
        pattern = r"```(?:(\w+)\n)?(.*?)```"
        
        def replace_code_block(match):
            language = match.group(1) or ""
            code = match.group(2)
            
            # إنشاء HTML لمقطع الشفرة
            result = f'<div class="code-block" style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; font-family: monospace; white-space: pre; margin: 10px 0; direction: ltr; text-align: left;">'
            
            if language:
                result += f'<div style="color: #666; margin-bottom: 5px; font-weight: bold; font-style: italic;">{language}</div>'
            
            # تنظيف الشفرة
            code = code.strip()
            
            # الهروب من HTML
            code = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            
            # إضافة نص الشفرة
            result += f"{code}"
            
            # إضافة زر نسخ
            result += (
                f'<div style="margin-top: 5px;">'
                f'<a href="#" onclick="copyCode(this)" style="color: #0066cc; text-decoration: none; cursor: pointer;" '
                f'data-code="{code.replace(chr(34), "&quot;")}">'
                f'نسخ الشفرة</a>'
                f'</div>'
            )
            
            result += '</div>'
            return result
        
        # تطبيق التنسيق على جميع مقاطع الشفرة
        return re.sub(pattern, replace_code_block, text, flags=re.DOTALL)
    
    def _format_headings(self, text: str) -> str:
        """
        تنسيق العناوين
        
        Args:
            text: النص الأصلي
            
        Returns:
            str: النص المنسق
        """
        import re
        
        # العناوين من المستوى 1 إلى 6
        for i in range(6, 0, -1):
            pattern = r"^" + ("#" * i) + r"\s+(.*?)$"
            replacement = r"<h\1 style='color: #333; margin: 15px 0 10px 0;'>\2</h\1>"
            text = re.sub(pattern, lambda m: f"<h{i} style='color: #333; margin: 15px 0 10px 0;'>{m.group(1)}</h{i}>", text, flags=re.MULTILINE)
        
        return text
    
    def _format_lists(self, text: str) -> str:
        """
        تنسيق القوائم
        
        Args:
            text: النص الأصلي
            
        Returns:
            str: النص المنسق
        """
        import re
        
        # القوائم المرقمة
        numbered_list_pattern = r"^(\d+)\.\s+(.*?)$"
        
        # تحديد القوائم المرقمة المتتالية
        chunks = []
        current_chunk = []
        in_numbered_list = False
        
        for line in text.split("\n"):
            if re.match(numbered_list_pattern, line):
                if not in_numbered_list:
                    # بداية قائمة جديدة
                    if current_chunk:
                        chunks.append("\n".join(current_chunk))
                        current_chunk = []
                    in_numbered_list = True
                    current_chunk.append("<ol>")
                
                # استخراج نص العنصر
                item_text = re.sub(numbered_list_pattern, r"\2", line)
                current_chunk.append(f"<li>{item_text}</li>")
            else:
                if in_numbered_list:
                    # نهاية القائمة
                    current_chunk.append("</ol>")
                    in_numbered_list = False
                
                current_chunk.append(line)
        
        # التأكد من إغلاق آخر قائمة
        if in_numbered_list:
            current_chunk.append("</ol>")
        
        if current_chunk:
            chunks.append("\n".join(current_chunk))
        
        text = "\n".join(chunks)
        
        # القوائم النقطية
        bullet_list_pattern = r"^[-*]\s+(.*?)$"
        
        # إعادة تحديد القطع
        chunks = []
        current_chunk = []
        in_bullet_list = False
        
        for line in text.split("\n"):
            if re.match(bullet_list_pattern, line):
                if not in_bullet_list:
                    # بداية قائمة جديدة
                    if current_chunk:
                        chunks.append("\n".join(current_chunk))
                        current_chunk = []
                    in_bullet_list = True
                    current_chunk.append("<ul>")
                
                # استخراج نص العنصر
                item_text = re.sub(bullet_list_pattern, r"\1", line)
                current_chunk.append(f"<li>{item_text}</li>")
            else:
                if in_bullet_list:
                    # نهاية القائمة
                    current_chunk.append("</ul>")
                    in_bullet_list = False
                
                current_chunk.append(line)
        
        # التأكد من إغلاق آخر قائمة
        if in_bullet_list:
            current_chunk.append("</ul>")
        
        if current_chunk:
            chunks.append("\n".join(current_chunk))
        
        return "\n".join(chunks)
    
    def _format_links(self, text: str) -> str:
        """
        تنسيق الروابط
        
        Args:
            text: النص الأصلي
            
        Returns:
            str: النص المنسق
        """
        import re
        
        # الروابط بصيغة [النص](الرابط)
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        text = re.sub(link_pattern, r'<a href="\2" style="color: #0066cc; text-decoration: none;">\1</a>', text)
        
        # الروابط المباشرة
        url_pattern = r"(https?://[^\s]+)"
        text = re.sub(url_pattern, r'<a href="\1" style="color: #0066cc; text-decoration: none;">\1</a>', text)
        
        return text
    
    def _format_emphasis(self, text: str) -> str:
        """
        تنسيق النص العريض والمائل
        
        Args:
            text: النص الأصلي
            
        Returns:
            str: النص المنسق
        """
        import re
        
        # النص العريض
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", text)
        
        # النص المائل
        text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
        text = re.sub(r"_([^_]+)_", r"<em>\1</em>", text)
        
        return text
    
    def clear_content(self):
        """مسح المحتوى"""
        self.text_edit.clear()
    
    def _copy_content(self):
        """نسخ المحتوى إلى الحافظة"""
        self.text_edit.selectAll()
        self.text_edit.copy()
        self.text_edit.moveCursor(QTextCursor.Start)
    
    def _save_content(self):
        """حفظ المحتوى إلى ملف"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "حفظ المحتوى", "", "ملفات HTML (*.html);;ملفات نص (*.txt)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                if file_path.endswith('.html'):
                    f.write(self.text_edit.toHtml())
                else:
                    f.write(self.text_edit.toPlainText())
            
            QMessageBox.information(self, "تم الحفظ", f"تم حفظ المحتوى إلى:\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"حدث خطأ أثناء الحفظ:\n{str(e)}")


class ChatPanel(QWidget):
    """لوحة المحادثة مع الذكاء الاصطناعي"""
    
    # الإشارات
    message_sent = Signal(str)  # الرسالة المرسلة
    
    def __init__(self, parent=None):
        """
        تهيئة لوحة المحادثة
        
        Args:
            parent: العنصر الأب
        """
        super().__init__(parent)
        self.chat_history = []
        self.current_file = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        # مزود الذكاء الاصطناعي
        provider_layout = QHBoxLayout()
        self.provider_label = QLabel("المزود:")
        self.provider_combo = QComboBox()
        self.provider_combo.addItems([
            "الافتراضي",
            "OpenAI GPT-4",
            "Claude Haiku",
            "Claude Sonnet",
            "Grok-3-beta",
            "DeepSeek"
        ])
        provider_layout.addWidget(self.provider_label)
        provider_layout.addWidget(self.provider_combo)
        provider_layout.addStretch()
        
        # عرض المحادثة
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        
        # حقل إدخال الرسالة
        self.message_input = QPlainTextEdit()
        self.message_input.setPlaceholderText("اكتب رسالتك هنا...")
        self.message_input.setMaximumHeight(100)
        
        # زر الإرسال
        self.send_button = QPushButton("إرسال")
        self.send_button.clicked.connect(self._send_message)
        
        # أزرار إضافية
        button_layout = QHBoxLayout()
        
        # زر مشاركة الملف الحالي
        self.share_file_button = QPushButton("مشاركة الملف الحالي")
        self.share_file_button.clicked.connect(self._share_current_file)
        self.share_file_button.setEnabled(False)
        
        # زر مسح المحادثة
        self.clear_button = QPushButton("مسح المحادثة")
        self.clear_button.clicked.connect(self._clear_chat)
        
        button_layout.addWidget(self.share_file_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        button_layout.addWidget(self.send_button)
        
        # التخطيط الرئيسي
        main_layout = QVBoxLayout()
        main_layout.addLayout(provider_layout)
        main_layout.addWidget(self.chat_display)
        main_layout.addWidget(self.message_input)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # اتصال الإدخال بزر الإرسال
        self.message_input.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """
        مرشح الأحداث للتعامل مع ضغط Enter في حقل الإدخال
        
        Args:
            obj: الكائن الذي حدث فيه الحدث
            event: الحدث
            
        Returns:
            bool: تم معالجة الحدث أم لا
        """
        if obj is self.message_input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return and event.modifiers() & Qt.ControlModifier:
                self._send_message()
                return True
        return super().eventFilter(obj, event)
    
    def set_current_file(self, file_path: str, file_content: str):
        """
        تعيين الملف الحالي
        
        Args:
            file_path: مسار الملف
            file_content: محتوى الملف
        """
        self.current_file = {
            "path": file_path,
            "content": file_content,
            "name": os.path.basename(file_path) if file_path else ""
        }
        
        self.share_file_button.setEnabled(bool(file_path))
    
    def add_message(self, sender: str, message: str, is_code: bool = False):
        """
        إضافة رسالة إلى المحادثة
        
        Args:
            sender: المرسل (user أو ai)
            message: نص الرسالة
            is_code: هل الرسالة عبارة عن شفرة برمجية
        """
        # إضافة إلى السجل
        self.chat_history.append({
            "role": "user" if sender == "أنت" else "assistant",
            "content": message
        })
        
        # تنسيق الرسالة
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # إنشاء تنسيق للمرسل
        sender_format = QTextCharFormat()
        sender_format.setFontWeight(QFont.Bold)
        if sender == "أنت":
            sender_format.setForeground(QColor("#0066cc"))
        else:
            sender_format.setForeground(QColor("#cc5500"))
        
        # كتابة اسم المرسل
        cursor.insertText(f"{sender}: ", sender_format)
        
        # كتابة الرسالة بتنسيق عادي
        message_format = QTextCharFormat()
        if is_code:
            # تنسيق خاص للشفرة البرمجية
            message_format.setFontFamily("Courier New")
            message_format.setBackground(QColor("#f0f0f0"))
        
        # معالجة أكواد الماركداون للشفرة البرمجية
        if "```" in message:
            parts = message.split("```")
            
            # النص قبل أول كتلة شفرة
            if parts[0]:
                cursor.insertText(parts[0], QTextCharFormat())
            
            # كتابة كتل الشفرة والنص بينها
            for i in range(1, len(parts)):
                if i % 2 == 1:  # كتلة شفرة
                    # تنسيق كتلة الشفرة
                    code_format = QTextCharFormat()
                    code_format.setFontFamily("Courier New")
                    code_format.setBackground(QColor("#f0f0f0"))
                    
                    cursor.insertBlock()
                    cursor.insertText(parts[i], code_format)
                    cursor.insertBlock()
                else:  # نص عادي
                    cursor.insertText(parts[i], QTextCharFormat())
        else:
            # رسالة عادية بدون كتل شفرة
            cursor.insertText(message, message_format)
        
        # إضافة سطر جديد
        cursor.insertBlock()
        cursor.insertBlock()
        
        # تمرير العرض إلى الأسفل
        self.chat_display.setTextCursor(cursor)
        self.chat_display.ensureCursorVisible()
    
    def _send_message(self):
        """إرسال رسالة"""
        message = self.message_input.toPlainText().strip()
        
        if not message:
            return
        
        # عرض الرسالة في المحادثة
        self.add_message("أنت", message)
        
        # مسح حقل الإدخال
        self.message_input.clear()
        
        # إطلاق إشارة بإرسال الرسالة
        self.message_sent.emit(message)
    
    def _share_current_file(self):
        """مشاركة الملف الحالي في المحادثة"""
        if not self.current_file:
            return
        
        file_name = self.current_file["name"]
        file_content = self.current_file["content"]
        
        if not file_content:
            return
        
        # تحديد طول الملف وتقصيره إذا لزم الأمر
        max_length = 4000
        if len(file_content) > max_length:
            truncated = True
            file_content = file_content[:max_length] + "\n...(تم اقتصاص الملف)..."
        else:
            truncated = False
        
        # إنشاء رسالة
        message = f"محتوى الملف '{file_name}':\n```\n{file_content}\n```"
        
        if truncated:
            message += "\n(تم اقتصاص الملف لأنه طويل جداً)"
        
        # إضافة رسالة لطلب التحليل
        message += "\n\nالرجاء تحليل هذا الملف وتقديم الملاحظات والاقتراحات للتحسين."
        
        # عرض الرسالة في المحادثة
        self.add_message("أنت", message, is_code=True)
        
        # إطلاق إشارة بإرسال الرسالة
        self.message_sent.emit(message)
    
    def _clear_chat(self):
        """مسح المحادثة"""
        self.chat_display.clear()
        self.chat_history = []


class ResultPanel(QWidget):
    """لوحة عرض نتائج التحليل"""
    
    def __init__(self, parent=None):
        """
        تهيئة لوحة النتائج
        
        Args:
            parent: العنصر الأب
        """
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """إعداد واجهة المستخدم"""
        # عرض النتائج
        self.result_display = QTextEdit()
        self.result_display.setReadOnly(True)
        
        # زر تصدير النتائج
        self.export_button = QPushButton("تصدير النتائج")
        self.export_button.clicked.connect(self._export_results)
        
        # زر مسح النتائج
        self.clear_button = QPushButton("مسح النتائج")
        self.clear_button.clicked.connect(self._clear_results)
        
        # تخطيط الأزرار
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.export_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        
        # التخطيط الرئيسي
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.result_display)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def set_results(self, results: str, is_code: bool = False):
        """
        تعيين نتائج التحليل
        
        Args:
            results: نص النتائج
            is_code: هل النتائج تحتوي على شفرة برمجية
        """
        self.result_display.clear()
        
        cursor = self.result_display.textCursor()
        
        # معالجة أكواد الماركداون للشفرة البرمجية
        if is_code and "```" in results:
            parts = results.split("```")
            
            # النص قبل أول كتلة شفرة
            if parts[0]:
                cursor.insertText(parts[0], QTextCharFormat())
            
            # كتابة كتل الشفرة والنص بينها
            for i in range(1, len(parts)):
                if i % 2 == 1:  # كتلة شفرة
                    # تنسيق كتلة الشفرة
                    code_format = QTextCharFormat()
                    code_format.setFontFamily("Courier New")
                    code_format.setBackground(QColor("#f0f0f0"))
                    
                    cursor.insertBlock()
                    cursor.insertText(parts[i], code_format)
                    cursor.insertBlock()
                else:  # نص عادي
                    cursor.insertText(parts[i], QTextCharFormat())
        else:
            # نص عادي
            cursor.insertText(results)
        
        # تمرير العرض إلى الأعلى
        cursor.movePosition(QTextCursor.Start)
        self.result_display.setTextCursor(cursor)
    
    def append_results(self, results: str, is_code: bool = False):
        """
        إضافة نتائج للعرض الحالي
        
        Args:
            results: نص النتائج
            is_code: هل النتائج تحتوي على شفرة برمجية
        """
        cursor = self.result_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # إضافة فاصل
        separator_format = QTextCharFormat()
        separator_format.setForeground(QColor("#888888"))
        
        cursor.insertBlock()
        cursor.insertBlock()
        cursor.insertText("-" * 40, separator_format)
        cursor.insertBlock()
        cursor.insertBlock()
        
        # إضافة النتائج الجديدة
        if is_code and "```" in results:
            parts = results.split("```")
            
            # النص قبل أول كتلة شفرة
            if parts[0]:
                cursor.insertText(parts[0], QTextCharFormat())
            
            # كتابة كتل الشفرة والنص بينها
            for i in range(1, len(parts)):
                if i % 2 == 1:  # كتلة شفرة
                    # تنسيق كتلة الشفرة
                    code_format = QTextCharFormat()
                    code_format.setFontFamily("Courier New")
                    code_format.setBackground(QColor("#f0f0f0"))
                    
                    cursor.insertBlock()
                    cursor.insertText(parts[i], code_format)
                    cursor.insertBlock()
                else:  # نص عادي
                    cursor.insertText(parts[i], QTextCharFormat())
        else:
            # نص عادي
            cursor.insertText(results)
    
    def _export_results(self):
        """تصدير النتائج إلى ملف"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "تصدير النتائج", "", "ملفات نصية (*.txt);;جميع الملفات (*)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.result_display.toPlainText())
            
            QMessageBox.information(self, "تم التصدير", f"تم تصدير النتائج إلى:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء تصدير النتائج:\n{str(e)}")
    
    def _clear_results(self):
        """مسح النتائج"""
        self.result_display.clear()
