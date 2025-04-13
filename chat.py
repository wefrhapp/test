#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إدارة المحادثات مع المساعد الذكي
"""
import os
import re
import json
import logging
import time
from typing import Dict, List, Any, Tuple, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime

from PySide6.QtCore import QObject, Signal, Slot, QThread
from PySide6.QtWidgets import QWidget

# استيراد المكونات الضرورية مع معالجة استثناءات الاستيراد
try:
    from analyzer import APIThreadManager
    HAS_THREAD_MANAGER = True
except ImportError:
    HAS_THREAD_MANAGER = False
    logging.getLogger("CodeAnalyzer.Chat").warning("تعذر استيراد APIThreadManager. لن يتم تنظيف خيوط المحادثة تلقائياً.")

from api_clients import APIConfig, get_api_client, XAIClient
from utils import save_json, read_file, write_file, ensure_dir

logger = logging.getLogger("CodeAnalyzer.Chat")

@dataclass
class ChatMessage:
    """تمثيل رسالة محادثة"""
    role: str  # "user" أو "assistant" أو "system"
    content: str
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل الرسالة إلى قاموس"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """إنشاء رسالة من قاموس"""
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", datetime.now().timestamp())
        )


@dataclass
class ChatSession:
    """تمثيل جلسة محادثة"""
    id: str  # معرف فريد للجلسة
    title: str  # عنوان الجلسة
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    
    def add_message(self, role: str, content: str) -> ChatMessage:
        """إضافة رسالة إلى الجلسة"""
        message = ChatMessage(role, content)
        self.messages.append(message)
        return message
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل الجلسة إلى قاموس"""
        return {
            "id": self.id,
            "title": self.title,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatSession':
        """إنشاء جلسة من قاموس"""
        session = cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            created_at=data.get("created_at", datetime.now().timestamp())
        )
        
        session.messages = [
            ChatMessage.from_dict(msg) for msg in data.get("messages", [])
        ]
        
        return session
    
    def clear_messages(self):
        """مسح جميع الرسائل في الجلسة"""
        self.messages = []
    
    def get_api_messages(self) -> List[Dict[str, str]]:
        """الحصول على الرسائل بتنسيق مناسب لواجهة API"""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.messages
        ]


class ChatThread(QThread):
    """خيط للمحادثة مع المساعد الذكي"""
    
    response_received = Signal(str)  # نص الاستجابة
    error_occurred = Signal(str)  # رسالة الخطأ
    
    def __init__(self, api_config: APIConfig, messages: List[Dict[str, str]]):
        super().__init__()
        self.api_config = api_config
        self.messages = messages
        self.provider = api_config.preferred_provider
        
        # تسجيل الخيط في مدير الخيوط إذا كان متاحاً
        if HAS_THREAD_MANAGER:
            APIThreadManager.register_thread(self)
    
    def run(self):
        """تنفيذ المحادثة"""
        try:
            # اختيار المزود المناسب
            provider = self.provider
            
            # التحقق من وجود مفتاح API
            if not self.api_config.get_api_key(provider):
                # محاولة استخدام مزود آخر متاح
                for alt_provider in ["xai", "openai", "claude", "grok", "deepseek"]:
                    if self.api_config.get_api_key(alt_provider):
                        provider = alt_provider
                        break
                else:
                    raise ValueError("لا يوجد مفتاح API متاح. يرجى إضافة مفتاح API في الإعدادات.")
            
            # الحصول على العميل المناسب
            client = get_api_client(self.api_config, provider)
            
            # إرسال الرسائل والحصول على الاستجابة
            response = client.chat(self.messages)
            
            self.response_received.emit(response)
        
        except Exception as e:
            logger.error(f"خطأ في المحادثة: {str(e)}")
            self.error_occurred.emit(str(e))
        
        finally:
            # إلغاء تسجيل الخيط من مدير الخيوط عند الانتهاء
            if HAS_THREAD_MANAGER:
                APIThreadManager.unregister_thread(self)


class ChatWorker(QObject):
    """عامل معالجة المحادثة في خلفية البرنامج"""
    
    finished = Signal(str)  # إشارة لإنهاء المعالجة
    error = Signal(str)  # إشارة للأخطاء
    
    def __init__(self, api_config: APIConfig, message: str, history: List[Dict[str, str]]):
        super().__init__()
        self.api_config = api_config
        self.message = message
        self.history = history
        self.provider = api_config.preferred_provider
    
    @Slot()
    def process(self):
        """معالجة الرسالة والحصول على استجابة"""
        try:
            # إعداد الرسائل
            messages = self.history.copy()
            messages.append({"role": "user", "content": self.message})
            
            # اختيار المزود المناسب
            provider = self.provider
            
            # التحقق من وجود مفتاح API
            if not self.api_config.get_api_key(provider):
                # محاولة استخدام مزود آخر متاح
                for alt_provider in ["xai", "openai", "claude", "grok", "deepseek"]:
                    if self.api_config.get_api_key(alt_provider):
                        provider = alt_provider
                        break
                else:
                    raise ValueError("لا يوجد مفتاح API متاح. يرجى إضافة مفتاح API في الإعدادات.")
            
            # الحصول على العميل المناسب
            client = get_api_client(self.api_config, provider)
            
            # إرسال الرسائل والحصول على الاستجابة
            response = client.chat(messages)
            
            self.finished.emit(response)
        
        except Exception as e:
            logger.error(f"خطأ في معالجة المحادثة: {str(e)}")
            self.error.emit(str(e))


class CodeModificationExtractor:
    """استخراج التعديلات المقترحة من ردود المحادثة"""
    
    def __init__(self):
        # أنماط استخراج تعديلات الكود
        self.patterns = {
            # نمط لاستخراج قسم من الشيفرة البرمجية
            "code_block": r"```(?:\w+)?\s*([\s\S]*?)```",
            
            # نمط لاستخراج مسار الملف
            "file_path": r"[`'\"]([^`'\"]+\.(py|js|dart|php|html|css|json))[`'\"]",
            
            # نمط لاستخراج وصف التعديل
            "modification_description": r"(?:يمكن|يجب|اقترح)\s+(?:تعديل|تغيير|تحديث)([^.]+)"
        }
    
    def extract_code_blocks(self, text: str) -> List[str]:
        """
        استخراج كتل الكود من النص
        """
        return re.findall(self.patterns["code_block"], text)

    def extract_file_paths(self, text: str) -> List[str]:
        """
        استخراج مسارات الملفات من النص
        """
        return [match[0] for match in re.findall(self.patterns["file_path"], text)]

    def extract_modifications(self, response: str) -> List[Dict[str, Any]]:
        """
        استخراج التعديلات المقترحة من رد المحادثة
        """
        modifications = []
        code_blocks = self.extract_code_blocks(response)
        file_paths = self.extract_file_paths(response)

        if code_blocks and file_paths:
            if len(code_blocks) == len(file_paths):
                for i in range(len(code_blocks)):
                    modifications.append({
                        "file_path": file_paths[i],
                        "code": code_blocks[i],
                        "description": self._extract_description(response)
                    })
            else:
                paragraphs = response.split('\n\n')
                for paragraph in paragraphs:
                    code_in_paragraph = self.extract_code_blocks(paragraph)
                    files_in_paragraph = self.extract_file_paths(paragraph)

                    for j in range(min(len(code_in_paragraph), len(files_in_paragraph))):
                        modifications.append({
                            "file_path": files_in_paragraph[j],
                            "code": code_in_paragraph[j],
                            "description": self._extract_description(paragraph)
                        })

        return modifications

    def _extract_description(self, text: str) -> str:
        """
        استخراج وصف التعديل
        """
        match = re.search(self.patterns["modification_description"], text)
        return match.group(1).strip() if match else "تعديل مقترح"


class FeatureDevelopmentHelper:
    """مساعد تطوير ميزات جديدة عبر المحادثة"""
    
    def __init__(self, project_dir: str, api_config: APIConfig):
        self.project_dir = project_dir
        self.api_config = api_config
        self.extractor = CodeModificationExtractor()
    
    def generate_feature(self, description: str, project_context: str) -> Dict[str, Any]:
        """توليد ميزة جديدة بناءً على الوصف"""
        # إنشاء سياق للطلب
        prompt = f"""
أنت مطور برمجيات محترف. أحتاج منك كتابة كود لإضافة ميزة جديدة إلى المشروع.

وصف الميزة المطلوبة:
{description}

معلومات عن المشروع:
{project_context}

يرجى كتابة الكود اللازم لتنفيذ هذه الميزة. لكل ملف ستقوم بإنشائه أو تعديله، 
قم بذكر مسار الملف ثم كتابة الكود كاملاً داخل كتلة الكود ```
مع شرح مختصر لما يفعله هذا الكود.
"""

        # محاولة استخدام X.AI إذا كان متاحاً لأنه أفضل لتوليد الشيفرة
        provider = self.api_config.preferred_provider
        if self.api_config.xai_api_key:
            provider = "xai"
            
        # إرسال الطلب إلى النموذج
        client = get_api_client(self.api_config, provider)
        messages = [
            {"role": "system", "content": "أنت مساعد برمجي متخصص في تطوير التطبيقات."},
            {"role": "user", "content": prompt}
        ]
        
        response = client.chat(messages)
        
        # استخراج التعديلات المقترحة
        modifications = self.extractor.extract_modifications(response)
        
        return {
            "feature_description": description,
            "response": response,
            "modifications": modifications
        }
    
    def apply_feature(self, feature_data: Dict[str, Any]) -> List[str]:
        """تطبيق الميزة المقترحة على المشروع"""
        applied_files = []
        
        for mod in feature_data.get("modifications", []):
            file_path = mod.get("file_path", "")
            code = mod.get("code", "")
            
            if not file_path or not code:
                continue
            
            # معالجة المسار
            if not os.path.isabs(file_path):
                file_path = os.path.join(self.project_dir, file_path)
            
            # التحقق من وجود الملف
            file_exists = os.path.exists(file_path)
            
            if file_exists:
                # تعديل ملف موجود
                original_content = read_file(file_path) or ""
                if write_file(file_path, code):
                    applied_files.append(file_path)
            else:
                # إنشاء ملف جديد
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                if write_file(file_path, code):
                    applied_files.append(file_path)
        
        return applied_files


class ChatComponent(QWidget):
    """مكون المحادثة مع المساعد الذكي"""
    
    message_sent = Signal(ChatMessage)
    message_received = Signal(ChatMessage)
    error_occurred = Signal(str)
    
    def __init__(self, api_config: APIConfig, project_dir: str = None, parent=None):
        """
        تهيئة مكون المحادثة مع إعدادات المشروع
        """
        super().__init__(parent)
        self.api_config = api_config
        self.project_dir = project_dir
        self.current_session = None
        self.sessions = []
        self.chat_threads = []  # قائمة لتتبع جميع الخيوط النشطة
        self.conversation_history = []  # تاريخ المحادثة
        
        # تهيئة مساعد تطوير الميزات ومجلد الجلسات
        if project_dir:
            self.feature_helper = FeatureDevelopmentHelper(project_dir, api_config)
            self.sessions_dir = os.path.join(project_dir, "_chat_sessions")
            os.makedirs(self.sessions_dir, exist_ok=True)
            
        # تهيئة واجهة المستخدم
        self.setup_ui()
    
    def setup_ui(self):
        """
        إعداد واجهة المستخدم
        """
        # يمكن إضافة رمز إعداد الواجهة هنا
        pass
    
    def send_message(self, message: str):
        """
        إرسال رسالة إلى الذكاء الاصطناعي
        """
        if not message.strip():
            return
            
        # إنشاء رسالة المستخدم
        user_message = ChatMessage(role="user", content=message)
        self.message_sent.emit(user_message)
        
        # تحديث تاريخ المحادثة
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
        
        # حفظ الجلسة الحالية إذا كانت موجودة
        if self.current_session:
            self.current_session.add_message("user", message)
            self.save_current_session()
        
        # إزالة أي خيوط سابقة نشطة
        self.stop_active_threads()
        
        # إنشاء عامل جديد للمحادثة وخيط
        chat_worker = ChatWorker(self.api_config, message, self.conversation_history)
        chat_thread = QThread()
        chat_worker.moveToThread(chat_thread)
        
        # تسجيل الخيط وتوصيل الإشارات
        self.chat_threads.append(chat_thread)
        
        chat_thread.started.connect(chat_worker.process)
        chat_worker.finished.connect(lambda response: self.handle_response(response))
        chat_worker.error.connect(lambda error: self.handle_error(error))
        chat_worker.finished.connect(chat_thread.quit)
        chat_worker.finished.connect(chat_worker.deleteLater)
        chat_thread.finished.connect(lambda: self.cleanup_thread(chat_thread))
        
        # بدء الخيط
        chat_thread.start()
    
    def handle_response(self, response: str):
        """
        معالجة الاستجابة من الذكاء الاصطناعي
        """
        # إنشاء رسالة المساعد
        assistant_message = ChatMessage(role="assistant", content=response)
        self.message_received.emit(assistant_message)
        
        # تحديث تاريخ المحادثة
        self.conversation_history.append({
            "role": "assistant",
            "content": response
        })
        
        # حفظ الجلسة الحالية إذا كانت موجودة
        if self.current_session:
            self.current_session.add_message("assistant", response)
            self.save_current_session()
    
    def handle_error(self, error: str):
        """
        معالجة الأخطاء
        """
        self.error_occurred.emit(error)
        logger.error(f"خطأ في المحادثة: {error}")
    
    def cleanup_thread(self, thread: QThread):
        """
        تنظيف الخيط بعد انتهاء العمل
        """
        if thread in self.chat_threads:
            self.chat_threads.remove(thread)
    
    def stop_active_threads(self):
        """
        إيقاف جميع الخيوط النشطة
        """
        for thread in self.chat_threads[:]:  # نسخة من القائمة لتجنب التعديل أثناء التكرار
            if thread.isRunning():
                thread.quit()
                thread.wait(1000)  # انتظار ثانية واحدة للتوقف الطبيعي
                
                if thread.isRunning():
                    logger.warning("الخيط لم يتوقف بشكل طبيعي، سيتم إنهاؤه بالقوة.")
                    thread.terminate()
                    thread.wait()
                
                self.chat_threads.remove(thread)
    
    def create_new_session(self, title: str = None) -> ChatSession:
        """
        إنشاء جلسة محادثة جديدة
        """
        # إنشاء معرف فريد
        session_id = f"session_{int(time.time())}"
        
        # إذا لم يتم تحديد عنوان، استخدم عنوانًا افتراضيًا
        if not title:
            title = f"محادثة {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # إنشاء الجلسة
        self.current_session = ChatSession(id=session_id, title=title)
        
        # إضافة رسالة النظام الافتراضية
        self.current_session.add_message("system", "أنت مساعد برمجة ذكي ومفيد. أجب دائماً باللغة العربية.")
        
        # إضافة الجلسة إلى قائمة الجلسات
        self.sessions.append(self.current_session)
        
        # حفظ الجلسة
        self.save_current_session()
        
        return self.current_session
    
    def load_session(self, session_id: str) -> Optional[ChatSession]:
        """
        تحميل جلسة محادثة
        """
        # البحث عن الجلسة في القائمة
        for session in self.sessions:
            if session.id == session_id:
                self.current_session = session
                
                # تحديث تاريخ المحادثة
                self.conversation_history = session.get_api_messages()
                
                return session
        
        # إذا لم يتم العثور على الجلسة، حاول تحميلها من الملف
        if self.project_dir:
            session_path = os.path.join(self.sessions_dir, f"{session_id}.json")
            if os.path.exists(session_path):
                try:
                    with open(session_path, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    
                    session = ChatSession.from_dict(session_data)
                    self.sessions.append(session)
                    self.current_session = session
                    
                    # تحديث تاريخ المحادثة
                    self.conversation_history = session.get_api_messages()
                    
                    return session
                except Exception as e:
                    logger.error(f"خطأ في تحميل الجلسة: {str(e)}")
        
        return None
    
    def save_current_session(self) -> bool:
        """
        حفظ الجلسة الحالية
        """
        if not self.current_session or not self.project_dir:
            return False
        
        try:
            # التأكد من وجود المجلد
            os.makedirs(self.sessions_dir, exist_ok=True)
            
            # حفظ الجلسة في ملف
            session_path = os.path.join(self.sessions_dir, f"{self.current_session.id}.json")
            with open(session_path, 'w', encoding='utf-8') as f:
                json.dump(self.current_session.to_dict(), f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"خطأ في حفظ الجلسة: {str(e)}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """
        حذف جلسة محادثة
        """
        # البحث عن الجلسة في القائمة
        for i, session in enumerate(self.sessions):
            if session.id == session_id:
                # حذف الجلسة من القائمة
                del self.sessions[i]
                
                # إذا كانت الجلسة الحالية، قم بإعادة تعيينها
                if self.current_session and self.current_session.id == session_id:
                    self.current_session = None
                    self.conversation_history = []
                
                # حذف ملف الجلسة
                if self.project_dir:
                    session_path = os.path.join(self.sessions_dir, f"{session_id}.json")
                    if os.path.exists(session_path):
                        os.remove(session_path)
                
                return True
        
        return False
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        الحصول على قائمة بجميع جلسات المحادثة
        """
        return [
            {
                "id": session.id,
                "title": session.title,
                "created_at": session.created_at,
                "message_count": len(session.messages)
            }
            for session in self.sessions
        ]
    
    def load_all_sessions(self):
        """
        تحميل جميع جلسات المحادثة من المجلد
        """
        if not self.project_dir:
            return
        
        self.sessions = []
        
        try:
            # التأكد من وجود المجلد
            os.makedirs(self.sessions_dir, exist_ok=True)
            
            # قراءة جميع ملفات الجلسات
            for filename in os.listdir(self.sessions_dir):
                if filename.endswith(".json"):
                    session_path = os.path.join(self.sessions_dir, filename)
                    try:
                        with open(session_path, 'r', encoding='utf-8') as f:
                            session_data = json.load(f)
                        
                        session = ChatSession.from_dict(session_data)
                        self.sessions.append(session)
                    except Exception as e:
                        logger.error(f"خطأ في تحميل الجلسة {filename}: {str(e)}")
            
            # ترتيب الجلسات حسب تاريخ الإنشاء (الأحدث أولاً)
            self.sessions.sort(key=lambda s: s.created_at, reverse=True)
        
        except Exception as e:
            logger.error(f"خطأ في تحميل جلسات المحادثة: {str(e)}")
    
    def generate_code(self, prompt: str, language: str = "python") -> str:
        """
        توليد شيفرة برمجية استناداً إلى الأمر
        """
        if not prompt.strip():
            return ""
        
        # إنشاء رسائل للطلب
        messages = [
            {"role": "system", "content": f"أنت مساعد برمجة متخصص في لغة {language}. قم بتوليد شيفرة برمجية استناداً إلى الطلب. قدم الشيفرة فقط بدون تفسير إضافي."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            # محاولة استخدام X.AI إذا كان متاحاً لأنه أفضل لتوليد الشيفرة
            provider = self.api_config.preferred_provider
            if self.api_config.xai_api_key:
                provider = "xai"
                
            # الحصول على العميل المناسب
            client = get_api_client(self.api_config, provider)
            
            # إرسال الطلب والحصول على الاستجابة
            response = client.chat(messages)
            
            # استخراج الشيفرة من الاستجابة
            code = self._extract_code(response, language)
            return code if code else response
        
        except Exception as e:
            logger.error(f"خطأ في توليد الشيفرة: {str(e)}")
            return f"خطأ: {str(e)}"
    
    def _extract_code(self, text: str, language: str) -> str:
        """استخراج الشيفرة البرمجية من النص"""
        # البحث عن الشيفرة المحاطة بعلامات ```
        
        # أنماط مختلفة لعلامات الشيفرة
        patterns = [
            # نمط لغة محددة: ```python
            rf"```{language}(.*?)```",
            # نمط عام: ```
            r"```(.*?)```",
            # نمط بديل: `
            r"`(.*?)`"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                # استخدام أول مطابقة
                return matches[0].strip()
        
        # إذا لم يتم العثور على علامات، أعد النص كما هو
        return text