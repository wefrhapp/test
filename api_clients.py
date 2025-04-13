#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
واجهات برمجة الذكاء الاصطناعي المختلفة
"""
import os
import json
import logging
import requests
import urllib3
import atexit
from typing import Dict, List, Any, Optional, Tuple, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from PySide6.QtCore import QObject, QThread, Signal, Slot

# استيراد APIThreadManager - يجب أن يكون هذا متاحاً
try:
    from analyzer import APIThreadManager
    HAS_THREAD_MANAGER = True
except ImportError:
    HAS_THREAD_MANAGER = False
    # نسجل رسالة تحذير
    logging.getLogger("CodeAnalyzer.API").warning("تعذر استيراد APIThreadManager. لن يتم تنظيف خيوط API تلقائياً.")

# للدعم المباشر لنموذج Grok-3-beta
from openai import OpenAI

# تجاهل تحذيرات SSL غير الآمنة
from urllib3.exceptions import InsecureRequestWarning
urllib3.disable_warnings(InsecureRequestWarning)

logger = logging.getLogger("CodeAnalyzer.API")

class APIRequestThread(QThread):
    """خيط للطلبات API لتجنب تجميد واجهة المستخدم"""
    
    request_completed = Signal(object)  # إشارة لإكمال الطلب
    request_failed = Signal(str)  # إشارة لفشل الطلب
    
    def __init__(self, url, headers, data, parent=None):
        super().__init__(parent)
        self.url = url
        self.headers = headers
        self.data = data
        self.verify_ssl = True
        self.response = None
        
        # تسجيل الخيط مع مدير الخيوط إذا كان متاحاً
        if HAS_THREAD_MANAGER:
            APIThreadManager.register_thread(self)
    
    def run(self):
        """تنفيذ الطلب API"""
        try:
            self.response = requests.post(
                self.url,
                headers=self.headers,
                json=self.data,
                verify=self.verify_ssl,
                timeout=120  # وقت أطول للطلبات المعقدة
            )
            
            if self.response.status_code in (200, 201):
                response_data = self.response.json()
                self.request_completed.emit(response_data)
            else:
                error_msg = f"خطأ في الطلب: {self.response.status_code}, {self.response.text}"
                logger.error(error_msg)
                self.request_failed.emit(error_msg)
        
        except Exception as e:
            error_msg = f"استثناء أثناء الطلب: {str(e)}"
            logger.error(error_msg)
            self.request_failed.emit(error_msg)
        
        finally:
            # إلغاء تسجيل الخيط من مدير الخيوط عند الانتهاء
            if HAS_THREAD_MANAGER:
                APIThreadManager.unregister_thread(self)


@dataclass
class APIConfig:
    """إعدادات API"""
    
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"
    openai_api_url: str = "https://api.openai.com/v1/chat/completions"
    
    claude_api_key: str = ""
    claude_model: str = "claude-3-opus-20240229"
    claude_api_url: str = "https://api.anthropic.com/v1/messages"
    
    grok_api_key: str = ""
    grok_model: str = "grok-1"
    grok_api_url: str = "https://api.groq.com/openai/v1/chat/completions"
    
    # إعدادات لنموذج grok-3-beta
    xai_api_key: str = ""
    xai_model: str = "grok-3-beta"
    xai_api_url: str = "https://api.x.ai/v1/chat/completions"
    
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-coder-33b-instruct"
    deepseek_api_url: str = "https://api.deepseek.com/v1/chat/completions"
    
    preferred_provider: str = "claude"  # المزود المفضل للتحليل
    analysis_prompt_template: str = """
    حلل الشيفرة البرمجية التالية واكتشف مشاكل الجودة، الأخطاء المنطقية، والثغرات الأمنية.
    
    اللغة: {language}
    الشيفرة:
    ```
    {code}
    ```
    
    قدم النتائج بتنسيق JSON بالهيكل التالي:
    {{
      "issues": [
        {{
          "line": رقم_السطر,
          "severity": "عالية" | "متوسطة" | "منخفضة",
          "message": "وصف مختصر للمشكلة",
          "code": "الشيفرة المتضررة",
          "description": "وصف مفصل للمشكلة",
          "recommendation": "توصية إصلاح المشكلة"
        }}
      ],
      "summary": "ملخص عام للشيفرة"
    }}
    """
    
    security_prompt_template: str = """
    حلل الشيفرة البرمجية التالية من منظور أمني فقط. ابحث عن الثغرات الأمنية المحتملة مثل:
    - SQL Injection
    - XSS (Cross-Site Scripting)
    - CSRF (Cross-Site Request Forgery)
    - Command Injection
    - Path Traversal
    - وغيرها من المشاكل الأمنية
    
    اللغة: {language}
    الشيفرة:
    ```
    {code}
    ```
    
    قدم النتائج بتنسيق JSON بالهيكل التالي:
    {{
      "issues": [
        {{
          "line": رقم_السطر,
          "severity": "عالية" | "متوسطة" | "منخفضة",
          "message": "وصف مختصر للثغرة",
          "code": "الشيفرة المتضررة",
          "description": "وصف مفصل للثغرة",
          "recommendation": "توصية إصلاح الثغرة"
        }}
      ],
      "security_score": 0-10
    }}
    """
    
    fix_prompt_template: str = """
    أصلح المشكلة التالية في الشيفرة البرمجية:
    
    اللغة: {language}
    الشيفرة الكاملة:
    ```
    {code}
    ```
    
    المشكلة في السطر {line}: {message}
    
    قدم النسخة المصححة كاملة من الشيفرة. لا تغير أي جزء من الشيفرة ليس له علاقة بالمشكلة.
    قدم النتائج بتنسيق JSON بالهيكل التالي:
    {{
      "fixed_code": "الشيفرة المصححة كاملة",
      "explanation": "شرح التصحيح"
    }}
    """
    
    @classmethod
    def from_config_file(cls, config_path: str) -> 'APIConfig':
        """إنشاء كائن APIConfig من ملف التكوين"""
        config = cls()
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # تعيين الخصائص من البيانات المحملة
                for key, value in config_data.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
            
            except Exception as e:
                logger.error(f"خطأ في تحميل ملف التكوين: {str(e)}")
                # إنشاء ملف تكوين جديد إذا كان هناك خطأ
                config.save_to_file(config_path)
        else:
            # إنشاء ملف تكوين جديد إذا لم يكن موجوداً
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            config.save_to_file(config_path)
        
        return config
    
    def save_to_file(self, config_path: str) -> bool:
        """حفظ الإعدادات إلى ملف"""
        try:
            # إنشاء المجلد إذا لم يكن موجوداً
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            # تحويل الكائن إلى قاموس
            config_data = {}
            for key, value in self.__dict__.items():
                config_data[key] = value
            
            # حفظ البيانات إلى ملف JSON
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            return True
        
        except Exception as e:
            logger.error(f"خطأ في حفظ ملف التكوين: {str(e)}")
            return False
    
    def get_api_key(self, provider: str) -> str:
        """الحصول على مفتاح API للمزود المحدد"""
        if provider == "openai":
            return self.openai_api_key
        elif provider == "claude":
            return self.claude_api_key
        elif provider == "grok":
            return self.grok_api_key
        elif provider == "xai":
            return self.xai_api_key
        elif provider == "deepseek":
            return self.deepseek_api_key
        else:
            return ""
    
    def set_api_key(self, provider: str, api_key: str) -> None:
        """تعيين مفتاح API للمزود المحدد"""
        if provider == "openai":
            self.openai_api_key = api_key
        elif provider == "claude":
            self.claude_api_key = api_key
        elif provider == "grok":
            self.grok_api_key = api_key
        elif provider == "xai":
            self.xai_api_key = api_key
        elif provider == "deepseek":
            self.deepseek_api_key = api_key
    
    def get_model(self, provider: str) -> str:
        """الحصول على نموذج للمزود المحدد"""
        if provider == "openai":
            return self.openai_model
        elif provider == "claude":
            return self.claude_model
        elif provider == "grok":
            return self.grok_model
        elif provider == "xai":
            return self.xai_model
        elif provider == "deepseek":
            return self.deepseek_model
        else:
            return ""
    
    def set_model(self, provider: str, model: str) -> None:
        """تعيين نموذج للمزود المحدد"""
        if provider == "openai":
            self.openai_model = model
        elif provider == "claude":
            self.claude_model = model
        elif provider == "grok":
            self.grok_model = model
        elif provider == "xai":
            self.xai_model = model
        elif provider == "deepseek":
            self.deepseek_model = model


class BaseAPIClient(ABC):
    """فئة أساسية لعملاء API"""
    
    def __init__(self, api_config: APIConfig):
        self.api_config = api_config
    
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]]) -> str:
        """إرسال رسائل إلى API والحصول على استجابة"""
        pass
    
    @abstractmethod
    def analyze_code(self, code: str, language: str) -> Dict[str, Any]:
        """تحليل الشيفرة البرمجية باستخدام API"""
        pass
    
    @abstractmethod
    def analyze_security(self, code: str, language: str) -> Dict[str, Any]:
        """تحليل الثغرات الأمنية في الشيفرة البرمجية"""
        pass
    
    @abstractmethod
    def fix_issue(self, code: str, language: str, line: int, message: str) -> Dict[str, Any]:
        """إصلاح مشكلة في الشيفرة البرمجية"""
        pass
    
    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """استخراج JSON من النص"""
        try:
            # البحث عن بداية ونهاية JSON
            start_idx = text.find('{')
            end_idx = text.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {}
        
        except Exception as e:
            logger.error(f"خطأ في استخراج JSON: {str(e)}")
            return {}


class OpenAIClient(BaseAPIClient):
    """عميل API لـ OpenAI"""
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        """إرسال رسائل إلى API والحصول على استجابة"""
        api_key = self.api_config.openai_api_key
        if not api_key:
            raise ValueError("مفتاح API غير موجود لـ OpenAI")
        
        url = self.api_config.openai_api_url
        model = self.api_config.openai_model
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": 0.1
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
        
        except Exception as e:
            logger.error(f"خطأ في OpenAI API: {str(e)}")
            raise
    
    def analyze_code(self, code: str, language: str) -> Dict[str, Any]:
        """تحليل الشيفرة البرمجية باستخدام OpenAI"""
        prompt = self.api_config.analysis_prompt_template.format(
            language=language,
            code=code
        )
        
        messages = [
            {"role": "system", "content": "أنت مساعد برمجة خبير يحلل الشيفرة البرمجية ويكتشف المشاكل. قدم نتائج التحليل بتنسيق JSON فقط."},
            {"role": "user", "content": prompt}
        ]
        
        response_text = self.chat(messages)
        return self._extract_json_from_text(response_text)
    
    def analyze_security(self, code: str, language: str) -> Dict[str, Any]:
        """تحليل الثغرات الأمنية في الشيفرة البرمجية"""
        prompt = self.api_config.security_prompt_template.format(
            language=language,
            code=code
        )
        
        messages = [
            {"role": "system", "content": "أنت خبير أمني متخصص في اكتشاف الثغرات الأمنية في الشيفرة البرمجية. قدم نتائج التحليل بتنسيق JSON فقط."},
            {"role": "user", "content": prompt}
        ]
        
        response_text = self.chat(messages)
        return self._extract_json_from_text(response_text)
    
    def fix_issue(self, code: str, language: str, line: int, message: str) -> Dict[str, Any]:
        """إصلاح مشكلة في الشيفرة البرمجية"""
        prompt = self.api_config.fix_prompt_template.format(
            language=language,
            code=code,
            line=line,
            message=message
        )
        
        messages = [
            {"role": "system", "content": "أنت مساعد برمجة خبير يعمل على إصلاح المشاكل في الشيفرة البرمجية. قدم الشيفرة المصححة بتنسيق JSON فقط."},
            {"role": "user", "content": prompt}
        ]
        
        response_text = self.chat(messages)
        return self._extract_json_from_text(response_text)


class ClaudeClient(BaseAPIClient):
    """عميل API لـ Claude من Anthropic"""
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        """إرسال رسائل إلى API والحصول على استجابة"""
        api_key = self.api_config.claude_api_key
        if not api_key:
            raise ValueError("مفتاح API غير موجود لـ Claude")
        
        url = self.api_config.claude_api_url
        model = self.api_config.claude_model
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        
        # تحويل تنسيق الرسائل من OpenAI إلى Claude
        system_content = ""
        claude_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                claude_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        data = {
            "model": model,
            "messages": claude_messages,
            "system": system_content,
            "temperature": 0.1,
            "max_tokens": 4000
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result["content"][0]["text"]
        
        except Exception as e:
            logger.error(f"خطأ في Claude API: {str(e)}")
            raise
    
    def analyze_code(self, code: str, language: str) -> Dict[str, Any]:
        """تحليل الشيفرة البرمجية باستخدام Claude"""
        prompt = self.api_config.analysis_prompt_template.format(
            language=language,
            code=code
        )
        
        messages = [
            {"role": "system", "content": "أنت مساعد برمجة خبير يحلل الشيفرة البرمجية ويكتشف المشاكل. قدم نتائج التحليل بتنسيق JSON فقط."},
            {"role": "user", "content": prompt}
        ]
        
        response_text = self.chat(messages)
        return self._extract_json_from_text(response_text)
    
    def analyze_security(self, code: str, language: str) -> Dict[str, Any]:
        """تحليل الثغرات الأمنية في الشيفرة البرمجية"""
        prompt = self.api_config.security_prompt_template.format(
            language=language,
            code=code
        )
        
        messages = [
            {"role": "system", "content": "أنت خبير أمني متخصص في اكتشاف الثغرات الأمنية في الشيفرة البرمجية. قدم نتائج التحليل بتنسيق JSON فقط."},
            {"role": "user", "content": prompt}
        ]
        
        response_text = self.chat(messages)
        return self._extract_json_from_text(response_text)
    
    def fix_issue(self, code: str, language: str, line: int, message: str) -> Dict[str, Any]:
        """إصلاح مشكلة في الشيفرة البرمجية"""
        prompt = self.api_config.fix_prompt_template.format(
            language=language,
            code=code,
            line=line,
            message=message
        )
        
        messages = [
            {"role": "system", "content": "أنت مساعد برمجة خبير يعمل على إصلاح المشاكل في الشيفرة البرمجية. قدم الشيفرة المصححة بتنسيق JSON فقط."},
            {"role": "user", "content": prompt}
        ]
        
        response_text = self.chat(messages)
        return self._extract_json_from_text(response_text)


class GrokClient(BaseAPIClient):
    """عميل API لـ Grok"""
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        """إرسال رسائل إلى API والحصول على استجابة"""
        api_key = self.api_config.grok_api_key
        if not api_key:
            raise ValueError("مفتاح API غير موجود لـ Grok")
        
        url = self.api_config.grok_api_url
        model = self.api_config.grok_model
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": 0.1
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
        
        except Exception as e:
            logger.error(f"خطأ في Grok API: {str(e)}")
            raise
    
    def analyze_code(self, code: str, language: str) -> Dict[str, Any]:
        """تحليل الشيفرة البرمجية باستخدام Grok"""
        prompt = self.api_config.analysis_prompt_template.format(
            language=language,
            code=code
        )
        
        messages = [
            {"role": "system", "content": "أنت مساعد برمجة خبير يحلل الشيفرة البرمجية ويكتشف المشاكل. قدم نتائج التحليل بتنسيق JSON فقط."},
            {"role": "user", "content": prompt}
        ]
        
        response_text = self.chat(messages)
        return self._extract_json_from_text(response_text)
    
    def analyze_security(self, code: str, language: str) -> Dict[str, Any]:
        """تحليل الثغرات الأمنية في الشيفرة البرمجية"""
        prompt = self.api_config.security_prompt_template.format(
            language=language,
            code=code
        )
        
        messages = [
            {"role": "system", "content": "أنت خبير أمني متخصص في اكتشاف الثغرات الأمنية في الشيفرة البرمجية. قدم نتائج التحليل بتنسيق JSON فقط."},
            {"role": "user", "content": prompt}
        ]
        
        response_text = self.chat(messages)
        return self._extract_json_from_text(response_text)
    
    def fix_issue(self, code: str, language: str, line: int, message: str) -> Dict[str, Any]:
        """إصلاح مشكلة في الشيفرة البرمجية"""
        prompt = self.api_config.fix_prompt_template.format(
            language=language,
            code=code,
            line=line,
            message=message
        )
        
        messages = [
            {"role": "system", "content": "أنت مساعد برمجة خبير يعمل على إصلاح المشاكل في الشيفرة البرمجية. قدم الشيفرة المصححة بتنسيق JSON فقط."},
            {"role": "user", "content": prompt}
        ]
        
        response_text = self.chat(messages)
        return self._extract_json_from_text(response_text)


class XAIClient(BaseAPIClient):
    """عميل API لـ X.AI (Grok-3-beta)"""
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        """إرسال رسائل إلى API والحصول على استجابة"""
        api_key = self.api_config.xai_api_key
        if not api_key:
            raise ValueError("مفتاح API غير موجود لـ X.AI")
        
        model = self.api_config.xai_model
        
        try:
            # استخدام مكتبة OpenAI مع تغيير نقطة النهاية
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.x.ai/v1",
            )
            
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
            )
            
            return completion.choices[0].message.content
        
        except Exception as e:
            logger.error(f"خطأ في X.AI API: {str(e)}")
            raise
    
    def analyze_code(self, code: str, language: str) -> Dict[str, Any]:
        """تحليل الشيفرة البرمجية باستخدام X.AI (Grok-3-beta)"""
        prompt = self.api_config.analysis_prompt_template.format(
            language=language,
            code=code
        )
        
        messages = [
            {"role": "system", "content": "أنت مساعد برمجة خبير يحلل الشيفرة البرمجية ويكتشف المشاكل. قدم نتائج التحليل بتنسيق JSON فقط."},
            {"role": "user", "content": prompt}
        ]
        
        response_text = self.chat(messages)
        return self._extract_json_from_text(response_text)
    
    def analyze_security(self, code: str, language: str) -> Dict[str, Any]:
        """تحليل الثغرات الأمنية في الشيفرة البرمجية"""
        prompt = self.api_config.security_prompt_template.format(
            language=language,
            code=code
        )
        
        messages = [
            {"role": "system", "content": "أنت خبير أمني متخصص في اكتشاف الثغرات الأمنية في الشيفرة البرمجية. قدم نتائج التحليل بتنسيق JSON فقط."},
            {"role": "user", "content": prompt}
        ]
        
        response_text = self.chat(messages)
        return self._extract_json_from_text(response_text)
    
    def fix_issue(self, code: str, language: str, line: int, message: str) -> Dict[str, Any]:
        """إصلاح مشكلة في الشيفرة البرمجية"""
        prompt = self.api_config.fix_prompt_template.format(
            language=language,
            code=code,
            line=line,
            message=message
        )
        
        messages = [
            {"role": "system", "content": "أنت مساعد برمجة خبير يعمل على إصلاح المشاكل في الشيفرة البرمجية. قدم الشيفرة المصححة بتنسيق JSON فقط."},
            {"role": "user", "content": prompt}
        ]
        
        response_text = self.chat(messages)
        return self._extract_json_from_text(response_text)


class DeepSeekClient(BaseAPIClient):
    """عميل API لـ DeepSeek"""
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        """إرسال رسائل إلى API والحصول على استجابة"""
        api_key = self.api_config.deepseek_api_key
        if not api_key:
            raise ValueError("مفتاح API غير موجود لـ DeepSeek")
        
        url = self.api_config.deepseek_api_url
        model = self.api_config.deepseek_model
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": 0.1
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
        
        except Exception as e:
            logger.error(f"خطأ في DeepSeek API: {str(e)}")
            raise
    
    def analyze_code(self, code: str, language: str) -> Dict[str, Any]:
        """تحليل الشيفرة البرمجية باستخدام DeepSeek"""
        prompt = self.api_config.analysis_prompt_template.format(
            language=language,
            code=code
        )
        
        messages = [
            {"role": "system", "content": "أنت مساعد برمجة خبير يحلل الشيفرة البرمجية ويكتشف المشاكل. قدم نتائج التحليل بتنسيق JSON فقط."},
            {"role": "user", "content": prompt}
        ]
        
        response_text = self.chat(messages)
        return self._extract_json_from_text(response_text)
    
    def analyze_security(self, code: str, language: str) -> Dict[str, Any]:
        """تحليل الثغرات الأمنية في الشيفرة البرمجية"""
        prompt = self.api_config.security_prompt_template.format(
            language=language,
            code=code
        )
        
        messages = [
            {"role": "system", "content": "أنت خبير أمني متخصص في اكتشاف الثغرات الأمنية في الشيفرة البرمجية. قدم نتائج التحليل بتنسيق JSON فقط."},
            {"role": "user", "content": prompt}
        ]
        
        response_text = self.chat(messages)
        return self._extract_json_from_text(response_text)
    
    def fix_issue(self, code: str, language: str, line: int, message: str) -> Dict[str, Any]:
        """إصلاح مشكلة في الشيفرة البرمجية"""
        prompt = self.api_config.fix_prompt_template.format(
            language=language,
            code=code,
            line=line,
            message=message
        )
        
        messages = [
            {"role": "system", "content": "أنت مساعد برمجة خبير يعمل على إصلاح المشاكل في الشيفرة البرمجية. قدم الشيفرة المصححة بتنسيق JSON فقط."},
            {"role": "user", "content": prompt}
        ]
        
        response_text = self.chat(messages)
        return self._extract_json_from_text(response_text)


def get_api_client(api_config: APIConfig, provider: str = None) -> BaseAPIClient:
    """الحصول على عميل API المناسب"""
    if provider is None:
        provider = api_config.preferred_provider
    
    if provider == "openai":
        return OpenAIClient(api_config)
    elif provider == "claude":
        return ClaudeClient(api_config)
    elif provider == "grok":
        return GrokClient(api_config)
    elif provider == "xai":
        return XAIClient(api_config)
    elif provider == "deepseek":
        return DeepSeekClient(api_config)
    else:
        # استخدام المزود المفضل إذا كان المزود المطلوب غير معروف
        provider = api_config.preferred_provider
        return get_api_client(api_config, provider)


class APIManager:
    """مدير واجهات برمجة الذكاء الاصطناعي"""
    
    def __init__(self, api_config: APIConfig):
        self.api_config = api_config
        self.clients = {}
    
    def get_client(self, provider: str = None) -> BaseAPIClient:
        """الحصول على عميل API"""
        if provider is None:
            provider = self.api_config.preferred_provider
        
        # إنشاء العميل إذا لم يكن موجوداً
        if provider not in self.clients:
            self.clients[provider] = get_api_client(self.api_config, provider)
        
        return self.clients[provider]
    
    def test_connection(self, provider: str) -> bool:
        """اختبار الاتصال بمزود API"""
        try:
            client = self.get_client(provider)
            response = client.chat([
                {"role": "system", "content": "أنت مساعد مفيد."},
                {"role": "user", "content": "مرحباً، هذا اختبار اتصال."}
            ])
            
            return len(response) > 0
        
        except Exception as e:
            logger.error(f"فشل اختبار الاتصال لـ {provider}: {str(e)}")
            return False
    
    def get_available_providers(self) -> List[str]:
        """الحصول على قائمة بمزودي API المتاحين (لديهم مفاتيح API)"""
        providers = []
        
        if self.api_config.openai_api_key:
            providers.append("openai")
        
        if self.api_config.claude_api_key:
            providers.append("claude")
        
        if self.api_config.grok_api_key:
            providers.append("grok")
        
        if self.api_config.xai_api_key:
            providers.append("xai")
        
        if self.api_config.deepseek_api_key:
            providers.append("deepseek")
        
        return providers
    
    def analyze_code_with_multiple_providers(self, code: str, language: str) -> Dict[str, Any]:
        """تحليل الشيفرة باستخدام عدة مزودين وجمع النتائج"""
        providers = self.get_available_providers()
        if not providers:
            raise ValueError("لا يوجد مزودي API متاحين")
        
        all_issues = []
        for provider in providers:
            try:
                client = self.get_client(provider)
                results = client.analyze_code(code, language)
                
                if "issues" in results and isinstance(results["issues"], list):
                    for issue in results["issues"]:
                        issue["source"] = provider
                        all_issues.append(issue)
            
            except Exception as e:
                logger.error(f"خطأ في تحليل الشيفرة باستخدام {provider}: {str(e)}")
        
        # تخلص من التكرارات وجمع النتائج
        unique_issues = []
        seen_messages = set()
        
        for issue in all_issues:
            key = f"{issue.get('line', 0)}_{issue.get('message', '')}"
            if key not in seen_messages:
                seen_messages.add(key)
                unique_issues.append(issue)
        
        # ترتيب المشاكل حسب الخطورة
        unique_issues.sort(
            key=lambda x: {"عالية": 0, "متوسطة": 1, "منخفضة": 2}.get(x.get("severity", "متوسطة"), 3)
        )
        
        return {
            "issues": unique_issues,
            "stats": {
                "total_issues": len(unique_issues),
                "providers_used": len(providers)
            }
        }