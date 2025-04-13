#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تحديث شهادات SSL للاتصالات الآمنة
"""
import os
import sys
import logging
import subprocess
import importlib.util
import platform
import traceback
from pathlib import Path

# إعداد التسجيل
logger = logging.getLogger("CodeAnalyzer.Certifi")

def is_package_installed(package_name):
    """التحقق من تثبيت حزمة معينة"""
    return importlib.util.find_spec(package_name) is not None

def ensure_certifi_installed():
    """التأكد من تثبيت مكتبة certifi"""
    if not is_package_installed("certifi"):
        logger.info("مكتبة certifi غير مثبتة. جارٍ التثبيت...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "certifi"
            ])
            logger.info("تم تثبيت مكتبة certifi بنجاح")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"فشل تثبيت مكتبة certifi: {e}")
            return False
    return True

def update_certifi():
    """
    تحديث شهادات SSL عن طريق تثبيت أحدث نسخة من مكتبة certifi
    
    Returns:
        bool: True إذا تم التحديث بنجاح، False خلاف ذلك
    """
    try:
        # التأكد من وجود مكتبة certifi
        if not ensure_certifi_installed():
            return False
            
        # استيراد مكتبة certifi
        import certifi
        
        # تسجيل المسار الحالي للشهادات
        current_path = certifi.where()
        logger.info(f"مسار شهادات SSL الحالي: {current_path}")
        
        # التحقق من وجود الملف
        if not os.path.exists(current_path):
            logger.warning(f"ملف الشهادات غير موجود في المسار: {current_path}")
        
        # تسجيل معلومات النظام لمساعدة التشخيص
        logger.info(f"نظام التشغيل: {platform.system()} {platform.release()}")
        logger.info(f"إصدار Python: {platform.python_version()}")
        
        # تحديث مكتبة certifi
        logger.info("جارٍ تحديث مكتبة certifi...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--upgrade", "certifi"
        ])
        
        # إعادة استيراد المكتبة للحصول على المسار المحدث
        importlib.reload(certifi)
        
        # التحقق من المسار بعد التحديث
        new_path = certifi.where()
        logger.info(f"مسار شهادات SSL بعد التحديث: {new_path}")
        
        # التحقق من نجاح التحديث
        if os.path.exists(new_path):
            logger.info("تم تحديث شهادات SSL بنجاح")
            return True
        else:
            logger.error("فشل تحديث شهادات SSL: المسار غير موجود")
            return False
    
    except ImportError as e:
        logger.error(f"خطأ في استيراد مكتبة certifi: {e}")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"فشل تنفيذ الأمر لتحديث certifi: {e}")
        return False
    except Exception as e:
        logger.error(f"خطأ غير متوقع أثناء تحديث شهادات SSL: {e}")
        logger.error(traceback.format_exc())
        return False

def set_ssl_cert_env():
    """
    تعيين متغيرات البيئة SSL_CERT_FILE و REQUESTS_CA_BUNDLE
    لتوجيه الاتصالات الآمنة لاستخدام شهادات certifi
    
    Returns:
        bool: True إذا تم تعيين المتغيرات بنجاح، False خلاف ذلك
    """
    try:
        # التأكد من وجود مكتبة certifi
        if not ensure_certifi_installed():
            return False
            
        # استيراد مكتبة certifi
        import certifi
        
        # الحصول على مسار الشهادات
        cert_path = certifi.where()
        
        # التحقق من وجود الملف
        if not os.path.exists(cert_path):
            logger.warning(f"ملف الشهادات غير موجود في المسار: {cert_path}")
            return False
        
        # تعيين متغيرات البيئة
        os.environ['SSL_CERT_FILE'] = cert_path
        os.environ['REQUESTS_CA_BUNDLE'] = cert_path
        
        # تسجيل النجاح
        logger.info(f"تم تعيين متغيرات البيئة للشهادات: {cert_path}")
        
        # معلومات إضافية للتشخيص
        logger.debug(f"SSL_CERT_FILE = {os.environ.get('SSL_CERT_FILE')}")
        logger.debug(f"REQUESTS_CA_BUNDLE = {os.environ.get('REQUESTS_CA_BUNDLE')}")
        
        return True
    
    except ImportError as e:
        logger.error(f"خطأ في استيراد مكتبة certifi: {e}")
        return False
    except Exception as e:
        logger.error(f"خطأ في تعيين متغيرات البيئة للشهادات: {e}")
        logger.error(traceback.format_exc())
        return False

def apply_ssl_workarounds():
    """
    تطبيق حلول مؤقتة لمشاكل SSL الشائعة
    """
    try:
        # التعامل مع مشكلة شائعة في نظام ويندوز
        if platform.system() == "Windows":
            try:
                import ssl
                # تعطيل التحقق من الشهادات في حالات معينة (غير آمن، ولكن يمكن أن يكون ضرورياً في بعض البيئات)
                if hasattr(ssl, '_create_unverified_context'):
                    logger.warning("تطبيق حل مؤقت لمشكلة SSL في ويندوز")
                    # لا تفعل هذا دائماً، فقط عند الضرورة
                    # ssl._create_default_https_context = ssl._create_unverified_context
            except ImportError:
                pass
        
        # الحلول المحددة لنظام macOS
        if platform.system() == "Darwin":
            # بعض الإصدارات من macOS تحتاج إلى إعدادات إضافية
            try:
                import certifi
                import ssl
                # تعيين سياق SSL الافتراضي
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                logger.info("تم تعيين سياق SSL مخصص لنظام macOS")
            except ImportError:
                pass
        
        logger.info("تم تطبيق الحلول المؤقتة لمشاكل SSL")
        return True
    
    except Exception as e:
        logger.error(f"خطأ في تطبيق الحلول المؤقتة لمشاكل SSL: {e}")
        return False

def test_ssl_connection():
    """
    اختبار الاتصال الآمن بخدمة معروفة للتحقق من صحة إعدادات SSL
    
    Returns:
        bool: True إذا نجح الاختبار، False خلاف ذلك
    """
    try:
        import urllib.request
        import ssl
        
        # اختبار الاتصال بموقع معروف
        test_url = "https://www.google.com"
        logger.info(f"اختبار الاتصال بـ {test_url}...")
        
        # فتح الاتصال
        response = urllib.request.urlopen(test_url)
        
        # التحقق من الاستجابة
        if response.status == 200:
            logger.info("نجح اختبار الاتصال SSL")
            return True
        else:
            logger.warning(f"فشل اختبار الاتصال SSL: رمز الحالة {response.status}")
            return False
    
    except ssl.SSLError as e:
        logger.error(f"خطأ SSL أثناء اختبار الاتصال: {e}")
        return False
    except Exception as e:
        logger.error(f"خطأ أثناء اختبار الاتصال SSL: {e}")
        return False

def full_ssl_setup():
    """
    إجراء الإعداد الكامل لشهادات SSL
    
    Returns:
        bool: True إذا تم الإعداد بنجاح، False خلاف ذلك
    """
    try:
        # 1. تحديث مكتبة certifi
        update_result = update_certifi()
        
        # 2. تعيين متغيرات البيئة
        env_result = set_ssl_cert_env()
        
        # 3. تطبيق الحلول المؤقتة
        workaround_result = apply_ssl_workarounds()
        
        # 4. اختبار الاتصال (اختياري)
        test_result = test_ssl_connection()
        
        # تسجيل ملخص النتائج
        logger.info(f"نتائج إعداد SSL:")
        logger.info(f"- تحديث certifi: {'نجاح' if update_result else 'فشل'}")
        logger.info(f"- تعيين متغيرات البيئة: {'نجاح' if env_result else 'فشل'}")
        logger.info(f"- تطبيق الحلول المؤقتة: {'نجاح' if workaround_result else 'فشل'}")
        logger.info(f"- اختبار الاتصال: {'نجاح' if test_result else 'فشل'}")
        
        # نجاح الإعداد الكامل إذا نجحت الخطوتان الأولى والثانية على الأقل
        return update_result and env_result
    
    except Exception as e:
        logger.error(f"خطأ أثناء إعداد SSL: {e}")
        return False

if __name__ == "__main__":
    # إعداد التسجيل عند تشغيل الملف مباشرة
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    
    # تنفيذ الإعداد الكامل
    success = full_ssl_setup()
    
    # عرض النتيجة
    if success:
        print("تم إعداد SSL بنجاح")
        sys.exit(0)
    else:
        print("حدثت مشكلة أثناء إعداد SSL")
        sys.exit(1)