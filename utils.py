#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
أدوات مساعدة عامة للبرنامج
"""
import os
import re
import json
import hashlib
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Union, Set

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("code_analyzer.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CodeAnalyzer.Utils")

# أنواع الملفات المدعومة
SUPPORTED_EXTENSIONS = {
    'python': ['.py', '.pyw', '.pyi'],
    'flutter_dart': ['.dart'],
    'laravel_php': ['.php', '.blade.php'],
    'javascript': ['.js', '.jsx', '.ts', '.tsx'],
    'html': ['.html', '.htm'],
    'css': ['.css', '.scss', '.sass'],
    'json': ['.json']
}

# المجلدات التي يتم تجاهلها بشكل افتراضي
DEFAULT_EXCLUDED_DIRS = [
    '__pycache__', '.git', '.svn', 'node_modules', 'venv', 'env',
    '.DS_Store', '.idea', '.vscode', 'dist', 'build', '.pytest_cache',
    '.next', 'bin', 'obj', 'target', 'vendor'
]

def get_file_type(file_path: str) -> Optional[str]:
    """
    تحديد نوع الملف بناءً على الامتداد
    
    Args:
        file_path: مسار الملف
        
    Returns:
        نوع الملف (لغة البرمجة) أو None إذا كان النوع غير مدعوم
    """
    ext = os.path.splitext(file_path)[1].lower()
    for lang, extensions in SUPPORTED_EXTENSIONS.items():
        if ext in extensions:
            return lang
    return None

def read_file(file_path: str) -> Optional[str]:
    """
    قراءة محتوى الملف
    
    Args:
        file_path: مسار الملف
        
    Returns:
        محتوى الملف كنص أو None في حالة الخطأ
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            # محاولة قراءة الملف بترميز مختلف
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            logger.error(f"خطأ في قراءة الملف {file_path} بترميز latin-1: {str(e)}")
            return None
    except FileNotFoundError:
        logger.error(f"الملف غير موجود: {file_path}")
        return None
    except Exception as e:
        logger.error(f"خطأ في قراءة الملف {file_path}: {str(e)}")
        return None

def write_file(file_path: str, content: str) -> bool:
    """
    كتابة محتوى إلى ملف
    
    Args:
        file_path: مسار الملف
        content: المحتوى المراد كتابته
        
    Returns:
        True إذا نجحت العملية، False في حالة الخطأ
    """
    try:
        # التأكد من وجود المجلد
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"خطأ في كتابة الملف {file_path}: {str(e)}")
        return False

def append_to_file(file_path: str, content: str) -> bool:
    """
    إضافة محتوى إلى نهاية ملف
    
    Args:
        file_path: مسار الملف
        content: المحتوى المراد إضافته
        
    Returns:
        True إذا نجحت العملية، False في حالة الخطأ
    """
    try:
        # التأكد من وجود المجلد
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"خطأ في الإضافة إلى الملف {file_path}: {str(e)}")
        return False

def read_binary_file(file_path: str) -> Optional[bytes]:
    """
    قراءة محتوى الملف بشكل ثنائي
    
    Args:
        file_path: مسار الملف
        
    Returns:
        محتوى الملف كبيانات ثنائية أو None في حالة الخطأ
    """
    try:
        with open(file_path, 'rb') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"الملف غير موجود: {file_path}")
        return None
    except Exception as e:
        logger.error(f"خطأ في قراءة الملف الثنائي {file_path}: {str(e)}")
        return None

def write_binary_file(file_path: str, content: bytes) -> bool:
    """
    كتابة محتوى ثنائي إلى ملف
    
    Args:
        file_path: مسار الملف
        content: المحتوى الثنائي المراد كتابته
        
    Returns:
        True إذا نجحت العملية، False في حالة الخطأ
    """
    try:
        # التأكد من وجود المجلد
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        with open(file_path, 'wb') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"خطأ في كتابة الملف الثنائي {file_path}: {str(e)}")
        return False

def calculate_file_hash(file_path: str) -> Optional[str]:
    """
    حساب القيمة المختصرة (hash) للملف
    
    Args:
        file_path: مسار الملف
        
    Returns:
        قيمة MD5 hash للملف أو None في حالة الخطأ
    """
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except FileNotFoundError:
        logger.error(f"الملف غير موجود: {file_path}")
        return None
    except Exception as e:
        logger.error(f"خطأ في حساب hash للملف {file_path}: {str(e)}")
        return None

def file_exists(file_path: str) -> bool:
    """
    التحقق من وجود ملف
    
    Args:
        file_path: مسار الملف
        
    Returns:
        True إذا كان الملف موجوداً، False في حالة عدم وجوده
    """
    return os.path.isfile(file_path)

def directory_exists(directory_path: str) -> bool:
    """
    التحقق من وجود مجلد
    
    Args:
        directory_path: مسار المجلد
        
    Returns:
        True إذا كان المجلد موجوداً، False في حالة عدم وجوده
    """
    return os.path.isdir(directory_path)

def create_directory(directory_path: str) -> bool:
    """
    إنشاء مجلد جديد
    
    Args:
        directory_path: مسار المجلد
        
    Returns:
        True إذا نجحت العملية، False في حالة الخطأ
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"خطأ في إنشاء المجلد {directory_path}: {str(e)}")
        return False

def delete_file(file_path: str) -> bool:
    """
    حذف ملف
    
    Args:
        file_path: مسار الملف
        
    Returns:
        True إذا نجحت العملية، False في حالة الخطأ
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        return True
    except Exception as e:
        logger.error(f"خطأ في حذف الملف {file_path}: {str(e)}")
        return False

def copy_file(source_path: str, destination_path: str) -> bool:
    """
    نسخ ملف
    
    Args:
        source_path: مسار الملف المصدر
        destination_path: مسار الوجهة
        
    Returns:
        True إذا نجحت العملية، False في حالة الخطأ
    """
    try:
        # التأكد من وجود المجلد
        directory = os.path.dirname(destination_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        shutil.copy2(source_path, destination_path)
        return True
    except Exception as e:
        logger.error(f"خطأ في نسخ الملف من {source_path} إلى {destination_path}: {str(e)}")
        return False

def find_files(directory: str, extensions: List[str] = None, excluded_dirs: List[str] = None) -> List[str]:
    """
    البحث عن ملفات في مجلد بناءً على الامتدادات المحددة
    
    Args:
        directory: مسار المجلد
        extensions: قائمة بامتدادات الملفات المطلوبة
        excluded_dirs: قائمة بأسماء المجلدات المستثناة
        
    Returns:
        قائمة بمسارات الملفات المطابقة
    """
    result = []
    
    if not os.path.exists(directory):
        logger.error(f"المجلد غير موجود: {directory}")
        return result
    
    if not os.path.isdir(directory):
        logger.error(f"المسار ليس مجلداً: {directory}")
        return result
    
    if extensions is None:
        # إذا لم يتم تحديد امتدادات، استخدم جميع الامتدادات المدعومة
        extensions = []
        for ext_list in SUPPORTED_EXTENSIONS.values():
            extensions.extend(ext_list)
    
    if excluded_dirs is None:
        excluded_dirs = DEFAULT_EXCLUDED_DIRS
    
    for root, dirs, files in os.walk(directory):
        # استثناء المجلدات المحددة
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
        
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                result.append(os.path.join(root, file))
    
    return result

def find_directories(directory: str, excluded_dirs: List[str] = None) -> List[str]:
    """
    البحث عن المجلدات الفرعية في مجلد
    
    Args:
        directory: مسار المجلد
        excluded_dirs: قائمة بأسماء المجلدات المستثناة
        
    Returns:
        قائمة بمسارات المجلدات المطابقة
    """
    result = []
    
    if not os.path.exists(directory):
        logger.error(f"المجلد غير موجود: {directory}")
        return result
    
    if not os.path.isdir(directory):
        logger.error(f"المسار ليس مجلداً: {directory}")
        return result
    
    if excluded_dirs is None:
        excluded_dirs = DEFAULT_EXCLUDED_DIRS
    
    for root, dirs, _ in os.walk(directory):
        # استثناء المجلدات المحددة
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
        
        for dir_name in dirs:
            result.append(os.path.join(root, dir_name))
    
    return result

def detect_project_type(directory: str) -> str:
    """
    تحديد نوع المشروع تلقائيًا بناءً على الملفات الموجودة
    
    Args:
        directory: مسار المجلد
        
    Returns:
        نوع المشروع (python, flutter_dart, laravel_php, javascript, react, etc.)
    """
    if not os.path.exists(directory) or not os.path.isdir(directory):
        logger.error(f"المجلد غير صالح: {directory}")
        return "unknown"
    
    # البحث عن ملفات مميزة لتحديد نوع المشروع
    files = os.listdir(directory)
    root_files = [f.lower() for f in files]
    
    # التحقق من وجود ملفات مميزة للمشاريع المختلفة
    if 'pubspec.yaml' in root_files or 'pubspec.yml' in root_files:
        return 'flutter_dart'
    elif 'composer.json' in root_files or 'artisan' in root_files:
        return 'laravel_php'
    elif 'package.json' in root_files:
        # التمييز بين مشاريع JavaScript المختلفة
        package_json_path = os.path.join(directory, 'package.json')
        try:
            with open(package_json_path, 'r', encoding='utf-8') as f:
                package_data = json.load(f)
                
            # التحقق من المكتبات المستخدمة
            dependencies = {**package_data.get('dependencies', {}), **package_data.get('devDependencies', {})}
            
            if 'react' in dependencies:
                return 'react'
            elif 'vue' in dependencies:
                return 'vue'
            elif 'angular' in dependencies or '@angular/core' in dependencies:
                return 'angular'
            elif 'svelte' in dependencies:
                return 'svelte'
            else:
                return 'javascript'
        except:
            # إذا لم يمكن قراءة ملف package.json، ابحث عن ملفات معينة
            if any(f.endswith('.tsx') or f.endswith('.jsx') for f in find_files(directory, ['.tsx', '.jsx'])):
                return 'react'
            return 'javascript'
    elif 'requirements.txt' in root_files or 'setup.py' in root_files or 'pyproject.toml' in root_files:
        return 'python'
    elif 'build.gradle' in root_files or 'settings.gradle' in root_files:
        return 'android'
    elif 'pom.xml' in root_files:
        return 'java_maven'
    elif 'build.sbt' in root_files:
        return 'scala'
    elif 'go.mod' in root_files:
        return 'golang'
    elif 'cargo.toml' in root_files:
        return 'rust'
    
    # إذا لم يتم التعرف على نوع المشروع، حاول تحديده عن طريق إحصاء أنواع الملفات
    file_counts = {}
    for lang, extensions in SUPPORTED_EXTENSIONS.items():
        file_counts[lang] = len(find_files(directory, extensions))
    
    # إرجاع النوع الأكثر شيوعًا
    if file_counts:
        return max(file_counts.items(), key=lambda x: x[1])[0]
    
    return 'unknown'

def get_project_metadata(directory: str) -> Dict[str, Any]:
    """
    استخراج البيانات الوصفية للمشروع
    
    Args:
        directory: مسار المجلد
        
    Returns:
        قاموس بالبيانات الوصفية للمشروع
    """
    metadata = {
        "name": os.path.basename(directory),
        "type": detect_project_type(directory),
        "path": directory,
        "files_count": 0,
        "directories_count": 0,
        "languages": {}
    }
    
    # عد الملفات حسب اللغة
    for lang, extensions in SUPPORTED_EXTENSIONS.items():
        files = find_files(directory, extensions)
        if files:
            metadata["languages"][lang] = len(files)
            metadata["files_count"] += len(files)
    
    # عد المجلدات
    metadata["directories_count"] = len(find_directories(directory))
    
    # إضافة معلومات إضافية حسب نوع المشروع
    project_type = metadata["type"]
    
    if project_type == "python":
        # البحث عن معلومات من setup.py أو pyproject.toml
        setup_py = os.path.join(directory, "setup.py")
        pyproject_toml = os.path.join(directory, "pyproject.toml")
        
        if os.path.exists(pyproject_toml):
            try:
                with open(pyproject_toml, 'r', encoding='utf-8') as f:
                    import toml
                    toml_data = toml.loads(f.read())
                    
                    if "tool" in toml_data and "poetry" in toml_data["tool"]:
                        poetry_data = toml_data["tool"]["poetry"]
                        metadata["name"] = poetry_data.get("name", metadata["name"])
                        metadata["version"] = poetry_data.get("version", "")
                        metadata["description"] = poetry_data.get("description", "")
                        metadata["dependencies"] = list(poetry_data.get("dependencies", {}).keys())
            except:
                pass
    
    elif project_type in ["javascript", "react", "vue", "angular"]:
        # البحث عن معلومات من package.json
        package_json = os.path.join(directory, "package.json")
        
        if os.path.exists(package_json):
            try:
                with open(package_json, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)
                    
                    metadata["name"] = package_data.get("name", metadata["name"])
                    metadata["version"] = package_data.get("version", "")
                    metadata["description"] = package_data.get("description", "")
                    metadata["dependencies"] = list(package_data.get("dependencies", {}).keys())
            except:
                pass
    
    return metadata

def save_json(data: Any, file_path: str) -> bool:
    """
    حفظ بيانات بصيغة JSON
    
    Args:
        data: البيانات المراد حفظها
        file_path: مسار الملف
        
    Returns:
        True إذا نجحت العملية، False في حالة الخطأ
    """
    try:
        # التأكد من وجود المجلد
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"خطأ في حفظ ملف JSON {file_path}: {str(e)}")
        return False

def load_json(file_path: str) -> Optional[Any]:
    """
    تحميل بيانات من ملف JSON
    
    Args:
        file_path: مسار الملف
        
    Returns:
        البيانات المحملة أو None في حالة الخطأ
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"ملف JSON غير موجود: {file_path}")
            return None
            
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.error(f"خطأ في تنسيق ملف JSON {file_path}")
        return None
    except Exception as e:
        logger.error(f"خطأ في قراءة ملف JSON {file_path}: {str(e)}")
        return None

def create_html_report(data: Dict[str, Any], output_path: str) -> bool:
    """
    إنشاء تقرير HTML تفاعلي من نتائج التحليل
    
    Args:
        data: بيانات التحليل
        output_path: مسار ملف الإخراج
        
    Returns:
        True إذا نجحت العملية، False في حالة الخطأ
    """
    # نموذج قالب HTML بسيط
    html_template = """<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>تقرير تحليل الشيفرة البرمجية</title>
    <style>
        :root {
            --primary-color: #4a86e8;
            --secondary-color: #f0f0f0;
            --background-color: #ffffff;
            --text-color: #333333;
            --border-color: #dddddd;
            --high-color: #ffdddd;
            --medium-color: #ffffcc;
            --low-color: #ddffdd;
            --border-radius: 8px;
        }
        
        body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 0;
            color: var(--text-color);
            background-color: var(--background-color);
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header { 
            background-color: var(--primary-color); 
            color: white;
            padding: 20px; 
            margin-bottom: 20px; 
            border-radius: var(--border-radius);
        }
        
        .section { 
            background-color: white;
            margin-bottom: 30px; 
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            padding: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .statistics {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .stat-box {
            flex: 1;
            min-width: 200px;
            padding: 15px;
            background-color: var(--secondary-color);
            border-radius: var(--border-radius);
            text-align: center;
        }
        
        .stat-box h3 {
            margin-top: 0;
        }
        
        table { 
            width: 100%; 
            border-collapse: collapse; 
            margin: 20px 0;
        }
        
        th, td { 
            padding: 12px 8px; 
            text-align: right; 
            border-bottom: 1px solid var(--border-color); 
        }
        
        th { 
            background-color: var(--secondary-color); 
        }
        
        .high { 
            background-color: var(--high-color); 
        }
        
        .medium { 
            background-color: var(--medium-color); 
        }
        
        .low { 
            background-color: var(--low-color); 
        }
        
        pre { 
            background-color: #f5f5f5; 
            padding: 10px; 
            border-radius: 5px; 
            overflow-x: auto; 
        }
        
        .chart-container {
            margin: 20px 0;
            height: 300px;
        }
        
        @media (prefers-color-scheme: dark) {
            :root {
                --primary-color: #2a66c8;
                --secondary-color: #2d2d2d;
                --background-color: #1a1a1a;
                --text-color: #f0f0f0;
                --border-color: #444444;
                --high-color: #5a3a3a;
                --medium-color: #5a5a3a;
                --low-color: #3a5a3a;
            }
        }
        
        @media (max-width: 768px) {
            .statistics {
                flex-direction: column;
            }
            
            .stat-box {
                min-width: unset;
            }
        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>تقرير تحليل الشيفرة البرمجية</h1>
            <p>تاريخ التحليل: {date}</p>
            <p>اسم المشروع: {project_name}</p>
            <p>نوع المشروع: {project_type}</p>
        </div>
        
        <div class="section">
            <h2>ملخص التحليل</h2>
            
            <div class="statistics">
                <div class="stat-box">
                    <h3>إجمالي الملفات</h3>
                    <p>{total_files}</p>
                </div>
                
                <div class="stat-box">
                    <h3>عدد المشاكل</h3>
                    <p>{total_issues}</p>
                </div>
                
                <div class="stat-box">
                    <h3>عدد الثغرات الأمنية</h3>
                    <p>{security_issues}</p>
                </div>
            </div>
            
            <h3>تصنيف المشاكل</h3>
            <div class="statistics">
                <div class="stat-box high">
                    <h3>عالية الخطورة</h3>
                    <p>{high_issues}</p>
                </div>
                
                <div class="stat-box medium">
                    <h3>متوسطة الخطورة</h3>
                    <p>{medium_issues}</p>
                </div>
                
                <div class="stat-box low">
                    <h3>منخفضة الخطورة</h3>
                    <p>{low_issues}</p>
                </div>
            </div>
            
            <div class="chart-container">
                <canvas id="issuesChart"></canvas>
            </div>
        </div>
        
        <div class="section">
            <h2>المشاكل المكتشفة</h2>
            <table>
                <tr>
                    <th>الخطورة</th>
                    <th>الملف</th>
                    <th>السطر</th>
                    <th>الوصف</th>
                </tr>
                {issues_table}
            </table>
        </div>
        
        <div class="section">
            <h2>الثغرات الأمنية</h2>
            <table>
                <tr>
                    <th>نوع الثغرة</th>
                    <th>الخطورة</th>
                    <th>الملف</th>
                    <th>السطر</th>
                    <th>الوصف</th>
                </tr>
                {security_table}
            </table>
        </div>
    </div>
    
    <script>
        // إنشاء رسم بياني للمشاكل
        const ctx = document.getElementById('issuesChart').getContext('2d');
        const issuesChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['عالية', 'متوسطة', 'منخفضة'],
                datasets: [{
                    label: 'عدد المشاكل حسب الخطورة',
                    data: [{high_issues}, {medium_issues}, {low_issues}],
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.5)',
                        'rgba(255, 205, 86, 0.5)',
                        'rgba(75, 192, 192, 0.5)'
                    ],
                    borderColor: [
                        'rgb(255, 99, 132)',
                        'rgb(255, 205, 86)',
                        'rgb(75, 192, 192)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'عدد المشاكل'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'مستوى الخطورة'
                        }
                    }
                }
            }
        });
    </script>
</body>
</html>
"""
    
    try:
        # توليد محتوى الجداول
        from datetime import datetime
        
        # توليد جدول المشاكل
        issues_rows = ""
        for issue in data.get('issues', []):
            severity = issue.get('severity', 'منخفضة')
            severity_class = {
                'حرجة': 'high',
                'عالية': 'high',
                'متوسطة': 'medium',
                'منخفضة': 'low'
            }.get(severity, '')
            
            file_path = issue.get('file', '')
            file_name = os.path.basename(file_path) if file_path else ''
            
            issues_rows += f"""
            <tr class="{severity_class}">
                <td>{severity}</td>
                <td>{file_name}</td>
                <td>{issue.get('line', '')}</td>
                <td>{issue.get('message', '')}</td>
            </tr>
            """
        
        # توليد جدول الثغرات الأمنية
        security_rows = ""
        for vuln in data.get('security_issues', []):
            severity = vuln.get('severity', 'منخفضة')
            severity_class = {
                'حرجة': 'high',
                'عالية': 'high',
                'متوسطة': 'medium',
                'منخفضة': 'low'
            }.get(severity, '')
            
            file_path = vuln.get('file', '')
            file_name = os.path.basename(file_path) if file_path else ''
            
            security_rows += f"""
            <tr class="{severity_class}">
                <td>{vuln.get('type', '')}</td>
                <td>{severity}</td>
                <td>{file_name}</td>
                <td>{vuln.get('line', '')}</td>
                <td>{vuln.get('message', '')}</td>
            </tr>
            """
        
        # إحصائيات المشاكل حسب الخطورة
        high_issues = sum(1 for issue in data.get('issues', []) if issue.get('severity') in ['حرجة', 'عالية'])
        medium_issues = sum(1 for issue in data.get('issues', []) if issue.get('severity') == 'متوسطة')
        low_issues = sum(1 for issue in data.get('issues', []) if issue.get('severity') == 'منخفضة')
        
        security_issues = len(data.get('security_issues', []))
        
        # تجميع المحتوى النهائي
        html_content = html_template.format(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            project_name=data.get('project_name', 'غير معروف'),
            project_type=data.get('project_type', 'غير معروف'),
            total_files=data.get('total_files', 0),
            total_issues=len(data.get('issues', [])),
            security_issues=security_issues,
            high_issues=high_issues,
            medium_issues=medium_issues,
            low_issues=low_issues,
            issues_table=issues_rows,
            security_table=security_rows
        )
        
        # حفظ الملف
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return True
    except Exception as e:
        logger.error(f"خطأ في إنشاء تقرير HTML: {str(e)}")
        return False

def format_code_diff(original: str, modified: str, context_lines: int = 3) -> str:
    """
    تنسيق الفرق بين نسختين من الكود
    
    Args:
        original: النص الأصلي
        modified: النص المعدل
        context_lines: عدد أسطر السياق المحيطة بالتغييرات
        
    Returns:
        نص يوضح الفرق بين النسختين
    """
    from difflib import unified_diff
    
    original_lines = original.splitlines()
    modified_lines = modified.splitlines()
    
    diff = unified_diff(
        original_lines, modified_lines,
        fromfile='Original', tofile='Modified',
        lineterm='', n=context_lines
    )
    
    return '\n'.join(diff)

def highlight_diff(original: str, modified: str) -> Dict[str, List[int]]:
    """
    تحديد أرقام الأسطر التي تم تغييرها
    
    Args:
        original: النص الأصلي
        modified: النص المعدل
        
    Returns:
        قاموس بأرقام الأسطر المضافة والمحذوفة والمعدلة
    """
    from difflib import SequenceMatcher
    
    original_lines = original.splitlines()
    modified_lines = modified.splitlines()
    
    matcher = SequenceMatcher(None, original_lines, modified_lines)
    
    result = {
        "added": [],    # أسطر مضافة في النص المعدل
        "removed": [],  # أسطر محذوفة من النص الأصلي
        "changed": []   # أسطر معدلة (موجودة في كلا النصين)
    }
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            # أسطر تم تعديلها
            result["changed"].extend(list(range(j1 + 1, j2 + 1)))
        elif tag == 'delete':
            # أسطر تم حذفها
            result["removed"].extend(list(range(i1 + 1, i2 + 1)))
        elif tag == 'insert':
            # أسطر تم إضافتها
            result["added"].extend(list(range(j1 + 1, j2 + 1)))
    
    return result

def truncate_text(text: str, max_length: int = 100, add_ellipsis: bool = True) -> str:
    """
    اختصار النص إلى طول محدد
    
    Args:
        text: النص المراد اختصاره
        max_length: الحد الأقصى للطول
        add_ellipsis: إضافة علامة الحذف (...) إذا تم اختصار النص
        
    Returns:
        النص المختصر
    """
    if not text or len(text) <= max_length:
        return text
    
    truncated = text[:max_length]
    if add_ellipsis:
        truncated = truncated.rstrip() + '...'
    
    return truncated

def relative_path(full_path: str, base_dir: str) -> str:
    """
    تحويل المسار المطلق إلى مسار نسبي
    
    Args:
        full_path: المسار المطلق
        base_dir: المجلد الأساسي
        
    Returns:
        المسار النسبي
    """
    return os.path.relpath(full_path, base_dir)

def absolute_path(rel_path: str, base_dir: str) -> str:
    """
    تحويل المسار النسبي إلى مسار مطلق
    
    Args:
        rel_path: المسار النسبي
        base_dir: المجلد الأساسي
        
    Returns:
        المسار المطلق
    """
    if os.path.isabs(rel_path):
        return rel_path
    
    return os.path.normpath(os.path.join(base_dir, rel_path))

def normalize_path(path: str) -> str:
    """
    تنظيم المسار وتوحيد الفواصل
    
    Args:
        path: المسار المراد تنظيمه
        
    Returns:
        المسار المنظم
    """
    return os.path.normpath(path)

def extract_filename(path: str) -> str:
    """
    استخراج اسم الملف من المسار
    
    Args:
        path: مسار الملف
        
    Returns:
        اسم الملف
    """
    return os.path.basename(path)

def extract_directory(path: str) -> str:
    """
    استخراج اسم المجلد من المسار
    
    Args:
        path: مسار الملف أو المجلد
        
    Returns:
        مسار المجلد
    """
    return os.path.dirname(path)

def extract_extension(path: str) -> str:
    """
    استخراج امتداد الملف من المسار
    
    Args:
        path: مسار الملف
        
    Returns:
        امتداد الملف
    """
    return os.path.splitext(path)[1]

def change_extension(path: str, new_extension: str) -> str:
    """
    تغيير امتداد الملف
    
    Args:
        path: مسار الملف
        new_extension: الامتداد الجديد
        
    Returns:
        المسار مع الامتداد الجديد
    """
    base = os.path.splitext(path)[0]
    
    # التأكد من أن الامتداد الجديد يبدأ بنقطة
    if not new_extension.startswith('.'):
        new_extension = '.' + new_extension
    
    return base + new_extension

def count_lines_in_file(file_path: str) -> int:
    """
    عد أسطر الملف
    
    Args:
        file_path: مسار الملف
        
    Returns:
        عدد الأسطر
    """
    try:
        content = read_file(file_path)
        if content is None:
            return 0
        
        return len(content.splitlines())
    except Exception as e:
        logger.error(f"خطأ في عد أسطر الملف {file_path}: {str(e)}")
        return 0

def get_file_size(file_path: str) -> int:
    """
    الحصول على حجم الملف بالبايت
    
    Args:
        file_path: مسار الملف
        
    Returns:
        حجم الملف بالبايت
    """
    try:
        return os.path.getsize(file_path)
    except Exception as e:
        logger.error(f"خطأ في الحصول على حجم الملف {file_path}: {str(e)}")
        return 0

def format_file_size(size_in_bytes: int) -> str:
    """
    تنسيق حجم الملف بشكل قابل للقراءة
    
    Args:
        size_in_bytes: حجم الملف بالبايت
        
    Returns:
        النص المنسق للحجم
    """
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    elif size_in_bytes < 1024 * 1024 * 1024:
        return f"{size_in_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_in_bytes / (1024 * 1024 * 1024):.1f} GB"

def get_git_root(path: str) -> Optional[str]:
    """
    الحصول على جذر مستودع Git
    
    Args:
        path: مسار داخل مستودع Git
        
    Returns:
        مسار جذر المستودع أو None إذا لم يكن المسار داخل مستودع
    """
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            cwd=path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None

def is_binary_file(file_path: str) -> bool:
    """
    التحقق مما إذا كان الملف ثنائيًا
    
    Args:
        file_path: مسار الملف
        
    Returns:
        True إذا كان الملف ثنائيًا، False إذا كان نصيًا
    """
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            return b'\0' in chunk
    except Exception:
        return False

def get_file_encoding(file_path: str) -> str:
    """
    محاولة تحديد ترميز الملف
    
    Args:
        file_path: مسار الملف
        
    Returns:
        ترميز الملف المقدر
    """
    try:
        import chardet
        with open(file_path, 'rb') as f:
            data = f.read()
            result = chardet.detect(data)
            return result['encoding'] or 'utf-8'
    except ImportError:
        # إذا لم تكن مكتبة chardet متاحة، افترض utf-8
        return 'utf-8'
    except Exception:
        return 'utf-8'

def slugify(text: str) -> str:
    """
    تحويل النص إلى نص صالح للاستخدام في عناوين URL
    
    Args:
        text: النص المراد تحويله
        
    Returns:
        النص المحول
    """
    # إزالة الأحرف غير الأبجدية الرقمية
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    # استبدال المسافات بشرطات
    text = re.sub(r'[\s]+', '-', text)
    return text

def extract_issues_from_ai_response(response, file_path):
    """
    استخراج المشكلات من رد نموذج الذكاء الاصطناعي
    """
    issues = []
    
    # محاولة تحديد أقسام المشكلات في الرد
    import re
    
    # البحث عن المشكلات المحددة بعناوين مثل "المشاكل" أو "الثغرات" أو "الأخطاء"
    issue_sections = re.split(r'#+\s*(مشاكل|مشكلات|ثغرات|أخطاء|Issues|Problems|Bugs|Vulnerabilities)', response)
    
    if len(issue_sections) > 1:
        # استخلاص قسم المشكلات
        issues_content = issue_sections[1]
        # قطع النص عند العنوان التالي إن وجد
        next_heading = re.search(r'#+\s+\w+', issues_content)
        if next_heading:
            issues_content = issues_content[:next_heading.start()]
            
        # البحث عن عناصر القائمة التي تشير إلى المشكلات
        issue_items = re.findall(r'\n[*\-\d+]\.?\s+(.*?)(?=\n[*\-\d+]\.?\s+|\n#+\s+|\Z)', issues_content, re.DOTALL)
        
        for item in issue_items:
            # محاولة استخراج رقم السطر
            line_match = re.search(r'سطر[: ]+(\d+)|[Ll]ine[: ]+(\d+)', item)
            line = int(line_match.group(1) or line_match.group(2)) if line_match else None
            
            # محاولة تحديد الشدة
            severity = 'info'  # الشدة الافتراضية
            if re.search(r'حرج|خطير|critical|severe', item, re.IGNORECASE):
                severity = 'critical'
            elif re.search(r'عالي|high', item, re.IGNORECASE):
                severity = 'high'
            elif re.search(r'متوسط|medium', item, re.IGNORECASE):
                severity = 'medium'
            elif re.search(r'منخفض|low', item, re.IGNORECASE):
                severity = 'low'
                
            # إنشاء المشكلة
            issues.append({
                'file': file_path,
                'line': line,
                'message': item.strip(),
                'severity': severity,
                'type': 'ai_analysis'
            })
    
    # إذا لم يتم العثور على مشاكل في قسم محدد، نبحث عن أنماط عامة
    if not issues:
        # البحث عن أنماط مثل "مشكلة:" أو "خطأ:" أو "ثغرة:"
        issue_patterns = [
            r'(مشكلة|خطأ|ثغرة)[: ]+(.*?)(?=\n\n|\Z)',
            r'(Problem|Issue|Bug|Error|Vulnerability)[: ]+(.*?)(?=\n\n|\Z)'
        ]
        
        for pattern in issue_patterns:
            for match in re.finditer(pattern, response, re.IGNORECASE | re.DOTALL):
                # استخراج وصف المشكلة
                issue_desc = match.group(2).strip()
                
                # محاولة استخراج رقم السطر
                line_match = re.search(r'سطر[: ]+(\d+)|[Ll]ine[: ]+(\d+)', issue_desc)
                line = int(line_match.group(1) or line_match.group(2)) if line_match else None
                
                # إنشاء المشكلة
                issues.append({
                    'file': file_path,
                    'line': line,
                    'message': issue_desc,
                    'severity': 'info',
                    'type': 'ai_analysis'
                })
    
    return issues