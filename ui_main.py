#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
النافذة الرئيسية والهيكل العام للواجهة
"""
import os
import json
import logging
import webbrowser
from typing import Dict, List, Any, Tuple, Optional, Union
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, QSize, QSettings, QTimer, Signal, Slot, QDir, QPoint, QEvent
from PySide6.QtGui import QFont, QIcon, QAction, QKeySequence, QCloseEvent, QPixmap, QColor
from PySide6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                              QToolBar, QStatusBar, QMenuBar, QMenu, QDockWidget,
                              QTabWidget, QMessageBox, QFileDialog, QSplitter, QFrame,
                              QProgressBar, QLabel, QComboBox, QTreeWidgetItem, QTreeWidget, QPushButton)

from analyzer import AnalysisManager, ModificationsManager
# الاستيرادات الصحيحة للفئات
from api_clients import ModelClientFactory
from chat import ChatManager
from project_model import ProjectModel
from api_clients import APIConfig, get_api_client
from chat import ChatComponent

from ui_components import (ProjectTreeWidget, IssuesTableWidget, AnalysisResultsWidget,
                          ChatWidget, SecurityIssuesWidget, StatusBar, AnalysisProgressBar,
                          CodeEditor)
from ui_dialogs import (APISettingsDialog, PendingModificationsDialog, IssueDetailsDialog,
                       ImportExportDialog, GeneralSettingsDialog, SecurityAnalysisDialog,
                       ConfirmationDialog, ProjectSelectionDialog, RevertModificationDialog,
                       ProgressDialog, AboutDialog, FeatureDevelopmentDialog, 
                       ApplyFeatureDialog, ErrorDialog, CodeComparisonDialog,
                       DependencyViewDialog, BatchAnalysisDialog, AnalysisHistoryDialog,
                       FileFilterDialog, LanguageSettingsDialog)

from utils import (read_file, write_file, calculate_file_hash, find_files, 
                  detect_project_type, save_json, load_json, create_html_report,
                  format_code_diff, truncate_text, relative_path)

logger = logging.getLogger("CodeAnalyzer.UI")

class MainWindow(QMainWindow):
    """النافذة الرئيسية للبرنامج"""
    
    def __init__(self, settings=None):
        super().__init__()
        
        # إعداد النافذة الرئيسية
        self.setWindowTitle("محلل الشيفرة البرمجية بالذكاء الاصطناعي")
        self.setMinimumSize(1200, 800)
        
        # تحميل الإعدادات
        if settings:
            self.settings = settings
        else:
            self.settings = QSettings("CodeAnalyzer", "Settings")
        
        self.load_settings()
        
        # إعداد API
        config_dir = os.path.join(os.path.expanduser("~"), ".code_analyzer")
        config_path = os.path.join(config_dir, "api_config.json")
        self.api_config = APIConfig.from_config_file(config_path)
        
        # إعداد المكونات الرئيسية
        self.project_model = None
        self.analysis_manager = AnalysisManager(self.api_config)
        self.modifications_manager = None
        self.chat_component = ChatComponent(self.api_config)
        
        # إعداد واجهة المستخدم
        self._setup_ui()
        self._setup_actions()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_statusbar()
        self._setup_connections()
        
        # تطبيق الإعدادات
        self._apply_settings()
        
        logger.info("تم إنشاء النافذة الرئيسية")
    
    def _setup_ui(self):
        """إعداد عناصر واجهة المستخدم"""
        # الويدجت المركزي
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # التخطيط الرئيسي
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # الفاصل الرئيسي (لوحة جانبية + المنطقة الرئيسية)
        main_splitter = QSplitter(Qt.Horizontal)
        
        # لوحة هيكل المشروع (الجانبية)
        self.project_tree = ProjectTreeWidget()
        
        # إنشاء ويدجت للشريط الجانبي
        sidebar_widget = QWidget()
        self.sidebar_layout = QVBoxLayout(sidebar_widget)
        self.sidebar_layout.setContentsMargins(5, 5, 5, 5)
        self.sidebar_layout.addWidget(self.project_tree)
        
        # منطقة العمل الرئيسية
        work_widget = QWidget()
        work_layout = QVBoxLayout(work_widget)
        work_layout.setContentsMargins(0, 0, 0, 0)
        
        # تبويبات العمل
        self.tabs = QTabWidget()
        
        # تبويب محرر الشيفرة
        self.code_editor = CodeEditor()
        self.tabs.addTab(self.code_editor, "محرر الشيفرة")
        
        # تبويب المحادثة
        self.chat_widget = ChatWidget()
        self.tabs.addTab(self.chat_widget, "المحادثة")
        
        # تبويب نتائج التحليل
        self.analysis_results = AnalysisResultsWidget()
        self.tabs.addTab(self.analysis_results, "نتائج التحليل")
        
        # تبويب الأمان والثغرات
        self.security_widget = SecurityIssuesWidget()
        self.tabs.addTab(self.security_widget, "الأمان والثغرات")
        
        # إضافة التبويبات إلى منطقة العمل
        work_layout.addWidget(self.tabs)
        
        # شريط التقدم
        self.progress_bar = AnalysisProgressBar()
        work_layout.addWidget(self.progress_bar)
        
        # إضافة العناصر إلى الفاصل الرئيسي
        main_splitter.addWidget(sidebar_widget)
        main_splitter.addWidget(work_widget)
        
        # تعيين النسب الافتراضية للفاصل
        main_splitter.setSizes([300, 900])
        
        # إضافة الفاصل إلى التخطيط الرئيسي
        main_layout.addWidget(main_splitter)
        
        # إنشاء شريط الحالة الافتراضي من Qt
        self.setStatusBar(QStatusBar())
        
        # إنشاء شريط الحالة المخصص كمكون منفصل
        self.status_bar = StatusBar()
        
        # إضافة شريط الحالة المخصص إلى التخطيط الرئيسي
        main_layout.addWidget(self.status_bar)

        # إعداد أزرار اختبار API
        self._setup_api_test_buttons()
    
    def _setup_actions(self):
        """إعداد الإجراءات"""
        # إجراءات القائمة "ملف"
        self.new_project_action = QAction(QIcon.fromTheme("document-new"), "مشروع جديد", self)
        self.new_project_action.setShortcut(QKeySequence.New)
        self.new_project_action.triggered.connect(self.new_project)
        
        self.open_project_action = QAction(QIcon.fromTheme("document-open"), "فتح مشروع", self)
        self.open_project_action.setShortcut(QKeySequence.Open)
        self.open_project_action.triggered.connect(self.open_project)
        
        self.save_file_action = QAction(QIcon.fromTheme("document-save"), "حفظ الملف", self)
        self.save_file_action.setShortcut(QKeySequence.Save)
        self.save_file_action.triggered.connect(self.save_current_file)
        
        self.import_action = QAction(QIcon.fromTheme("document-import"), "استيراد", self)
        self.import_action.triggered.connect(self.import_data)
        
        self.export_action = QAction(QIcon.fromTheme("document-export"), "تصدير", self)
        self.export_action.triggered.connect(self.export_data)
        
        self.exit_action = QAction(QIcon.fromTheme("application-exit"), "خروج", self)
        self.exit_action.setShortcut(QKeySequence.Quit)
        self.exit_action.triggered.connect(self.close)
        
        # إجراءات القائمة "تحرير"
        self.settings_action = QAction(QIcon.fromTheme("preferences-system"), "إعدادات", self)
        self.settings_action.triggered.connect(self.show_settings)
        
        self.api_settings_action = QAction(QIcon.fromTheme("preferences-system-network"), "إعدادات API", self)
        self.api_settings_action.triggered.connect(self.show_api_settings)
        
        # إجراءات القائمة "عرض"
        self.show_project_tree_action = QAction("لوحة هيكل المشروع", self)
        self.show_project_tree_action.setCheckable(True)
        self.show_project_tree_action.setChecked(True)
        self.show_project_tree_action.triggered.connect(self._toggle_project_tree)
        
        # إجراءات القائمة "تحليل"
        self.start_analysis_action = QAction(QIcon.fromTheme("system-run"), "بدء التحليل", self)
        self.start_analysis_action.setShortcut(QKeySequence("F5"))
        self.start_analysis_action.triggered.connect(self.start_analysis)
        
        self.stop_analysis_action = QAction(QIcon.fromTheme("process-stop"), "إيقاف التحليل", self)
        self.stop_analysis_action.setEnabled(False)
        self.stop_analysis_action.triggered.connect(self.stop_analysis)
        
        self.security_analysis_action = QAction(QIcon.fromTheme("security-high"), "تحليل الأمان", self)
        self.security_analysis_action.triggered.connect(self.show_security_analysis)
        
        self.batch_analysis_action = QAction(QIcon.fromTheme("document-multiple"), "تحليل دفعة ملفات", self)
        self.batch_analysis_action.triggered.connect(self.show_batch_analysis)
        
        self.analysis_history_action = QAction(QIcon.fromTheme("document-properties"), "سجل التحليل", self)
        self.analysis_history_action.triggered.connect(self.show_analysis_history)
        
        # إجراءات القائمة "أدوات"
        self.modifications_action = QAction(QIcon.fromTheme("document-properties"), "التعديلات المعلقة", self)
        self.modifications_action.triggered.connect(self.show_modifications)
        
        self.dependency_view_action = QAction(QIcon.fromTheme("network-wired"), "عرض الاعتمادات", self)
        self.dependency_view_action.triggered.connect(self.show_dependencies)
        
        self.file_filter_action = QAction(QIcon.fromTheme("view-filter"), "فلترة الملفات", self)
        self.file_filter_action.triggered.connect(self.show_file_filters)
        
        self.language_settings_action = QAction(QIcon.fromTheme("preferences-desktop-locale"), "إعدادات اللغات", self)
        self.language_settings_action.triggered.connect(self.show_language_settings)
        
        self.develop_feature_action = QAction(QIcon.fromTheme("document-new"), "تطوير ميزة جديدة", self)
        self.develop_feature_action.triggered.connect(self.show_feature_development)
        
        # إجراءات القائمة "مساعدة"
        self.about_action = QAction(QIcon.fromTheme("help-about"), "حول البرنامج", self)
        self.about_action.triggered.connect(self.show_about)
        
        self.help_action = QAction(QIcon.fromTheme("help-contents"), "مساعدة", self)
        self.help_action.setShortcut(QKeySequence.HelpContents)
        self.help_action.triggered.connect(self.show_help)
    
    def _setup_menus(self):
        """إعداد القوائم"""
        # القائمة الرئيسية
        self.menu_bar = QMenuBar()
        self.setMenuBar(self.menu_bar)
        
        # قائمة "ملف"
        file_menu = self.menu_bar.addMenu("ملف")
        file_menu.addAction(self.new_project_action)
        file_menu.addAction(self.open_project_action)
        file_menu.addAction(self.save_file_action)
        file_menu.addSeparator()
        file_menu.addAction(self.import_action)
        file_menu.addAction(self.export_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        
        # قائمة "تحرير"
        edit_menu = self.menu_bar.addMenu("تحرير")
        edit_menu.addAction(self.settings_action)
        edit_menu.addAction(self.api_settings_action)
        
        # قائمة "عرض"
        view_menu = self.menu_bar.addMenu("عرض")
        view_menu.addAction(self.show_project_tree_action)
        
        # قائمة "تحليل"
        analysis_menu = self.menu_bar.addMenu("تحليل")
        analysis_menu.addAction(self.start_analysis_action)
        analysis_menu.addAction(self.stop_analysis_action)
        analysis_menu.addSeparator()
        analysis_menu.addAction(self.security_analysis_action)
        analysis_menu.addAction(self.batch_analysis_action)
        analysis_menu.addAction(self.analysis_history_action)
        
        # قائمة "أدوات"
        tools_menu = self.menu_bar.addMenu("أدوات")
        tools_menu.addAction(self.modifications_action)
        tools_menu.addAction(self.dependency_view_action)
        tools_menu.addSeparator()
        tools_menu.addAction(self.file_filter_action)
        tools_menu.addAction(self.language_settings_action)
        tools_menu.addSeparator()
        tools_menu.addAction(self.develop_feature_action)
        
        # قائمة "مساعدة"
        help_menu = self.menu_bar.addMenu("مساعدة")
        help_menu.addAction(self.help_action)
        help_menu.addSeparator()
        help_menu.addAction(self.about_action)
    
    def _setup_toolbar(self):
        """إعداد شريط الأدوات"""
        # شريط الأدوات الرئيسي
        self.main_toolbar = QToolBar("شريط الأدوات الرئيسي")
        self.main_toolbar.setIconSize(QSize(32, 32))
        self.main_toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.addToolBar(self.main_toolbar)
        
        # إضافة الإجراءات إلى شريط الأدوات
        self.main_toolbar.addAction(self.new_project_action)
        self.main_toolbar.addAction(self.open_project_action)
        self.main_toolbar.addAction(self.save_file_action)
        self.main_toolbar.addSeparator()
        self.main_toolbar.addAction(self.start_analysis_action)
        self.main_toolbar.addAction(self.stop_analysis_action)
        self.main_toolbar.addSeparator()
        self.main_toolbar.addAction(self.security_analysis_action)
        
        # إضافة قائمة منسدلة لاختيار نموذج الذكاء الاصطناعي
        ai_model_label = QLabel("نموذج الذكاء الاصطناعي:")
        self.main_toolbar.addWidget(ai_model_label)
        
        self.ai_model_combo = QComboBox()
        self.ai_model_combo.addItems([
            "Claude 3.7 Sonnet",
            "Claude 3.5 Sonnet",
            "Grok-2-latest",
            "DeepSeek-V3",
            "GPT-4o",
            "GPT-3.5 Turbo"
        ])
        self.ai_model_combo.setCurrentText(self.api_config.get_model(self.api_config.preferred_provider))
        self.ai_model_combo.currentTextChanged.connect(self._on_ai_model_changed)
        
        self.main_toolbar.addWidget(self.ai_model_combo)
    
    def _setup_statusbar(self):
        """إعداد شريط الحالة"""
        # تم إنشاء شريط الحالة بالفعل في دالة _setup_ui
        pass
    
    def _setup_connections(self):
        """إعداد الاتصالات بين المكونات"""
        # اتصالات شجرة المشروع
        self.project_tree.file_selected.connect(self._on_file_selected)
        
        # اتصالات واجهة المحادثة
        self.chat_widget.send_message.connect(self._on_chat_message_sent)
        
        # اتصالات مدير التحليل
        self.analysis_manager.analysis_started.connect(self._on_analysis_started)
        self.analysis_manager.analysis_progress.connect(self._on_analysis_progress)
        self.analysis_manager.file_analyzed.connect(self._on_file_analyzed)
        self.analysis_manager.analysis_completed.connect(self._on_analysis_completed)
        self.analysis_manager.analysis_failed.connect(self._on_analysis_failed)
        
        # اتصالات واجهة نتائج التحليل
        self.analysis_results.issues_table.issue_selected.connect(self._on_issue_selected)
        self.analysis_results.issues_table.apply_fix.connect(self._on_apply_fix)
        self.analysis_results.issues_table.ignore_issue.connect(self._on_ignore_issue)
        
        # اتصالات واجهة الأمان
        self.security_widget.issue_selected.connect(self._on_security_issue_selected)
        self.security_widget.apply_fix.connect(self._on_apply_security_fix)
        
        # اتصالات مكون المحادثة
        self.chat_component.message_sent.connect(self._on_chat_message_sent_internal)
        self.chat_component.message_received.connect(self._on_chat_message_received)
        self.chat_component.error_occurred.connect(self._on_chat_error)
    
    def _apply_settings(self):
        """تطبيق الإعدادات المحفوظة"""
        # استعادة حجم وموضع النافذة
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        # استعادة حالة النافذة
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)
        
        # استعادة التبويب النشط
        active_tab = self.settings.value("activeTab", 0, int)
        self.tabs.setCurrentIndex(active_tab)
        
        # استعادة اتجاه الواجهة
        ui_direction = self.settings.value("ui_direction", "rtl")
        if ui_direction == "ltr":
            self.setLayoutDirection(Qt.LeftToRight)
        else:
            self.setLayoutDirection(Qt.RightToLeft)
        
        # استعادة السمة
        theme = self.settings.value("theme", "light")
        if theme == "dark":
            self._apply_dark_theme()
        else:
            self._apply_light_theme()
    
    def _apply_light_theme(self):
        """تطبيق السمة الفاتحة"""
        # إعادة تعيين ورقة النمط
        QApplication.instance().setStyleSheet("")
    
    def _apply_dark_theme(self):
        """تطبيق السمة الداكنة"""
        # تطبيق ورقة النمط الداكنة
        style_sheet = """
        QMainWindow, QDialog, QWidget {
            background-color: #2d2d2d;
            color: #e0e0e0;
        }
        
        QMenuBar, QMenu {
            background-color: #2d2d2d;
            color: #e0e0e0;
        }
        
        QMenuBar::item:selected, QMenu::item:selected {
            background-color: #3d3d3d;
        }
        
        QToolBar {
            background-color: #2d2d2d;
            border-bottom: 1px solid #3d3d3d;
        }
        
        QToolButton {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 1px solid transparent;
        }
        
        QToolButton:hover {
            background-color: #3d3d3d;
        }
        
        QStatusBar {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border-top: 1px solid #3d3d3d;
        }
        
        QTabWidget::pane {
            border: 1px solid #3d3d3d;
        }
        
        QTabBar::tab {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 1px solid #3d3d3d;
            padding: 6px 12px;
        }
        
        QTabBar::tab:selected {
            background-color: #3d3d3d;
        }
        
        QTreeView, QListView, QTableView {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 1px solid #3d3d3d;
        }
        
        QTreeView::item:selected, QListView::item:selected, QTableView::item:selected {
            background-color: #3d3d3d;
        }
        
        QHeaderView::section {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 1px solid #3d3d3d;
        }
        
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 1px solid #3d3d3d;
        }
        
        QPushButton {
            background-color: #3d3d3d;
            color: #e0e0e0;
            border: 1px solid #4d4d4d;
            padding: 5px 10px;
            border-radius: 3px;
        }
        
        QPushButton:hover {
            background-color: #4d4d4d;
        }
        
        QPushButton:pressed {
            background-color: #5d5d5d;
        }
        
        QComboBox {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 1px solid #3d3d3d;
            padding: 3px;
        }
        
        QComboBox::drop-down {
            border: 0px;
        }
        
        QComboBox QAbstractItemView {
            background-color: #2d2d2d;
            color: #e0e0e0;
            selection-background-color: #3d3d3d;
        }
        
        QProgressBar {
            border: 1px solid #3d3d3d;
            background-color: #2d2d2d;
            color: #e0e0e0;
            text-align: center;
        }
        
        QProgressBar::chunk {
            background-color: #4d4d4d;
        }
        
        QCheckBox, QRadioButton {
            color: #e0e0e0;
        }
        
        QGroupBox {
            border: 1px solid #3d3d3d;
            margin-top: 12px;
            padding-top: 12px;
            color: #e0e0e0;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            color: #e0e0e0;
            left: 12px;
            padding: 0 3px;
        }
        """
        
        QApplication.instance().setStyleSheet(style_sheet)
    
    def load_settings(self):
        """تحميل الإعدادات المحفوظة"""
        # تحميل الإعدادات العامة
        # يتم استخدامها في دالة _apply_settings
        pass
    
    def save_settings(self):
        """حفظ الإعدادات"""
        # حفظ حجم وموضع النافذة
        self.settings.setValue("geometry", self.saveGeometry())
        
        # حفظ حالة النافذة
        self.settings.setValue("windowState", self.saveState())
        
        # حفظ التبويب النشط
        self.settings.setValue("activeTab", self.tabs.currentIndex())
        
        # حفظ اتجاه الواجهة
        self.settings.setValue("ui_direction", "ltr" if self.layoutDirection() == Qt.LeftToRight else "rtl")
    
    def closeEvent(self, event: QCloseEvent):
        """
        معالجة حدث إغلاق النافذة
        """
        # إيقاف جميع المواضيع النشطة
        if hasattr(self, 'chat_widget') and self.chat_widget:
            self.chat_widget.stop_all_threads()
            
        # إيقاف أي مواضيع تحليل نشطة
        if hasattr(self, 'analysis_threads'):
            for thread in self.analysis_threads:
                if thread.isRunning():
                    thread.quit()
                    thread.wait(1000)
                    if thread.isRunning():
                        thread.terminate()
        
        # حفظ الإعدادات قبل الإغلاق
        self.save_settings()
        
        # السماح بإكمال الإغلاق
        event.accept()
    
    def has_unsaved_changes(self) -> bool:
        """التحقق من وجود تعديلات غير محفوظة"""
        # التحقق من محرر الشيفرة
        if self.code_editor.document().isModified():
            return True
        
        # التحقق من التعديلات المعلقة
        if self.modifications_manager and self.modifications_manager.get_history():
            return True
        
        return False
    
    # ---- طرق القائمة "ملف" ----
    
    def new_project(self):
        """إنشاء مشروع جديد"""
        # عرض نافذة اختيار المشروع
        dialog = ProjectSelectionDialog(self)
        if dialog.exec_():
            # الحصول على مسار المجلد ونوع المشروع
            folder_path = dialog.get_folder_path()
            project_type = dialog.get_project_type()
            
            # تحميل المشروع
            if folder_path:
                self._load_project(folder_path, project_type)
    
    def open_project(self, folder_path: str = None):
        """فتح مشروع موجود"""
        if not folder_path:
            # عرض نافذة اختيار المجلد
            folder_path = QFileDialog.getExistingDirectory(
                self,
                "اختيار مجلد المشروع"
            )
        
        if folder_path:
            # تحميل المشروع
            self._load_project(folder_path)
    
    def save_current_file(self):
        """حفظ الملف الحالي في المحرر"""
        if self.code_editor.file_path:
            # حفظ الملف
            if self.code_editor.save_file():
                # إزالة علامة التعديل
                self.code_editor.document().setModified(False)
                
                # عرض رسالة في شريط الحالة
                self.statusBar().showMessage(f"تم حفظ الملف: {self.code_editor.file_path}", 3000)
            else:
                QMessageBox.warning(
                    self,
                    "خطأ",
                    "تعذر حفظ الملف."
                )
        else:
            # فتح نافذة "حفظ باسم"
            self.save_file_as()
    
    def save_file_as(self):
        """حفظ الملف الحالي باسم جديد"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ الملف باسم",
            "",
            "جميع الملفات (*.*)"
        )
        
        if file_path:
            # حفظ الملف
            if self.code_editor.save_file(file_path):
                # تحديث مسار الملف
                self.code_editor.file_path = file_path
                
                # إزالة علامة التعديل
                self.code_editor.document().setModified(False)
                
                # عرض رسالة في شريط الحالة
                self.statusBar().showMessage(f"تم حفظ الملف: {file_path}", 3000)
            else:
                QMessageBox.warning(
                    self,
                    "خطأ",
                    "تعذر حفظ الملف."
                )
    
    def _load_project(self, folder_path: str, project_type: str = "auto"):
        """تحميل مشروع من مجلد"""
        try:
            # إنشاء نموذج المشروع
            self.project_model = ProjectModel(folder_path)
            
            # تعيين نوع المشروع إذا كان محددًا
            if project_type != "auto":
                self.project_model.project_type = project_type
            else:
                # استخدام وظيفة كشف النوع الجديدة من utils
                detected_type = detect_project_type(folder_path)
                self.project_model.project_type = detected_type
            
            # تحميل المشروع
            if not self.project_model.load_project():
                QMessageBox.warning(
                    self,
                    "خطأ",
                    "حدث خطأ أثناء تحميل المشروع."
                )
                return
            
            # إنشاء مدير التعديلات
            self.modifications_manager = ModificationsManager(folder_path)
            self.modifications_manager.setup()
            
            # تحديث عنوان النافذة
            project_name = os.path.basename(folder_path)
            self.setWindowTitle(f"محلل الشيفرة البرمجية - {project_name}")
            
            # تحديث شجرة المشروع
            self.project_tree.load_project(folder_path)
            
            # تعيين نموذج المشروع لمدير التحليل
            self.analysis_manager.set_project_model(self.project_model)
            
            # تحديث حالة الإجراءات
            self.start_analysis_action.setEnabled(True)
            self.security_analysis_action.setEnabled(True)
            self.batch_analysis_action.setEnabled(True)
            self.dependency_view_action.setEnabled(True)
            self.modifications_action.setEnabled(True)
            
            # تحديث مكون المحادثة
            self.chat_component = ChatComponent(self.api_config, folder_path)
            self._setup_chat_connections()
            
            # عرض رسالة نجاح
            self.statusBar().showMessage(f"تم تحميل المشروع: {folder_path}", 5000)
            
            logger.info(f"تم تحميل المشروع: {folder_path}")
        
        except Exception as e:
            # عرض رسالة خطأ
            QMessageBox.critical(
                self,
                "خطأ",
                f"حدث خطأ أثناء تحميل المشروع:\n{str(e)}"
            )
            
            logger.error(f"خطأ في تحميل المشروع: {str(e)}")
    
    def _setup_chat_connections(self):
        """إعداد اتصالات مكون المحادثة"""
        # إعادة ربط إشارات المحادثة
        self.chat_component.message_sent.connect(self._on_chat_message_sent_internal)
        self.chat_component.message_received.connect(self._on_chat_message_received)
        self.chat_component.error_occurred.connect(self._on_chat_error)
        
        # ربط واجهة المحادثة بمكون المحادثة
        self.chat_widget.send_message.connect(self._on_chat_message_sent)
        
        # تحميل جلسات المحادثة السابقة
        sessions = self.chat_component.load_sessions()
        if sessions:
            # تعيين الجلسة الحالية إلى أحدث جلسة
            self.chat_component.set_current_session(sessions[0].id)
            
            # عرض الرسائل السابقة في واجهة المحادثة
            self.chat_widget.clear_chat()
            for msg in self.chat_component.current_session.messages:
                if msg.role != "system":  # تخطي رسائل النظام
                    self.chat_widget.add_message(msg.role, msg.content)
    
    def import_data(self):
        """استيراد بيانات التحليل"""
        # عرض نافذة الاستيراد
        dialog = ImportExportDialog(self)
        dialog.import_data.connect(self._on_import_data)
        dialog.exec_()
    
    def _on_import_data(self, file_path: str):
        """معالجة استيراد البيانات"""
        try:
            # استخدام الدالة الجديدة من utils لتحميل JSON
            data = load_json(file_path)
            if data is None:
                QMessageBox.warning(
                    self,
                    "خطأ",
                    "فشل في قراءة ملف البيانات."
                )
                return
            
            # التحقق من صحة البيانات
            if "issues" not in data or "security_issues" not in data:
                QMessageBox.warning(
                    self,
                    "خطأ",
                    "ملف البيانات غير صالح."
                )
                return
            
            # عرض النتائج في واجهة نتائج التحليل
            self.analysis_results.set_results(data)
            
            # عرض الثغرات الأمنية في واجهة الأمان
            self.security_widget.set_security_issues(data.get("security_issues", []))
            
            # تحديث شريط الحالة
            self._update_status_bar(data)
            
            # الانتقال إلى تبويب نتائج التحليل
            self.tabs.setCurrentWidget(self.analysis_results)
            
            # عرض رسالة نجاح
            self.statusBar().showMessage(f"تم استيراد البيانات من: {file_path}", 5000)
            
            logger.info(f"تم استيراد البيانات من: {file_path}")
        
        except Exception as e:
            # عرض رسالة خطأ
            QMessageBox.critical(
                self,
                "خطأ",
                f"حدث خطأ أثناء استيراد البيانات:\n{str(e)}"
            )
            
            logger.error(f"خطأ في استيراد البيانات: {str(e)}")
    
    def export_data(self):
        """تصدير بيانات التحليل"""
        # عرض نافذة التصدير
        dialog = ImportExportDialog(self)
        dialog.export_data.connect(self._on_export_data)
        dialog.exec_()
    
    def _on_export_data(self, file_path: str, create_html: bool):
        """معالجة تصدير البيانات"""
        try:
            # التحقق من وجود نتائج تحليل
            if not hasattr(self.analysis_manager, "analysis_results") or not self.analysis_manager.analysis_results:
                QMessageBox.warning(
                    self,
                    "تنبيه",
                    "لا توجد نتائج تحليل للتصدير."
                )
                return
            
            # تصدير البيانات إلى ملف JSON باستخدام وظيفة save_json من utils
            if not save_json(self.analysis_manager.analysis_results, file_path):
                QMessageBox.warning(
                    self,
                    "خطأ",
                    "حدث خطأ أثناء تصدير البيانات."
                )
                return
            
            # إنشاء تقرير HTML إذا كان مطلوبًا باستخدام وظيفة create_html_report من utils
            if create_html:
                html_path = os.path.splitext(file_path)[0] + ".html"
                if not create_html_report(self.analysis_manager.analysis_results, html_path):
                    QMessageBox.warning(
                        self,
                        "تنبيه",
                        "تم تصدير البيانات بنجاح، ولكن حدث خطأ أثناء إنشاء تقرير HTML."
                    )
                else:
                    # عرض رسالة نجاح
                    QMessageBox.information(
                        self,
                        "تم التصدير",
                        f"تم تصدير البيانات بنجاح إلى:\n{file_path}\n\nوإنشاء تقرير HTML في:\n{html_path}"
                    )
            else:
                # عرض رسالة نجاح
                QMessageBox.information(
                    self,
                    "تم التصدير",
                    f"تم تصدير البيانات بنجاح إلى:\n{file_path}"
                )
            
            logger.info(f"تم تصدير البيانات إلى: {file_path}")
        
        except Exception as e:
            # عرض رسالة خطأ
            QMessageBox.critical(
                self,
                "خطأ",
                f"حدث خطأ أثناء تصدير البيانات:\n{str(e)}"
            )
            
            logger.error(f"خطأ في تصدير البيانات: {str(e)}")
    
    # ---- طرق القائمة "تحرير" ----
    
    def show_settings(self):
        """عرض نافذة الإعدادات العامة"""
        # تحميل الإعدادات الحالية
        current_settings = {
            "ui_direction": self.settings.value("ui_direction", "rtl"),
            "theme": self.settings.value("theme", "light"),
            "font_size": self.settings.value("font_size", 10, int),
            "use_ai": self.settings.value("use_ai", True, bool),
            "analyze_security": self.settings.value("analyze_security", True, bool),
            "analysis_threads": self.settings.value("analysis_threads", 4, int)
        }
        
        # عرض نافذة الإعدادات
        dialog = GeneralSettingsDialog(current_settings, self)
        if dialog.exec_():
            # حفظ الإعدادات المحدثة
            for key, value in dialog.settings.items():
                self.settings.setValue(key, value)
            
            # تطبيق الإعدادات الجديدة
            self._apply_settings()
            
            # عرض رسالة نجاح
            self.statusBar().showMessage("تم حفظ الإعدادات", 3000)
    
    def show_api_settings(self):
        """عرض نافذة إعدادات API"""
        # عرض نافذة إعدادات API
        dialog = APISettingsDialog(self.api_config, self)
        if dialog.exec_():
            # تحديث القائمة المنسدلة لنموذج الذكاء الاصطناعي
            model = self.api_config.get_model(self.api_config.preferred_provider)
            if model:
                self.ai_model_combo.setCurrentText(model)
            
            # عرض رسالة نجاح
            self.statusBar().showMessage("تم حفظ إعدادات API", 3000)
    
    # ---- طرق القائمة "عرض" ----
    
    def _toggle_project_tree(self):
        """إخفاء/إظهار لوحة هيكل المشروع"""
        if self.project_tree.isVisible():
            self.project_tree.hide()
        else:
            self.project_tree.show()
        
        # تحديث حالة الإجراء
        self.show_project_tree_action.setChecked(self.project_tree.isVisible())
    
    # ---- طرق القائمة "تحليل" ----
    
    def start_analysis(self):
        """بدء تحليل المشروع"""
        # التحقق من تحميل المشروع
        if not self.project_model:
            QMessageBox.warning(
                self,
                "تنبيه",
                "يرجى تحميل مشروع أولاً."
            )
            return
        
        # الحصول على خيارات التحليل من الإعدادات
        use_ai = self.settings.value("use_ai", True, bool)
        analyze_security = self.settings.value("analyze_security", True, bool)
        
        # بدء التحليل
        self.analysis_manager.start_analysis(use_ai, analyze_security)
    
    def stop_analysis(self):
        """إيقاف التحليل الجاري"""
        # إيقاف التحليل
        self.analysis_manager.stop_analysis()
        
        # تحديث الواجهة
        self.stop_analysis_action.setEnabled(False)
        self.start_analysis_action.setEnabled(True)
        
        # عرض رسالة
        self.statusBar().showMessage("تم إيقاف التحليل", 3000)
    
    def show_security_analysis(self):
        """عرض نافذة تحليل الأمان"""
        # التحقق من تحميل المشروع
        if not self.project_model:
            QMessageBox.warning(
                self,
                "تنبيه",
                "يرجى تحميل مشروع أولاً."
            )
            return
        
        # عرض نافذة تحليل الأمان
        dialog = SecurityAnalysisDialog(self)
        dialog.start_analysis.connect(self._on_start_security_analysis)
        dialog.exec_()
    
    def _on_start_security_analysis(self, full_project: bool):
        """معالجة بدء تحليل الأمان"""
        # بدء تحليل الأمان
        self.analysis_manager.start_analysis(True, True)
        
        # الانتقال إلى تبويب الأمان والثغرات
        self.tabs.setCurrentWidget(self.security_widget)
    
    def show_batch_analysis(self):
        """عرض نافذة تحليل دفعة ملفات"""
        # التحقق من تحميل المشروع
        if not self.project_model:
            QMessageBox.warning(
                self,
                "تنبيه",
                "يرجى تحميل مشروع أولاً."
            )
            return
        
        # عرض نافذة تحليل دفعة ملفات
        dialog = BatchAnalysisDialog(self.project_model, self)
        dialog.start_analysis.connect(self._on_start_batch_analysis)
        dialog.exec_()
    
    def _on_start_batch_analysis(self, file_paths: List[str], use_ai: bool, analyze_security: bool):
        """معالجة بدء تحليل دفعة ملفات"""
        # تحليل الملفات المحددة
        # (يجب إضافة دعم لتحليل ملفات محددة في مدير التحليل)
        
        # تحديث الواجهة
        self.tabs.setCurrentWidget(self.analysis_results)
    
    def show_analysis_history(self):
        """عرض نافذة سجل التحليل"""
        # تحديد مجلد سجل التحليل
        if not self.project_model:
            QMessageBox.warning(
                self,
                "تنبيه",
                "يرجى تحميل مشروع أولاً."
            )
            return
        
        history_dir = os.path.join(self.project_model.project_dir, "_analysis_history")
        
        # عرض نافذة سجل التحليل
        dialog = AnalysisHistoryDialog(history_dir, self)
        dialog.load_analysis.connect(self._on_load_analysis_history)
        dialog.exec_()
    
    def _on_load_analysis_history(self, file_path: str):
        """معالجة تحميل تحليل سابق"""
        self._on_import_data(file_path)
    
    # ---- طرق القائمة "أدوات" ----
    
    def show_modifications(self):
        """عرض نافذة التعديلات المعلقة"""
        # التحقق من وجود مدير التعديلات
        if not self.modifications_manager:
            QMessageBox.warning(
                self,
                "تنبيه",
                "يرجى تحميل مشروع أولاً."
            )
            return
        
        # الحصول على قائمة التعديلات
        modifications = self.modifications_manager.get_history()
        
        if not modifications:
            QMessageBox.information(
                self,
                "معلومات",
                "لا توجد تعديلات معلقة."
            )
            return
        
        # عرض نافذة التعديلات المعلقة
        dialog = PendingModificationsDialog(modifications, self)
        dialog.apply_selected.connect(self._on_apply_modifications)
        dialog.apply_all.connect(self._on_apply_all_modifications)
        dialog.exec_()
    
    def _on_apply_modifications(self, modifications: List[Dict[str, Any]]):
        """معالجة تطبيق التعديلات المحددة"""
        applied_count = 0
        
        for mod in modifications:
            # الحصول على مسار الملف والمحتوى المعدل
            file_path = mod.get("file_path", "")
            modified_content = mod.get("modified_content", "")
            
            # تطبيق التعديل
            if file_path and modified_content:
                # استخدام الوظيفة الجديدة write_file من utils
                if write_file(os.path.join(self.project_model.project_dir, file_path), modified_content):
                    applied_count += 1
                    
                    # إذا كان الملف مفتوحًا في المحرر، تحديثه
                    if self.code_editor.file_path == file_path:
                        self.code_editor.setPlainText(modified_content)
        
        # عرض رسالة نجاح
        QMessageBox.information(
            self,
            "تم التطبيق",
            f"تم تطبيق {applied_count} من {len(modifications)} تعديل بنجاح."
        )
    
    def _on_apply_all_modifications(self):
        """معالجة تطبيق جميع التعديلات"""
        # الحصول على جميع التعديلات
        all_modifications = self.modifications_manager.get_history()
        
        # تطبيق جميع التعديلات
        self._on_apply_modifications(all_modifications)
    
    def show_dependencies(self):
        """عرض نافذة الاعتمادات"""
        # التحقق من تحميل المشروع
        if not self.project_model:
            QMessageBox.warning(
                self,
                "تنبيه",
                "يرجى تحميل مشروع أولاً."
            )
            return
        
        # عرض نافذة الاعتمادات
        dialog = DependencyViewDialog(self.project_model, self)
        dialog.exec_()
    
    def show_file_filters(self):
        """عرض نافذة فلترة الملفات"""
        # الحصول على الفلاتر الحالية من الإعدادات
        current_extensions = self.settings.value("file_extensions", [], list)
        excluded_dirs = self.settings.value("excluded_dirs", [], list)
        
        # عرض نافذة فلترة الملفات
        dialog = FileFilterDialog(current_extensions, excluded_dirs, self)
        dialog.apply_filters.connect(self._on_apply_filters)
        dialog.exec_()
    
    def _on_apply_filters(self, extensions: List[str], excluded_dirs: List[str]):
        """معالجة تطبيق فلاتر الملفات"""
        # حفظ الفلاتر في الإعدادات
        self.settings.setValue("file_extensions", extensions)
        self.settings.setValue("excluded_dirs", excluded_dirs)
        
        # عرض رسالة نجاح
        self.statusBar().showMessage("تم حفظ فلاتر الملفات", 3000)
    
    def show_language_settings(self):
        """عرض نافذة إعدادات اللغات"""
        # الحصول على الإعدادات الحالية
        current_settings = {key: self.settings.value(key) for key in self.settings.allKeys() if key.startswith("python_") or key.startswith("php_") or key.startswith("js_") or key.startswith("dart_")}
        
        # عرض نافذة إعدادات اللغات
        dialog = LanguageSettingsDialog(current_settings, self)
        dialog.apply_settings.connect(self._on_apply_language_settings)
        dialog.exec_()
    
    def _on_apply_language_settings(self, settings: Dict[str, Any]):
        """معالجة تطبيق إعدادات اللغات"""
        # حفظ الإعدادات
        for key, value in settings.items():
            self.settings.setValue(key, value)
        
        # عرض رسالة نجاح
        self.statusBar().showMessage("تم حفظ إعدادات اللغات", 3000)
    
    def show_feature_development(self):
        """عرض نافذة تطوير ميزة جديدة"""
        # التحقق من تحميل المشروع
        if not self.project_model:
            QMessageBox.warning(
                self,
                "تنبيه",
                "يرجى تحميل مشروع أولاً."
            )
            return
        
        # عرض نافذة تطوير ميزة جديدة
        dialog = FeatureDevelopmentDialog(self)
        dialog.develop_feature.connect(self._on_develop_feature)
        dialog.exec_()
    
    def _on_develop_feature(self, description: str, context: str):
        """معالجة تطوير ميزة جديدة"""
        try:
            # عرض نافذة التقدم
            progress_dialog = ProgressDialog("تطوير الميزة", "جاري تطوير الميزة الجديدة...", self)
            progress_dialog.show()
            QApplication.processEvents()
            
            # تطوير الميزة
            feature_data = self.chat_component.develop_feature(description, context)
            
            # إغلاق نافذة التقدم
            progress_dialog.accept()
            
            # عرض نافذة تطبيق الميزة
            apply_dialog = ApplyFeatureDialog(feature_data, self)
            apply_dialog.apply_feature.connect(self._on_apply_feature)
            apply_dialog.exec_()
        
        except Exception as e:
            # عرض رسالة خطأ
            QMessageBox.critical(
                self,
                "خطأ",
                f"حدث خطأ أثناء تطوير الميزة:\n{str(e)}"
            )
            
            logger.error(f"خطأ في تطوير الميزة: {str(e)}")
    
    def _on_apply_feature(self, feature_data: Dict[str, Any]):
        """معالجة تطبيق ميزة مطورة"""
        try:
            # عرض نافذة التقدم
            progress_dialog = ProgressDialog("تطبيق الميزة", "جاري تطبيق الميزة الجديدة...", self)
            progress_dialog.show()
            QApplication.processEvents()
            
            # تطبيق الميزة
            applied_files = self.chat_component.apply_feature(feature_data)
            
            # إغلاق نافذة التقدم
            progress_dialog.accept()
            
            # عرض رسالة نجاح
            QMessageBox.information(
                self,
                "تم التطبيق",
                f"تم تطبيق الميزة الجديدة بنجاح.\nالملفات المعدلة: {len(applied_files)}"
            )
            
            # عرض الملفات المطبقة في عرض مقارنة إذا وجدت
            if applied_files and len(applied_files) <= 5:  # تحديد عدد معقول للعرض
                for file_path in applied_files:
                    # قراءة محتوى الملف
                    original_content = ""
                    # البحث عن النسخة الأصلية في التعديلات المعلقة
                    for mod in self.modifications_manager.get_history():
                        if mod.get("file_path") == file_path:
                            original_content = mod.get("original_content", "")
                            break
                    
                    # قراءة النسخة الحالية
                    current_content = read_file(file_path) or ""
                    
                    # عرض المقارنة إذا كان هناك محتوى أصلي
                    if original_content and current_content:
                        dialog = CodeComparisonDialog(file_path, original_content, current_content, self)
                        dialog.exec_()
        
        except Exception as e:
            # عرض رسالة خطأ
            QMessageBox.critical(
                self,
                "خطأ",
                f"حدث خطأ أثناء تطبيق الميزة:\n{str(e)}"
            )
            
            logger.error(f"خطأ في تطبيق الميزة: {str(e)}")
    
    # ---- طرق القائمة "مساعدة" ----
    
    def show_about(self):
        """عرض نافذة حول البرنامج"""
        dialog = AboutDialog(self)
        dialog.exec_()
    
    def show_help(self):
        """عرض مساعدة البرنامج"""
        # يمكن فتح دليل المستخدم أو صفحة ويب
        try:
            webbrowser.open("https://example.com/code-analyzer-help")
        except Exception as e:
            QMessageBox.warning(
                self,
                "تنبيه",
                f"تعذر فتح صفحة المساعدة:\n{str(e)}"
            )
    
    # ---- معالجات الأحداث ----
    
    def _on_file_selected(self, file_path: str):
        """معالجة اختيار ملف من شجرة المشروع"""
        # تحميل الملف في محرر الشيفرة باستخدام وظيفة read_file من utils
        content = read_file(file_path)
        if content is not None:
            self.code_editor.setPlainText(content)
            self.code_editor.file_path = file_path
            self.code_editor.document().setModified(False)
            
            # تحديد لغة البرمجة للكود
            ext = os.path.splitext(file_path)[1].lower()
            from ui_components import LANGUAGE_EXTENSIONS
            language = LANGUAGE_EXTENSIONS.get(ext, "")
            
            if language:
                from ui_components import SyntaxHighlighter
                self.code_editor.highlighter = SyntaxHighlighter(
                    self.code_editor.document(), language
                )
            
            # الانتقال إلى تبويب محرر الشيفرة
            self.tabs.setCurrentWidget(self.code_editor)
            
            # عرض اسم الملف في شريط الحالة
            rel_path = relative_path(file_path, self.project_model.project_dir)
            self.statusBar().showMessage(f"تم تحميل الملف: {rel_path}", 3000)
        else:
            QMessageBox.warning(
                self,
                "خطأ",
                f"تعذر تحميل الملف: {file_path}"
            )
    
    def _on_ai_model_changed(self, model_name: str):
        """معالجة تغيير نموذج الذكاء الاصطناعي"""
        # تحديد المزود بناءً على اسم النموذج
        provider = None
        
        if "Claude" in model_name:
            provider = "claude"
        elif "Grok" in model_name:
            provider = "grok"
        elif "DeepSeek" in model_name:
            provider = "deepseek"
        elif "GPT" in model_name:
            provider = "openai"
        
        # تحديث النموذج المفضل إذا كان المزود معروفًا
        if provider:
            # تحديث المزود المفضل
            self.api_config.preferred_provider = provider
            
            # تحديث النموذج
            self.api_config.models[provider] = model_name
            
            # عرض رسالة في شريط الحالة
            self.statusBar().showMessage(f"تم تغيير نموذج الذكاء الاصطناعي إلى: {model_name}", 3000)
    
    def _on_chat_message_sent(self, message: str):
        """معالجة إرسال رسالة من واجهة المحادثة"""
        # إرسال الرسالة عبر مكون المحادثة
        self.chat_component.send_message(message)
    
    def _on_chat_message_sent_internal(self, message):
        """معالجة إرسال رسالة داخلية من مكون المحادثة"""
        # عرض الرسالة في واجهة المحادثة (إذا لم تكن معروضة بالفعل)
        # (تجنب الازدواجية)
        pass
    
    def _on_chat_message_received(self, message):
        """معالجة استلام رسالة من مكون المحادثة"""
        # عرض الرسالة المستلمة في واجهة المحادثة
        is_code = "```" in message.content
        self.chat_widget.add_message("assistant", message.content, is_code)
        
        # الانتقال إلى تبويب المحادثة
        self.tabs.setCurrentWidget(self.chat_widget)
    
    def _on_chat_error(self, error: str):
        """معالجة خطأ في المحادثة"""
        # عرض رسالة خطأ في واجهة المحادثة
        self.chat_widget.add_system_message(f"حدث خطأ: {error}")
    
    def _on_analysis_started(self):
        """معالجة بدء التحليل"""
        # تحديث الواجهة
        self.start_analysis_action.setEnabled(False)
        self.stop_analysis_action.setEnabled(True)
        
        # إعادة تعيين شريط التقدم
        self.progress_bar.update_progress(0, 100)
        
        # عرض رسالة في شريط الحالة
        self.statusBar().showMessage("جاري تحليل المشروع...", 0)
    
    def _on_analysis_progress(self, current: int, total: int):
        """معالجة تقدم التحليل"""
        # تحديث شريط التقدم
        self.progress_bar.update_progress(current, total)
        
        # تحديث شريط الحالة
        self.status_bar.update_files_count(current, total)
    
    def _on_file_analyzed(self, file_path: str, issues: List[Dict[str, Any]]):
        """معالجة تحليل ملف"""
        # عرض اسم الملف النسبي في شريط الحالة إذا كان هناك مشاكل
        if issues:
            rel_path = relative_path(file_path, self.project_model.project_dir)
            self.statusBar().showMessage(f"تم العثور على {len(issues)} مشكلة في: {rel_path}", 3000)
    
    def _on_analysis_completed(self, results: Dict[str, Any]):
        """معالجة اكتمال التحليل"""
        # تحديث الواجهة
        self.start_analysis_action.setEnabled(True)
        self.stop_analysis_action.setEnabled(False)
        
        # تعيين تقدم الاكتمال لشريط التقدم
        self.progress_bar.update_progress(100, 100)
        
        # تحديث واجهة نتائج التحليل
        self.analysis_results.set_results(results)
        
        # تحديث واجهة الأمان والثغرات
        self.security_widget.set_security_issues(results.get("security_issues", []))
        
        # تحديث شريط الحالة المخصص
        self._update_status_bar(results)
        
        # الانتقال إلى تبويب نتائج التحليل
        self.tabs.setCurrentWidget(self.analysis_results)
        
        # حفظ نتائج التحليل في سجل التحليل
        self._save_analysis_history(results)
        
        # عرض رسالة في شريط الحالة
        total_issues = len(results.get("issues", []))
        total_security_issues = len(results.get("security_issues", []))
        self.statusBar().showMessage(f"اكتمل التحليل. تم العثور على {total_issues} مشكلة و {total_security_issues} ثغرة أمنية.", 5000)
    
    def _save_analysis_history(self, results: Dict[str, Any]):
        """حفظ نتائج التحليل في سجل التحليل"""
        if not self.project_model:
            return
        
        # إنشاء مجلد السجل إذا لم يكن موجودًا
        history_dir = os.path.join(self.project_model.project_dir, "_analysis_history")
        os.makedirs(history_dir, exist_ok=True)
        
        # إنشاء اسم الملف بالتاريخ والوقت
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(history_dir, f"analysis_{timestamp}.json")
        
        # إضافة التاريخ إلى النتائج
        results["analysis_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # حفظ النتائج
        save_json(results, file_path)
    
    def _update_status_bar(self, results: Dict[str, Any]):
        """تحديث شريط الحالة بناءً على نتائج التحليل"""
        # تصنيف المشاكل حسب الخطورة
        high_issues = sum(1 for issue in results.get("issues", []) if issue.get("severity") == "عالية")
        medium_issues = sum(1 for issue in results.get("issues", []) if issue.get("severity") == "متوسطة")
        low_issues = sum(1 for issue in results.get("issues", []) if issue.get("severity") == "منخفضة")
        
        # تحديث الأعداد في شريط الحالة
        self.status_bar.update_issues_count(high_issues, medium_issues, low_issues)
        
        # تحديث عدد الملفات
        total_files = results.get("total_files", 0)
        processed_files = results.get("processed_files", 0)
        self.status_bar.update_files_count(processed_files, total_files)
    
    def _on_analysis_failed(self, error: str):
        """معالجة فشل التحليل"""
        # تحديث الواجهة
        self.start_analysis_action.setEnabled(True)
        self.stop_analysis_action.setEnabled(False)
        
        # عرض رسالة خطأ
        QMessageBox.critical(
            self,
            "خطأ",
            f"فشل التحليل:\n{error}"
        )
        
        # عرض رسالة في شريط الحالة
        self.statusBar().showMessage("فشل التحليل", 5000)
    
    def _on_issue_selected(self, issue: Dict[str, Any]):
        """معالجة اختيار مشكلة من قائمة المشاكل"""
        # عرض تفاصيل المشكلة
        file_path = issue.get("file", "")
        if (file_path):
            try:
                # قراءة الملف المصدري باستخدام وظيفة read_file من utils
                code = read_file(file_path)
                if code is None:
                    QMessageBox.warning(
                        self,
                        "خطأ",
                        f"تعذر قراءة الملف: {file_path}"
                    )
                    return
                
                # إنشاء الكود المعدل (إذا كان متوفرًا)
                fixed_code = None
                if "suggestion" in issue:
                    # تطبيق الاقتراح على الكود الأصلي
                    lines = code.split('\n')
                    line = issue.get("line", 0)
                    if line > 0 and line <= len(lines):
                        # هذا تبسيط، في التطبيق الحقيقي قد يكون التطبيق أكثر تعقيدًا
                        lines[line - 1] = issue["suggestion"]
                        fixed_code = '\n'.join(lines)
                
                # عرض تفاصيل المشكلة في نافذة منفصلة
                dialog = IssueDetailsDialog(issue, code, fixed_code, self)
                dialog.apply_fix.connect(self._on_apply_fix)
                dialog.exec_()
            
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "خطأ",
                    f"تعذر عرض تفاصيل المشكلة:\n{str(e)}"
                )
    
    def _on_apply_fix(self, issue: Dict[str, Any]):
        """معالجة تطبيق حل لمشكلة"""
        file_path = issue.get("file", "")
        fixed_code = issue.get("fixed_code", "")
        
        if not file_path or not fixed_code:
            QMessageBox.warning(
                self,
                "خطأ",
                "معلومات غير كافية لتطبيق الحل."
            )
            return
        
        try:
            # قراءة الكود الأصلي باستخدام وظيفة read_file من utils
            original_code = read_file(file_path)
            if original_code is None:
                QMessageBox.warning(
                    self,
                    "خطأ",
                    f"تعذر قراءة الملف: {file_path}"
                )
                return
            
            # إضافة التعديل إلى مدير التعديلات
            if self.modifications_manager:
                self.modifications_manager.add_modification(
                    file_path=file_path,
                    original_content=original_code,
                    modified_content=fixed_code,
                    modification_type="تحليل",
                    description=issue.get("message", "تعديل تلقائي")
                )
            
            # كتابة الكود المعدل إلى الملف باستخدام وظيفة write_file من utils
            if not write_file(file_path, fixed_code):
                QMessageBox.warning(
                    self,
                    "خطأ",
                    f"تعذر كتابة الملف: {file_path}"
                )
                return
            
            # إذا كان الملف مفتوحًا في المحرر، تحديثه
            if self.code_editor.file_path == file_path:
                self.code_editor.setPlainText(fixed_code)
                self.code_editor.document().setModified(False)
            
            # عرض نافذة مقارنة الكود
            dialog = CodeComparisonDialog(file_path, original_code, fixed_code, self)
            dialog.exec_()
            
            # عرض رسالة نجاح
            QMessageBox.information(
                self,
                "تم التطبيق",
                "تم تطبيق الحل بنجاح."
            )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "خطأ",
                f"حدث خطأ أثناء تطبيق الحل:\n{str(e)}"
            )
            
            logger.error(f"خطأ في تطبيق الحل: {str(e)}")
    
    def _on_ignore_issue(self, issue: Dict[str, Any]):
        """معالجة تجاهل مشكلة"""
        # إضافة المشكلة إلى قائمة المشاكل المتجاهلة
        ignored_issues = self.settings.value("ignored_issues", [], list)
        
        # إنشاء معرف فريد للمشكلة (مسار الملف + رقم السطر + الوصف)
        issue_id = f"{issue.get('file', '')}:{issue.get('line', '')}:{issue.get('message', '')}"
        
        # إضافة المشكلة إلى القائمة إذا لم تكن موجودة
        if issue_id not in ignored_issues:
            ignored_issues.append(issue_id)
            self.settings.setValue("ignored_issues", ignored_issues)
        
        # عرض رسالة
        self.statusBar().showMessage("تم تجاهل المشكلة", 3000)
    
    def _on_security_issue_selected(self, issue: Dict[str, Any]):
        """معالجة اختيار ثغرة أمنية"""
        # عرض تفاصيل الثغرة (مشابه لـ _on_issue_selected)
        self._on_issue_selected(issue)
    
    def _on_apply_security_fix(self, issue: Dict[str, Any]):
        """معالجة تطبيق حل لثغرة أمنية"""
        # تطبيق الحل (مشابه لـ _on_apply_fix)
        self._on_apply_fix(issue)

    def initialize_chat_manager(self):
        """
        تهيئة مدير المحادثة مع السياق المناسب
        """
        if hasattr(self, 'chat_manager'):
            # تجهيز سياق المشروع
            if self.current_project:
                project_info = {
                    "name": self.current_project.name,
                    "structure": self.get_project_structure_as_text(),
                    "languages": self.current_project.get_languages(),
                    "dependencies": self.current_project.get_dependencies()
                }
                self.chat_manager.set_project_context(project_info)
            
            # تجهيز سياق الملف الحالي إذا كان موجوداً
            if hasattr(self, 'current_file') and self.current_file:
                file_info = {
                    "path": self.current_file.path,
                    "type": self.current_file.file_type,
                    "content": self.current_file.content
                }
                self.chat_manager.set_file_context(file_info)
            
            # تجهيز سياق الشيفرة المحددة إذا كانت هناك
            if hasattr(self, 'code_editor') and self.code_editor:
                selected_text = self.code_editor.textCursor().selectedText()
                if selected_text:
                    cursor = self.code_editor.textCursor()
                    start_line = self.code_editor.document().findBlock(cursor.selectionStart()).blockNumber() + 1
                    end_line = self.code_editor.document().findBlock(cursor.selectionEnd()).blockNumber() + 1
                    self.chat_manager.set_code_context(selected_text, start_line, end_line)

    def send_chat_message(self):
        if not hasattr(self, 'chat_manager'):
            # إنشاء مدير المحادثة إذا لم يكن موجوداً
            api_key = self.settings.value("api_key", "")
            model_type = self.settings.value("model_type", "openai")
            model_name = self.settings.value("model_name", "gpt-4o")
            
            api_client = ModelClientFactory.create_client(model_type, api_key, model_name)
            self.chat_manager = ChatManager(api_client)
        
        # تحديث السياق قبل إرسال الرسالة
        self.initialize_chat_manager()
        
        # إرسال الرسالة مع نوع المهمة المناسب
        message = self.chat_input.toPlainText()
        if message.strip():
            # تحديد نوع المهمة من القائمة المنسدلة إذا كانت موجودة
            task_type = None
            if hasattr(self, 'task_type_combo') and self.task_type_combo:
                task_type = self.task_type_combo.currentText()
                
            # إضافة رسالة المستخدم إلى نافذة المحادثة
            self.append_chat_message(message, is_user=True)
            
            # مسح حقل الإدخال
            self.chat_input.clear()
            
            # إرسال الرسالة والحصول على الرد
            response = self.chat_manager.send_message(message, task_type)
            
            # إضافة رد المساعد إلى نافذة المحادثة
            self.append_chat_message(response, is_user=False)

    def _setup_api_test_buttons(self):
        """إعداد أزرار اختبار API لكل منصة"""
        self.test_openai_button = QPushButton("اختبار OpenAI API")
        self.test_openai_button.clicked.connect(lambda: self._test_api("openai"))

        self.test_anthropic_button = QPushButton("اختبار Anthropic API")
        self.test_anthropic_button.clicked.connect(lambda: self._test_api("anthropic"))

        # إضافة الأزرار إلى واجهة المستخدم (على سبيل المثال، في شريط جانبي أو نافذة إعدادات)
        self.sidebar_layout.addWidget(self.test_openai_button)
        self.sidebar_layout.addWidget(self.test_anthropic_button)

    def _test_api(self, provider):
        """اختبار الاتصال بـ API معين"""
        api_client = get_api_client(self.api_config, provider)
        success, message = api_client.test_connection()

        if success:
            QMessageBox.information(self, "نجاح", message)
        else:
            QMessageBox.critical(self, "فشل", message)