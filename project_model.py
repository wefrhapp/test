#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تمثيل بيانات المشروع وتحليل العلاقات بين الملفات والكيانات البرمجية
"""
import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple, Optional, Union
import networkx as nx
import time
import hashlib
from datetime import datetime

from utils import (
    get_file_type, read_file, find_files, detect_project_type, calculate_file_hash,
    write_file, SUPPORTED_EXTENSIONS, ensure_dir
)

logger = logging.getLogger("CodeAnalyzer.ProjectModel")

class CodeEntity:
    """تمثيل كيان برمجي (class, function, variable, etc.)"""
    
    def __init__(self, name: str, entity_type: str, file_path: str, 
                 start_line: int, end_line: int = None):
        """
        تهيئة كيان برمجي جديد
        
        Args:
            name: اسم الكيان
            entity_type: نوع الكيان (class, function, method, variable, etc.)
            file_path: مسار الملف الذي يحتوي على الكيان
            start_line: رقم سطر بداية الكيان
            end_line: رقم سطر نهاية الكيان (اختياري)
        """
        self.name = name
        self.type = entity_type
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line
        self.children = []  # الكيانات الفرعية (مثل methods داخل class)
        self.parent = None  # الكيان الأب (إذا كان فرعي)
        self.properties = {}  # خصائص إضافية للكيان
        self.references = []  # الإشارات إلى هذا الكيان
        self.issues = []  # قضايا متعلقة بالكيان
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل الكيان إلى قاموس"""
        return {
            "name": self.name,
            "type": self.type,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "properties": self.properties,
            "references": self.references,
            "issues": self.issues,
            "children": [child.to_dict() for child in self.children]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodeEntity':
        """إنشاء كيان من قاموس"""
        entity = cls(
            name=data.get("name", ""),
            entity_type=data.get("type", ""),
            file_path=data.get("file_path", ""),
            start_line=data.get("start_line", 0),
            end_line=data.get("end_line")
        )
        
        entity.properties = data.get("properties", {})
        entity.references = data.get("references", [])
        entity.issues = data.get("issues", [])
        
        # إعادة بناء الكيانات الفرعية
        for child_data in data.get("children", []):
            child_entity = CodeEntity.from_dict(child_data)
            entity.add_child(child_entity)
        
        return entity
    
    def add_child(self, child: 'CodeEntity') -> None:
        """إضافة كيان فرعي"""
        self.children.append(child)
        child.parent = self
    
    def find_child(self, name: str, entity_type: str = None) -> Optional['CodeEntity']:
        """البحث عن كيان فرعي بالاسم والنوع"""
        for child in self.children:
            if child.name == name and (entity_type is None or child.type == entity_type):
                return child
        return None
    
    def remove_child(self, child: 'CodeEntity') -> bool:
        """إزالة كيان فرعي"""
        if child in self.children:
            self.children.remove(child)
            child.parent = None
            return True
        return False
    
    def get_full_name(self) -> str:
        """الحصول على الاسم الكامل للكيان (مع اسم الأب إذا وجد)"""
        if self.parent and self.parent.type == "class":
            return f"{self.parent.name}.{self.name}"
        return self.name
    
    def get_code_snippet(self, content: str = None, context_lines: int = 2) -> str:
        """
        الحصول على مقطع الشفرة للكيان
        
        Args:
            content: محتوى الملف (اختياري)
            context_lines: عدد الأسطر قبل وبعد الكيان (للسياق)
            
        Returns:
            str: مقطع الشفرة
        """
        if content is None:
            content = read_file(self.file_path)
            
        if not content:
            return ""
            
        lines = content.splitlines()
        
        # تحديد نطاق الأسطر
        start = max(0, self.start_line - 1 - context_lines)
        if self.end_line:
            end = min(len(lines), self.end_line + context_lines)
        else:
            end = min(len(lines), self.start_line + 10)  # افتراضي إذا لم يتم تحديد نهاية
            
        return "\n".join(lines[start:end])
    
    def add_issue(self, severity: str, message: str, description: str = None, 
                  recommendation: str = None) -> Dict[str, Any]:
        """
        إضافة قضية متعلقة بالكيان
        
        Args:
            severity: مستوى الخطورة (عالية، متوسطة، منخفضة)
            message: رسالة موجزة للقضية
            description: وصف مفصل للقضية (اختياري)
            recommendation: توصية لحل القضية (اختياري)
            
        Returns:
            Dict: قضية تم إنشاؤها
        """
        issue = {
            "entity_name": self.name,
            "entity_type": self.type,
            "file_path": self.file_path,
            "line": self.start_line,
            "severity": severity,
            "message": message,
            "description": description or message,
            "recommendation": recommendation or "",
            "created_at": datetime.now().timestamp()
        }
        
        self.issues.append(issue)
        return issue
    
    def __str__(self) -> str:
        return f"{self.type}: {self.name} ({self.file_path}:{self.start_line})"
    
    def __repr__(self) -> str:
        return self.__str__()


class CodeFile:
    """تمثيل ملف برمجي مع كياناته والاعتمادات الخاصة به"""
    
    def __init__(self, file_path: str, language: str = None):
        """
        تهيئة ملف برمجي جديد
        
        Args:
            file_path: مسار الملف
            language: لغة البرمجة (اختياري، سيتم اكتشافها تلقائيا إذا لم تُحدد)
        """
        self.file_path = file_path
        self.relative_path = None  # المسار النسبي من جذر المشروع
        self.language = language or get_file_type(file_path)
        self.content = None  # محتوى الملف (يتم تحميله عند الحاجة)
        self.hash = None     # قيمة hash للملف (للتحقق من التغييرات)
        self.entities = []   # الكيانات البرمجية في الملف
        self.imports = []    # استيرادات الملف
        self.dependencies = set()  # اعتمادات الملف
        self.modified = False  # هل تم تعديل الملف
        self.last_modified = None  # تاريخ آخر تعديل
        self.errors = []  # أخطاء التحليل
        self.issues = []  # قضايا الجودة والأمان
        self.last_analyzed = None  # تاريخ آخر تحليل
        self.file_size = 0  # حجم الملف
        self.line_count = 0  # عدد الأسطر
        self.metrics = {}  # مقاييس جودة الشفرة
    
    def load_content(self) -> bool:
        """تحميل محتوى الملف وحساب قيمة hash"""
        self.content = read_file(self.file_path)
        if self.content is not None:
            self.hash = calculate_file_hash(self.file_path)
            if os.path.exists(self.file_path):
                self.last_modified = os.path.getmtime(self.file_path)
                self.file_size = os.path.getsize(self.file_path)
                self.line_count = len(self.content.splitlines())
            return True
        return False
    
    def save_content(self, new_content: str) -> bool:
        """حفظ محتوى جديد للملف"""
        if write_file(self.file_path, new_content):
            self.content = new_content
            self.hash = calculate_file_hash(self.file_path)
            self.modified = True
            self.last_modified = os.path.getmtime(self.file_path)
            self.file_size = os.path.getsize(self.file_path)
            self.line_count = len(new_content.splitlines())
            # إعادة تحليل الكيانات بعد التعديل
            self.parse_entities()
            return True
        return False
    
    def is_modified(self) -> bool:
        """التحقق مما إذا كان الملف قد تم تعديله من خارج البرنامج"""
        if not os.path.exists(self.file_path) or not self.hash:
            return False
        
        current_hash = calculate_file_hash(self.file_path)
        return current_hash != self.hash
    
    def set_relative_path(self, project_root: str) -> None:
        """تعيين المسار النسبي من جذر المشروع"""
        if project_root:
            try:
                # استخدام Path للتعامل مع اختلافات أنظمة التشغيل
                project_root_path = Path(project_root).resolve()
                file_path = Path(self.file_path).resolve()
                self.relative_path = str(file_path.relative_to(project_root_path))
            except ValueError:
                # إذا كان الملف ليس داخل جذر المشروع
                self.relative_path = os.path.basename(self.file_path)
    
    def parse_entities(self) -> bool:
        """تحليل الكيانات في الملف"""
        if self.content is None:
            if not self.load_content():
                return False
        
        self.entities = []
        self.errors = []
        
        try:
            if not self.language:
                self.language = get_file_type(self.file_path)
            
            if self.language == "python":
                self._parse_python_entities()
            elif self.language in ["dart", "flutter_dart"]:
                self._parse_dart_entities()
            elif self.language in ["php", "laravel_php"]:
                self._parse_php_entities()
            elif self.language in ["javascript", "react", "typescript"]:
                self._parse_javascript_entities()
            elif self.language == "html":
                self._parse_html_entities()
            elif self.language == "css":
                self._parse_css_entities()
            
            self.last_analyzed = time.time()
            return True
        except Exception as e:
            error_msg = f"خطأ في تحليل الكيانات للملف {self.file_path}: {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return False
    
    def _parse_python_entities(self) -> None:
        """تحليل كيانات Python"""
        if not self.content:
            return
        
        lines = self.content.splitlines()
        
        # تحليل الاستيرادات
        import_pattern = r'^import\s+(\w+(?:\.\w+)*)|^from\s+([.\w]+)\s+import'
        for i, line in enumerate(lines):
            match = re.search(import_pattern, line)
            if match:
                module = match.group(1) or match.group(2)
                self.imports.append(module)
                if '.' not in module and not module.startswith('.'):
                    self.dependencies.add(module)
        
        # تحليل الفئات والدوال والمتغيرات
        class_pattern = r'^class\s+(\w+)(?:\(([^)]*)\))?:'
        function_pattern = r'^def\s+(\w+)\s*\('
        method_pattern = r'^\s+def\s+(\w+)\s*\('
        variable_pattern = r'^(\w+)\s*='
        
        current_class = None
        current_function = None
        indent_level = -1  # مستوى التسلسل الهرمي الحالي
        i = 0
        
        while i < len(lines):
            line = lines[i]
            current_indent = len(line) - len(line.lstrip())
            
            # التحقق من مستوى التسلسل الهرمي
            if indent_level >= 0 and current_indent <= indent_level:
                # انتهاء الكتلة الحالية
                if current_class and (not current_function or current_indent <= indent_level - 4):
                    # تحديد نهاية الفئة
                    current_class.end_line = i
                    current_class = None
                    indent_level = -1
                elif current_function:
                    # تحديد نهاية الدالة
                    current_function.end_line = i
                    current_function = None
                    indent_level = -1
            
            # البحث عن تعريفات الفئات
            class_match = re.search(class_pattern, line)
            if class_match:
                class_name = class_match.group(1)
                class_parents = class_match.group(2) if class_match.group(2) else ""
                
                class_entity = CodeEntity(
                    name=class_name,
                    entity_type="class",
                    file_path=self.file_path,
                    start_line=i + 1
                )
                
                # إضافة المعلومات الإضافية
                if class_parents:
                    class_entity.properties["parents"] = [p.strip() for p in class_parents.split(',')]
                
                self.entities.append(class_entity)
                current_class = class_entity
                indent_level = current_indent
                i += 1
                continue
            
            # البحث عن تعريفات الدوال
            function_match = re.search(function_pattern, line)
            if function_match and not line.startswith(' '):
                function_name = function_match.group(1)
                function_entity = CodeEntity(
                    name=function_name,
                    entity_type="function",
                    file_path=self.file_path,
                    start_line=i + 1
                )
                
                self.entities.append(function_entity)
                current_function = function_entity
                indent_level = current_indent
                i += 1
                continue
            
            # البحث عن تعريفات الطرق (داخل فئة)
            method_match = re.search(method_pattern, line)
            if method_match and current_class:
                method_name = method_match.group(1)
                method_entity = CodeEntity(
                    name=method_name,
                    entity_type="method",
                    file_path=self.file_path,
                    start_line=i + 1
                )
                
                # إضافة خصائص إضافية
                if method_name == "__init__":
                    method_entity.properties["is_constructor"] = True
                elif method_name.startswith("__") and method_name.endswith("__"):
                    method_entity.properties["is_magic_method"] = True
                
                # كشف API لواجهات الذكاء الاصطناعي
                if "api" in method_name.lower() or "gpt" in method_name.lower() or "claude" in method_name.lower() or "openai" in method_name.lower() or "grok" in method_name.lower():
                    method_entity.properties["is_ai_related"] = True
                
                current_class.add_child(method_entity)
                current_function = method_entity
                indent_level = current_indent
                i += 1
                continue
            
            # البحث عن تعريفات المتغيرات العامة
            variable_match = re.search(variable_pattern, line)
            if variable_match and not line.startswith(' '):
                variable_name = variable_match.group(1)
                # تجاهل المتغيرات الداخلية والثوابت
                if not variable_name.startswith('_') and not variable_name.isupper():
                    variable_entity = CodeEntity(
                        name=variable_name,
                        entity_type="variable",
                        file_path=self.file_path,
                        start_line=i + 1,
                        end_line=i + 1
                    )
                    self.entities.append(variable_entity)
                
                # كشف مفاتيح API محتملة
                if ("api_key" in variable_name.lower() or 
                    "secret" in variable_name.lower() or 
                    "token" in variable_name.lower()):
                    # تنبيه حول مفاتيح API
                    logger.warning(f"تم العثور على متغير يحتمل أن يكون مفتاح API: {variable_name} في {self.file_path}:{i+1}")
            
            i += 1
    
    def _parse_javascript_entities(self) -> None:
        """تحليل كيانات JavaScript/TypeScript"""
        if not self.content:
            return
        
        lines = self.content.splitlines()
        
        # أنماط كشف الاستيرادات
        import_patterns = [
            r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]',  # ES6 import
            r'const\s+\w+\s*=\s*require\([\'"]([^\'"]+)[\'"]\)',  # CommonJS require
            r'import\([\'"]([^\'"]+)[\'"]\)',  # Dynamic import
        ]
        
        # أنماط كشف الكيانات
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?'
        function_pattern = r'function\s+(\w+)\s*\('
        const_pattern = r'const\s+(\w+)\s*='
        let_pattern = r'let\s+(\w+)\s*='
        var_pattern = r'var\s+(\w+)\s*='
        
        # أنماط خاصة بـ React
        component_pattern = r'const\s+(\w+)\s*=\s*(?:React\.)?(?:memo|forwardRef|createClass)?\(?(?:\(\)|function\s*\([^)]*\)|\([^)]*\)\s*=>\s*)'
        hook_pattern = r'function\s+use(\w+)\s*\('
        
        # فحص الاستيرادات
        for i, line in enumerate(lines):
            for pattern in import_patterns:
                matches = re.findall(pattern, line)
                for module in matches:
                    self.imports.append(module)
                    # استخراج اسم الحزمة الأساسي
                    if '/' in module:
                        pkg = module.split('/')[0]
                        if pkg.startswith('@'):
                            # للحزم مثل @org/pkg
                            pkg_parts = module.split('/')[:2]
                            pkg = '/'.join(pkg_parts)
                        self.dependencies.add(pkg)
                    else:
                        self.dependencies.add(module)
        
        # البحث عن تعريفات React بالإضافة إلى AI Libraries
        has_react = any("react" in imp.lower() for imp in self.imports)
        has_ai_libs = any(lib in ' '.join(self.imports).lower() 
                        for lib in ["openai", "claude", "anthropic", "gpt", "langchain", "ai", "huggingface"])
        
        if has_ai_libs:
            self.language = "ai_javascript"
        elif has_react:
            self.language = "react"
        
        # فحص الكيانات
        i = 0
        while i < len(lines):
            line = lines[i]
            line_stripped = line.strip()
            
            # فحص الفئات
            class_match = re.search(class_pattern, line_stripped)
            if class_match:
                class_name = class_match.group(1)
                parent_class = class_match.group(2)
                
                class_entity = CodeEntity(
                    name=class_name,
                    entity_type="class",
                    file_path=self.file_path,
                    start_line=i + 1
                )
                
                if parent_class:
                    class_entity.properties["extends"] = parent_class
                
                # للفئات في React
                if has_react and ("Component" in line or "PureComponent" in line):
                    class_entity.properties["is_react_component"] = True
                
                self.entities.append(class_entity)
                
                # محاولة تحديد نهاية الفئة
                bracket_count = 0
                for j in range(i, len(lines)):
                    if "{" in lines[j]:
                        bracket_count += lines[j].count("{")
                    if "}" in lines[j]:
                        bracket_count -= lines[j].count("}")
                    if bracket_count == 0 and j > i:
                        class_entity.end_line = j + 1
                        break
            
            # فحص الدوال
            function_match = re.search(function_pattern, line_stripped)
            if function_match:
                function_name = function_match.group(1)
                
                function_entity = CodeEntity(
                    name=function_name,
                    entity_type="function",
                    file_path=self.file_path,
                    start_line=i + 1
                )
                
                # كشف hooks في React
                if has_react and function_name.startswith("use") and function_name[3:4].isupper():
                    function_entity.properties["is_react_hook"] = True
                
                # كشف دوال متعلقة بالذكاء الاصطناعي
                if (has_ai_libs and 
                    any(term in function_name.lower() for term in ["ai", "chat", "completion", "gpt", "model", "generate", "predict"])):
                    function_entity.properties["is_ai_related"] = True
                
                self.entities.append(function_entity)
                
                # محاولة تحديد نهاية الدالة
                bracket_count = 0
                for j in range(i, len(lines)):
                    if "{" in lines[j]:
                        bracket_count += lines[j].count("{")
                    if "}" in lines[j]:
                        bracket_count -= lines[j].count("}")
                    if bracket_count == 0 and j > i:
                        function_entity.end_line = j + 1
                        break
            
            # فحص مكونات React
            component_match = re.search(component_pattern, line_stripped)
            if has_react and component_match:
                component_name = component_match.group(1)
                
                component_entity = CodeEntity(
                    name=component_name,
                    entity_type="component",
                    file_path=self.file_path,
                    start_line=i + 1
                )
                
                component_entity.properties["is_react_component"] = True
                
                self.entities.append(component_entity)
            
            # فحص المتغيرات
            for pattern, var_type in [(const_pattern, "constant"), (let_pattern, "variable"), (var_pattern, "variable")]:
                var_match = re.search(pattern, line_stripped)
                if var_match:
                    var_name = var_match.group(1)
                    
                    var_entity = CodeEntity(
                        name=var_name,
                        entity_type=var_type,
                        file_path=self.file_path,
                        start_line=i + 1,
                        end_line=i + 1
                    )
                    
                    # كشف مفاتيح API محتملة
                    is_api_key = any(term in var_name.lower() for term in ["apikey", "api_key", "secret", "token", "password"])
                    if is_api_key:
                        var_entity.properties["is_sensitive"] = True
                        logger.warning(f"تم العثور على متغير حساس محتمل: {var_name} في {self.file_path}:{i+1}")
                    
                    self.entities.append(var_entity)
            
            i += 1
    
    def _parse_dart_entities(self) -> None:
        """تحليل كيانات Dart/Flutter"""
        if not self.content:
            return
        
        lines = self.content.splitlines()
        
        # أنماط استيراد الحزم
        import_pattern = r'import\s+[\'"]([^\'"]+)[\'"]'
        
        # أنماط كشف الكيانات
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^{]+))?'
        method_pattern = r'(?:@\w+\s+)*(?:void|Future|Widget|[\w<>]+)\s+(\w+)\s*\('
        variable_pattern = r'(?:final|const|var|late)?\s+(?:[\w<>?]+)\s+(\w+)\s*='
        widget_pattern = r'class\s+(\w+)\s+extends\s+(?:StatelessWidget|StatefulWidget)'
        state_pattern = r'class\s+_(\w+)State\s+extends\s+State<(\w+)>'
        
        # فحص الاستيرادات
        for i, line in enumerate(lines):
            import_matches = re.findall(import_pattern, line)
            for module in import_matches:
                self.imports.append(module)
                # تحديد الحزم الخارجية
                if ':' in module:
                    pkg_type, pkg_path = module.split(':', 1)
                    if pkg_type == 'package':
                        pkg_name = pkg_path.split('/')[0]
                        self.dependencies.add(pkg_name)
        
        # تحديد نوع المشروع
        has_flutter = any("flutter" in imp for imp in self.imports)
        if has_flutter:
            self.language = "flutter_dart"
        
        # فحص الكيانات
        i = 0
        while i < len(lines):
            line = lines[i]
            line_stripped = line.strip()
            
            # فحص الفئات
            class_match = re.search(class_pattern, line_stripped)
            if class_match:
                class_name = class_match.group(1)
                parent_class = class_match.group(2)
                implements = class_match.group(3)
                
                class_entity = CodeEntity(
                    name=class_name,
                    entity_type="class",
                    file_path=self.file_path,
                    start_line=i + 1
                )
                
                if parent_class:
                    class_entity.properties["extends"] = parent_class
                
                if implements:
                    class_entity.properties["implements"] = [
                        impl.strip() for impl in implements.split(',')
                    ]
                
                # كشف Widgets في Flutter
                if has_flutter and parent_class and ("Widget" in parent_class):
                    class_entity.properties["is_widget"] = True
                    class_entity.type = "widget"
                
                self.entities.append(class_entity)
                
                # البحث عن نهاية الفئة
                bracket_count = 0
                class_end = i
                for j in range(i, len(lines)):
                    if "{" in lines[j]:
                        bracket_count += lines[j].count("{")
                    if "}" in lines[j]:
                        bracket_count -= lines[j].count("}")
                    if bracket_count == 0 and j > i:
                        class_end = j
                        class_entity.end_line = j + 1
                        break
                
                # البحث عن الطرق والمتغيرات داخل الفئة
                current_class = class_entity
                j = i + 1
                while j < class_end:
                    method_match = re.search(method_pattern, lines[j].strip())
                    if method_match:
                        method_name = method_match.group(1)
                        method_entity = CodeEntity(
                            name=method_name,
                            entity_type="method",
                            file_path=self.file_path,
                            start_line=j + 1
                        )
                        
                        if has_flutter and method_name == "build" and "Widget" in lines[j]:
                            method_entity.properties["is_build_method"] = True
                        
                        current_class.add_child(method_entity)
                    
                    var_match = re.search(variable_pattern, lines[j].strip())
                    if var_match:
                        var_name = var_match.group(1)
                        var_entity = CodeEntity(
                            name=var_name,
                            entity_type="variable",
                            file_path=self.file_path,
                            start_line=j + 1,
                            end_line=j + 1
                        )
                        
                        current_class.add_child(var_entity)
                    
                    j += 1
            
            # فحص خاص لـ Flutter Widgets وState
            widget_match = re.search(widget_pattern, line_stripped)
            state_match = re.search(state_pattern, line_stripped)
            
            if has_flutter and widget_match:
                widget_name = widget_match.group(1)
                existing_entity = next((e for e in self.entities if e.name == widget_name), None)
                
                if existing_entity:
                    existing_entity.properties["is_widget"] = True
                    existing_entity.type = "widget"
            
            if has_flutter and state_match:
                state_name = state_match.group(1)
                widget_name = state_match.group(2)
                
                # ربط State مع Widget المرتبط
                for entity in self.entities:
                    if entity.name == widget_name:
                        entity.properties["has_state"] = True
                        break
            
            i += 1
    
    def _parse_php_entities(self) -> None:
        """تحليل كيانات PHP/Laravel"""
        if not self.content:
            return
        
        lines = self.content.splitlines()
        
        # أنماط تحليل PHP
        namespace_pattern = r'namespace\s+([^;]+);'
        use_pattern = r'use\s+([^;]+);'
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^{]+))?'
        function_pattern = r'function\s+(\w+)\s*\('
        variable_pattern = r'(?:public|protected|private)(?:\s+static)?\s+\$(\w+)'
        method_pattern = r'(?:public|protected|private)(?:\s+static)?\s+function\s+(\w+)\s*\('
        
        # متغيرات تتبع السياق
        current_namespace = None
        current_class = None
        
        # تحليل الفضاء المسمى واستيرادات
        for i, line in enumerate(lines):
            namespace_match = re.search(namespace_pattern, line)
            if namespace_match:
                current_namespace = namespace_match.group(1).strip()
            
            use_match = re.search(use_pattern, line)
            if use_match:
                import_path = use_match.group(1).strip()
                self.imports.append(import_path)
                
                # استخراج اسم الحزمة
                if '\\' in import_path:
                    main_package = import_path.split('\\')[0]
                    if main_package not in ['App', 'Illuminate']:  # استبعاد حزم Laravel الأساسية
                        self.dependencies.add(main_package)
        
        # كشف إذا كان مشروع Laravel
        has_laravel = any("Illuminate" in imp for imp in self.imports)
        if has_laravel:
            self.language = "laravel_php"
        
        # تحليل الكيانات
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # تحليل الفئات
            class_match = re.search(class_pattern, line)
            if class_match:
                class_name = class_match.group(1)
                parent_class = class_match.group(2)
                implements = class_match.group(3)
                
                class_entity = CodeEntity(
                    name=class_name,
                    entity_type="class",
                    file_path=self.file_path,
                    start_line=i + 1
                )
                
                if current_namespace:
                    class_entity.properties["namespace"] = current_namespace
                    class_entity.properties["full_name"] = f"{current_namespace}\\{class_name}"
                
                if parent_class:
                    class_entity.properties["extends"] = parent_class
                
                if implements:
                    class_entity.properties["implements"] = [
                        impl.strip() for impl in implements.split(',')
                    ]
                
                # خصائص Laravel الخاصة
                if has_laravel:
                    # كشف أنواع مختلفة من فئات Laravel
                    if "Controller" in class_name:
                        class_entity.properties["is_controller"] = True
                        class_entity.type = "controller"
                    elif "Model" in parent_class or "Eloquent" in line:
                        class_entity.properties["is_model"] = True
                        class_entity.type = "model"
                    elif "Migration" in parent_class:
                        class_entity.properties["is_migration"] = True
                        class_entity.type = "migration"
                    elif "Middleware" in parent_class or "Middleware" in implements:
                        class_entity.properties["is_middleware"] = True
                        class_entity.type = "middleware"
                
                self.entities.append(class_entity)
                current_class = class_entity
                
                # البحث عن نهاية الفئة
                bracket_count = 0
                class_end = i
                for j in range(i, len(lines)):
                    current_line = lines[j]
                    if "{" in current_line:
                        bracket_count += current_line.count("{")
                    if "}" in current_line:
                        bracket_count -= current_line.count("}")
                    if bracket_count <= 0 and j > i and "}" in current_line:
                        class_end = j
                        class_entity.end_line = j + 1
                        break
                
                # تحليل الطرق والمتغيرات داخل الفئة
                j = i + 1
                while j < class_end:
                    j_line = lines[j]
                    
                    # تحليل الطرق
                    method_match = re.search(method_pattern, j_line)
                    if method_match and current_class:
                        method_name = method_match.group(1)
                        method_entity = CodeEntity(
                            name=method_name,
                            entity_type="method",
                            file_path=self.file_path,
                            start_line=j + 1
                        )
                        
                        # خصائص Laravel الخاصة
                        if has_laravel and current_class.properties.get("is_controller"):
                            if method_name in ["index", "show", "create", "store", "edit", "update", "destroy"]:
                                method_entity.properties["is_resource_method"] = True
                        
                        current_class.add_child(method_entity)
                    
                    # تحليل المتغيرات
                    var_match = re.search(variable_pattern, j_line)
                    if var_match and current_class:
                        var_name = var_match.group(1)
                        var_entity = CodeEntity(
                            name=var_name,
                            entity_type="property",
                            file_path=self.file_path,
                            start_line=j + 1,
                            end_line=j + 1
                        )
                        
                        # خصائص Laravel الخاصة
                        if has_laravel and current_class.properties.get("is_model"):
                            if var_name in ["fillable", "guarded", "casts", "hidden", "table"]:
                                var_entity.properties["is_model_property"] = True
                        
                        # كشف متغيرات حساسة
                        if any(term in var_name.lower() for term in ["api", "key", "token", "secret", "password"]):
                            var_entity.properties["is_sensitive"] = True
                            logger.warning(f"تم العثور على متغير حساس محتمل: {var_name} في {self.file_path}:{j+1}")
                        
                        current_class.add_child(var_entity)
                    
                    j += 1
                
                i = class_end + 1
                continue
            
            # تحليل الدوال المستقلة
            function_match = re.search(function_pattern, line)
            if function_match and not line.strip().startswith(('public', 'protected', 'private')):
                function_name = function_match.group(1)
                function_entity = CodeEntity(
                    name=function_name,
                    entity_type="function",
                    file_path=self.file_path,
                    start_line=i + 1
                )
                
                if current_namespace:
                    function_entity.properties["namespace"] = current_namespace
                
                self.entities.append(function_entity)
            
            i += 1
    
    def _parse_html_entities(self) -> None:
        """تحليل كيانات HTML"""
        if not self.content:
            return
        
        lines = self.content.splitlines()
        
        # أنماط تحليل HTML
        title_pattern = r'<title>(.*?)</title>'
        script_pattern = r'<script[^>]*src=["\']([^"\']+)["\']'
        link_pattern = r'<link[^>]*href=["\']([^"\']+)["\']'
        form_pattern = r'<form[^>]*(?:id=["\']([^"\']+)["\'])?'
        div_id_pattern = r'<div[^>]*id=["\']([^"\']+)["\']'
        
        # تحليل العنوان
        for i, line in enumerate(lines):
            title_match = re.search(title_pattern, line)
            if title_match:
                title = title_match.group(1)
                title_entity = CodeEntity(
                    name=title,
                    entity_type="title",
                    file_path=self.file_path,
                    start_line=i + 1,
                    end_line=i + 1
                )
                self.entities.append(title_entity)
                break
        
        # تحليل الاستيرادات (JavaScript و CSS)
        for i, line in enumerate(lines):
            script_matches = re.findall(script_pattern, line)
            link_matches = re.findall(link_pattern, line)
            
            for src in script_matches:
                self.imports.append(src)
                if '/' in src and not src.startswith(('//', 'http')):
                    # للملفات المحلية فقط
                    entity = CodeEntity(
                        name=os.path.basename(src),
                        entity_type="script",
                        file_path=self.file_path,
                        start_line=i + 1,
                        end_line=i + 1
                    )
                    entity.properties["path"] = src
                    self.entities.append(entity)
            
            for href in link_matches:
                self.imports.append(href)
                if '.css' in href and not href.startswith(('//', 'http')):
                    # للملفات CSS المحلية
                    entity = CodeEntity(
                        name=os.path.basename(href),
                        entity_type="stylesheet",
                        file_path=self.file_path,
                        start_line=i + 1,
                        end_line=i + 1
                    )
                    entity.properties["path"] = href
                    self.entities.append(entity)
        
        # تحليل النماذج
        for i, line in enumerate(lines):
            form_match = re.search(form_pattern, line)
            if form_match:
                form_id = form_match.group(1) or f"form_{i}"
                form_entity = CodeEntity(
                    name=form_id,
                    entity_type="form",
                    file_path=self.file_path,
                    start_line=i + 1
                )
                
                # البحث عن نهاية النموذج
                form_end = len(lines)
                for j in range(i + 1, len(lines)):
                    if "</form>" in lines[j]:
                        form_end = j
                        break
                
                form_entity.end_line = form_end + 1
                self.entities.append(form_entity)
        
        # تحليل العناصر div المهمة
        for i, line in enumerate(lines):
            div_matches = re.findall(div_id_pattern, line)
            for div_id in div_matches:
                div_entity = CodeEntity(
                    name=div_id,
                    entity_type="div",
                    file_path=self.file_path,
                    start_line=i + 1
                )
                self.entities.append(div_entity)
    
    def _parse_css_entities(self) -> None:
        """تحليل كيانات CSS"""
        if not self.content:
            return
        
        lines = self.content.splitlines()
        
        # أنماط تحليل CSS
        selector_pattern = r'([^{]+){[^}]*}'
        property_pattern = r'([a-zA-Z-]+)\s*:\s*([^;]+);'
        
        i = 0
        while i < len(lines):
            line = lines[i]
            selector_match = re.search(selector_pattern, line)
            
            # جمع أسطر متعددة للبحث عن selectors
            j = i
            full_line = line
            while j < len(lines) - 1 and not '}' in full_line:
                j += 1
                full_line += " " + lines[j]
            
            selectors_blocks = re.findall(selector_pattern, full_line)
            
            for selector in selectors_blocks:
                selector = selector.strip()
                if selector:
                    selector_entity = CodeEntity(
                        name=selector,
                        entity_type="selector",
                        file_path=self.file_path,
                        start_line=i + 1
                    )
                    
                    # البحث عن نهاية الكتلة
                    end_line = i
                    for k in range(i, len(lines)):
                        if '}' in lines[k]:
                            end_line = k
                            break
                    
                    selector_entity.end_line = end_line + 1
                    
                    # البحث عن خصائص داخل الـ selector
                    properties = {}
                    for k in range(i, end_line + 1):
                        property_matches = re.findall(property_pattern, lines[k])
                        for prop_name, prop_value in property_matches:
                            properties[prop_name.strip()] = prop_value.strip()
                    
                    selector_entity.properties["css_properties"] = properties
                    
                    self.entities.append(selector_entity)
                    
                    # تجاوز الكتلة الحالية
                    i = end_line + 1
                    break
            else:
                i += 1
    
    def analyze_complexity(self) -> Dict[str, Any]:
        """
        تحليل تعقيد الملف
        
        يحسب مقاييس تعقيد مختلفة مثل تعقيد McCabe والتعقيد الهيكلي
        
        Returns:
            Dict[str, Any]: نتائج تحليل التعقيد
        """
        if not self.content:
            self.load_content()
        
        complexity_metrics = {
            "file_size": self.file_size,
            "line_count": self.line_count,
            "entity_count": len(self.entities),
            "cyclomatic_complexity": 0,
            "nesting_depth": 0,
            "complexity_score": 0
        }
        
        if not self.content:
            return complexity_metrics
        
        lines = self.content.splitlines()
        
        # حساب تعقيد McCabe
        # (كل شرط if, for, while, case يزيد التعقيد)
        cyclomatic_patterns = [
            r'\bif\b', r'\belse\s+if\b', r'\bfor\b', r'\bwhile\b',
            r'\bcase\b', r'\bcatch\b', r'\?', r'\|\|', r'\&\&'
        ]
        
        cyclomatic_complexity = 1  # القيمة الأساسية
        
        for line in lines:
            for pattern in cyclomatic_patterns:
                cyclomatic_complexity += len(re.findall(pattern, line))
        
        complexity_metrics["cyclomatic_complexity"] = cyclomatic_complexity
        
        # حساب عمق التداخل
        max_nesting = 0
        current_nesting = 0
        
        for line in lines:
            # زيادة المستوى عند بداية كتلة
            current_nesting += line.count('{')
            # حساب المستوى الحالي
            max_nesting = max(max_nesting, current_nesting)
            # تقليل المستوى عند نهاية كتلة
            current_nesting -= line.count('}')
        
        complexity_metrics["nesting_depth"] = max_nesting
        
        # حساب درجة تعقيد الملف بناءً على المقاييس المحسوبة
        # الصيغة: (تعقيد McCabe * 0.5) + (عمق التداخل * 0.3) + (عدد الكيانات * 0.2)
        complexity_score = (
            (cyclomatic_complexity * 0.5) +
            (max_nesting * 0.3) +
            (len(self.entities) * 0.2)
        )
        
        complexity_metrics["complexity_score"] = round(complexity_score, 2)
        
        self.metrics = complexity_metrics
        return complexity_metrics
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل ملف الشفرة إلى قاموس"""
        return {
            "file_path": self.file_path,
            "relative_path": self.relative_path,
            "language": self.language,
            "hash": self.hash,
            "last_modified": self.last_modified,
            "last_analyzed": self.last_analyzed,
            "entities": [entity.to_dict() for entity in self.entities],
            "imports": self.imports,
            "dependencies": list(self.dependencies),
            "modified": self.modified,
            "errors": self.errors,
            "issues": self.issues,
            "file_size": self.file_size,
            "line_count": self.line_count,
            "metrics": self.metrics
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodeFile':
        """إنشاء ملف شفرة من قاموس"""
        code_file = cls(
            file_path=data.get("file_path", ""),
            language=data.get("language")
        )
        
        code_file.relative_path = data.get("relative_path")
        code_file.hash = data.get("hash")
        code_file.last_modified = data.get("last_modified")
        code_file.last_analyzed = data.get("last_analyzed")
        code_file.imports = data.get("imports", [])
        code_file.dependencies = set(data.get("dependencies", []))
        code_file.modified = data.get("modified", False)
        code_file.errors = data.get("errors", [])
        code_file.issues = data.get("issues", [])
        code_file.file_size = data.get("file_size", 0)
        code_file.line_count = data.get("line_count", 0)
        code_file.metrics = data.get("metrics", {})
        
        # إعادة بناء الكيانات
        for entity_data in data.get("entities", []):
            entity = CodeEntity.from_dict(entity_data)
            code_file.entities.append(entity)
        
        return code_file
    
    def __str__(self) -> str:
        return f"CodeFile({self.file_path}, {self.language}, entities={len(self.entities)})"
    
    def __repr__(self) -> str:
        return self.__str__()


class Project:
    """تمثيل مشروع برمجي مع إدارة ملفاته وكياناته والعلاقات بينها"""
    
    def __init__(self, root_dir: str):
        """
        تهيئة مشروع جديد من مجلد
        
        Args:
            root_dir: المسار الجذري للمشروع
        """
        self.root_dir = os.path.abspath(root_dir)
        self.name = os.path.basename(self.root_dir)
        self.files: Dict[str, CodeFile] = {}  # مفتاح: المسار النسبي
        self.file_count = 0
        self.entity_count = 0
        self.project_type = None
        self.dependency_graph = nx.DiGraph()
        self.created_at = time.time()
        self.last_modified = time.time()
        self.issues = []  # قضايا المشروع
        self.ai_analysis_results = {}  # نتائج تحليل الذكاء الاصطناعي
        self.metadata = {}  # بيانات وصفية إضافية
    
    def scan_files(self, include_patterns: List[str] = None, exclude_patterns: List[str] = None) -> int:
        """
        مسح واكتشاف الملفات في المشروع
        
        Args:
            include_patterns: أنماط شاملة للملفات
            exclude_patterns: أنماط مستبعدة للملفات
            
        Returns:
            int: عدد الملفات المكتشفة
        """
        # استخدام الامتدادات المدعومة إذا لم يتم تحديد أنماط شاملة
        if not include_patterns:
            include_patterns = [f"**/*.{ext}" for ext in SUPPORTED_EXTENSIONS]
        
        # أنماط افتراضية للاستبعاد
        default_exclude = [
            "**/.git/**", "**/node_modules/**", "**/venv/**", "**/__pycache__/**",
            "**/build/**", "**/dist/**", "**/.idea/**", "**/.vscode/**"
        ]
        
        if exclude_patterns:
            exclude_patterns = default_exclude + exclude_patterns
        else:
            exclude_patterns = default_exclude
        
        # البحث عن الملفات المطابقة
        found_files = find_files(
            self.root_dir,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns
        )
        
        # إضافة الملفات إلى المشروع
        for file_path in found_files:
            relative_path = os.path.relpath(file_path, self.root_dir)
            
            code_file = CodeFile(file_path)
            code_file.set_relative_path(self.root_dir)
            
            # تحميل المحتوى وتحليل الكيانات
            if code_file.load_content():
                code_file.parse_entities()
            
            # إضافة الملف إلى القاموس
            self.files[relative_path] = code_file
        
        # تحديث إحصائيات المشروع
        self.file_count = len(self.files)
        self.entity_count = sum(len(f.entities) for f in self.files.values())
        
        # كشف نوع المشروع
        self.project_type = detect_project_type(self.root_dir)
        
        # بناء رسم بياني للاعتمادات
        self._build_dependency_graph()
        
        return self.file_count
    
    def _build_dependency_graph(self) -> None:
        """بناء رسم بياني للاعتمادات بين ملفات المشروع"""
        # إنشاء رسم بياني جديد
        self.dependency_graph = nx.DiGraph()
        
        # إضافة جميع الملفات كعقد
        for file_path, code_file in self.files.items():
            self.dependency_graph.add_node(file_path, type="file", language=code_file.language)
        
        # إضافة الاعتمادات كحواف
        for file_path, code_file in self.files.items():
            for dependency in code_file.dependencies:
                # البحث عن الملف الذي يحتوي على الوحدة المطلوبة
                for dep_path, dep_file in self.files.items():
                    if dependency in os.path.basename(dep_path).split(".")[0]:
                        self.dependency_graph.add_edge(file_path, dep_path, type="import")
                        break
    
    def analyze_dependencies(self) -> Dict[str, Any]:
        """
        تحليل الاعتمادات في المشروع
        
        Returns:
            Dict[str, Any]: تحليل الاعتمادات
        """
        result = {
            "central_files": [],
            "isolated_files": [],
            "external_dependencies": {},
            "circular_dependencies": []
        }
        
        # إذا كان الرسم البياني للاعتمادات فارغاً
        if not self.dependency_graph:
            self._build_dependency_graph()
        
        # الملفات المركزية (الأكثر استخداماً)
        try:
            centrality = nx.degree_centrality(self.dependency_graph)
            central_files = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:10]
            result["central_files"] = [{"file": f, "centrality": round(c, 3)} for f, c in central_files]
        except:
            result["central_files"] = []
        
        # الملفات المعزولة (بدون اعتمادات)
        isolated_files = [f for f, d in self.dependency_graph.degree() if d == 0]
        result["isolated_files"] = isolated_files
        
        # الاعتمادات الخارجية
        external_deps = {}
        for _, code_file in self.files.items():
            for dep in code_file.dependencies:
                if not any(dep in os.path.basename(f) for f in self.files.keys()):
                    external_deps[dep] = external_deps.get(dep, 0) + 1
        
        result["external_dependencies"] = dict(sorted(external_deps.items(), key=lambda x: x[1], reverse=True))
        
        # الاعتمادات الدائرية
        try:
            cycles = list(nx.simple_cycles(self.dependency_graph))
            result["circular_dependencies"] = [list(c) for c in cycles]
        except:
            result["circular_dependencies"] = []
        
        return result
    
    def find_similar_files(self, threshold: float = 0.8) -> List[Tuple[str, str, float]]:
        """
        البحث عن الملفات المتشابهة في المشروع
        
        Args:
            threshold: عتبة التشابه (0.0 إلى 1.0)
            
        Returns:
            List[Tuple[str, str, float]]: قائمة من أزواج الملفات المتشابهة مع درجة التشابه
        """
        similar_files = []
        files_list = list(self.files.items())
        
        for i in range(len(files_list)):
            path1, file1 = files_list[i]
            if not file1.content:
                file1.load_content()
            
            for j in range(i + 1, len(files_list)):
                path2, file2 = files_list[j]
                if not file2.content:
                    file2.load_content()
                
                # تجاهل الملفات من أنواع مختلفة
                if file1.language != file2.language:
                    continue
                
                # حساب التشابه
                similarity = self._calculate_similarity(file1.content, file2.content)
                
                if similarity >= threshold:
                    similar_files.append((path1, path2, similarity))
        
        # ترتيب حسب درجة التشابه (تنازلياً)
        similar_files.sort(key=lambda x: x[2], reverse=True)
        
        return similar_files
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        حساب التشابه بين نصين
        
        Args:
            text1: النص الأول
            text2: النص الثاني
            
        Returns:
            float: درجة التشابه (0.0 إلى 1.0)
        """
        if not text1 or not text2:
            return 0.0
        
        # إزالة التعليقات والمسافات لتحسين المقارنة
        text1 = re.sub(r'#.*$|//.*$|/\*[\s\S]*?\*/|^\s*$', '', text1, flags=re.MULTILINE)
        text2 = re.sub(r'#.*$|//.*$|/\*[\s\S]*?\*/|^\s*$', '', text2, flags=re.MULTILINE)
        
        lines1 = set(line.strip() for line in text1.splitlines() if line.strip())
        lines2 = set(line.strip() for line in text2.splitlines() if line.strip())
        
        # مقياس جاكارد للتشابه
        if not lines1 or not lines2:
            return 0.0
        
        intersection = len(lines1.intersection(lines2))
        union = len(lines1.union(lines2))
        
        return intersection / union if union > 0 else 0.0
    
    def find_entity(self, name: str, entity_type: str = None) -> List[CodeEntity]:
        """
        البحث عن كيان بالاسم والنوع
        
        Args:
            name: اسم الكيان
            entity_type: نوع الكيان (اختياري)
            
        Returns:
            List[CodeEntity]: قائمة الكيانات المطابقة
        """
        found_entities = []
        
        for code_file in self.files.values():
            for entity in code_file.entities:
                if entity.name == name and (entity_type is None or entity.type == entity_type):
                    found_entities.append(entity)
                
                # البحث في الكيانات الفرعية
                for child in entity.children:
                    if child.name == name and (entity_type is None or child.type == entity_type):
                        found_entities.append(child)
        
        return found_entities
    
    def find_file(self, name: str) -> Optional[CodeFile]:
        """
        البحث عن ملف بالاسم
        
        Args:
            name: اسم الملف
            
        Returns:
            Optional[CodeFile]: الملف المطابق أو None
        """
        for path, code_file in self.files.items():
            if os.path.basename(path) == name:
                return code_file
        return None
    
    def get_project_structure(self) -> Dict[str, Any]:
        """
        الحصول على هيكل المشروع كشجرة
        
        Returns:
            Dict[str, Any]: هيكل المشروع
        """
        tree = {"name": self.name, "type": "directory", "children": []}
        
        # بناء القاموس للمجلدات
        directories = {}
        
        # إضافة الملفات إلى الشجرة
        for path in sorted(self.files.keys()):
            parts = path.split(os.sep)
            current_dir = tree
            
            # بناء المسار
            for i, part in enumerate(parts):
                if i < len(parts) - 1:  # إذا كان مجلداً
                    dir_path = os.sep.join(parts[:i+1])
                    
                    if dir_path not in directories:
                        new_dir = {"name": part, "type": "directory", "children": []}
                        current_dir["children"].append(new_dir)
                        directories[dir_path] = new_dir
                    
                    current_dir = directories[dir_path]
                else:  # إذا كان ملفاً
                    code_file = self.files[path]
                    file_info = {
                        "name": part,
                        "type": "file",
                        "language": code_file.language,
                        "entity_count": len(code_file.entities),
                        "file_size": code_file.file_size,
                        "line_count": code_file.line_count
                    }
                    current_dir["children"].append(file_info)
        
        return tree
    
    def add_issue(self, file_path: str, line: int, severity: str, message: str, 
                  description: str = None, recommendation: str = None,
                  source: str = None) -> Dict[str, Any]:
        """
        إضافة قضية للمشروع
        
        Args:
            file_path: مسار الملف
            line: رقم السطر
            severity: مستوى الخطورة
            message: رسالة موجزة
            description: وصف مفصل (اختياري)
            recommendation: توصية لحل المشكلة (اختياري)
            source: مصدر القضية (اختياري)
            
        Returns:
            Dict[str, Any]: القضية المضافة
        """
        # تحويل المسار المطلق إلى نسبي
        if os.path.isabs(file_path) and file_path.startswith(self.root_dir):
            relative_path = os.path.relpath(file_path, self.root_dir)
        else:
            relative_path = file_path
        
        issue = {
            "file_path": relative_path,
            "line": line,
            "severity": severity,
            "message": message,
            "description": description or message,
            "recommendation": recommendation or "",
            "source": source or "manual",
            "created_at": time.time()
        }
        
        self.issues.append(issue)
        
        # إضافة القضية أيضاً إلى الملف المعني
        if relative_path in self.files:
            code_file = self.files[relative_path]
            code_file.issues.append(issue)
        
        return issue
    
    def save_to_file(self, file_path: str) -> bool:
        """
        حفظ بيانات المشروع إلى ملف
        
        Args:
            file_path: مسار الملف
            
        Returns:
            bool: نجاح العملية
        """
        try:
            # التأكد من وجود المجلد
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # تحويل المشروع إلى قاموس
            project_data = self.to_dict()
            
            # حفظ البيانات كملف JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"خطأ في حفظ بيانات المشروع: {str(e)}")
            return False
    
    @classmethod
    def load_from_file(cls, file_path: str) -> Optional['Project']:
        """
        تحميل بيانات المشروع من ملف
        
        Args:
            file_path: مسار الملف
            
        Returns:
            Optional[Project]: المشروع المحمل أو None
        """
        try:
            # التحقق من وجود الملف
            if not os.path.exists(file_path):
                logger.error(f"ملف المشروع غير موجود: {file_path}")
                return None
            
            # قراءة البيانات من ملف JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            # إنشاء كائن المشروع
            root_dir = project_data.get("root_dir")
            if not root_dir or not os.path.exists(root_dir):
                logger.error(f"مجلد المشروع غير موجود: {root_dir}")
                return None
            
            project = cls(root_dir)
            project.from_dict(project_data)
            
            return project
        except Exception as e:
            logger.error(f"خطأ في تحميل بيانات المشروع: {str(e)}")
            return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        تحويل المشروع إلى قاموس
        
        Returns:
            Dict[str, Any]: بيانات المشروع
        """
        # تحويل الرسم البياني للاعتمادات
        dependency_data = None
        if self.dependency_graph:
            try:
                dependency_data = {
                    "nodes": list(self.dependency_graph.nodes()),
                    "edges": list(self.dependency_graph.edges())
                }
            except:
                dependency_data = None
        
        # بناء قاموس المشروع
        return {
            "name": self.name,
            "root_dir": self.root_dir,
            "project_type": self.project_type,
            "file_count": self.file_count,
            "entity_count": self.entity_count,
            "created_at": self.created_at,
            "last_modified": self.last_modified,
            "files": {path: file.to_dict() for path, file in self.files.items()},
            "dependency_graph": dependency_data,
            "issues": self.issues,
            "ai_analysis_results": self.ai_analysis_results,
            "metadata": self.metadata
        }
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        تحديث المشروع من قاموس
        
        Args:
            data: بيانات المشروع
        """
        self.name = data.get("name", self.name)
        self.root_dir = data.get("root_dir", self.root_dir)
        self.project_type = data.get("project_type")
        self.file_count = data.get("file_count", 0)
        self.entity_count = data.get("entity_count", 0)
        self.created_at = data.get("created_at", time.time())
        self.last_modified = data.get("last_modified", time.time())
        self.issues = data.get("issues", [])
        self.ai_analysis_results = data.get("ai_analysis_results", {})
        self.metadata = data.get("metadata", {})
        
        # إعادة بناء الملفات
        self.files = {}
        for path, file_data in data.get("files", {}).items():
            self.files[path] = CodeFile.from_dict(file_data)
        
        # إعادة بناء الرسم البياني للاعتمادات
        dependency_data = data.get("dependency_graph")
        if dependency_data:
            self.dependency_graph = nx.DiGraph()
            
            # إضافة العقد
            for node in dependency_data.get("nodes", []):
                self.dependency_graph.add_node(node)
            
            # إضافة الحواف
            for edge in dependency_data.get("edges", []):
                if len(edge) >= 2:
                    self.dependency_graph.add_edge(edge[0], edge[1])
        else:
            # إعادة بناء الرسم البياني
            self._build_dependency_graph()
    
    def __str__(self) -> str:
        return f"Project({self.name}, files={self.file_count}, entities={self.entity_count})"
    
    def __repr__(self) -> str:
        return self.__str__()