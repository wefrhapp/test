#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نقطة دخول التطبيق، تهيئة QApplication وإعدادات Qt
Code Analyzer - Application Entry Point
"""
import os
import sys
import logging
import argparse
import subprocess
from pathlib import Path
import time
import platform
import traceback
import atexit

from PySide6.QtCore import QTranslator, QLocale, QLibraryInfo, QDir, Qt, QCoreApplication, QEvent
from PySide6.QtGui import QFont, QIcon, QPixmap, QSplashScreen
from PySide6.QtWidgets import QApplication, QMessageBox

from ui_main import MainWindow
from api_clients import APIConfig, get_api_client
from analyzer import APIThreadManager

# معلومات التطبيق
APP_NAME = "محلل الشيفرة البرمجية"
APP_VERSION = "1.0.0"
APP_ORGANIZATION = "AIDev"
APP_DOMAIN = "aidev.example.com"

# مسارات التطبيق
def get_app_paths():
    """الحصول على مسارات التطبيق الأساسية"""
    # مسار التطبيق
    app_dir = os.path.dirname(os.path.abspath(__file__))
    
    # مسار البيانات
    if platform.system() == "Windows":
        data_dir = os.path.join(os.environ.get("APPDATA", ""), APP_ORGANIZATION, APP_NAME)
    elif platform.system() == "Darwin":  # macOS
        data_dir = os.path.join(os.path.expanduser("~/Library/Application Support"), APP_ORGANIZATION, APP_NAME)
    else:  # Linux وأنظمة Unix الأخرى
        data_dir = os.path.join(os.path.expanduser("~/.local/share"), APP_NAME.lower().replace(" ", "_"))
    
    # التأكد من وجود المجلدات
    os.makedirs(data_dir, exist_ok=True)
    
    # مسار السجلات
    logs_dir = os.path.join(data_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # مسار الإعدادات
    config_dir = os.path.join(data_dir, "config")
    os.makedirs(config_dir, exist_ok=True)
    
    # مسار المكونات الإضافية
    plugins_dir = os.path.join(data_dir, "plugins")
    os.makedirs(plugins_dir, exist_ok=True)
    
    # مسار الموارد
    resources_dir = os.path.join(app_dir, "resources")
    
    return {
        "app_dir": app_dir,
        "data_dir": data_dir,
        "logs_dir": logs_dir,
        "config_dir": config_dir,
        "plugins_dir": plugins_dir,
        "resources_dir": resources_dir
    }

# إعداد التسجيل (Setup logging)
def setup_logging():
    """إعداد تسجيل الأحداث"""
    app_paths = get_app_paths()
    log_file = os.path.join(app_paths["logs_dir"], f"code_analyzer_{time.strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    
    # إنشاء مساحة تسجيل عامة للتطبيق
    app_logger = logging.getLogger("CodeAnalyzer")
    
    # تسجيل معلومات النظام
    app_logger.info(f"نظام التشغيل: {platform.system()} {platform.version()}")
    app_logger.info(f"إصدار Python: {platform.python_version()}")
    app_logger.info(f"مسار التطبيق: {app_paths['app_dir']}")
    app_logger.info(f"مسار البيانات: {app_paths['data_dir']}")
    
    return app_logger

# إنشاء المسجل (Create logger)
logger = setup_logging()

# تنفيذ دالة update_certifi محلياً في حالة عدم وجود الملف
def update_certifi_local():
    """تحديث شهادات SSL محلياً"""
    try:
        # محاولة استيراد certifi
        import certifi
        
        # تعيين متغيرات البيئة الضرورية
        os.environ['SSL_CERT_FILE'] = certifi.where()
        os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
        
        logger.info(f"تم تعيين مسار شهادات SSL: {certifi.where()}")
        
        # محاولة تحديث certifi
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--upgrade", "certifi"
        ])
        
        logger.info("تم تحديث مكتبة certifi بنجاح")
        return True
    
    except ImportError:
        logger.warning("مكتبة certifi غير مثبتة")
        return False
    except subprocess.CalledProcessError as e:
        logger.warning(f"فشل تحديث مكتبة certifi: {e}")
        return False
    except Exception as e:
        logger.warning(f"خطأ أثناء معالجة الشهادات: {e}")
        return False

# استيراد وتحديث شهادات SSL
try:
    from update_certifi import update_certifi, set_ssl_cert_env
    # تحديث شهادات SSL
    update_result = update_certifi()
    # تعيين متغيرات البيئة للشهادات
    set_ssl_result = set_ssl_cert_env()
    
    if update_result and set_ssl_result:
        logger.info("تم تحديث وتهيئة شهادات SSL بنجاح")
    else:
        logger.warning("تم تنفيذ update_certifi ولكن قد تكون هناك مشكلات")
except ImportError:
    logger.warning("ملف update_certifi.py غير موجود، سيتم استخدام التنفيذ المحلي")
    update_certifi_local()
except Exception as e:
    logger.error(f"خطأ أثناء معالجة شهادات SSL: {e}")
    # محاولة استخدام التنفيذ المحلي
    update_certifi_local()

def setup_ui_language(app):
    """إعداد لغة واجهة المستخدم"""
    # تحديد اللغة الافتراضية
    locale = QLocale.system().name()
    
    # إذا كانت اللغة العربية متاحة، استخدمها
    if locale.startswith('ar'):
        # تحميل ملف الترجمة
        translator = QTranslator(app)
        translations_path = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
        
        if translator.load("qt_ar", translations_path):
            app.installTranslator(translator)
            logger.info("تم تحميل ملف ترجمة اللغة العربية")
        else:
            logger.warning("فشل تحميل ملف ترجمة اللغة العربية")
    
    # تعيين اتجاه التخطيط الافتراضي حسب اللغة
    if locale.startswith('ar'):
        app.setLayoutDirection(Qt.RightToLeft)
        logger.info("تم تعيين اتجاه التخطيط من اليمين إلى اليسار")
    else:
        app.setLayoutDirection(Qt.LeftToRight)
        logger.info("تم تعيين اتجاه التخطيط من اليسار إلى اليمين")

def setup_ui_style(app):
    """إعداد نمط واجهة المستخدم"""
    # تعيين الخط الافتراضي
    font = QFont("Arial", 10)
    app.setFont(font)
    
    # تعيين نمط المواضيع الافتراضي
    app.setStyle("Fusion")
    
    # تطبيق ورقة نمط خاصة (CSS)
    style_sheet = """
    QMainWindow {
        background-color: #f8f8f8;
    }
    
    QToolBar {
        background-color: #ffffff;
        border-bottom: 1px solid #e0e0e0;
        spacing: 8px;
    }
    
    QToolButton {
        border: 1px solid transparent;
        border-radius: 4px;
        padding: 4px;
    }
    
    QToolButton:hover {
        background-color: #e0e0e0;
    }
    
    QStatusBar {
        background-color: #f0f0f0;
        border-top: 1px solid #e0e0e0;
    }
    
    QTabWidget::pane {
        border: 1px solid #e0e0e0;
        border-top: 0px;
    }
    
    QTabBar::tab {
        background-color: #f0f0f0;
        border: 1px solid #e0e0e0;
        border-bottom: 0px;
        padding: 6px 12px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    
    QTabBar::tab:selected {
        background-color: #ffffff;
    }
    
    QGroupBox {
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        margin-top: 16px;
        padding-top: 16px;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 5px;
    }
    
    QLineEdit, QTextEdit, QPlainTextEdit {
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        padding: 4px;
        background-color: white;
    }
    
    QPushButton {
        background-color: #f0f0f0;
        border: 1px solid #d0d0d0;
        border-radius: 4px;
        padding: 6px 12px;
    }
    
    QPushButton:hover {
        background-color: #e0e0e0;
    }
    
    QPushButton:pressed {
        background-color: #d0d0d0;
    }
    
    QComboBox {
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        padding: 4px;
        background-color: white;
    }
    
    QTreeView, QTableView, QListView {
        border: 1px solid #e0e0e0;
        background-color: white;
    }
    
    QTreeView::item:selected, QTableView::item:selected, QListView::item:selected {
        background-color: #0078d7;
        color: white;
    }
    """
    
    app.setStyleSheet(style_sheet)
    logger.info("تم تطبيق نمط واجهة المستخدم")

def setup_exception_handler():
    """إعداد معالج الاستثناءات غير المتوقعة"""
    def exception_hook(exctype, value, tb):
        """معالج الاستثناءات العام"""
        # تسجيل الاستثناء
        logger.critical(f"استثناء غير متوقع: {value}", exc_info=True)
        
        # رسالة خطأ للمستخدم
        error_msg = f"حدث خطأ غير متوقع في البرنامج:\n\n{exctype.__name__}: {value}\n\n"
        error_msg += "تم تسجيل تفاصيل الخطأ في ملف السجل."
        
        # عرض الرسالة فقط إذا كان التطبيق لا يزال قيد التشغيل
        if QApplication.instance():
            QMessageBox.critical(None, "خطأ", error_msg)
        
        # استدعاء معالج الاستثناءات الافتراضي
        sys.__excepthook__(exctype, value, tb)
    
    # تعيين معالج الاستثناءات
    sys.excepthook = exception_hook
    logger.info("تم تعيين معالج الاستثناءات")

def parse_arguments():
    """تحليل وسيطات سطر الأوامر"""
    parser = argparse.ArgumentParser(description="محلل الشيفرة البرمجية بالذكاء الاصطناعي")
    
    parser.add_argument(
        "--project", "-p",
        help="مجلد المشروع للتحليل",
        type=str
    )
    
    parser.add_argument(
        "--analyze", "-a",
        help="بدء التحليل تلقائيًا بعد فتح المشروع",
        action="store_true"
    )
    
    parser.add_argument(
        "--rtl",
        help="استخدام اتجاه RTL للواجهة",
        action="store_true"
    )
    
    parser.add_argument(
        "--ltr",
        help="استخدام اتجاه LTR للواجهة",
        action="store_true"
    )
    
    parser.add_argument(
        "--debug",
        help="تمكين وضع التصحيح لطباعة المزيد من المعلومات",
        action="store_true"
    )
    
    parser.add_argument(
        "--version", "-v",
        help="عرض إصدار البرنامج",
        action="store_true"
    )
    
    return parser.parse_args()

def show_version():
    """عرض معلومات إصدار البرنامج"""
    print(f"{APP_NAME} - الإصدار {APP_VERSION}")
    print("Copyright © 2025")
    sys.exit(0)

def setup_api_config():
    """إعداد تكوين API للذكاء الاصطناعي"""
    app_paths = get_app_paths()
    config_path = os.path.join(app_paths["config_dir"], "api_config.json")
    
    try:
        # تحميل أو إنشاء تكوين API
        api_config = APIConfig.from_config_file(config_path)
        logger.info("تم تحميل تكوين API بنجاح")
        return api_config
    except Exception as e:
        logger.error(f"فشل تحميل تكوين API: {str(e)}")
        # إنشاء تكوين افتراضي
        api_config = APIConfig()
        # حفظ التكوين الافتراضي
        api_config.save_to_file(config_path)
        logger.info("تم إنشاء تكوين API افتراضي")
        return api_config

def cleanup_resources():
    """تنظيف الموارد عند إغلاق التطبيق"""
    logger.info("جارٍ تنظيف الموارد...")
    
    # إغلاق جميع الخيوط المفتوحة
    try:
        APIThreadManager.cleanup_all_threads()
        logger.info("تم إغلاق جميع الخيوط بنجاح")
    except Exception as e:
        logger.error(f"حدث خطأ أثناء إغلاق الخيوط: {str(e)}")
    
    logger.info("تم إغلاق التطبيق بنجاح")

def check_api_connectivity(api_config):
    """التحقق من الاتصال بخدمات API"""
    # اختبار الاتصال بالمزود المفضل إذا كان هناك مفتاح API
    provider = api_config.preferred_provider
    api_key = api_config.get_api_key(provider)
    
    if api_key:
        try:
            client = get_api_client(api_config, provider)
            test_message = [
                {"role": "system", "content": "اختبار اتصال."},
                {"role": "user", "content": "مرحباً، هذا اختبار."}
            ]
            
            # اختبار طلب خفيف
            logger.info(f"جارٍ اختبار الاتصال بـ {provider}...")
            _ = client.chat(test_message)
            logger.info(f"تم الاتصال بنجاح بـ {provider}")
            return True
        except Exception as e:
            logger.warning(f"فشل الاتصال بـ {provider}: {str(e)}")
            return False
    else:
        logger.warning(f"لا يوجد مفتاح API لـ {provider}")
        return False

def create_app():
    """
    إنشاء وتهيئة تطبيق المحلل
    """
    # إعداد معالج الاستثناءات
    setup_exception_handler()
    
    # إنشاء التطبيق
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_ORGANIZATION)
    app.setOrganizationDomain(APP_DOMAIN)
    
    # إعداد مسارات التطبيق
    app_paths = get_app_paths()
    
    # إعداد شاشة البداية
    splash_path = os.path.join(app_paths.get("resources_dir", ""), "splash.png")
    if os.path.exists(splash_path):
        splash_pixmap = QPixmap(splash_path)
        splash = QSplashScreen(splash_pixmap)
        splash.show()
        app.processEvents()
    else:
        splash = None
        logger.warning("ملف شاشة البداية غير موجود")
    
    # إعداد لغة واجهة المستخدم
    setup_ui_language(app)
    
    # إعداد نمط واجهة المستخدم
    setup_ui_style(app)
    
    # تحميل تكوين API
    api_config = setup_api_config()
    
    # إنشاء النافذة الرئيسية
    main_window = MainWindow(api_config)
    
    # تسجيل دالة التنظيف عند الخروج
    atexit.register(cleanup_resources)
    
    # إخفاء شاشة البداية وإظهار النافذة الرئيسية
    if splash:
        splash.finish(main_window)
    
    main_window.show()
    
    return app, main_window, api_config

def main():
    """الدالة الرئيسية للتطبيق"""
    # تحليل وسيطات سطر الأوامر
    args = parse_arguments()
    
    # عرض الإصدار إذا تم طلبه
    if args.version:
        show_version()
    
    # ضبط مستوى السجل إذا كان وضع التصحيح مفعلاً
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("تم تفعيل وضع التصحيح")
    
    # إنشاء تطبيق Qt
    app, main_window, api_config = create_app()
    
    # تبديل اتجاه الواجهة إذا تم تحديده
    if args.rtl:
        app.setLayoutDirection(Qt.RightToLeft)
        logger.info("تم تعيين اتجاه الواجهة من اليمين إلى اليسار (RTL)")
    elif args.ltr:
        app.setLayoutDirection(Qt.LeftToRight)
        logger.info("تم تعيين اتجاه الواجهة من اليسار إلى اليمين (LTR)")
    
    # اختبار الاتصال بخدمات API
    check_api_connectivity(api_config)
    
    # فتح المشروع تلقائيًا إذا تم تحديده
    if args.project:
        project_path = Path(args.project).resolve()
        if project_path.exists() and project_path.is_dir():
            logger.info(f"جاري فتح المشروع: {project_path}")
            main_window.open_project(str(project_path))
            
            # بدء التحليل تلقائيًا إذا تم تحديده
            if args.analyze:
                logger.info("بدء التحليل التلقائي للمشروع")
                main_window.start_analysis()
        else:
            logger.error(f"مجلد المشروع غير موجود: {args.project}")
    
    # تشغيل حلقة الأحداث
    logger.info("بدء تشغيل التطبيق")
    return app.exec()

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        logger.critical(f"حدث خطأ غير متوقع: {str(e)}", exc_info=True)
        sys.exit(1)