"""نموذج معلومات الملف"""
from dataclasses import dataclass, field
from typing import List, Set
from app.config import LANGUAGE_ICONS, DANGER_COLORS


@dataclass
class FileInfo:
    path: str
    name: str
    language: str = 'unknown'
    total_lines: int = 0
    code_lines: int = 0
    complexity: int = 0
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    imports_internal: Set[str] = field(default_factory=set)
    imports_external: Set[str] = field(default_factory=set)
    danger_level: str = 'unknown'
    danger_score: float = 0
    role: str = 'normal'
    is_isolated: bool = False
    is_bridge: bool = False
    depended_by: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'id': self.path,
            'name': self.name,
            'label': f"{LANGUAGE_ICONS.get(self.language, '📄')} {self.name}",
            'language': self.language,
            'icon': LANGUAGE_ICONS.get(self.language, '📄'),
            'lines': self.total_lines,
            'complexity': self.complexity,
            'functions': len(self.functions),
            'classes': len(self.classes),
            'danger_level': self.danger_level,
            'danger_score': round(self.danger_score, 1),
            'role': self.role,
            'is_isolated': self.is_isolated,
            'is_bridge': self.is_bridge,
            'color': DANGER_COLORS.get(self.danger_level, '#808080'),
            'external_deps': list(self.imports_external),
            'depended_by': self.depended_by,
            'depends_on': self.depends_on
        }
