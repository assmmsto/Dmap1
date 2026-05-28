"""إعدادات مركزية"""
from pathlib import Path
import os

BASE_DIR = Path(__file__).parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
DB_PATH = BASE_DIR / "cgps.db"

SUPPORTED_EXTENSIONS = {
    '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
    '.html': 'html', '.css': 'css', '.json': 'json',
    '.md': 'markdown', '.java': 'java', '.go': 'go',
    '.rs': 'rust', '.cpp': 'cpp', '.txt': 'text'
}

LANGUAGE_ICONS = {
    'python': '🐍', 'javascript': '💛', 'typescript': '💙',
    'html': '🟠', 'css': '🎨', 'json': '📋',
    'markdown': '📝', 'java': '☕', 'go': '🔵',
    'rust': '🦀', 'cpp': '⚙️', 'text': '📄', 'unknown': '📄'
}

DANGER_COLORS = {
    'critical': '#8B0000', 'high': '#DC143C',
    'medium': '#FF8C00', 'low': '#FFD700',
    'safe': '#228B22', 'unknown': '#808080'
}

IGNORE_DIRS = {
    'node_modules', '.git', '__pycache__', 'venv',
    '.venv', 'dist', 'build', '.next', 'coverage', 'uploads'
}

ALLOWED_PATHS = [
    "/data/data/com.termux/files", "/sdcard",
    "/storage", "/home", "/tmp"
]

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_WORKERS = (os.cpu_count() or 4) * 2
SESSION_TTL = 2400  # 24 ساعة
