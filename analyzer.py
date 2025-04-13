#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
محركات تحليل الشيفرة البرمجية
"""
import os
import re
import json
import time
import logging
import threading
import atexit
from typing import Dict, List, Set, Any, Tuple, Optional, Union

from PySide6.QtCore import QObject, Signal, Slot, QThread

from project_model import ProjectModel, ProjectFolder, CodeFile
from api_clients import APIConfig, BaseAPIClient, get_api_client
from utils import read_file, save_json, write_file

logger = logging.getLogger("CodeAnalyzer.Analyzer")

# إدارة خيوط API
class APIThreadManager:
    """مدير خيوط API للتأكد من إيقافها عند إغلاق البرنامج"""
    
    _threads = set()
    
    @classmethod
    def register_thread(cls, thread):
        """تسجيل خيط جديد"""
        cls._threads.add(thread)
    
    @classmethod
    def unregister_thread(cls, thread):
        """إلغاء تسجيل خيط"""
        if thread in cls._threads:
            cls._threads.remove(thread)
    
    @classmethod
    def stop_all_threads(cls):
        """إيقاف جميع الخيوط النشطة"""
        for thread in list(cls._threads):
            if thread.isRunning():
                thread.terminate()
                thread.wait(1000)  # انتظار ثانية كحد أقصى
            cls.unregister_thread(thread)

# تسجيل دالة لإيقاف جميع الخيوط عند إغلاق البرنامج
atexit.register(APIThreadManager.stop_all_threads)

class LocalAnalyzer:
    """محلل الشيفرة البرمجية محلي بدون API"""
    
    def __init__(self):
        # القواعد البسيطة للتحليل المحلي
        self.rules = {
            "python": [
                {
                    "pattern": r"print\(",
                    "message": "استخدام print في كود الإنتاج",
                    "severity": "منخفضة"
                },
                {
                    "pattern": r"except\s*:",
                    "message": "استخدام except العام بدون تحديد نوع الاستثناء",
                    "severity": "متوسطة"
                },
                {
                    "pattern": r"import\s+\*",
                    "message": "استيراد كل الوحدات من حزمة (يفضل تحديد الوحدات المطلوبة)",
                    "severity": "منخفضة"
                },
                {
                    "pattern": r"^\s*#\s*TODO",
                    "message": "تعليق TODO موجود",
                    "severity": "منخفضة"
                },
                {
                    "pattern": r"exec\(",
                    "message": "استخدام exec لتنفيذ كود ديناميكي (خطر أمني محتمل)",
                    "severity": "عالية"
                },
                {
                    "pattern": r"os\.system\(",
                    "message": "استخدام os.system لتنفيذ أوامر النظام (خطر أمني محتمل)",
                    "severity": "عالية"
                }
            ],
            "php": [
                {
                    "pattern": r"mysql_",
                    "message": "استخدام دوال mysql_ المهملة",
                    "severity": "عالية"
                },
                {
                    "pattern": r"echo\s+\$_",
                    "message": "عرض متغيرات $_GET أو $_POST أو $_REQUEST مباشرة (خطر XSS)",
                    "severity": "عالية"
                },
                {
                    "pattern": r"eval\(\$",
                    "message": "استخدام eval على متغير (خطر أمني)",
                    "severity": "عالية"
                },
                {
                    "pattern": r"SELECT.+FROM.+WHERE.+\$_",
                    "message": "استخدام متغيرات $_GET أو $_POST في استعلام SQL (خطر SQL Injection)",
                    "severity": "عالية"
                },
                {
                    "pattern": r"\bdie\(",
                    "message": "استخدام die() في كود الإنتاج",
                    "severity": "متوسطة"
                }
            ],
            "javascript": [
                {
                    "pattern": r"console\.log\(",
                    "message": "استخدام console.log في كود الإنتاج",
                    "severity": "منخفضة"
                },
                {
                    "pattern": r"localStorage\.",
                    "message": "استخدام localStorage بدون تحقق من توفره",
                    "severity": "منخفضة"
                },
                {
                    "pattern": r"document\.write\(",
                    "message": "استخدام document.write (ممارسة سيئة)",
                    "severity": "متوسطة"
                },
                {
                    "pattern": r"eval\(",
                    "message": "استخدام eval (خطر أمني)",
                    "severity": "عالية"
                },
                {
                    "pattern": r"new\s+Function\(",
                    "message": "استخدام Function constructor (مماثل لـ eval)",
                    "severity": "عالية"
                }
            ],
            "dart": [
                {
                    "pattern": r"print\(",
                    "message": "استخدام print في كود الإنتاج",
                    "severity": "منخفضة"
                },
                {
                    "pattern": r"TODO",
                    "message": "تعليق TODO موجود",
                    "severity": "منخفضة"
                },
                {
                    "pattern": r"setState\(\(\)\s*=>",
                    "message": "استخدام setState قد يكون غير ضروري، فكر في استخدام StatefulBuilder",
                    "severity": "منخفضة"
                }
            ],
            "flutter": [
                {
                    "pattern": r"debugPrint\(",
                    "message": "استخدام debugPrint في كود الإنتاج",
                    "severity": "منخفضة"
                },
                {
                    "pattern": r"TODO",
                    "message": "تعليق TODO موجود",
                    "severity": "منخفضة"
                }
            ],
            "laravel_php": [
                {
                    "pattern": r"Route::.*",
                    "message": "تحقق من أمان نقاط النهاية في Laravel",
                    "severity": "متوسطة"
                }
            ],
            "css": [
                {
                    "pattern": r"!important",
                    "message": "استخدام !important (تجنب استخدامها إلا عند الضرورة)",
                    "severity": "منخفضة"
                }
            ],
            "html": [
                {
                    "pattern": r"<img[^>]+>",
                    "message": "تحقق من وجود بديل نصي alt للصورة",
                    "severity": "منخفضة"
                },
                {
                    "pattern": r"<a[^>]*>",
                    "message": "تحقق من وجود عنوان مناسب لرابط التنقل",
                    "severity": "منخفضة"
                }
            ]
        }
    
    def analyze_file(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """تحليل ملف وإرجاع قائمة بالمشاكل"""
        language = self._detect_language(file_path)
        if not language or language not in self.rules:
            return []
        
        issues = []
        lines = content.split('\n')
        
        for rule in self.rules[language]:
            pattern = rule["pattern"]
            
            for i, line in enumerate(lines):
                if re.search(pattern, line):
                    issues.append({
                        "file": file_path,
                        "line": i + 1,
                        "severity": rule["severity"],
                        "message": rule["message"],
                        "code": line.strip(),
                        "type": "quality"  # إضافة نوع المشكلة
                    })
        
        return issues
    
    def _detect_language(self, file_path: str) -> Optional[str]:
        """تحديد لغة البرمجة من امتداد الملف"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.py':
            return "python"
        elif ext == '.php':
            return "php"
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            return "javascript"
        elif ext == '.dart':
            return "dart"
        elif ext in ['.css', '.scss', '.sass']:
            return "css"
        elif ext in ['.html', '.htm']:
            return "html"
        
        return None


class SecurityAnalyzer:
    """محلل الثغرات الأمنية"""
    
    def __init__(self, api_config: APIConfig):
        self.api_config = api_config
        self.local_rules = {
            "php": [
                {
                    "pattern": r"\$_(?:GET|POST|REQUEST|COOKIE)\[['\"][^'\"]+['\"]\]",
                    "message": "استخدام متغيرات $_GET/$_POST/$_REQUEST دون تنظيف (خطر XSS)",
                    "severity": "عالية"
                },
                {
                    "pattern": r"echo\s+\$_",
                    "message": "عرض متغيرات HTTP دون تنظيف (خطر XSS)",
                    "severity": "عالية"
                },
                {
                    "pattern": r"mysqli_query\s*\(\s*\$[^,]+,\s*[\"']SELECT.+\$_",
                    "message": "استخدام استعلام SQL مع متغيرات HTTP (SQL Injection)",
                    "severity": "عالية"
                }
            ],
            "python": [
                {
                    "pattern": r"os\.system\s*\(|subprocess\.call\s*\(|subprocess\.Popen\s*\(",
                    "message": "استخدام أوامر النظام مع مدخلات المستخدم (خطر Remote Code Execution)",
                    "severity": "عالية"
                },
                {
                    "pattern": r"eval\s*\(|exec\s*\(",
                    "message": "استخدام eval/exec مع مدخلات المستخدم (خطر Code Injection)",
                    "severity": "عالية"
                },
                {
                    "pattern": r"open\s*\([^,]+,\s*['\"]w['\"]",
                    "message": "فتح ملف للكتابة مع مدخلات المستخدم (خطر Path Traversal)",
                    "severity": "متوسطة"
                },
                {
                    "pattern": r"flask.*send_file\(",
                    "message": "تحقق من مسار الملف في send_file لتجنب Path Traversal",
                    "severity": "متوسطة"
                },
                {
                    "pattern": r"flask.*render_template\([^,]+\+",
                    "message": "استخدام مدخلات المستخدم في مسار القالب (خطر Template Injection)",
                    "severity": "عالية"
                }
            ],
            "javascript": [
                {
                    "pattern": r"eval\s*\(|new\s+Function\s*\(",
                    "message": "استخدام eval أو Function constructor (خطر XSS)",
                    "severity": "عالية"
                },
                {
                    "pattern": r"innerHTML\s*=|document\.write\s*\(",
                    "message": "استخدام innerHTML أو document.write مع مدخلات المستخدم (خطر XSS)",
                    "severity": "عالية"
                },
                {
                    "pattern": r"localStorage\.|sessionStorage\.",
                    "message": "تخزين بيانات حساسة في localStorage/sessionStorage",
                    "severity": "متوسطة"
                },
                {
                    "pattern": r"location\.(href|replace|assign)\s*=",
                    "message": "توجيه URL غير آمن (خطر Open Redirect)",
                    "severity": "متوسطة"
                }
            ],
            "html": [
                {
                    "pattern": r"<form[^>]*method=['\"]get['\"]",
                    "message": "استخدام GET في النماذج للبيانات الحساسة (غير آمن)",
                    "severity": "متوسطة"
                },
                {
                    "pattern": r"<input[^>]*type=['\"]password['\"][^>]*autocomplete=['\"]off['\"]",
                    "message": "منع الملء التلقائي للكلمات السرية قد لا يعمل في كل المتصفحات",
                    "severity": "منخفضة"
                }
            ]
        }
    
    def analyze_file(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """تحليل ملف للثغرات الأمنية محلياً"""
        language = self._detect_language(file_path)
        if not language or language not in self.local_rules:
            return []
        
        issues = []
        lines = content.split('\n')
        
        for rule in self.local_rules[language]:
            pattern = rule["pattern"]
            
            for i, line in enumerate(lines):
                if re.search(pattern, line):
                    issues.append({
                        "file": file_path,
                        "line": i + 1,
                        "severity": rule["severity"],
                        "message": rule["message"],
                        "code": line.strip(),
                        "type": "security"  # تحديد نوع المشكلة
                    })
        
        return issues
    
    def analyze_with_api(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """تحليل ملف للثغرات الأمنية باستخدام API"""
        language = self._detect_language(file_path)
        if not language:
            return []
        
        try:
            client = get_api_client(self.api_config)
            result = client.analyze_security(content, language)
            
            if "issues" in result and isinstance(result["issues"], list):
                # تحويل النتائج إلى التنسيق المطلوب
                issues = []
                for issue in result["issues"]:
                    issues.append({
                        "file": file_path,
                        "line": issue.get("line", 1),
                        "severity": issue.get("severity", "متوسطة"),
                        "message": issue.get("message", ""),
                        "code": issue.get("code", ""),
                        "type": "security",
                        "description": issue.get("description", ""),
                        "recommendation": issue.get("recommendation", "")
                    })
                return issues
            return []
        
        except Exception as e:
            logger.error(f"خطأ في تحليل الأمان باستخدام API: {str(e)}")
            return []
    
    def _detect_language(self, file_path: str) -> Optional[str]:
        """تحديد لغة البرمجة من امتداد الملف"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.py':
            return "python"
        elif ext == '.php':
            return "php"
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            return "javascript"
        elif ext in ['.html', '.htm']:
            return "html"
        
        return None


class CodeQualityAnalyzer:
    """محلل جودة الشيفرة البرمجية باستخدام API"""
    
    def __init__(self, api_config: APIConfig):
        self.api_config = api_config
    
    def analyze_file(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """تحليل ملف لجودة الشيفرة البرمجية"""
        language = self._detect_language(file_path)
        if not language:
            return []
        
        try:
            client = get_api_client(self.api_config)
            result = client.analyze_code(content, language)
            
            if "issues" in result and isinstance(result["issues"], list):
                # تحويل النتائج إلى التنسيق المطلوب
                issues = []
                for issue in result["issues"]:
                    issues.append({
                        "file": file_path,
                        "line": issue.get("line", 1),
                        "severity": issue.get("severity", "متوسطة"),
                        "message": issue.get("message", ""),
                        "code": issue.get("code", ""),
                        "type": "quality",
                        "description": issue.get("description", ""),
                        "recommendation": issue.get("recommendation", "")
                    })
                return issues
            return []
        
        except Exception as e:
            logger.error(f"خطأ في تحليل جودة الشيفرة باستخدام API: {str(e)}")
            return []
    
    def _detect_language(self, file_path: str) -> Optional[str]:
        """تحديد لغة البرمجة من امتداد الملف"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.py':
            return "python"
        elif ext == '.php':
            return "php"
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            return "javascript"
        elif ext == '.dart':
            return "dart"
        elif ext in ['.html', '.htm']:
            return "html"
        elif ext in ['.css', '.scss', '.sass']:
            return "css"
        
        return None


class AnalysisThread(QThread):
    """خيط لتنفيذ التحليل بشكل غير متزامن"""
    
    analysis_completed = Signal(object)  # إشارة لإكمال التحليل
    analysis_progress = Signal(int, int)  # إشارة للتقدم (الملف الحالي، إجمالي الملفات)
    
    def __init__(self, analyzers, files_to_analyze, parent=None):
        super().__init__(parent)
        self.analyzers = analyzers
        self.files_to_analyze = files_to_analyze
        self.results = {
            "issues": [],
            "stats": {
                "total_files": len(files_to_analyze),
                "analyzed_files": 0,
                "total_issues": 0,
                "severity_counts": {
                    "عالية": 0,
                    "متوسطة": 0,
                    "منخفضة": 0
                },
                "type_counts": {  # إضافة إحصائيات حسب النوع
                    "quality": 0,
                    "security": 0
                }
            }
        }
        self.abort_flag = False  # علم لإيقاف التحليل
        
        # تسجيل الخيط في مدير الخيوط
        APIThreadManager.register_thread(self)
    
    def run(self):
        """تنفيذ التحليل"""
        try:
            for i, file_info in enumerate(self.files_to_analyze):
                # التحقق من طلب إلغاء التحليل
                if self.abort_flag:
                    break
                    
                file_path = file_info["path"]
                content = file_info.get("content")
                
                # قراءة محتوى الملف إذا لم يتم توفيره
                if content is None:
                    content = read_file(file_path)
                    if content is None:
                        continue
                
                # تحليل الملف باستخدام كل محلل
                file_issues = []
                for analyzer in self.analyzers:
                    issues = analyzer.analyze_file(file_path, content)
                    file_issues.extend(issues)
                
                # إضافة المشاكل إلى النتائج
                self.results["issues"].extend(file_issues)
                
                # تحديث الإحصائيات
                self.results["stats"]["analyzed_files"] += 1
                self.results["stats"]["total_issues"] += len(file_issues)
                
                for issue in file_issues:
                    severity = issue.get("severity", "متوسطة")
                    if severity in self.results["stats"]["severity_counts"]:
                        self.results["stats"]["severity_counts"][severity] += 1
                    
                    issue_type = issue.get("type", "quality")
                    if issue_type in self.results["stats"]["type_counts"]:
                        self.results["stats"]["type_counts"][issue_type] += 1
                
                # إرسال إشارة التقدم
                self.analysis_progress.emit(i + 1, len(self.files_to_analyze))
            
            # ترتيب المشاكل حسب الخطورة
            self.results["issues"].sort(
                key=lambda x: {"عالية": 0, "متوسطة": 1, "منخفضة": 2}.get(x.get("severity", "متوسطة"), 3)
            )
            
            # إرسال إشارة اكتمال التحليل
            self.analysis_completed.emit(self.results)
        
        finally:
            # إلغاء تسجيل الخيط عند الانتهاء
            APIThreadManager.unregister_thread(self)
    
    def abort(self):
        """إلغاء التحليل"""
        self.abort_flag = True


class AnalysisManager(QObject):
    """مدير التحليل"""
    
    signal_analysis_progress = Signal(int, int)  # إشارة لتقدم التحليل (الحالي، الإجمالي)
    signal_analysis_completed = Signal(object)  # إشارة لاكتمال التحليل ونتائجه
    
    def __init__(self, api_config: APIConfig):
        super().__init__()
        self.api_config = api_config
        self.local_analyzer = LocalAnalyzer()
        self.security_analyzer = SecurityAnalyzer(api_config)
        self.quality_analyzer = CodeQualityAnalyzer(api_config)
        self.analysis_thread = None
        self.last_results = None
    
    def set_api_config(self, api_config: APIConfig):
        """تحديث إعدادات API"""
        self.api_config = api_config
        self.security_analyzer = SecurityAnalyzer(api_config)
        self.quality_analyzer = CodeQualityAnalyzer(api_config)
    
    def analyze_project(self, project_model: ProjectModel):
        """تحليل المشروع بالكامل"""
        # التأكد من عدم وجود تحليل جارٍ
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.abort_analysis()
            self.analysis_thread.wait()
        
        # الحصول على قائمة الملفات للتحليل
        files_to_analyze = []
        for code_file in project_model.get_code_files():
            files_to_analyze.append({
                "path": code_file.file_path,
                "content": None  # سيتم قراءة المحتوى في الخيط
            })
        
        # إعداد المحللات
        analyzers = [self.local_analyzer]
        
        # إذا كان مفتاح API متوفر، أضف المحللات المتقدمة
        if self.api_config.get_api_key(self.api_config.preferred_provider):
            analyzers.append(self.quality_analyzer)
            analyzers.append(self.security_analyzer)
        
        # بدء خيط التحليل
        self.analysis_thread = AnalysisThread(analyzers, files_to_analyze)
        self.analysis_thread.analysis_progress.connect(self.on_analysis_progress)
        self.analysis_thread.analysis_completed.connect(self.on_analysis_completed)
        self.analysis_thread.start()
    
    def analyze_file(self, file_path: str, content: str):
        """تحليل ملف واحد"""
        # التأكد من عدم وجود تحليل جارٍ
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.abort_analysis()
            self.analysis_thread.wait()
        
        # إعداد المحللات
        analyzers = [self.local_analyzer]
        
        # إذا كان مفتاح API متوفر، أضف المحللات المتقدمة
        if self.api_config.get_api_key(self.api_config.preferred_provider):
            analyzers.append(self.quality_analyzer)
            analyzers.append(self.security_analyzer)
        
        # بدء خيط التحليل
        self.analysis_thread = AnalysisThread(analyzers, [{"path": file_path, "content": content}])
        self.analysis_thread.analysis_progress.connect(self.on_analysis_progress)
        self.analysis_thread.analysis_completed.connect(self.on_analysis_completed)
        self.analysis_thread.start()
    
    def abort_analysis(self):
        """إيقاف التحليل الجاري"""
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.analysis_thread.abort()
    
    def on_analysis_progress(self, current, total):
        """معالجة إشارة تقدم التحليل"""
        # إعادة إرسال إشارة التقدم
        self.signal_analysis_progress.emit(current, total)
    
    def on_analysis_completed(self, results):
        """معالجة إشارة اكتمال التحليل"""
        self.last_results = results
        
        # حفظ النتائج إلى ملف (اختياري)
        results_dir = os.path.join(os.path.expanduser("~"), ".code_analyzer", "results")
        os.makedirs(results_dir, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(results_dir, f"analysis_results_{timestamp}.json")
        save_json(results_file, results)
        
        # إرسال إشارة اكتمال التحليل
        self.signal_analysis_completed.emit(results)
    
    def get_last_results(self):
        """الحصول على نتائج آخر تحليل"""
        return self.last_results
    
    def filter_results_by_severity(self, severity: str) -> Dict[str, Any]:
        """تصفية النتائج حسب مستوى الخطورة"""
        if not self.last_results:
            return {"issues": [], "stats": {}}
        
        filtered_issues = [issue for issue in self.last_results["issues"]
                         if issue.get("severity") == severity]
        
        return {
            "issues": filtered_issues,
            "stats": {
                "total_issues": len(filtered_issues)
            }
        }
    
    def filter_results_by_type(self, issue_type: str) -> Dict[str, Any]:
        """تصفية النتائج حسب نوع المشكلة"""
        if not self.last_results:
            return {"issues": [], "stats": {}}
        
        filtered_issues = [issue for issue in self.last_results["issues"]
                         if issue.get("type") == issue_type]
        
        return {
            "issues": filtered_issues,
            "stats": {
                "total_issues": len(filtered_issues)
            }
        }
    
    def generate_report(self, report_path: str) -> bool:
        """إنشاء تقرير تحليل ملف HTML"""
        if not self.last_results:
            return False
        
        try:
            from utils import create_html_report
            return create_html_report(report_path, self.last_results)
        except Exception as e:
            logger.error(f"خطأ في إنشاء تقرير التحليل: {str(e)}")
            return False


class ModificationsManager:
    """مدير التعديلات المقترحة"""
    
    def __init__(self, project_model: ProjectModel):
        self.project_model = project_model
        self.pending_modifications = []
        self.applied_modifications = []
        
        # تحميل التعديلات المعلقة
        self._load_pending_modifications()
        self._load_applied_modifications()
    
    def _load_pending_modifications(self):
        """تحميل التعديلات المعلقة من ملف"""
        if not self.project_model:
            return
        
        mods_dir = os.path.join(self.project_model.project_dir, ".code_analyzer")
        if not os.path.exists(mods_dir):
            os.makedirs(mods_dir, exist_ok=True)
            return
        
        mods_file = os.path.join(mods_dir, "pending_modifications.json")
        if os.path.exists(mods_file):
            try:
                with open(mods_file, 'r', encoding='utf-8') as f:
                    self.pending_modifications = json.load(f)
            except Exception as e:
                logger.error(f"خطأ في تحميل التعديلات المعلقة: {str(e)}")
    
    def _save_pending_modifications(self):
        """حفظ التعديلات المعلقة إلى ملف"""
        if not self.project_model:
            return
        
        mods_dir = os.path.join(self.project_model.project_dir, ".code_analyzer")
        os.makedirs(mods_dir, exist_ok=True)
        
        mods_file = os.path.join(mods_dir, "pending_modifications.json")
        try:
            with open(mods_file, 'w', encoding='utf-8') as f:
                json.dump(self.pending_modifications, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ التعديلات المعلقة: {str(e)}")
    
    def _load_applied_modifications(self):
        """تحميل التعديلات المطبقة من ملف"""
        if not self.project_model:
            return
        
        mods_dir = os.path.join(self.project_model.project_dir, ".code_analyzer")
        mods_file = os.path.join(mods_dir, "applied_modifications.json")
        if os.path.exists(mods_file):
            try:
                with open(mods_file, 'r', encoding='utf-8') as f:
                    self.applied_modifications = json.load(f)
            except Exception as e:
                logger.error(f"خطأ في تحميل التعديلات المطبقة: {str(e)}")
    
    def _save_applied_modifications(self):
        """حفظ التعديلات المطبقة إلى ملف"""
        if not self.project_model:
            return
        
        mods_dir = os.path.join(self.project_model.project_dir, ".code_analyzer")
        os.makedirs(mods_dir, exist_ok=True)
        
        mods_file = os.path.join(mods_dir, "applied_modifications.json")
        try:
            with open(mods_file, 'w', encoding='utf-8') as f:
                json.dump(self.applied_modifications, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ التعديلات المطبقة: {str(e)}")
    
    def add_modification(self, modification: Dict[str, Any]) -> bool:
        """إضافة تعديل مقترح إلى القائمة"""
        # التحقق من صحة التعديل
        if not self._validate_modification(modification):
            return False
        
        # إضافة timestamp للتعديل
        modification["timestamp"] = time.time()
        modification["id"] = f"mod_{int(time.time() * 1000)}"
        
        # إضافة التعديل إلى القائمة
        self.pending_modifications.append(modification)
        
        # حفظ التعديلات المعلقة
        self._save_pending_modifications()
        
        return True
    
    def add_batch_modifications(self, modifications: List[Dict[str, Any]]) -> int:
        """إضافة مجموعة من التعديلات المقترحة"""
        success_count = 0
        for mod in modifications:
            if self.add_modification(mod):
                success_count += 1
        return success_count
    
    def remove_modification(self, modification_id: str) -> bool:
        """إزالة تعديل من القائمة بواسطة المعرف"""
        for i, mod in enumerate(self.pending_modifications):
            if mod.get("id") == modification_id:
                del self.pending_modifications[i]
                self._save_pending_modifications()
                return True
        return False
    
    def get_pending_modifications(self) -> List[Dict[str, Any]]:
        """الحصول على قائمة التعديلات المعلقة"""
        return self.pending_modifications
    
    def get_applied_modifications(self) -> List[Dict[str, Any]]:
        """الحصول على قائمة التعديلات المطبقة"""
        return self.applied_modifications
    
    def has_pending_modifications(self) -> bool:
        """التحقق مما إذا كانت هناك تعديلات معلقة"""
        return len(self.pending_modifications) > 0
    
    def has_pending_modifications_for_file(self, file_path: str) -> bool:
        """التحقق مما إذا كانت هناك تعديلات معلقة للملف المحدد"""
        return any(mod.get("file_path") == file_path for mod in self.pending_modifications)
    
    def get_modification_by_id(self, modification_id: str) -> Optional[Dict[str, Any]]:
        """الحصول على تعديل بواسطة المعرف"""
        for mod in self.pending_modifications:
            if mod.get("id") == modification_id:
                return mod
        return None
    
    def apply_modifications(self, selected_ids: List[str]) -> List[Dict[str, Any]]:
        """تطبيق التعديلات المحددة"""
        applied = []
        errors = []
        
        for mod_id in selected_ids:
            mod = self.get_modification_by_id(mod_id)
            if mod:
                file_path = mod.get("file_path")
                new_content = mod.get("content")
                
                if file_path and new_content and os.path.exists(file_path):
                    try:
                        # قراءة المحتوى الحالي للملف
                        current_content = read_file(file_path)
                        
                        # كتابة المحتوى الجديد
                        success = write_file(file_path, new_content)
                        if not success:
                            raise Exception(f"فشل في كتابة الملف: {file_path}")
                        
                        # إضافة التعديل إلى قائمة التعديلات المطبقة
                        mod_copy = mod.copy()
                        mod_copy["previous_content"] = current_content
                        mod_copy["applied_at"] = time.time()
                        self.applied_modifications.append(mod_copy)
                        
                        # إزالة التعديل من قائمة التعديلات المعلقة
                        self.remove_modification(mod_id)
                        
                        # إضافة إلى قائمة التعديلات المطبقة
                        applied.append(mod_copy)
                    
                    except Exception as e:
                        errors.append({
                            "id": mod_id,
                            "file_path": file_path,
                            "error": str(e)
                        })
        
        # حفظ التعديلات المطبقة
        self._save_applied_modifications()
        
        return applied
    
    def apply_all_modifications(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """تطبيق جميع التعديلات المعلقة"""
        mod_ids = [mod.get("id") for mod in self.pending_modifications]
        applied = self.apply_modifications(mod_ids)
        
        # حساب الأخطاء
        applied_ids = [mod.get("id") for mod in applied]
        errors = [mod for mod in self.pending_modifications if mod.get("id") not in applied_ids]
        
        return applied, errors
    
    def _validate_modification(self, modification: Dict[str, Any]) -> bool:
        """التحقق من صحة التعديل"""
        # التحقق من وجود المفاتيح المطلوبة
        required_keys = ["file_path", "content", "description"]
        for key in required_keys:
            if key not in modification:
                logger.error(f"التعديل يفتقد للمفتاح المطلوب: {key}")
                return False
        
        # التحقق من وجود الملف
        file_path = modification["file_path"]
        if not os.path.exists(file_path):
            logger.error(f"الملف غير موجود: {file_path}")
            return False
        
        return True
    
    def revert_modification(self, modification_id: str) -> bool:
        """التراجع عن تعديل تم تطبيقه"""
        for i, mod in enumerate(self.applied_modifications):
            if mod.get("id") == modification_id:
                file_path = mod.get("file_path")
                previous_content = mod.get("previous_content")
                
                if file_path and previous_content and os.path.exists(file_path):
                    try:
                        # كتابة المحتوى السابق
                        success = write_file(file_path, previous_content)
                        if not success:
                            raise Exception(f"فشل في استعادة الملف: {file_path}")
                        
                        # إزالة التعديل من قائمة التعديلات المطبقة
                        del self.applied_modifications[i]
                        self._save_applied_modifications()
                        
                        # إعادة التعديل إلى قائمة التعديلات المعلقة (اختياري)
                        mod_copy = mod.copy()
                        del mod_copy["previous_content"]  # حذف المحتوى السابق
                        del mod_copy["applied_at"]  # حذف وقت التطبيق
                        self.pending_modifications.append(mod_copy)
                        self._save_pending_modifications()
                        
                        return True
                    
                    except Exception as e:
                        logger.error(f"خطأ في التراجع عن التعديل: {str(e)}")
        
        return False
    
    def create_modification_from_issue(self, issue: Dict[str, Any], new_content: str) -> Dict[str, Any]:
        """إنشاء تعديل مقترح من مشكلة"""
        return {
            "file_path": issue.get("file", ""),
            "content": new_content,
            "description": f"إصلاح مشكلة: {issue.get('message', '')}",
            "issue_line": issue.get("line", 0),
            "severity": issue.get("severity", "متوسطة"),
            "type": issue.get("type", "quality")
        }