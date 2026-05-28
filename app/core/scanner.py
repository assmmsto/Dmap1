"""
الماسح فائق السرعة
- مسح متوازي مع ThreadPoolExecutor
- تجاهل الملفات الثنائية تلقائياً
- فهرسة مسبقة للحزم
- حد أقصى لحجم الملف
"""
import os
import ast
import re
import threading
from pathlib import Path
from typing import Dict, List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.config import (
    SUPPORTED_EXTENSIONS, IGNORE_DIRS, 
    MAX_FILE_SIZE, MAX_WORKERS
)
from app.models.file_info import FileInfo


# أنماط regex مجمعة مسبقاً (أسرع)
_RE_JS_IMPORT = re.compile(
    r"import\s+.*?from\s+['\"]([^'\"]+)['\"]|require\s*\(\s*['\"]([^'\"]+)['\"]"
)
_RE_JS_FUNC = re.compile(
    r'(?:function\s+(\w+)|(\w+)\s*=\s*(?:async\s*)?\(|(\w+)\s*:\s*function)'
)
_RE_JS_CLASS = re.compile(r'class\s+(\w+)')
_RE_TS_DECORATOR = re.compile(r'@\w+')

# كلمات محجوزة (لا تعتبر دوال)
_RESERVED = {'if','for','while','switch','catch','return','else','try','except','finally','with','class','import','from','async','await','yield','break','continue','pass','raise','assert','del','global','nonlocal','lambda','True','False','None'}


class FastScanner:
    """ماسح متوازي فائق السرعة"""
    
    def __init__(self, root_path: str, max_workers: int = None):
        self.root_path = Path(root_path).resolve()
        self.files: Dict[str, FileInfo] = {}
        self.packages: Set[str] = set()
        self._lock = threading.Lock()
        self.max_workers = max_workers or MAX_WORKERS
        self._all_files: List[Path] = []
    
    def _collect_files(self) -> List[Path]:
        """جمع كل الملفات دفعة واحدة"""
        files = []
        
        for root, dirs, filenames in os.walk(self.root_path):
            # تجاهل المجلدات غير المرغوبة
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
            
            for f in filenames:
                ext = os.path.splitext(f)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    fp = Path(root) / f
                    # تجاهل الملفات الكبيرة جداً
                    try:
                        if fp.stat().st_size <= MAX_FILE_SIZE:
                            files.append(fp)
                    except OSError:
                        pass
        
        return files
    
    def scan_parallel(self) -> Dict[str, FileInfo]:
        """مسح متوازي لجميع الملفات"""
        self._all_files = self._collect_files()
        
        if not self._all_files:
            return {}
        
        # بناء فهرس الحزم أولاً
        self._build_package_index()
        
        # مسح متوازي
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._scan_safe, fp): fp 
                for fp in self._all_files
            }
            
            for future in as_completed(futures):
                fp = futures[future]
                try:
                    info = future.result(timeout=10)
                    if info:
                        with self._lock:
                            rel = str(info.path)
                            self.files[rel] = info
                except Exception:
                    pass
        
        return self.files
    
    def _build_package_index(self) -> None:
        """فهرسة الحزم سريعاً"""
        for fp in self._all_files:
            try:
                rel = fp.relative_to(self.root_path)
                parts = rel.parts
                for part in parts[:-1]:  # كل المجلدات
                    self.packages.add(part)
                self.packages.add(fp.stem)  # اسم الملف بدون امتداد
            except ValueError:
                pass
    
    def _scan_safe(self, fp: Path) -> FileInfo | None:
        """مسح آمن لملف واحد"""
        try:
            return self._scan_file(fp)
        except Exception:
            return None
    
    def _scan_file(self, fp: Path) -> FileInfo | None:
        """مسح ملف واحد"""
        ext = fp.suffix.lower()
        lang = SUPPORTED_EXTENSIONS.get(ext, 'unknown')
        
        try:
            rel = fp.relative_to(self.root_path)
        except ValueError:
            rel = fp
        
        # قراءة الملف
        try:
            with open(fp, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return None
        
        lines = content.split('\n')
        total = len(lines)
        
        # عد الأسطر الفعلية (غير الفارغة والتعليقات)
        code_lines = 0
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith(('#', '//', '/*', '*', '<!--')):
                code_lines += 1
        
        info = FileInfo(
            path=str(rel).replace('\\', '/'),
            name=fp.name,
            language=lang,
            total_lines=total,
            code_lines=code_lines
        )
        
        # تحليل حسب اللغة
        if lang == 'python':
            self._analyze_python(content, info)
        elif lang in ('javascript', 'typescript'):
            self._analyze_js_ts(content, info, lang)
        
        return info
    
    def _analyze_python(self, content: str, info: FileInfo) -> None:
        """تحليل Python باستخدام AST"""
        try:
            tree = ast.parse(content)
            
            complexity = 0
            func_count = 0
            
            for node in ast.walk(tree):
                # Imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.name.split('.')[0]
                        info.imports_external.add(name)
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        if node.level > 0:  # استيراد نسبي
                            info.imports_internal.add(node.module)
                        else:
                            info.imports_external.add(node.module.split('.')[0])
                
                # دوال
                elif isinstance(node, ast.FunctionDef):
                    info.functions.append(node.name)
                    func_count += 1
                    # حساب التعقيد للدالة
                    func_complexity = 1
                    for child in ast.walk(node):
                        if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                            func_complexity += 1
                        elif isinstance(child, ast.BoolOp):
                            func_complexity += len(child.values) - 1
                    complexity += func_complexity
                
                # كلاسات
                elif isinstance(node, ast.ClassDef):
                    info.classes.append(node.name)
            
            info.complexity = complexity
            
        except SyntaxError:
            pass
    
    def _analyze_js_ts(self, content: str, info: FileInfo, lang: str) -> None:
        """تحليل JavaScript/TypeScript باستخدام regex"""
        # Imports
        for m in _RE_JS_IMPORT.finditer(content):
            src = m.group(1) or m.group(2)
            if src:
                if src.startswith('.'):
                    info.imports_internal.add(src)
                else:
                    info.imports_external.add(src.split('/')[0])
        
        # دوال
        for m in _RE_JS_FUNC.finditer(content):
            name = m.group(1) or m.group(2) or m.group(3)
            if name and name not in _RESERVED:
                info.functions.append(name)
        
        # كلاسات
        for m in _RE_JS_CLASS.finditer(content):
            info.classes.append(m.group(1))
        
        # تعقيد بسيط
        complexity = 1
        for pattern in ['if ', 'for ', 'while ', 'switch ', 'catch', '&&', '||', '?']:
            complexity += content.count(pattern)
        info.complexity = complexity
