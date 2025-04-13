#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نوافذ الحوار المختلفة للبرنامج
"""
import os
import re
import json
import logging
import hashlib
from typing import Dict, List, Any, Tuple, Optional, Union
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QSize, Signal, Slot, QDir, QSettings, QTimer, QEvent
from PySide6.QtGui import (QFont, QIcon, QColor, QPalette, QTextFormat, QKeySequence, QTextCursor, 
                         QTextCharFormat)
from PySide6.QtWidgets import (QDialog, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
                              QGridLayout, QFormLayout, QLineEdit, QTextEdit, QComboBox,
                              QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem, 
                              QFileDialog, QMessageBox, QDialogButtonBox, QGroupBox, 
                              QTabWidget, QCheckBox, QRadioButton, QListWidget, QListWidgetItem, 
                              QSpinBox, QProgressBar, QFrame, QSplitter, QInputDialog,
                              QScrollArea, QApplication)

from project_model import ProjectModel, CodeEntity
from api_clients import APIConfig, get_api_client
from utils import read_file, write_file, save_json, load_json, create_html_report

logger = logging.getLogger("CodeAnalyzer.Dialogs")

class BaseDialog(QDialog):
    """الفئة الأساسية لجميع نوافذ الحوار مع دعم الموضوعات"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("CodeAnalyzer", "Settings")
        self.apply_theme()
    
    def apply_theme(self):
        """تطبيق الموضوع (فاتح/داكن) على النافذة"""
        theme = self.settings.value("theme", "light")
        if theme == "dark":
            self._apply_dark_theme()
        else:
            self._apply_light_theme()
    
    def _apply_dark_theme(self):
        """تطبيق الموضوع الداكن"""
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, QColor(0, 0, 0))
        palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
        self.setPalette(palette)
    
    def _apply_light_theme(self):
        """تطبيق الموضوع الفاتح"""
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.Text, QColor(0, 0, 0))
        palette.setColor(QPalette.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(0, 0, 255))
        palette.setColor(QPalette.Highlight, QColor(51, 153, 255))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)
    
    def show_error(self, title: str, message: str, details: str = None):
        """عرض رسالة خطأ"""
        error_dialog = ErrorDialog(title, message, details, self)
        error_dialog.exec_()


class APISettingsDialog(BaseDialog):
    """نافذة إعدادات API"""
    
    def __init__(self, api_config: APIConfig, parent=None):
        super().__init__(parent)
        
        self.api_config = api_config
        
        # ضبط خصائص النافذة
        self.setWindowTitle("إعدادات API")
        self.setMinimumWidth(500)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # مجموعة المزود المفضل
        provider_group = QGroupBox("المزود المفضل للذكاء الاصطناعي")
        provider_layout = QVBoxLayout(provider_group)
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["claude", "grok", "deepseek", "openai"])
        self.provider_combo.setCurrentText(api_config.preferred_provider)
        
        provider_layout.addWidget(self.provider_combo)
        
        # مجموعة مفاتيح API
        keys_group = QGroupBox("مفاتيح API")
        keys_layout = QFormLayout(keys_group)
        
        self.api_key_inputs = {}
        
        for provider in ["claude", "grok", "deepseek", "openai"]:
            line_edit = QLineEdit()
            line_edit.setText(api_config.get_api_key(provider))
            line_edit.setEchoMode(QLineEdit.Password)
            
            keys_layout.addRow(f"مفتاح {provider}:", line_edit)
            self.api_key_inputs[provider] = line_edit
        
        # مجموعة النماذج
        models_group = QGroupBox("النماذج")
        models_layout = QFormLayout(models_group)
        
        self.model_inputs = {}
        
        for provider, default_model in [
            ("claude", "claude-3-7-sonnet"),
            ("grok", "grok-2-latest"),
            ("deepseek", "deepseek-v3"),
            ("openai", "gpt-4o")
        ]:
            line_edit = QLineEdit()
            line_edit.setText(api_config.get_model(provider) or default_model)
            
            models_layout.addRow(f"نموذج {provider}:", line_edit)
            self.model_inputs[provider] = line_edit
        
        # أزرار التأكيد والإلغاء
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # إضافة زر الاختبار
        test_button = QPushButton("اختبار الاتصال")
        test_button.clicked.connect(self._test_connection)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(provider_group)
        layout.addWidget(keys_group)
        layout.addWidget(models_group)
        layout.addWidget(test_button)
        layout.addWidget(button_box)
    
    def _test_connection(self):
        """اختبار الاتصال مع مزود API المحدد"""
        try:
            # تحديث API Config بالقيم الحالية
            provider = self.provider_combo.currentText()
            model = self.model_inputs[provider].text()
            api_key = self.api_key_inputs[provider].text()
            
            if not api_key:
                QMessageBox.warning(self, "تنبيه", f"يرجى إدخال مفتاح API لـ {provider} أولاً.")
                return
            
            # إنشاء نسخة مؤقتة من API Config للاختبار
            temp_config = APIConfig(
                api_keys={provider: api_key},
                preferred_provider=provider,
                models={provider: model}
            )
            
            # إنشاء عميل API واختبار الاتصال
            client = get_api_client(temp_config, provider)
            
            # عرض نافذة تقدم
            progress = ProgressDialog("اختبار الاتصال", f"جاري الاتصال بـ {provider}...", self)
            progress.show()
            QApplication.processEvents()
            
            # اختبار بسيط للمحادثة
            response = client.chat([{"role": "user", "content": "Hello, This is a test message. Please respond with a short confirmation."}])
            
            # إغلاق نافذة التقدم
            progress.accept()
            
            if response:
                QMessageBox.information(self, "نجاح", f"تم الاتصال بـ {provider} بنجاح.")
            else:
                QMessageBox.warning(self, "تنبيه", f"لم يتم استلام استجابة من {provider}.")
        
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل الاتصال: {str(e)}")
    
    def accept(self):
        """حفظ الإعدادات عند الضغط على زر التأكيد"""
        try:
            # تحديث المزود المفضل
            self.api_config.preferred_provider = self.provider_combo.currentText()
            
            # تحديث مفاتيح API
            for provider, line_edit in self.api_key_inputs.items():
                self.api_config.api_keys[provider] = line_edit.text()
            
            # تحديث النماذج
            for provider, line_edit in self.model_inputs.items():
                self.api_config.models[provider] = line_edit.text()
            
            super().accept()
        except Exception as e:
            self.show_error("خطأ", "حدث خطأ أثناء حفظ الإعدادات", str(e))


class PendingModificationsDialog(BaseDialog):
    """نافذة عرض التعديلات المعلقة"""
    
    apply_selected = Signal(list)  # إشارة تطبيق التعديلات المحددة
    apply_all = Signal()  # إشارة تطبيق جميع التعديلات
    
    def __init__(self, modifications: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        
        # ضبط خصائص النافذة
        self.setWindowTitle("التعديلات المعلقة")
        self.setMinimumSize(700, 500)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # جدول التعديلات
        self.modifications_table = QTableWidget()
        self.modifications_table.setColumnCount(5)
        self.modifications_table.setHorizontalHeaderLabels(["", "الملف", "النوع", "الوصف", "التاريخ"])
        self.modifications_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.modifications_table.verticalHeader().setVisible(False)
        self.modifications_table.horizontalHeader().setStretchLastSection(True)
        
        # إضافة التعديلات إلى الجدول
        self._populate_table(modifications)
        
        # منطقة عرض الكود
        code_layout = QHBoxLayout()
        
        # الكود الأصلي
        original_group = QGroupBox("الكود الأصلي")
        original_layout = QVBoxLayout(original_group)
        
        self.original_text = QTextEdit()
        self.original_text.setReadOnly(True)
        
        original_layout.addWidget(self.original_text)
        
        # الكود المعدل
        modified_group = QGroupBox("الكود المعدل")
        modified_layout = QVBoxLayout(modified_group)
        
        self.modified_text = QTextEdit()
        self.modified_text.setReadOnly(True)
        
        modified_layout.addWidget(self.modified_text)
        
        code_layout.addWidget(original_group)
        code_layout.addWidget(modified_group)
        
        # أزرار الإجراءات
        actions_layout = QHBoxLayout()
        
        self.apply_selected_button = QPushButton("تطبيق المحدد")
        self.apply_selected_button.clicked.connect(self._on_apply_selected)
        
        self.apply_all_button = QPushButton("تطبيق الجميع")
        self.apply_all_button.clicked.connect(self._on_apply_all)
        
        self.close_button = QPushButton("إغلاق")
        self.close_button.clicked.connect(self.reject)
        
        actions_layout.addWidget(self.apply_selected_button)
        actions_layout.addWidget(self.apply_all_button)
        actions_layout.addStretch()
        actions_layout.addWidget(self.close_button)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(self.modifications_table, 1)
        layout.addLayout(code_layout, 2)
        layout.addLayout(actions_layout)
        
        # ربط الأحداث
        self.modifications_table.itemSelectionChanged.connect(self._on_selection_changed)
        
        # المتغيرات الداخلية
        self.modifications = modifications
    
    def _populate_table(self, modifications: List[Dict[str, Any]]):
        """ملء جدول التعديلات"""
        self.modifications_table.setRowCount(len(modifications))
        
        for i, mod in enumerate(modifications):
            # خلية الاختيار
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            
            self.modifications_table.setCellWidget(i, 0, checkbox_widget)
            
            # خلية الملف
            file_path = mod.get("file_path", "")
            file_name = os.path.basename(file_path)
            self.modifications_table.setItem(i, 1, QTableWidgetItem(file_name))
            
            # خلية النوع
            mod_type = mod.get("type", "تعديل")
            self.modifications_table.setItem(i, 2, QTableWidgetItem(mod_type))
            
            # خلية الوصف
            description = mod.get("description", "")
            self.modifications_table.setItem(i, 3, QTableWidgetItem(description))
            
            # خلية التاريخ
            timestamp = mod.get("timestamp", 0)
            date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            self.modifications_table.setItem(i, 4, QTableWidgetItem(date_str))
        
        self.modifications_table.resizeColumnsToContents()
    
    @Slot()
    def _on_selection_changed(self):
        """معالجة تغيير التحديد"""
        selected_rows = self.modifications_table.selectedIndexes()
        if selected_rows:
            row = selected_rows[0].row()
            mod = self.modifications[row]
            
            # عرض الكود الأصلي والمعدل
            self.original_text.setPlainText(mod.get("original_content", ""))
            self.modified_text.setPlainText(mod.get("modified_content", ""))
    
    @Slot()
    def _on_apply_selected(self):
        """معالجة النقر على زر تطبيق المحدد"""
        selected_indices = []
        
        for i in range(self.modifications_table.rowCount()):
            checkbox_widget = self.modifications_table.cellWidget(i, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            
            if checkbox and checkbox.isChecked():
                selected_indices.append(i)
        
        if selected_indices:
            selected_mods = [self.modifications[i] for i in selected_indices]
            self.apply_selected.emit(selected_mods)
            self.accept()
    
    @Slot()
    def _on_apply_all(self):
        """معالجة النقر على زر تطبيق الجميع"""
        self.apply_all.emit()
        self.accept()


class IssueDetailsDialog(BaseDialog):
    """نافذة عرض تفاصيل المشكلة"""
    
    apply_fix = Signal(dict)  # إشارة تطبيق الحل
    
    def __init__(self, issue: Dict[str, Any], original_code: str, fixed_code: str = None, parent=None):
        super().__init__(parent)
        
        # ضبط خصائص النافذة
        self.setWindowTitle("تفاصيل المشكلة")
        self.setMinimumSize(800, 600)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # معلومات المشكلة
        info_group = QGroupBox("معلومات المشكلة")
        info_layout = QGridLayout(info_group)
        
        file_label = QLabel("الملف:")
        file_value = QLabel(issue.get("file", ""))
        
        line_label = QLabel("السطر:")
        line_value = QLabel(str(issue.get("line", "")))
        
        severity_label = QLabel("الخطورة:")
        severity_value = QLabel(issue.get("severity", "منخفضة"))
        
        description_label = QLabel("الوصف:")
        description_value = QLabel(issue.get("message", ""))
        description_value.setWordWrap(True)
        
        info_layout.addWidget(file_label, 0, 0)
        info_layout.addWidget(file_value, 0, 1)
        info_layout.addWidget(line_label, 1, 0)
        info_layout.addWidget(line_value, 1, 1)
        info_layout.addWidget(severity_label, 2, 0)
        info_layout.addWidget(severity_value, 2, 1)
        info_layout.addWidget(description_label, 3, 0, Qt.AlignTop)
        info_layout.addWidget(description_value, 3, 1)
        
        # الكود قبل وبعد التعديل
        code_tabs = QTabWidget()
        
        # تبويب الكود الأصلي
        original_tab = QWidget()
        original_layout = QVBoxLayout(original_tab)
        
        self.original_text = QTextEdit()
        self.original_text.setReadOnly(True)
        self.original_text.setPlainText(original_code)
        
        original_layout.addWidget(self.original_text)
        
        # تبويب الكود المعدل
        fixed_tab = QWidget()
        fixed_layout = QVBoxLayout(fixed_tab)
        
        self.fixed_text = QTextEdit()
        self.fixed_text.setPlainText(fixed_code or issue.get("suggestion", ""))
        
        fixed_layout.addWidget(self.fixed_text)
        
        # إضافة التبويبات
        code_tabs.addTab(original_tab, "الكود الأصلي")
        code_tabs.addTab(fixed_tab, "الكود المعدل")
        
        # خطوات الحل
        steps_group = QGroupBox("خطوات الحل")
        steps_layout = QVBoxLayout(steps_group)
        
        self.steps_text = QTextEdit()
        self.steps_text.setReadOnly(True)
        
        # إنشاء خطوات الحل من الاقتراح
        suggestion = issue.get("suggestion", "")
        if suggestion:
            steps = "1. " + suggestion
            self.steps_text.setPlainText(steps)
        
        steps_layout.addWidget(self.steps_text)
        
        # أزرار الإجراءات
        actions_layout = QHBoxLayout()
        
        self.apply_button = QPushButton("تطبيق الحل")
        self.apply_button.clicked.connect(self._on_apply_clicked)
        
        self.close_button = QPushButton("إغلاق")
        self.close_button.clicked.connect(self.reject)
        
        actions_layout.addWidget(self.apply_button)
        actions_layout.addStretch()
        actions_layout.addWidget(self.close_button)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(info_group)
        layout.addWidget(code_tabs, 3)
        layout.addWidget(steps_group)
        layout.addLayout(actions_layout)
        
        # المتغيرات الداخلية
        self.issue = issue
    
    @Slot()
    def _on_apply_clicked(self):
        """معالجة النقر على زر تطبيق الحل"""
        # إضافة الكود المعدل إلى المشكلة
        self.issue["fixed_code"] = self.fixed_text.toPlainText()
        self.apply_fix.emit(self.issue)
        self.accept()


class ImportExportDialog(BaseDialog):
    """نافذة استيراد وتصدير البيانات"""
    
    import_data = Signal(str)  # إشارة استيراد البيانات (مسار الملف)
    export_data = Signal(str, bool)  # إشارة تصدير البيانات (مسار الملف، تقرير HTML)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ضبط خصائص النافذة
        self.setWindowTitle("استيراد / تصدير")
        self.setMinimumWidth(500)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # مجموعة الاستيراد
        import_group = QGroupBox("استيراد البيانات")
        import_layout = QVBoxLayout(import_group)
        
        import_description = QLabel("استيراد نتائج تحليل سابقة من ملف JSON.")
        
        import_file_layout = QHBoxLayout()
        self.import_path_edit = QLineEdit()
        self.import_path_edit.setReadOnly(True)
        self.import_browse_button = QPushButton("استعراض...")
        self.import_browse_button.clicked.connect(self._on_import_browse)
        
        import_file_layout.addWidget(self.import_path_edit)
        import_file_layout.addWidget(self.import_browse_button)
        
        self.import_button = QPushButton("استيراد")
        self.import_button.clicked.connect(self._on_import)
        
        import_layout.addWidget(import_description)
        import_layout.addLayout(import_file_layout)
        import_layout.addWidget(self.import_button)
        
        # مجموعة التصدير
        export_group = QGroupBox("تصدير البيانات")
        export_layout = QVBoxLayout(export_group)
        
        export_description = QLabel("تصدير نتائج التحليل إلى ملف.")
        
        export_file_layout = QHBoxLayout()
        self.export_path_edit = QLineEdit()
        self.export_path_edit.setReadOnly(True)
        self.export_browse_button = QPushButton("استعراض...")
        self.export_browse_button.clicked.connect(self._on_export_browse)
        
        export_file_layout.addWidget(self.export_path_edit)
        export_file_layout.addWidget(self.export_browse_button)
        
        self.export_html_check = QCheckBox("إنشاء تقرير HTML تفاعلي")
        self.export_html_check.setChecked(True)
        
        self.export_button = QPushButton("تصدير")
        self.export_button.clicked.connect(self._on_export)
        
        export_layout.addWidget(export_description)
        export_layout.addLayout(export_file_layout)
        export_layout.addWidget(self.export_html_check)
        export_layout.addWidget(self.export_button)
        
        # زر الإغلاق
        self.close_button = QPushButton("إغلاق")
        self.close_button.clicked.connect(self.reject)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(import_group)
        layout.addWidget(export_group)
        layout.addWidget(self.close_button)
    
    @Slot()
    def _on_import_browse(self):
        """اختيار ملف للاستيراد"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "اختيار ملف للاستيراد",
            "",
            "ملفات JSON (*.json)"
        )
        
        if file_path:
            self.import_path_edit.setText(file_path)
    
    @Slot()
    def _on_export_browse(self):
        """اختيار موقع للتصدير"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "اختيار موقع للتصدير",
            "",
            "ملفات JSON (*.json)"
        )
        
        if file_path:
            if not file_path.endswith('.json'):
                file_path += '.json'
            self.export_path_edit.setText(file_path)
    
    @Slot()
    def _on_import(self):
        """معالجة النقر على زر الاستيراد"""
        file_path = self.import_path_edit.text()
        if file_path:
            self.import_data.emit(file_path)
            self.accept()
        else:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار ملف للاستيراد أولاً.")
    
    @Slot()
    def _on_export(self):
        """معالجة النقر على زر التصدير"""
        file_path = self.export_path_edit.text()
        if file_path:
            create_html = self.export_html_check.isChecked()
            self.export_data.emit(file_path, create_html)
            self.accept()
        else:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار موقع للتصدير أولاً.")


class GeneralSettingsDialog(BaseDialog):
    """نافذة الإعدادات العامة"""
    
    def __init__(self, settings: Dict[str, Any], parent=None):
        super().__init__(parent)
        
        self.settings = settings
        
        # ضبط خصائص النافذة
        self.setWindowTitle("الإعدادات العامة")
        self.setMinimumWidth(500)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # تبويبات الإعدادات
        tabs = QTabWidget()
        
        # تبويب الواجهة
        ui_tab = QWidget()
        ui_layout = QVBoxLayout(ui_tab)
        
        # اتجاه الواجهة
        direction_group = QGroupBox("اتجاه الواجهة")
        direction_layout = QVBoxLayout(direction_group)
        
        self.rtl_radio = QRadioButton("من اليمين إلى اليسار (RTL)")
        self.ltr_radio = QRadioButton("من اليسار إلى اليمين (LTR)")
        
        if settings.get("ui_direction") == "ltr":
            self.ltr_radio.setChecked(True)
        else:
            self.rtl_radio.setChecked(True)
        
        direction_layout.addWidget(self.rtl_radio)
        direction_layout.addWidget(self.ltr_radio)
        
        # سمة الواجهة
        theme_group = QGroupBox("سمة الواجهة")
        theme_layout = QVBoxLayout(theme_group)
        
        self.light_theme_radio = QRadioButton("فاتحة")
        self.dark_theme_radio = QRadioButton("داكنة")
        
        if settings.get("theme") == "dark":
            self.dark_theme_radio.setChecked(True)
        else:
            self.light_theme_radio.setChecked(True)
        
        theme_layout.addWidget(self.light_theme_radio)
        theme_layout.addWidget(self.dark_theme_radio)
        
        # حجم الخط
        font_group = QGroupBox("حجم الخط")
        font_layout = QHBoxLayout(font_group)
        
        font_label = QLabel("حجم الخط:")
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(settings.get("font_size", 10))
        
        font_layout.addWidget(font_label)
        font_layout.addWidget(self.font_size_spin)
        
        # إضافة العناصر إلى تبويب الواجهة
        ui_layout.addWidget(direction_group)
        ui_layout.addWidget(theme_group)
        ui_layout.addWidget(font_group)
        ui_layout.addStretch()
        
        # تبويب التحليل
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout(analysis_tab)
        
        # استخدام الذكاء الاصطناعي
        ai_group = QGroupBox("استخدام الذكاء الاصطناعي")
        ai_layout = QVBoxLayout(ai_group)
        
        self.use_ai_check = QCheckBox("استخدام الذكاء الاصطناعي في التحليل")
        self.use_ai_check.setChecked(settings.get("use_ai", True))
        
        self.analyze_security_check = QCheckBox("تحليل الثغرات الأمنية")
        self.analyze_security_check.setChecked(settings.get("analyze_security", True))
        
        ai_layout.addWidget(self.use_ai_check)
        ai_layout.addWidget(self.analyze_security_check)
        
        # عدد خيوط التحليل
        threads_group = QGroupBox("عدد خيوط التحليل")
        threads_layout = QHBoxLayout(threads_group)
        
        threads_label = QLabel("عدد الخيوط:")
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 16)
        self.threads_spin.setValue(settings.get("analysis_threads", 4))
        
        threads_layout.addWidget(threads_label)
        threads_layout.addWidget(self.threads_spin)
        
        # إضافة العناصر إلى تبويب التحليل
        analysis_layout.addWidget(ai_group)
        analysis_layout.addWidget(threads_group)
        analysis_layout.addStretch()
        
        # إضافة التبويبات
        tabs.addTab(ui_tab, "الواجهة")
        tabs.addTab(analysis_tab, "التحليل")
        
        # أزرار التأكيد والإلغاء
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(tabs)
        layout.addWidget(button_box)
    
    def accept(self):
        """حفظ الإعدادات عند الضغط على زر التأكيد"""
        # إعدادات الواجهة
        self.settings["ui_direction"] = "ltr" if self.ltr_radio.isChecked() else "rtl"
        self.settings["theme"] = "dark" if self.dark_theme_radio.isChecked() else "light"
        self.settings["font_size"] = self.font_size_spin.value()
        
        # إعدادات التحليل
        self.settings["use_ai"] = self.use_ai_check.isChecked()
        self.settings["analyze_security"] = self.analyze_security_check.isChecked()
        self.settings["analysis_threads"] = self.threads_spin.value()
        
        super().accept()


class SecurityAnalysisDialog(BaseDialog):
    """نافذة تحليل الأمان"""
    
    start_analysis = Signal(bool)  # إشارة بدء التحليل (تحليل المشروع بأكمله)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ضبط خصائص النافذة
        self.setWindowTitle("تحليل الأمان")
        self.setMinimumSize(600, 400)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # مجموعة الخيارات
        options_group = QGroupBox("خيارات التحليل")
        options_layout = QVBoxLayout(options_group)
        
        self.full_project_check = QCheckBox("تحليل المشروع بأكمله")
        self.full_project_check.setChecked(True)
        
        self.scan_dependencies_check = QCheckBox("فحص المكتبات والتبعيات")
        self.scan_dependencies_check.setChecked(True)
        
        self.detailed_report_check = QCheckBox("إنشاء تقرير مفصل")
        self.detailed_report_check.setChecked(True)
        
        options_layout.addWidget(self.full_project_check)
        options_layout.addWidget(self.scan_dependencies_check)
        options_layout.addWidget(self.detailed_report_check)
        
        # أنواع الثغرات
        vuln_types_group = QGroupBox("أنواع الثغرات للفحص")
        vuln_types_layout = QVBoxLayout(vuln_types_group)
        
        self.sql_injection_check = QCheckBox("حقن SQL")
        self.sql_injection_check.setChecked(True)
        
        self.xss_check = QCheckBox("Cross-Site Scripting (XSS)")
        self.xss_check.setChecked(True)
        
        self.csrf_check = QCheckBox("Cross-Site Request Forgery (CSRF)")
        self.csrf_check.setChecked(True)
        
        self.command_injection_check = QCheckBox("حقن الأوامر")
        self.command_injection_check.setChecked(True)
        
        self.auth_issues_check = QCheckBox("مشاكل المصادقة والتفويض")
        self.auth_issues_check.setChecked(True)
        
        vuln_types_layout.addWidget(self.sql_injection_check)
        vuln_types_layout.addWidget(self.xss_check)
        vuln_types_layout.addWidget(self.csrf_check)
        vuln_types_layout.addWidget(self.command_injection_check)
        vuln_types_layout.addWidget(self.auth_issues_check)
        
        # أزرار التحكم
        control_layout = QHBoxLayout()
        
        self.start_button = QPushButton("بدء التحليل")
        self.start_button.clicked.connect(self._on_start_clicked)
        
        self.cancel_button = QPushButton("إلغاء")
        self.cancel_button.clicked.connect(self.reject)
        
        control_layout.addWidget(self.start_button)
        control_layout.addStretch()
        control_layout.addWidget(self.cancel_button)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(options_group)
        layout.addWidget(vuln_types_group)
        layout.addStretch()
        layout.addLayout(control_layout)
    
    @Slot()
    def _on_start_clicked(self):
        """معالجة النقر على زر بدء التحليل"""
        full_project = self.full_project_check.isChecked()
        self.start_analysis.emit(full_project)
        self.accept()


class ConfirmationDialog(BaseDialog):
    """نافذة تأكيد للعمليات المهمة"""
    
    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)
        
        # ضبط خصائص النافذة
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # رسالة التأكيد
        self.message_label = QLabel(message)
        self.message_label.setWordWrap(True)
        
        # أيقونة التحذير
        icon_layout = QHBoxLayout()
        warning_icon = QLabel()
        warning_icon.setPixmap(QIcon.fromTheme("dialog-warning").pixmap(32, 32))
        
        icon_layout.addWidget(warning_icon)
        icon_layout.addWidget(self.message_label, 1)
        
        # أزرار التأكيد والإلغاء
        button_box = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addLayout(icon_layout)
        layout.addWidget(button_box)


class ProjectSelectionDialog(BaseDialog):
    """نافذة اختيار مجلد المشروع"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ضبط خصائص النافذة
        self.setWindowTitle("اختيار مشروع")
        self.setMinimumWidth(500)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # مجموعة اختيار المجلد
        folder_group = QGroupBox("مجلد المشروع")
        folder_layout = QHBoxLayout(folder_group)
        
        self.folder_path_edit = QLineEdit()
        self.folder_path_edit.setReadOnly(True)
        
        self.browse_button = QPushButton("استعراض...")
        self.browse_button.clicked.connect(self._on_browse)
        
        folder_layout.addWidget(self.folder_path_edit)
        folder_layout.addWidget(self.browse_button)
        
        # مجموعة نوع المشروع
        type_group = QGroupBox("نوع المشروع")
        type_layout = QVBoxLayout(type_group)
        
        self.auto_detect_check = QCheckBox("اكتشاف نوع المشروع تلقائيًا")
        self.auto_detect_check.setChecked(True)
        self.auto_detect_check.toggled.connect(self._on_auto_detect_toggled)
        
        self.project_type_combo = QComboBox()
        self.project_type_combo.addItems(["python", "flutter_dart", "laravel_php", "javascript", "react"])
        self.project_type_combo.setEnabled(False)
        
        type_layout.addWidget(self.auto_detect_check)
        type_layout.addWidget(self.project_type_combo)
        
        # أزرار التأكيد والإلغاء
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(folder_group)
        layout.addWidget(type_group)
        layout.addWidget(button_box)
    
    @Slot()
    def _on_browse(self):
        """اختيار مجلد المشروع"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "اختيار مجلد المشروع"
        )
        
        if folder_path:
            self.folder_path_edit.setText(folder_path)
    
    @Slot(bool)
    def _on_auto_detect_toggled(self, checked: bool):
        """معالجة تغيير خيار الاكتشاف التلقائي"""
        self.project_type_combo.setEnabled(not checked)
    
    def get_folder_path(self) -> str:
        """الحصول على مسار المجلد"""
        return self.folder_path_edit.text()
    
    def get_project_type(self) -> str:
        """الحصول على نوع المشروع"""
        if self.auto_detect_check.isChecked():
            return "auto"
        else:
            return self.project_type_combo.currentText()
    
    def accept(self):
        """التحقق من البيانات قبل القبول"""
        if not self.folder_path_edit.text():
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار مجلد المشروع.")
            return
        
        super().accept()


class RevertModificationDialog(BaseDialog):
    """نافذة التراجع عن تعديل"""
    
    def __init__(self, modification: Dict[str, Any], parent=None):
        super().__init__(parent)
        
        # ضبط خصائص النافذة
        self.setWindowTitle("التراجع عن تعديل")
        self.setMinimumWidth(500)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # معلومات التعديل
        info_group = QGroupBox("معلومات التعديل")
        info_layout = QFormLayout(info_group)
        
        file_path = modification.get("file_path", "")
        description = modification.get("description", "")
        mod_type = modification.get("type", "")
        
        file_label = QLabel(file_path)
        description_label = QLabel(description)
        type_label = QLabel(mod_type)
        
        info_layout.addRow("الملف:", file_label)
        info_layout.addRow("الوصف:", description_label)
        info_layout.addRow("النوع:", type_label)
        
        # رسالة تنبيه
        warning_label = QLabel("هل أنت متأكد من أنك تريد التراجع عن هذا التعديل؟ سيتم استعادة الملف إلى حالته الأصلية.")
        warning_label.setStyleSheet("color: red;")
        warning_label.setWordWrap(True)
        
        # أزرار التأكيد والإلغاء
        button_box = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(info_group)
        layout.addWidget(warning_label)
        layout.addWidget(button_box)


class ProgressDialog(BaseDialog):
    """نافذة تقدم العمليات الطويلة"""
    
    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)
        
        # ضبط خصائص النافذة
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setModal(True)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # رسالة
        self.message_label = QLabel(message)
        self.message_label.setWordWrap(True)
        
        # شريط التقدم
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # نمط غير محدد
        
        # زر الإلغاء
        self.cancel_button = QPushButton("إلغاء")
        self.cancel_button.clicked.connect(self.reject)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(self.message_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.cancel_button, 0, Qt.AlignCenter)
    
    def set_progress(self, value: int, maximum: int):
        """تعيين تقدم العملية"""
        self.progress_bar.setRange(0, maximum)
        self.progress_bar.setValue(value)
    
    def set_message(self, message: str):
        """تعيين رسالة التقدم"""
        self.message_label.setText(message)


class AboutDialog(BaseDialog):
    """نافذة حول البرنامج"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ضبط خصائص النافذة
        self.setWindowTitle("حول البرنامج")
        self.setMinimumWidth(500)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # عنوان البرنامج
        title_label = QLabel("محلل الشيفرة البرمجية بالذكاء الاصطناعي")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        
        # وصف البرنامج
        description_label = QLabel(
            "برنامج لتحليل الشيفرة البرمجية باستخدام نماذج الذكاء الاصطناعي، "
            "واكتشاف المشاكل، وتقديم الاقتراحات والحلول. "
            "يتميز بفهمه العميق للمشروع كاملاً وليس كملفات منفصلة."
        )
        description_label.setWordWrap(True)
        description_label.setAlignment(Qt.AlignCenter)
        
        # معلومات الإصدار
        version_label = QLabel("الإصدار: 1.1.0")
        version_label.setAlignment(Qt.AlignCenter)
        
        # معلومات المطور
        developer_label = QLabel("تطوير: فريق محلل الشيفرة البرمجية")
        developer_label.setAlignment(Qt.AlignCenter)
        
        # خط فاصل
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        
        # نماذج الذكاء الاصطناعي المدعومة
        models_group = QGroupBox("نماذج الذكاء الاصطناعي المدعومة")
        models_layout = QVBoxLayout(models_group)
        
        models_text = QLabel(
            "- Claude: نماذج Claude 3.5 Sonnet وClaude 3.7 Sonnet\n"
            "- Grok AI: نموذج grok-2-latest\n"
            "- DeepSeek: نموذج DeepSeek-V3\n"
            "- OpenAI: نماذج GPT-3.5 Turbo وGPT-4o"
        )
        
        models_layout.addWidget(models_text)
        
        # اللغات المدعومة
        languages_group = QGroupBox("اللغات المدعومة")
        languages_layout = QVBoxLayout(languages_group)
        
        languages_text = QLabel(
            "- Python\n"
            "- Flutter/Dart\n"
            "- Laravel/PHP\n"
            "- JavaScript/React\n"
            "- HTML/CSS"
        )
        
        languages_layout.addWidget(languages_text)
        
        # زر الإغلاق
        close_button = QPushButton("إغلاق")
        close_button.clicked.connect(self.accept)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addWidget(version_label)
        layout.addWidget(developer_label)
        layout.addWidget(line)
        layout.addWidget(models_group)
        layout.addWidget(languages_group)
        layout.addWidget(close_button, 0, Qt.AlignCenter)


class FeatureDevelopmentDialog(BaseDialog):
    """نافذة تطوير ميزات جديدة"""
    
    develop_feature = Signal(str, str)  # إشارة تطوير ميزة (الوصف، سياق المشروع)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ضبط خصائص النافذة
        self.setWindowTitle("تطوير ميزة جديدة")
        self.setMinimumSize(700, 500)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # وصف الميزة
        description_group = QGroupBox("وصف الميزة المطلوبة")
        description_layout = QVBoxLayout(description_group)
        
        description_label = QLabel("اكتب وصفاً تفصيلياً للميزة التي ترغب في إضافتها:")
        
        self.description_text = QTextEdit()
        self.description_text.setPlaceholderText("مثال: إضافة ميزة البحث في الشيفرة البرمجية عن نمط محدد...")
        
        description_layout.addWidget(description_label)
        description_layout.addWidget(self.description_text)
        
        # معلومات السياق
        context_group = QGroupBox("معلومات إضافية عن المشروع (اختياري)")
        context_layout = QVBoxLayout(context_group)
        
        context_label = QLabel("أضف أي معلومات قد تساعد في فهم سياق المشروع:")
        
        self.context_text = QTextEdit()
        self.context_text.setPlaceholderText("مثال: المشروع يستخدم واجهة Qt ويحتاج إلى دعم تعدد اللغات...")
        
        context_layout.addWidget(context_label)
        context_layout.addWidget(self.context_text)
        
        # أزرار التحكم
        button_layout = QHBoxLayout()
        
        self.develop_button = QPushButton("تطوير الميزة")
        self.develop_button.clicked.connect(self._on_develop)
        
        self.cancel_button = QPushButton("إلغاء")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.develop_button)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(description_group)
        layout.addWidget(context_group)
        layout.addLayout(button_layout)
    
    @Slot()
    def _on_develop(self):
        """معالجة النقر على زر تطوير الميزة"""
        description = self.description_text.toPlainText().strip()
        context = self.context_text.toPlainText().strip()
        
        if not description:
            QMessageBox.warning(self, "تنبيه", "يرجى كتابة وصف للميزة المطلوبة.")
            return
        
        self.develop_feature.emit(description, context)
        self.accept()


class ApplyFeatureDialog(BaseDialog):
    """نافذة تطبيق ميزة مطورة"""
    
    apply_feature = Signal(Dict[str, Any])  # إشارة تطبيق الميزة (بيانات الميزة)
    
    def __init__(self, feature_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        
        self.feature_data = feature_data
        
        # ضبط خصائص النافذة
        self.setWindowTitle("تطبيق ميزة جديدة")
        self.setMinimumSize(800, 600)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # وصف الميزة
        description_group = QGroupBox("الميزة المطورة")
        description_layout = QVBoxLayout(description_group)
        
        self.description_label = QLabel(feature_data.get("feature_description", ""))
        self.description_label.setWordWrap(True)
        
        description_layout.addWidget(self.description_label)
        
        # الملفات المطلوب تعديلها
        files_group = QGroupBox("الملفات التي سيتم تعديلها")
        files_layout = QVBoxLayout(files_group)
        
        self.files_list = QListWidget()
        
        modifications = feature_data.get("modifications", [])
        for mod in modifications:
            file_path = mod.get("file_path", "")
            if file_path:
                item = QListWidgetItem(file_path)
                item.setData(Qt.UserRole, mod)
                self.files_list.addItem(item)
        
        files_layout.addWidget(self.files_list)
        
        # معاينة الكود
        preview_group = QGroupBox("معاينة الكود")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        
        preview_layout.addWidget(self.preview_text)
        
        # أزرار التحكم
        button_layout = QHBoxLayout()
        
        self.apply_button = QPushButton("تطبيق الميزة")
        self.apply_button.clicked.connect(self._on_apply)
        
        self.cancel_button = QPushButton("إلغاء")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.apply_button)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(description_group)
        layout.addWidget(files_group)
        layout.addWidget(preview_group)
        layout.addLayout(button_layout)
        
        # ربط الأحداث
        self.files_list.itemSelectionChanged.connect(self._on_file_selected)
        
        # تحديد أول عنصر تلقائياً
        if self.files_list.count() > 0:
            self.files_list.setCurrentRow(0)
    
    @Slot()
    def _on_file_selected(self):
        """معالجة تغيير تحديد الملف"""
        selected_items = self.files_list.selectedItems()
        if selected_items:
            mod = selected_items[0].data(Qt.UserRole)
            code = mod.get("code", "")
            self.preview_text.setPlainText(code)
    
    @Slot()
    def _on_apply(self):
        """معالجة النقر على زر تطبيق الميزة"""
        reply = QMessageBox.question(
            self,
            "تأكيد التطبيق",
            "هل أنت متأكد من أنك تريد تطبيق هذه الميزة؟ سيتم تعديل الملفات المذكورة.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.apply_feature.emit(self.feature_data)
            self.accept()


class ErrorDialog(BaseDialog):
    """نافذة عرض الأخطاء"""
    
    def __init__(self, title: str, message: str, details: str = None, parent=None):
        super().__init__(parent)
        
        # ضبط خصائص النافذة
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # أيقونة الخطأ والرسالة
        message_layout = QHBoxLayout()
        
        error_icon = QLabel()
        error_icon.setPixmap(QIcon.fromTheme("dialog-error").pixmap(32, 32))
        
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        
        message_layout.addWidget(error_icon)
        message_layout.addWidget(message_label, 1)
        
        # تفاصيل الخطأ (اختياري)
        if details:
            details_group = QGroupBox("تفاصيل الخطأ")
            details_layout = QVBoxLayout(details_group)
            
            details_text = QTextEdit()
            details_text.setReadOnly(True)
            details_text.setPlainText(details)
            
            details_layout.addWidget(details_text)
        else:
            details_group = None
        
        # زر الإغلاق
        close_button = QPushButton("إغلاق")
        close_button.clicked.connect(self.accept)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addLayout(message_layout)
        if details_group:
            layout.addWidget(details_group)
        layout.addWidget(close_button, 0, Qt.AlignCenter)


class CodeComparisonDialog(BaseDialog):
    """نافذة مقارنة الكود قبل وبعد التعديل"""
    
    def __init__(self, file_path: str, original_code: str, modified_code: str, parent=None):
        super().__init__(parent)
        
        # ضبط خصائص النافذة
        self.setWindowTitle(f"مقارنة الكود - {os.path.basename(file_path)}")
        self.setMinimumSize(800, 600)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # معلومات الملف
        info_label = QLabel(f"الملف: {file_path}")
        
        # مقارنة الكود
        comparison_splitter = QSplitter(Qt.Horizontal)
        
        # الكود الأصلي
        original_widget = QWidget()
        original_layout = QVBoxLayout(original_widget)
        
        original_label = QLabel("الكود الأصلي:")
        original_label.setStyleSheet("font-weight: bold;")
        
        self.original_editor = QTextEdit()
        self.original_editor.setReadOnly(True)
        self.original_editor.setPlainText(original_code)
        self.original_editor.setFont(QFont("Courier New", 10))
        
        original_layout.addWidget(original_label)
        original_layout.addWidget(self.original_editor)
        
        # الكود المعدل
        modified_widget = QWidget()
        modified_layout = QVBoxLayout(modified_widget)
        
        modified_label = QLabel("الكود المعدل:")
        modified_label.setStyleSheet("font-weight: bold;")
        
        self.modified_editor = QTextEdit()
        self.modified_editor.setReadOnly(True)
        self.modified_editor.setPlainText(modified_code)
        self.modified_editor.setFont(QFont("Courier New", 10))
        
        modified_layout.addWidget(modified_label)
        modified_layout.addWidget(self.modified_editor)
        
        # إضافة المكونات إلى المقارنة
        comparison_splitter.addWidget(original_widget)
        comparison_splitter.addWidget(modified_widget)
        comparison_splitter.setSizes([400, 400])
        
        # إبراز الاختلافات
        self._highlight_differences()
        
        # زر الإغلاق
        close_button = QPushButton("إغلاق")
        close_button.clicked.connect(self.accept)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(info_label)
        layout.addWidget(comparison_splitter)
        layout.addWidget(close_button, 0, Qt.AlignCenter)
    
    def _highlight_differences(self):
        """إبراز الاختلافات بين الكود الأصلي والمعدل"""
        try:
            import difflib
            
            # استخراج الأسطر
            original_lines = self.original_editor.toPlainText().splitlines()
            modified_lines = self.modified_editor.toPlainText().splitlines()
            
            # إنشاء المقارنة
            matcher = difflib.SequenceMatcher(None, original_lines, modified_lines)
            
            # تهيئة التنسيقات
            delete_format = QTextCharFormat()
            delete_format.setBackground(QColor(255, 200, 200))  # لون أحمر فاتح للحذف
            
            insert_format = QTextCharFormat()
            insert_format.setBackground(QColor(200, 255, 200))  # لون أخضر فاتح للإضافة
            
            change_format = QTextCharFormat()
            change_format.setBackground(QColor(255, 255, 200))  # لون أصفر فاتح للتغيير
            
            # إعادة تعيين التنسيقات الحالية
            original_cursor = QTextCursor(self.original_editor.document())
            modified_cursor = QTextCursor(self.modified_editor.document())
            
            # تطبيق التنسيقات بناءً على عمليات المقارنة
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == 'replace':
                    # استبدال أسطر في الكود الأصلي
                    self._highlight_lines_range(self.original_editor, i1, i2, delete_format)
                    
                    # استبدال أسطر في الكود المعدل
                    self._highlight_lines_range(self.modified_editor, j1, j2, insert_format)
                
                elif tag == 'delete':
                    # حذف أسطر من الكود الأصلي
                    self._highlight_lines_range(self.original_editor, i1, i2, delete_format)
                
                elif tag == 'insert':
                    # إضافة أسطر في الكود المعدل
                    self._highlight_lines_range(self.modified_editor, j1, j2, insert_format)
                
                elif tag == 'equal':
                    # لا شيء لأن الأسطر متطابقة
                    pass
        
        except Exception as e:
            logger.error(f"خطأ في إبراز الاختلافات: {str(e)}")
    
    def _highlight_lines_range(self, editor, start_line, end_line, format):
        """إبراز نطاق من الأسطر بتنسيق معين"""
        try:
            if start_line < 0 or end_line > editor.document().blockCount():
                return
            
            cursor = QTextCursor(editor.document())
            
            for line_num in range(start_line, end_line):
                # الانتقال إلى بداية السطر
                cursor.setPosition(editor.document().findBlockByNumber(line_num).position())
                
                # الانتقال إلى نهاية السطر مع تحديد كل المحتوى
                cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                
                # تطبيق التنسيق على المحتوى المحدد
                cursor.setCharFormat(format)
        
        except Exception as e:
            logger.error(f"خطأ في إبراز نطاق الأسطر: {str(e)}")


class DependencyViewDialog(BaseDialog):
    """نافذة عرض الاعتمادات بين الملفات"""
    
    def __init__(self, project_model: ProjectModel, parent=None):
        super().__init__(parent)
        
        # ضبط خصائص النافذة
        self.setWindowTitle("عرض الاعتمادات")
        self.setMinimumSize(800, 600)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # مجموعة الخيارات
        options_group = QGroupBox("خيارات العرض")
        options_layout = QHBoxLayout(options_group)
        
        show_cycles_label = QLabel("عرض الدورات:")
        self.show_cycles_check = QCheckBox()
        self.show_cycles_check.setChecked(True)
        self.show_cycles_check.toggled.connect(self._update_view)
        
        options_layout.addWidget(show_cycles_label)
        options_layout.addWidget(self.show_cycles_check)
        options_layout.addStretch()
        
        # منطقة عرض الاعتمادات
        dependencies_group = QGroupBox("اعتمادات الملفات")
        dependencies_layout = QVBoxLayout(dependencies_group)
        
        self.dependencies_tree = QTreeWidget()
        self.dependencies_tree.setHeaderLabels(["الملف", "المعتمدين عليه"])
        self.dependencies_tree.setColumnCount(2)
        
        dependencies_layout.addWidget(self.dependencies_tree)
        
        # منطقة عرض الدورات
        cycles_group = QGroupBox("الدورات المكتشفة")
        cycles_layout = QVBoxLayout(cycles_group)
        
        self.cycles_list = QListWidget()
        
        cycles_layout.addWidget(self.cycles_list)
        
        # إضافة المكونات إلى عرض مقسم
        view_splitter = QSplitter(Qt.Vertical)
        view_splitter.addWidget(dependencies_group)
        view_splitter.addWidget(cycles_group)
        view_splitter.setSizes([400, 200])
        
        # زر الإغلاق
        close_button = QPushButton("إغلاق")
        close_button.clicked.connect(self.accept)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(options_group)
        layout.addWidget(view_splitter)
        layout.addWidget(close_button, 0, Qt.AlignCenter)
        
        # تعيين نموذج المشروع وتحديث العرض
        self.project_model = project_model
        self._update_view()
    
    def _update_view(self):
        """تحديث عرض الاعتمادات والدورات"""
        if not self.project_model:
            return
        
        # تحديث شجرة الاعتمادات
        self.dependencies_tree.clear()
        
        for file_path, dependencies in self.project_model.dependency_graph.adjacency():
            item = QTreeWidgetItem()
            item.setText(0, os.path.basename(file_path))
            item.setToolTip(0, file_path)
            
            # إضافة الملفات المعتمدة عليها
            dependent_files = [dep for dep in dependencies]
            if dependent_files:
                item.setText(1, str(len(dependent_files)))
                
                for dep_file in dependent_files:
                    child = QTreeWidgetItem()
                    child.setText(0, os.path.basename(dep_file))
                    child.setToolTip(0, dep_file)
                    item.addChild(child)
            else:
                item.setText(1, "0")
            
            self.dependencies_tree.addTopLevelItem(item)
        
        self.dependencies_tree.resizeColumnToContents(0)
        
        # تحديث قائمة الدورات
        self.cycles_list.clear()
        
        if self.show_cycles_check.isChecked():
            cycles = self.project_model.find_file_cycles()
            
            for cycle in cycles:
                # عرض الدورة كقائمة بمسارات الملفات
                cycle_str = " -> ".join([os.path.basename(file) for file in cycle])
                cycle_str += f" -> {os.path.basename(cycle[0])}"
                
                item = QListWidgetItem(cycle_str)
                item.setToolTip("\n".join(cycle))
                self.cycles_list.addItem(item)


class BatchAnalysisDialog(BaseDialog):
    """نافذة تحليل مجموعة من الملفات دفعة واحدة"""
    
    start_analysis = Signal(list, bool, bool)  # إشارة بدء التحليل (قائمة الملفات، استخدام AI، تحليل الأمان)
    
    def __init__(self, project_model: ProjectModel, parent=None):
        super().__init__(parent)
        
        # ضبط خصائص النافذة
        self.setWindowTitle("تحليل دفعة ملفات")
        self.setMinimumSize(700, 500)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # قائمة الملفات
        files_group = QGroupBox("الملفات المراد تحليلها")
        files_layout = QVBoxLayout(files_group)
        
        self.files_list = QListWidget()
        self.files_list.setSelectionMode(QListWidget.ExtendedSelection)
        
        # أزرار اختيار الملفات
        files_buttons_layout = QHBoxLayout()
        
        self.select_all_button = QPushButton("تحديد الكل")
        self.select_all_button.clicked.connect(self._select_all)
        
        self.deselect_all_button = QPushButton("إلغاء التحديد")
        self.deselect_all_button.clicked.connect(self._deselect_all)
        
        self.add_files_button = QPushButton("إضافة ملفات...")
        self.add_files_button.clicked.connect(self._add_files)
        
        files_buttons_layout.addWidget(self.select_all_button)
        files_buttons_layout.addWidget(self.deselect_all_button)
        files_buttons_layout.addStretch()
        files_buttons_layout.addWidget(self.add_files_button)
        
        files_layout.addWidget(self.files_list)
        files_layout.addLayout(files_buttons_layout)
        
        # خيارات التحليل
        options_group = QGroupBox("خيارات التحليل")
        options_layout = QVBoxLayout(options_group)
        
        self.use_ai_check = QCheckBox("استخدام الذكاء الاصطناعي في التحليل")
        self.use_ai_check.setChecked(True)
        
        self.analyze_security_check = QCheckBox("تحليل الثغرات الأمنية")
        self.analyze_security_check.setChecked(True)
        
        options_layout.addWidget(self.use_ai_check)
        options_layout.addWidget(self.analyze_security_check)
        
        # أزرار التحكم
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("بدء التحليل")
        self.start_button.clicked.connect(self._on_start)
        
        self.cancel_button = QPushButton("إلغاء")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.start_button)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(files_group)
        layout.addWidget(options_group)
        layout.addLayout(button_layout)
        
        # تعيين نموذج المشروع وتحديث قائمة الملفات
        self.project_model = project_model
        self._load_project_files()
    
    def _load_project_files(self):
        """تحميل ملفات المشروع إلى القائمة"""
        if not self.project_model:
            return
        
        # إضافة ملفات المشروع إلى القائمة
        for file_path in self.project_model.files:
            item = QListWidgetItem(os.path.basename(file_path))
            item.setToolTip(file_path)
            item.setData(Qt.UserRole, file_path)
            self.files_list.addItem(item)
    
    @Slot()
    def _select_all(self):
        """تحديد جميع الملفات"""
        for i in range(self.files_list.count()):
            self.files_list.item(i).setSelected(True)
    
    @Slot()
    def _deselect_all(self):
        """إلغاء تحديد جميع الملفات"""
        for i in range(self.files_list.count()):
            self.files_list.item(i).setSelected(False)
    
    @Slot()
    def _add_files(self):
        """إضافة ملفات إضافية للتحليل"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "اختيار ملفات للتحليل",
            "",
            "ملفات الكود (*.py *.js *.php *.dart *.html *.css *.json)"
        )
        
        for file_path in files:
            # التحقق من عدم وجود الملف مسبقاً
            exists = False
            for i in range(self.files_list.count()):
                if self.files_list.item(i).data(Qt.UserRole) == file_path:
                    exists = True
                    break
            
            if not exists:
                item = QListWidgetItem(os.path.basename(file_path))
                item.setToolTip(file_path)
                item.setData(Qt.UserRole, file_path)
                self.files_list.addItem(item)
    
    @Slot()
    def _on_start(self):
        """معالجة النقر على زر بدء التحليل"""
        selected_items = self.files_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار ملف واحد على الأقل للتحليل.")
            return
        
        # جمع مسارات الملفات المحددة
        selected_files = [item.data(Qt.UserRole) for item in selected_items]
        
        # قراءة خيارات التحليل
        use_ai = self.use_ai_check.isChecked()
        analyze_security = self.analyze_security_check.isChecked()
        
        # إرسال إشارة بدء التحليل
        self.start_analysis.emit(selected_files, use_ai, analyze_security)
        self.accept()


class AnalysisHistoryDialog(BaseDialog):
    """نافذة عرض سجل عمليات التحليل السابقة"""
    
    load_analysis = Signal(str)  # إشارة تحميل تحليل سابق (مسار الملف)
    
    def __init__(self, history_dir: str, parent=None):
        super().__init__(parent)
        
        self.history_dir = history_dir
        
        # ضبط خصائص النافذة
        self.setWindowTitle("سجل التحليل")
        self.setMinimumSize(600, 400)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # قائمة عمليات التحليل السابقة
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["التاريخ", "اسم المشروع", "عدد الملفات", "الإجراءات"])
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        
        # زر الإغلاق
        close_button = QPushButton("إغلاق")
        close_button.clicked.connect(self.reject)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(self.history_table)
        layout.addWidget(close_button, 0, Qt.AlignCenter)
        
        # تحميل سجل التحليل
        self._load_history()
    
    def _load_history(self):
        """تحميل سجل عمليات التحليل السابقة"""
        try:
            if not os.path.exists(self.history_dir):
                return
            
            # البحث عن ملفات التحليل
            analysis_files = []
            for file_name in os.listdir(self.history_dir):
                if file_name.endswith('.json'):
                    file_path = os.path.join(self.history_dir, file_name)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # استخراج المعلومات المطلوبة
                        timestamp = os.path.getmtime(file_path)
                        date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                        
                        project_name = data.get('project_name', "غير معروف")
                        total_files = data.get('total_files', 0)
                        
                        analysis_files.append({
                            "file_path": file_path,
                            "date": date_str,
                            "timestamp": timestamp,
                            "project_name": project_name,
                            "total_files": total_files
                        })
                    
                    except Exception as e:
                        logger.error(f"خطأ في قراءة ملف التحليل {file_path}: {str(e)}")
            
            # ترتيب الملفات حسب التاريخ (الأحدث أولاً)
            analysis_files.sort(key=lambda x: x["timestamp"], reverse=True)
            
            # ملء الجدول
            self.history_table.setRowCount(len(analysis_files))
            
            for i, analysis in enumerate(analysis_files):
                # خلية التاريخ
                self.history_table.setItem(i, 0, QTableWidgetItem(analysis["date"]))
                
                # خلية اسم المشروع
                self.history_table.setItem(i, 1, QTableWidgetItem(analysis["project_name"]))
                
                # خلية عدد الملفات
                self.history_table.setItem(i, 2, QTableWidgetItem(str(analysis["total_files"])))
                
                # خلية الإجراءات
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(0, 0, 0, 0)
                
                load_button = QPushButton("تحميل")
                load_button.setProperty("file_path", analysis["file_path"])
                load_button.clicked.connect(self._on_load_clicked)
                
                actions_layout.addWidget(load_button)
                
                self.history_table.setCellWidget(i, 3, actions_widget)
            
            self.history_table.resizeColumnsToContents()
        
        except Exception as e:
            logger.error(f"خطأ في تحميل سجل التحليل: {str(e)}")
    
    @Slot()
    def _on_load_clicked(self):
        """معالجة النقر على زر التحميل"""
        sender = self.sender()
        file_path = sender.property("file_path")
        
        if file_path:
            self.load_analysis.emit(file_path)
            self.accept()


class FileFilterDialog(BaseDialog):
    """نافذة تكوين فلترة الملفات عند التحليل"""
    
    apply_filters = Signal(list, list)  # إشارة تطبيق الفلاتر (قائمة الامتدادات، قائمة المجلدات المستثناة)
    
    def __init__(self, current_extensions: list = None, excluded_dirs: list = None, parent=None):
        super().__init__(parent)
        
        # ضبط خصائص النافذة
        self.setWindowTitle("فلترة الملفات")
        self.setMinimumWidth(500)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # مجموعة امتدادات الملفات
        extensions_group = QGroupBox("امتدادات الملفات المدعومة")
        extensions_layout = QVBoxLayout(extensions_group)
        
        # قائمة الامتدادات المدعومة
        self.extensions_list = QListWidget()
        
        all_extensions = [
            ".py", ".pyw", ".pyi",  # Python
            ".dart",  # Dart
            ".php", ".blade.php",  # PHP
            ".js", ".jsx", ".ts", ".tsx",  # JavaScript
            ".html", ".htm", ".css", ".scss", ".sass",  # Web
            ".json"  # JSON
        ]
        
        for ext in all_extensions:
            item = QListWidgetItem(ext)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            
            # تحديد العناصر المحددة مسبقاً
            if current_extensions and ext in current_extensions:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            
            self.extensions_list.addItem(item)
        
        extensions_layout.addWidget(self.extensions_list)
        
        # أزرار الامتدادات
        extensions_buttons_layout = QHBoxLayout()
        
        self.select_all_ext_button = QPushButton("تحديد الكل")
        self.select_all_ext_button.clicked.connect(self._select_all_extensions)
        
        self.deselect_all_ext_button = QPushButton("إلغاء التحديد")
        self.deselect_all_ext_button.clicked.connect(self._deselect_all_extensions)
        
        extensions_buttons_layout.addWidget(self.select_all_ext_button)
        extensions_buttons_layout.addWidget(self.deselect_all_ext_button)
        
        extensions_layout.addLayout(extensions_buttons_layout)
        
        # مجموعة المجلدات المستثناة
        excluded_group = QGroupBox("المجلدات المستثناة")
        excluded_layout = QVBoxLayout(excluded_group)
        
        # قائمة المجلدات المستثناة
        self.excluded_dirs_list = QListWidget()
        
        # إضافة المجلدات المستثناة الافتراضية
        default_excluded = [
            "__pycache__", ".git", ".svn", "node_modules", "venv", "env",
            ".DS_Store", ".idea", ".vscode", "dist", "build"
        ]
        
        # تجميع المجلدات المستثناة
        all_excluded = sorted(list(set(default_excluded + (excluded_dirs or []))))
        
        for dir_name in all_excluded:
            item = QListWidgetItem(dir_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            
            # تحديد العناصر المحددة مسبقاً
            if excluded_dirs and dir_name in excluded_dirs:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            
            self.excluded_dirs_list.addItem(item)
        
        excluded_layout.addWidget(self.excluded_dirs_list)
        
        # أزرار المجلدات المستثناة
        excluded_buttons_layout = QHBoxLayout()
        
        self.add_excluded_button = QPushButton("إضافة")
        self.add_excluded_button.clicked.connect(self._add_excluded_dir)
        
        self.remove_excluded_button = QPushButton("حذف")
        self.remove_excluded_button.clicked.connect(self._remove_excluded_dir)
        
        excluded_buttons_layout.addWidget(self.add_excluded_button)
        excluded_buttons_layout.addWidget(self.remove_excluded_button)
        
        excluded_layout.addLayout(excluded_buttons_layout)
        
        # أزرار التأكيد والإلغاء
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(extensions_group)
        layout.addWidget(excluded_group)
        layout.addWidget(button_box)
    
    @Slot()
    def _select_all_extensions(self):
        """تحديد جميع امتدادات الملفات"""
        for i in range(self.extensions_list.count()):
            self.extensions_list.item(i).setCheckState(Qt.Checked)
    
    @Slot()
    def _deselect_all_extensions(self):
        """إلغاء تحديد جميع امتدادات الملفات"""
        for i in range(self.extensions_list.count()):
            self.extensions_list.item(i).setCheckState(Qt.Unchecked)
    
    @Slot()
    def _add_excluded_dir(self):
        """إضافة مجلد مستثنى جديد"""
        # إنشاء نافذة حوار بسيطة لإدخال اسم المجلد
        dir_name, ok = QInputDialog.getText(
            self,
            "إضافة مجلد مستثنى",
            "اسم المجلد:"
        )
        
        if ok and dir_name:
            # التحقق من عدم وجود المجلد مسبقاً
            exists = False
            for i in range(self.excluded_dirs_list.count()):
                if self.excluded_dirs_list.item(i).text() == dir_name:
                    exists = True
                    break
            
            if not exists:
                item = QListWidgetItem(dir_name)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                self.excluded_dirs_list.addItem(item)
    
    @Slot()
    def _remove_excluded_dir(self):
        """حذف المجلد المستثنى المحدد"""
        selected_items = self.excluded_dirs_list.selectedItems()
        for item in selected_items:
            self.excluded_dirs_list.takeItem(self.excluded_dirs_list.row(item))
    
    def accept(self):
        """حفظ التغييرات عند الضغط على زر التأكيد"""
        # جمع امتدادات الملفات المحددة
        selected_extensions = []
        for i in range(self.extensions_list.count()):
            item = self.extensions_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_extensions.append(item.text())
        
        # جمع المجلدات المستثناة المحددة
        selected_excluded_dirs = []
        for i in range(self.excluded_dirs_list.count()):
            item = self.excluded_dirs_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_excluded_dirs.append(item.text())
        
        # إرسال إشارة بالفلاتر المحددة
        self.apply_filters.emit(selected_extensions, selected_excluded_dirs)
        
        super().accept()


class LanguageSettingsDialog(BaseDialog):
    """نافذة تكوين إعدادات خاصة بلغات البرمجة المختلفة"""
    
    apply_settings = Signal(dict)  # إشارة تطبيق الإعدادات (قاموس الإعدادات)
    
    def __init__(self, current_settings: dict = None, parent=None):
        super().__init__(parent)
        
        self.current_settings = current_settings or {}
        
        # ضبط خصائص النافذة
        self.setWindowTitle("إعدادات لغات البرمجة")
        self.setMinimumSize(600, 400)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # تبويبات اللغات
        self.tabs = QTabWidget()
        
        # إضافة تبويب لكل لغة
        self.tabs.addTab(self._create_python_tab(), "Python")
        self.tabs.addTab(self._create_php_tab(), "PHP")
        self.tabs.addTab(self._create_javascript_tab(), "JavaScript")
        self.tabs.addTab(self._create_dart_tab(), "Dart")
        
        # أزرار التأكيد والإلغاء
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(self.tabs)
        layout.addWidget(button_box)
    
    def _create_python_tab(self) -> QWidget:
        """إنشاء تبويب إعدادات Python"""
        python_tab = QWidget()
        python_layout = QVBoxLayout(python_tab)
        
        # مجموعة معايير الجودة
        quality_group = QGroupBox("معايير الجودة")
        quality_layout = QFormLayout(quality_group)
        
        # عدد أسطر الدالة
        self.python_func_lines = QSpinBox()
        self.python_func_lines.setRange(10, 200)
        self.python_func_lines.setValue(self.current_settings.get("python_max_func_lines", 50))
        
        # عدد المعاملات
        self.python_params = QSpinBox()
        self.python_params.setRange(1, 20)
        self.python_params.setValue(self.current_settings.get("python_max_params", 5))
        
        # التعقيد الدوري
        self.python_complexity = QSpinBox()
        self.python_complexity.setRange(1, 50)
        self.python_complexity.setValue(self.current_settings.get("python_max_complexity", 10))
        
        quality_layout.addRow("الحد الأقصى لعدد أسطر الدالة:", self.python_func_lines)
        quality_layout.addRow("الحد الأقصى لعدد المعاملات:", self.python_params)
        quality_layout.addRow("الحد الأقصى للتعقيد الدوري:", self.python_complexity)
        
        # مجموعة الفحوصات
        checks_group = QGroupBox("الفحوصات")
        checks_layout = QVBoxLayout(checks_group)
        
        self.python_check_docstrings = QCheckBox("التحقق من توثيق الدوال والفئات")
        self.python_check_docstrings.setChecked(self.current_settings.get("python_check_docstrings", True))
        
        self.python_check_typing = QCheckBox("التحقق من annotation أنواع البيانات")
        self.python_check_typing.setChecked(self.current_settings.get("python_check_typing", True))
        
        self.python_check_imports = QCheckBox("التحقق من الاستيرادات غير المستخدمة")
        self.python_check_imports.setChecked(self.current_settings.get("python_check_imports", True))
        
        checks_layout.addWidget(self.python_check_docstrings)
        checks_layout.addWidget(self.python_check_typing)
        checks_layout.addWidget(self.python_check_imports)
        
        # إضافة المجموعات إلى التبويب
        python_layout.addWidget(quality_group)
        python_layout.addWidget(checks_group)
        python_layout.addStretch()
        
        return python_tab
    
    def _create_php_tab(self) -> QWidget:
        """إنشاء تبويب إعدادات PHP"""
        php_tab = QWidget()
        php_layout = QVBoxLayout(php_tab)
    
        # مجموعة معايير الأمان
        security_group = QGroupBox("معايير الأمان")
        security_layout = QVBoxLayout(security_group)
    
        self.php_check_sql_injection = QCheckBox("فحص حقن SQL")
        self.php_check_sql_injection.setChecked(self.current_settings.get("php_check_sql_injection", True))
        security_layout.addWidget(self.php_check_sql_injection)
    
        self.php_check_xss = QCheckBox("فحص XSS")
        self.php_check_xss.setChecked(self.current_settings.get("php_check_xss", True))
        security_layout.addWidget(self.php_check_xss)
    
        self.php_check_csrf = QCheckBox("فحص CSRF")
        self.php_check_csrf.setChecked(self.current_settings.get("php_check_csrf", True))
        security_layout.addWidget(self.php_check_csrf)
    
        self.php_check_file_inclusion = QCheckBox("فحص تضمين الملفات")
        self.php_check_file_inclusion.setChecked(self.current_settings.get("php_check_file_inclusion", True))
        security_layout.addWidget(self.php_check_file_inclusion)
    
        # مجموعة إعدادات PHP العامة
        general_settings_group = QGroupBox("إعدادات PHP العامة")
        general_settings_layout = QVBoxLayout(general_settings_group)
    
        self.php_enable_error_reporting = QCheckBox("تفعيل تقرير الأخطاء")
        self.php_enable_error_reporting.setChecked(self.current_settings.get("php_enable_error_reporting", False))
        general_settings_layout.addWidget(self.php_enable_error_reporting)
    
        self.php_display_errors = QCheckBox("عرض الأخطاء")
        self.php_display_errors.setChecked(self.current_settings.get("php_display_errors", False))
        general_settings_layout.addWidget(self.php_display_errors)
    
        self.php_log_errors = QCheckBox("تسجيل الأخطاء")
        self.php_log_errors.setChecked(self.current_settings.get("php_log_errors", True))
        general_settings_layout.addWidget(self.php_log_errors)
    
        # إضافة المجموعات إلى التبويب
        php_layout.addWidget(security_group)
        php_layout.addWidget(general_settings_group)
        php_layout.addStretch()
        
        return php_tab
    
    def _create_javascript_tab(self) -> QWidget:
        """إنشاء تبويب إعدادات JavaScript"""
        js_tab = QWidget()
        js_layout = QVBoxLayout(js_tab)
        
        # مجموعة معايير الجودة
        quality_group = QGroupBox("معايير الجودة")
        quality_layout = QFormLayout(quality_group)
        
        # عدد أسطر الدالة
        self.js_func_lines = QSpinBox()
        self.js_func_lines.setRange(10, 200)
        self.js_func_lines.setValue(self.current_settings.get("js_max_func_lines", 50))
        
        # عمق التداخل
        self.js_nesting_depth = QSpinBox()
        self.js_nesting_depth.setRange(1, 10)
        self.js_nesting_depth.setValue(self.current_settings.get("js_max_nesting_depth", 4))
        
        quality_layout.addRow("الحد الأقصى لعدد أسطر الدالة:", self.js_func_lines)
        quality_layout.addRow("الحد الأقصى لعمق التداخل:", self.js_nesting_depth)
        
        # مجموعة الفحوصات
        checks_group = QGroupBox("الفحوصات")
        checks_layout = QVBoxLayout(checks_group)
        
        self.js_check_eslint = QCheckBox("استخدام قواعد ESLint")
        self.js_check_eslint.setChecked(self.current_settings.get("js_check_eslint", True))
        
        self.js_check_unused = QCheckBox("التحقق من المتغيرات غير المستخدمة")
        self.js_check_unused.setChecked(self.current_settings.get("js_check_unused", True))
        
        self.js_check_console_log = QCheckBox("التحقق من وجود console.log")
        self.js_check_console_log.setChecked(self.current_settings.get("js_check_console_log", True))
        
        checks_layout.addWidget(self.js_check_eslint)
        checks_layout.addWidget(self.js_check_unused)
        checks_layout.addWidget(self.js_check_console_log)
        
        # إضافة المجموعات إلى التبويب
        js_layout.addWidget(quality_group)
        js_layout.addWidget(checks_group)
        js_layout.addStretch()
        
        return js_tab
    
    def _create_dart_tab(self) -> QWidget:
        """إنشاء تبويب إعدادات Dart"""
        dart_tab = QWidget()
        dart_layout = QVBoxLayout(dart_tab)
        
        # مجموعة معايير الجودة
        quality_group = QGroupBox("معايير الجودة")
        quality_layout = QFormLayout(quality_group)
        
        # عدد أسطر الكلاس
        self.dart_class_lines = QSpinBox()
        self.dart_class_lines.setRange(50, 1000)
        self.dart_class_lines.setValue(self.current_settings.get("dart_max_class_lines", 300))
        
        # عدد أسطر الدالة
        self.dart_func_lines = QSpinBox()
        self.dart_func_lines.setRange(10, 200)
        self.dart_func_lines.setValue(self.current_settings.get("dart_max_func_lines", 50))
        
        quality_layout.addRow("الحد الأقصى لعدد أسطر الكلاس:", self.dart_class_lines)
        quality_layout.addRow("الحد الأقصى لعدد أسطر الدالة:", self.dart_func_lines)
        
        # مجموعة الفحوصات
        checks_group = QGroupBox("الفحوصات")
        checks_layout = QVBoxLayout(checks_group)
        
        self.dart_check_lint = QCheckBox("استخدام Dart Lint")
        self.dart_check_lint.setChecked(self.current_settings.get("dart_check_lint", True))
        
        self.dart_check_formatting = QCheckBox("التحقق من تنسيق الكود")
        self.dart_check_formatting.setChecked(self.current_settings.get("dart_check_formatting", True))
        
        self.dart_check_state_management = QCheckBox("التحقق من إدارة الحالة")
        self.dart_check_state_management.setChecked(self.current_settings.get("dart_check_state_management", True))
        
        checks_layout.addWidget(self.dart_check_lint)
        checks_layout.addWidget(self.dart_check_formatting)
        checks_layout.addWidget(self.dart_check_state_management)
        
        # إضافة المجموعات إلى التبويب
        dart_layout.addWidget(quality_group)
        dart_layout.addWidget(checks_group)
        dart_layout.addStretch()
        
        return dart_tab
    
    def accept(self):
        """حفظ الإعدادات عند الضغط على زر التأكيد"""
        # جمع إعدادات Python
        self.current_settings["python_max_func_lines"] = self.python_func_lines.value()
        self.current_settings["python_max_params"] = self.python_params.value()
        self.current_settings["python_max_complexity"] = self.python_complexity.value()
        self.current_settings["python_check_docstrings"] = self.python_check_docstrings.isChecked()
        self.current_settings["python_check_typing"] = self.python_check_typing.isChecked()
        self.current_settings["python_check_imports"] = self.python_check_imports.isChecked()
        
        # جمع إعدادات PHP
        self.current_settings["php_check_sql_injection"] = self.php_check_sql_injection.isChecked()
        self.current_settings["php_check_xss"] = self.php_check_xss.isChecked()
        self.current_settings["php_check_csrf"] = self.php_check_csrf.isChecked()
        self.current_settings["php_check_file_inclusion"] = self.php_check_file_inclusion.isChecked()
        self.current_settings["php_enable_error_reporting"] = self.php_enable_error_reporting.isChecked()
        self.current_settings["php_display_errors"] = self.php_display_errors.isChecked()
        self.current_settings["php_log_errors"] = self.php_log_errors.isChecked()
        
        # جمع إعدادات JavaScript
        self.current_settings["js_max_func_lines"] = self.js_func_lines.value()
        self.current_settings["js_max_nesting_depth"] = self.js_nesting_depth.value()
        self.current_settings["js_check_eslint"] = self.js_check_eslint.isChecked()
        self.current_settings["js_check_unused"] = self.js_check_unused.isChecked()
        self.current_settings["js_check_console_log"] = self.js_check_console_log.isChecked()
        
        # جمع إعدادات Dart
        self.current_settings["dart_max_class_lines"] = self.dart_class_lines.value()
        self.current_settings["dart_max_func_lines"] = self.dart_func_lines.value()
        self.current_settings["dart_check_lint"] = self.dart_check_lint.isChecked()
        self.current_settings["dart_check_formatting"] = self.dart_check_formatting.isChecked()
        self.current_settings["dart_check_state_management"] = self.dart_check_state_management.isChecked()
        
        # إرسال إشارة بالإعدادات المحدثة
        self.apply_settings.emit(self.current_settings)
        
        super().accept()


class ProjectSummaryDialog(BaseDialog):
    """نافذة عرض ملخص المشروع"""
    
    def __init__(self, project_model: ProjectModel, parent=None):
        super().__init__(parent)
        
        # ضبط خصائص النافذة
        self.setWindowTitle("ملخص المشروع")
        self.setMinimumSize(700, 500)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # معلومات المشروع
        info_group = QGroupBox("معلومات المشروع")
        info_layout = QFormLayout(info_group)
        
        project_dir = project_model.project_dir
        project_name = os.path.basename(project_dir)
        project_type = project_model.project_type
        total_files = len(project_model.files)
        
        project_name_label = QLabel(project_name)
        project_name_label.setStyleSheet("font-weight: bold;")
        
        project_dir_label = QLabel(project_dir)
        project_type_label = QLabel(project_type)
        total_files_label = QLabel(str(total_files))
        
        info_layout.addRow("اسم المشروع:", project_name_label)
        info_layout.addRow("المسار:", project_dir_label)
        info_layout.addRow("النوع:", project_type_label)
        info_layout.addRow("عدد الملفات:", total_files_label)
        
        # إحصائيات اللغات
        languages_group = QGroupBox("إحصائيات اللغات")
        languages_layout = QVBoxLayout(languages_group)
        
        self.languages_table = QTableWidget()
        self.languages_table.setColumnCount(2)
        self.languages_table.setHorizontalHeaderLabels(["اللغة", "عدد الملفات"])
        self.languages_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.languages_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.languages_table.horizontalHeader().setStretchLastSection(True)
        
        # إحصاء الملفات حسب اللغة
        language_counts = {}
        for file_path, code_file in project_model.files.items():
            lang = code_file.language or "أخرى"
            language_counts[lang] = language_counts.get(lang, 0) + 1
        
        # ملء الجدول
        self.languages_table.setRowCount(len(language_counts))
        for i, (lang, count) in enumerate(sorted(language_counts.items())):
            self.languages_table.setItem(i, 0, QTableWidgetItem(lang))
            self.languages_table.setItem(i, 1, QTableWidgetItem(str(count)))
        
        languages_layout.addWidget(self.languages_table)
        
        # ملخص الكيانات
        entities_group = QGroupBox("ملخص الكيانات")
        entities_layout = QVBoxLayout(entities_group)
        
        self.entities_tree = QTreeWidget()
        self.entities_tree.setHeaderLabels(["النوع", "العدد"])
        self.entities_tree.setColumnCount(2)
        
        # إحصاء الكيانات
        entity_counts = {}
        for file_path, code_file in project_model.files.items():
            for entity in code_file.entities:
                entity_type = entity.type
                entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
                
                # إحصاء الكيانات الفرعية
                for child in entity.children:
                    child_type = child.type
                    child_key = f"{entity_type}.{child_type}"
                    entity_counts[child_key] = entity_counts.get(child_key, 0) + 1
        
        # ملء الشجرة
        for entity_type, count in sorted(entity_counts.items()):
            if "." in entity_type:
                # كيان فرعي
                parent_type, child_type = entity_type.split(".")
                parent_items = self.entities_tree.findItems(parent_type, Qt.MatchExactly, 0)
                
                if parent_items:
                    parent_item = parent_items[0]
                    child_item = QTreeWidgetItem(parent_item)
                    child_item.setText(0, child_type)
                    child_item.setText(1, str(count))
            else:
                # كيان رئيسي
                item = QTreeWidgetItem(self.entities_tree)
                item.setText(0, entity_type)
                item.setText(1, str(count))
        
        self.entities_tree.expandAll()
        entities_layout.addWidget(self.entities_tree)
        
        # زر الإغلاق
        close_button = QPushButton("إغلاق")
        close_button.clicked.connect(self.accept)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(info_group)
        layout.addWidget(languages_group)
        layout.addWidget(entities_group)
        layout.addWidget(close_button, 0, Qt.AlignCenter)


class ProjectHealthDialog(BaseDialog):
    """نافذة عرض صحة المشروع وجودة الكود"""
    
    def __init__(self, project_model: ProjectModel, analysis_results: Dict[str, Any], parent=None):
        super().__init__(parent)
        
        # ضبط خصائص النافذة
        self.setWindowTitle("صحة المشروع")
        self.setMinimumSize(700, 500)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # ملخص الصحة
        health_group = QGroupBox("ملخص صحة المشروع")
        health_layout = QVBoxLayout(health_group)
        
        # حساب درجة الصحة
        total_issues = len(analysis_results.get('issues', []))
        total_security_issues = len(analysis_results.get('security_issues', []))
        total_files = analysis_results.get('total_files', len(project_model.files))
        
        if total_files > 0:
            health_score = 100 - min(100, (total_issues + total_security_issues * 2) * 100 / (total_files * 5))
        else:
            health_score = 0
        
        # عرض درجة الصحة
        health_score_layout = QHBoxLayout()
        
        health_score_label = QLabel(f"درجة صحة المشروع: {health_score:.1f}%")
        health_score_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        
        health_score_progress = QProgressBar()
        health_score_progress.setRange(0, 100)
        health_score_progress.setValue(int(health_score))
        health_score_progress.setTextVisible(False)
        
        # تحديد لون شريط التقدم حسب درجة الصحة
        if health_score >= 80:
            health_score_progress.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
        elif health_score >= 60:
            health_score_progress.setStyleSheet("QProgressBar::chunk { background-color: #FFC107; }")
        else:
            health_score_progress.setStyleSheet("QProgressBar::chunk { background-color: #F44336; }")
        
        health_score_layout.addWidget(health_score_label)
        health_score_layout.addWidget(health_score_progress)
        
        health_layout.addLayout(health_score_layout)
        
        # ملخص المشاكل
        issues_summary_layout = QHBoxLayout()
        
        # إحصاء المشاكل حسب الخطورة
        high_issues = sum(1 for issue in analysis_results.get('issues', []) if issue.get('severity') == 'عالية')
        medium_issues = sum(1 for issue in analysis_results.get('issues', []) if issue.get('severity') == 'متوسطة')
        low_issues = sum(1 for issue in analysis_results.get('issues', []) if issue.get('severity') == 'منخفضة')
        
        high_issues_label = QLabel(f"مشاكل عالية الخطورة: {high_issues}")
        high_issues_label.setStyleSheet("color: #F44336;")
        
        medium_issues_label = QLabel(f"مشاكل متوسطة الخطورة: {medium_issues}")
        medium_issues_label.setStyleSheet("color: #FFC107;")
        
        low_issues_label = QLabel(f"مشاكل منخفضة الخطورة: {low_issues}")
        low_issues_label.setStyleSheet("color: #4CAF50;")
        
        issues_summary_layout.addWidget(high_issues_label)
        issues_summary_layout.addWidget(medium_issues_label)
        issues_summary_layout.addWidget(low_issues_label)
        
        health_layout.addLayout(issues_summary_layout)
        
        # ملخص الثغرات الأمنية
        security_summary_layout = QHBoxLayout()
        
        # إحصاء الثغرات حسب النوع
        sql_injection = sum(1 for issue in analysis_results.get('security_issues', []) if issue.get('type') == 'SQL Injection')
        xss = sum(1 for issue in analysis_results.get('security_issues', []) if issue.get('type') == 'XSS')
        csrf = sum(1 for issue in analysis_results.get('security_issues', []) if issue.get('type') == 'CSRF')
        
        sql_injection_label = QLabel(f"حقن SQL: {sql_injection}")
        xss_label = QLabel(f"XSS: {xss}")
        csrf_label = QLabel(f"CSRF: {csrf}")
        
        security_summary_layout.addWidget(sql_injection_label)
        security_summary_layout.addWidget(xss_label)
        security_summary_layout.addWidget(csrf_label)
        
        health_layout.addLayout(security_summary_layout)
        
        # توصيات تحسين الكود
        recommendations_group = QGroupBox("توصيات لتحسين جودة الكود")
        recommendations_layout = QVBoxLayout(recommendations_group)
        
        self.recommendations_list = QListWidget()
        
        # إضافة التوصيات
        recommendations = []
        
        if high_issues > 0:
            recommendations.append("معالجة المشاكل عالية الخطورة بأسرع وقت ممكن")
        
        if total_security_issues > 0:
            recommendations.append("إجراء مراجعة أمنية شاملة للكود")
        
        if any(cycle for cycle in project_model.find_file_cycles()):
            recommendations.append("إزالة الدورات بين الملفات لتحسين بنية المشروع")
        
        # إضافة توصيات عامة
        general_recommendations = [
            "تطبيق مبادئ SOLID في تصميم البرمجيات",
            "استخدام أنماط التصميم المناسبة",
            "إضافة اختبارات وحدة للوظائف الأساسية",
            "توثيق الكود بشكل أفضل",
            "تقليل التعقيد في الدوال الطويلة"
        ]
        
        recommendations.extend(general_recommendations)
        
        for recommendation in recommendations:
            self.recommendations_list.addItem(recommendation)
        
        recommendations_layout.addWidget(self.recommendations_list)
        
        # زر الإغلاق
        close_button = QPushButton("إغلاق")
        close_button.clicked.connect(self.accept)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(health_group)
        layout.addWidget(recommendations_group)
        layout.addWidget(close_button, 0, Qt.AlignCenter)


class FindReplaceDialog(BaseDialog):
    """نافذة البحث والاستبدال في الكود"""
    
    find_text = Signal(str, bool, bool)  # إشارة البحث (النص، حساسية الحالة، بحث كامل)
    replace_text = Signal(str, str, bool, bool)  # إشارة الاستبدال (النص القديم، النص الجديد، حساسية الحالة، استبدال الكل)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ضبط خصائص النافذة
        self.setWindowTitle("بحث واستبدال")
        self.setMinimumWidth(400)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # مجموعة البحث
        find_group = QGroupBox("بحث")
        find_layout = QGridLayout(find_group)
        
        find_label = QLabel("البحث عن:")
        self.find_edit = QLineEdit()
        
        self.case_sensitive_check = QCheckBox("حساسية حالة الأحرف")
        self.whole_word_check = QCheckBox("كلمة كاملة فقط")
        
        self.find_button = QPushButton("بحث")
        self.find_button.clicked.connect(self._on_find)
        
        find_layout.addWidget(find_label, 0, 0)
        find_layout.addWidget(self.find_edit, 0, 1)
        find_layout.addWidget(self.case_sensitive_check, 1, 0)
        find_layout.addWidget(self.whole_word_check, 1, 1)
        find_layout.addWidget(self.find_button, 2, 1)
        
        # مجموعة الاستبدال
        replace_group = QGroupBox("استبدال")
        replace_layout = QGridLayout(replace_group)
        
        replace_label = QLabel("استبدال بـ:")
        self.replace_edit = QLineEdit()
        
        self.replace_button = QPushButton("استبدال")
        self.replace_button.clicked.connect(self._on_replace)
        
        self.replace_all_button = QPushButton("استبدال الكل")
        self.replace_all_button.clicked.connect(self._on_replace_all)
        
        replace_layout.addWidget(replace_label, 0, 0)
        replace_layout.addWidget(self.replace_edit, 0, 1)
        replace_layout.addWidget(self.replace_button, 1, 0)
        replace_layout.addWidget(self.replace_all_button, 1, 1)
        
        # زر الإغلاق
        close_button = QPushButton("إغلاق")
        close_button.clicked.connect(self.reject)
        
        # إضافة العناصر إلى التخطيط الرئيسي
        layout.addWidget(find_group)
        layout.addWidget(replace_group)
        layout.addWidget(close_button, 0, Qt.AlignCenter)
        
        # تفعيل مفاتيح الاختصارات
        self.find_edit.textChanged.connect(self._update_buttons)
        self._update_buttons()
    
    def _update_buttons(self):
        """تحديث حالة الأزرار"""
        has_text = bool(self.find_edit.text())
        self.find_button.setEnabled(has_text)
        self.replace_button.setEnabled(has_text)
        self.replace_all_button.setEnabled(has_text)
    
    @Slot()
    def _on_find(self):
        """معالجة النقر على زر البحث"""
        find_text = self.find_edit.text()
        if find_text:
            case_sensitive = self.case_sensitive_check.isChecked()
            whole_word = self.whole_word_check.isChecked()
            self.find_text.emit(find_text, case_sensitive, whole_word)
    
    @Slot()
    def _on_replace(self):
        """معالجة النقر على زر الاستبدال"""
        find_text = self.find_edit.text()
        replace_text = self.replace_edit.text()
        if find_text:
            case_sensitive = self.case_sensitive_check.isChecked()
            self.replace_text.emit(find_text, replace_text, case_sensitive, False)
    
class CodeSearchDialog(BaseDialog):
    """نافذة البحث في الشيفرة البرمجية"""
    
    search_requested = Signal(str, list, bool, bool)  # إشارة طلب البحث (نص البحث، قائمة الملفات، حساسية الحالة، استخدام التعابير المنتظمة)
    
    def __init__(self, project_model: ProjectModel, parent=None):
        super().__init__(parent)
        
        self.project_model = project_model
        
        # ضبط خصائص النافذة
        self.setWindowTitle("البحث في الشيفرة البرمجية")
        self.setMinimumSize(600, 400)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # مجموعة البحث
        search_group = QGroupBox("معايير البحث")
        search_layout = QGridLayout(search_group)
        
        search_label = QLabel("نص البحث:")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("أدخل نص البحث أو تعبير منتظم...")
        
        self.case_sensitive_check = QCheckBox("حساسية حالة الأحرف")
        self.regex_check = QCheckBox("استخدام التعابير المنتظمة")
        
        self.search_button = QPushButton("بحث")
        self.search_button.clicked.connect(self._on_search)
        
        search_layout.addWidget(search_label, 0, 0)
        search_layout.addWidget(self.search_edit, 0, 1, 1, 2)
        search_layout.addWidget(self.case_sensitive_check, 1, 0)
        search_layout.addWidget(self.regex_check, 1, 1)
        search_layout.addWidget(self.search_button, 1, 2)
        
        # مجموعة المجلدات والملفات
        files_group = QGroupBox("البحث في")
        files_layout = QVBoxLayout(files_group)
        
        self.all_files_radio = QRadioButton("جميع ملفات المشروع")
        self.all_files_radio.setChecked(True)
        
        self.selected_files_radio = QRadioButton("الملفات المحددة")
        self.selected_files_radio.toggled.connect(self._on_files_selection_changed)
        
        self.files_list = QListWidget()
        self.files_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.files_list.setEnabled(False)
        
        # إضافة ملفات المشروع إلى القائمة
        if self.project_model:
            for file_path in sorted(self.project_model.files.keys()):
                item = QListWidgetItem(file_path)
                item.setData(Qt.UserRole, file_path)
                self.files_list.addItem(item)
        
        files_selection_layout = QHBoxLayout()
        self.select_all_button = QPushButton("تحديد الكل")
        self.select_all_button.clicked.connect(self._select_all_files)
        self.select_all_button.setEnabled(False)
        
        self.deselect_all_button = QPushButton("إلغاء التحديد")
        self.deselect_all_button.clicked.connect(self._deselect_all_files)
        self.deselect_all_button.setEnabled(False)
        
        files_selection_layout.addWidget(self.select_all_button)
        files_selection_layout.addWidget(self.deselect_all_button)
        
        files_layout.addWidget(self.all_files_radio)
        files_layout.addWidget(self.selected_files_radio)
        files_layout.addWidget(self.files_list)
        files_layout.addLayout(files_selection_layout)
        
        # أزرار التحكم
        buttons_layout = QHBoxLayout()
        
        close_button = QPushButton("إغلاق")
        close_button.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(close_button)
        
        # إضافة المكونات إلى التخطيط الرئيسي
        layout.addWidget(search_group)
        layout.addWidget(files_group)
        layout.addLayout(buttons_layout)
        
        # تفعيل مفاتيح الاختصارات
        self.search_edit.textChanged.connect(self._update_buttons)
        self._update_buttons()
    
    def _update_buttons(self):
        """تحديث حالة الأزرار"""
        has_text = bool(self.search_edit.text())
        self.search_button.setEnabled(has_text)
    
    @Slot(bool)
    def _on_files_selection_changed(self, enabled: bool):
        """معالجة تغيير خيار تحديد الملفات"""
        self.files_list.setEnabled(enabled)
        self.select_all_button.setEnabled(enabled)
        self.deselect_all_button.setEnabled(enabled)
    
    @Slot()
    def _select_all_files(self):
        """تحديد جميع الملفات"""
        for i in range(self.files_list.count()):
            self.files_list.item(i).setSelected(True)
    
    @Slot()
    def _deselect_all_files(self):
        """إلغاء تحديد جميع الملفات"""
        for i in range(self.files_list.count()):
            self.files_list.item(i).setSelected(False)
    
    @Slot()
    def _on_search(self):
        """معالجة النقر على زر البحث"""
        search_text = self.search_edit.text()
        if not search_text:
            return
        
        # تحديد الملفات للبحث
        files_to_search = []
        if self.selected_files_radio.isChecked():
            selected_items = self.files_list.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "تنبيه", "يرجى تحديد ملف واحد على الأقل للبحث فيه.")
                return
            
            files_to_search = [item.data(Qt.UserRole) for item in selected_items]
        else:
            # جميع الملفات
            files_to_search = list(self.project_model.files.keys()) if self.project_model else []
        
        # إرسال إشارة طلب البحث
        case_sensitive = self.case_sensitive_check.isChecked()
        use_regex = self.regex_check.isChecked()
        self.search_requested.emit(search_text, files_to_search, case_sensitive, use_regex)
        self.accept()


class SearchResultsDialog(BaseDialog):
    """نافذة عرض نتائج البحث"""
    
    result_selected = Signal(str, int)  # إشارة اختيار نتيجة (مسار الملف، رقم السطر)
    
    def __init__(self, search_text: str, results: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        
        # ضبط خصائص النافذة
        self.setWindowTitle("نتائج البحث")
        self.setMinimumSize(700, 500)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # معلومات البحث
        info_layout = QHBoxLayout()
        
        search_label = QLabel(f"نتائج البحث عن: <b>{search_text}</b>")
        results_count_label = QLabel(f"عدد النتائج: {len(results)}")
        
        info_layout.addWidget(search_label)
        info_layout.addStretch()
        info_layout.addWidget(results_count_label)
        
        # قائمة النتائج
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["الملف", "السطر", "النص"])
        self.results_tree.setColumnCount(3)
        self.results_tree.setAlternatingRowColors(True)
        
        # تنظيم النتائج حسب الملف
        grouped_results = {}
        for result in results:
            file_path = result.get('file', '')
            if file_path not in grouped_results:
                grouped_results[file_path] = []
            
            grouped_results[file_path].append(result)
        
        # إضافة النتائج إلى الشجرة
        for file_path, file_results in grouped_results.items():
            file_item = QTreeWidgetItem(self.results_tree)
            file_item.setText(0, os.path.basename(file_path))
            file_item.setToolTip(0, file_path)
            file_item.setData(0, Qt.UserRole, file_path)
            file_item.setText(1, f"{len(file_results)} نتيجة")
            
            for result in file_results:
                result_item = QTreeWidgetItem(file_item)
                result_item.setText(0, "")
                result_item.setText(1, str(result.get('line', 0)))
                result_item.setText(2, result.get('text', '').strip())
                result_item.setData(0, Qt.UserRole, result)
            
            file_item.setExpanded(True)
        
        self.results_tree.resizeColumnToContents(0)
        self.results_tree.resizeColumnToContents(1)
        
        # ربط حدث النقر المزدوج
        self.results_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        # أزرار التحكم
        buttons_layout = QHBoxLayout()
        
        export_button = QPushButton("تصدير النتائج")
        export_button.clicked.connect(self._on_export_results)
        
        close_button = QPushButton("إغلاق")
        close_button.clicked.connect(self.accept)
        
        buttons_layout.addWidget(export_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(close_button)
        
        # إضافة المكونات إلى التخطيط الرئيسي
        layout.addLayout(info_layout)
        layout.addWidget(self.results_tree)
        layout.addLayout(buttons_layout)
        
        # المتغيرات الداخلية
        self.search_text = search_text
        self.results = results
    
    @Slot(QTreeWidgetItem, int)
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """معالجة النقر المزدوج على عنصر"""
        # التحقق من أن العنصر هو نتيجة وليس ملف
        parent = item.parent()
        if parent:
            # عنصر نتيجة
            result = item.data(0, Qt.UserRole)
            if result:
                file_path = result.get('file', '')
                line = result.get('line', 0)
                if file_path and line > 0:
                    self.result_selected.emit(file_path, line)
        else:
            # عنصر ملف - توسيع/طي الفرع
            item.setExpanded(not item.isExpanded())
    
    @Slot()
    def _on_export_results(self):
        """تصدير نتائج البحث إلى ملف"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "تصدير نتائج البحث",
                "",
                "ملفات نصية (*.txt);;ملفات CSV (*.csv)"
            )
            
            if not file_path:
                return
            
            # تنسيق النتائج
            output = f"نتائج البحث عن: {self.search_text}\n"
            output += f"عدد النتائج: {len(self.results)}\n\n"
            
            for result in self.results:
                file_path = result.get('file', '')
                line = result.get('line', 0)
                text = result.get('text', '').strip()
                
                output += f"الملف: {file_path}\n"
                output += f"السطر: {line}\n"
                output += f"النص: {text}\n"
                output += "-" * 50 + "\n"
            
            # حفظ الملف
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(output)
            
            QMessageBox.information(self, "تم التصدير", f"تم تصدير نتائج البحث إلى:\n{file_path}")
        
        except Exception as e:
            self.show_error("خطأ", "حدث خطأ أثناء تصدير النتائج", str(e))


class LogViewerDialog(BaseDialog):
    """نافذة عرض سجلات التطبيق"""
    
    def __init__(self, log_file: str = None, parent=None):
        super().__init__(parent)
        
        # ضبط خصائص النافذة
        self.setWindowTitle("عارض السجلات")
        self.setMinimumSize(800, 600)
        
        # إعداد التخطيط
        layout = QVBoxLayout(self)
        
        # أدوات التحكم
        tools_layout = QHBoxLayout()
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["جميع السجلات", "خطأ", "تحذير", "معلومات", "تصحيح"])
        self.log_level_combo.currentIndexChanged.connect(self._filter_logs)
        
        filter_label = QLabel("تصفية:")
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("أدخل نص للتصفية...")
        self.filter_edit.textChanged.connect(self._filter_logs)
        
        refresh_button = QPushButton("تحديث")
        refresh_button.clicked.connect(self._load_logs)
        
        tools_layout.addWidget(QLabel("مستوى السجل:"))
        tools_layout.addWidget(self.log_level_combo)
        tools_layout.addWidget(filter_label)
        tools_layout.addWidget(self.filter_edit)
        tools_layout.addWidget(refresh_button)
        
        # عرض السجلات
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 10))
        
        # أزرار التحكم
        buttons_layout = QHBoxLayout()
        
        clear_button = QPushButton("مسح السجلات")
        clear_button.clicked.connect(self._clear_logs)
        
        export_button = QPushButton("تصدير")
        export_button.clicked.connect(self._export_logs)
        
        close_button = QPushButton("إغلاق")
        close_button.clicked.connect(self.accept)
        
        buttons_layout.addWidget(clear_button)
        buttons_layout.addWidget(export_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(close_button)
        
        # إضافة المكونات إلى التخطيط الرئيسي
        layout.addLayout(tools_layout)
        layout.addWidget(self.log_text)
        layout.addLayout(buttons_layout)
        
        # تحميل السجلات
        self.log_file = log_file or "code_analyzer.log"
        self.all_logs = []
        self._load_logs()
    
    def _load_logs(self):
        """تحميل محتوى ملف السجلات"""
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    self.all_logs = f.readlines()
                
                self._filter_logs()
            else:
                self.log_text.setPlainText("ملف السجلات غير موجود.")
        
        except Exception as e:
            self.show_error("خطأ", "حدث خطأ أثناء تحميل السجلات", str(e))
    
    def _filter_logs(self):
        """تصفية السجلات حسب المستوى والفلتر"""
        try:
            level_idx = self.log_level_combo.currentIndex()
            level_filter = ""
            
            if level_idx == 1:  # خطأ
                level_filter = "ERROR"
            elif level_idx == 2:  # تحذير
                level_filter = "WARNING"
            elif level_idx == 3:  # معلومات
                level_filter = "INFO"
            elif level_idx == 4:  # تصحيح
                level_filter = "DEBUG"
            
            text_filter = self.filter_edit.text().lower()
            
            filtered_logs = []
            for log_line in self.all_logs:
                # تطبيق فلتر المستوى
                if level_filter and level_filter not in log_line:
                    continue
                
                # تطبيق فلتر النص
                if text_filter and text_filter not in log_line.lower():
                    continue
                
                filtered_logs.append(log_line)
            
            # تطبيق تنسيق الألوان على مستويات السجل
            formatted_logs = []
            for log_line in filtered_logs:
                if "ERROR" in log_line:
                    formatted_logs.append(f'<span style="color: red">{log_line}</span>')
                elif "WARNING" in log_line:
                    formatted_logs.append(f'<span style="color: orange">{log_line}</span>')
                elif "INFO" in log_line:
                    formatted_logs.append(f'<span style="color: blue">{log_line}</span>')
                elif "DEBUG" in log_line:
                    formatted_logs.append(f'<span style="color: gray">{log_line}</span>')
                else:
                    formatted_logs.append(log_line)
            
            # عرض السجلات المصفاة
            self.log_text.setHtml("".join(formatted_logs))
        
        except Exception as e:
            self.show_error("خطأ", "حدث خطأ أثناء تصفية السجلات", str(e))
    
    def _clear_logs(self):
        """مسح محتوى ملف السجلات"""
        try:
            result = QMessageBox.question(
                self,
                "تأكيد المسح",
                "هل أنت متأكد من رغبتك في مسح جميع السجلات؟",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if result == QMessageBox.Yes:
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    f.write("")
                
                self.all_logs = []
                self.log_text.clear()
                QMessageBox.information(self, "تم المسح", "تم مسح السجلات بنجاح.")
        
        except Exception as e:
            self.show_error("خطأ", "حدث خطأ أثناء مسح السجلات", str(e))
    
    def _export_logs(self):
        """تصدير السجلات إلى ملف"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "تصدير السجلات",
                "",
                "ملفات نصية (*.txt);;ملفات سجل (*.log)"
            )
            
            if not file_path:
                return
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.log_text.toPlainText())
            
            QMessageBox.information(self, "تم التصدير", f"تم تصدير السجلات إلى:\n{file_path}")
        
        except Exception as e:
            self.show_error("خطأ", "حدث خطأ أثناء تصدير السجلات", str(e))