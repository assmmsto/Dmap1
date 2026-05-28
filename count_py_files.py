import sys
sys.path.insert(0, '/data/data/com.termux/files/home/CGPS')
from pathlib import Path

test_path = input("أدخل مسار المجلد لتحليله: ").strip()

from app.core.scanner import FastScanner
scanner = FastScanner(test_path)
files = scanner.scan_parallel()

py_files = 0
for file_path, info in files.items():
    if info.language == 'python' and info.role != 'isolated':
        py_files += 1

print(f"\n📊 عدد ملفات Python التي ستحلل بـ AI: {py_files}")
print(f"⏱️ تقدير الزمن: {py_files * 3} ثانية ({py_files * 3 / 60:.1f} دقيقة)")
