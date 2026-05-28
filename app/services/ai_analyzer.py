"""
وحدة التحليل الذكي - OpenRouter (5 مفاتيح مع rotation)
جميع المهام عبر نموذج google/gemini-2.0-flash-001
"""
import json
import urllib.request
import threading
import base64
import re
from typing import Optional, Dict, List
from dataclasses import dataclass, field


# ============ مفاتيح مشفرة ============
_KEYS_ENCODED = [
    "c2stb3ItdjEtZjM5ZTUzNWZkZDAzYzhjZmRkNmUxN2VjNzFiODM3N2M4YjM1NDU4NjRmNTc0N2EwODI5Mjg0Mzg4MmQ4ZDBiOA==",
    "c2stb3ItdjEtNzI0MzY1NGZjZDBhODYxZGZmYjIwMjE2NGZjMGEwZmU5ZTYxM2M4YTlhZmU1YmQ5ZDgzZjE4ZjU3YTBiYjcxMg==",
    "c2stb3ItdjEtOWY4MDA3OTNlNjMxYTE5MjJhMDBlOTE1NDNiZTg3OTJhMDcyYjA3MzJiZjk4ZDMyZTJmYTM0ZGUzODI3NTkzNA==",
    "c2stb3ItdjEtMmJkODhjNTA3ZWJhMmFjMTUxOGI1YTgxZTgxMmI0Zjc5Y2U3YTc2ZTIzMzY0ZWRjYTQ3ZTU5ZDBjN2Y5MTcxOA==",
    "c2stb3ItdjEtODhmN2IzNDljZTMyOGE4YmMzMTliMzg1ZGQyNjFiNTlkMWQ3NGIxNDMzYmU4YTAzNTcyNDc1NzViZDkzN2ExZQ==",
]

_MODEL = "google/gemini-2.0-flash-001"


def _decode(encoded: str) -> str:
    try:
        return base64.b64decode(encoded).decode()
    except:
        return ""


@dataclass
class AIResult:
    summary: str = ""
    quality_score: float = 0
    security_issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    architecture_note: str = ""
    error: str = ""


class AIAnalyzer:
    def __init__(self):
        self._keys = [_decode(k) for k in _KEYS_ENCODED if _decode(k)]
        self._idx = 0
        self._lock = threading.Lock()

    def _next_key(self) -> str:
        with self._lock:
            if not self._keys:
                return ""
            key = self._keys[self._idx]
            self._idx = (self._idx + 1) % len(self._keys)
            return key

    def _call(self, prompt: str) -> str:
        """استدعاء OpenRouter وإرجاع النص"""
        key = self._next_key()
        if not key:
            return ""

        try:
            data = json.dumps({
                "model": _MODEL,
                "messages": [{"role": "user", "content": prompt}]
            }).encode()

            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {key}",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "CGPS"
                }
            )
            r = urllib.request.urlopen(req, timeout=20)
            resp = json.loads(r.read())
            return resp["choices"][0]["message"]["content"]
        except Exception as e:
            return ""

    def _parse_json(self, text: str) -> dict:
        """استخراج JSON من النص"""
        text = re.sub(r'```json\s*|\s*```', '', text).strip()
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        return {}

    def analyze_file(self, file_path: str, content: str, language: str, lang: str = "ar") -> AIResult:
        """تحليل كامل لملف واحد"""
        result = AIResult()

        # اقتصاص الكود إذا كان طويلاً
        code = content[:6000]

        prompt = f"""أنت خبير برمجي. حلل هذا الملف ({language}) وأجب بـ JSON فقط:

{{
  "summary": "شرح عربي مختصر للملف في 2-3 أسطر",
  "score": تقييم جودة الكود من 10,
  "security": ["ثغرة1", "ثغرة2"],
  "suggestions": ["اقتراح1 لتحسين الكود", "اقتراح2"],
  "architecture": "ملاحظة معمارية عربية مختصرة"
}}

المسار: {file_path}
الكود:
{code}"""

        text = self._call(prompt)
        if text:
            parsed = self._parse_json(text)
            result.summary = parsed.get("summary", "")
            result.quality_score = float(parsed.get("score", 0))
            result.security_issues = parsed.get("security", [])
            result.suggestions = parsed.get("suggestions", [])
            result.architecture_note = parsed.get("architecture", "")
        else:
            result.error = "فشل الاتصال بـ OpenRouter"

        return result

    def analyze_project(self, summary: dict) -> str:
        """وصف عام للمشروع"""
        prompt = f"""أنت خبير برمجي. صف هذا المشروع باختصار بالعربية (3-4 جمل):

الإحصائيات:
- عدد الملفات: {summary.get('total_files', 0)}
- إجمالي الأسطر: {summary.get('total_lines', 0)}
- توزيع الخطورة: {summary.get('danger_distribution', {})}
- توزيع الأدوار: {summary.get('role_distribution', {})}

اذكر: نوع المشروع، نمط الهندسة، نقاط القوة والضعف."""
        return self._call(prompt) or ""

    def analyze_god_files(self, files: List[dict]) -> List[dict]:
        """تحليل الملفات الخطرة (god files) واقتراح تفكيكها"""
        results = []
        for f in files[:3]:  # أقصى 3 ملفات
            prompt = f"""هذا ملف خطر (God File) في المشروع. اقترح طريقة لتفكيكه لملفات أصغر. أجب بـ JSON:

{{
  "split_into": ["اسم_ملف1", "اسم_ملف2"],
  "reason": "سبب التفكيك بالعربية"
}}

الملف: {f['name']}
الأسطر: {f['lines']}
الدوال: {f['functions']}
الكلاسات: {f['classes']}"""

            text = self._call(prompt)
            if text:
                parsed = self._parse_json(text)
                parsed["file"] = f["name"]
                results.append(parsed)

        return results


# نسخة مفردة
ai = AIAnalyzer()
