"""
المحلل فائق السرعة
- فهرسة O(1) لحل الاعتماديات
- تصنيف متعدد المستويات
- كشف God Files والجسور
"""
import os
from typing import Dict, List, Set, Tuple
from collections import defaultdict
from app.models.file_info import FileInfo


class FastAnalyzer:
    """محلل اعتماديات سريع مع فهرسة O(1)"""
    
    def __init__(self, files: Dict[str, FileInfo]):
        self.files = files
        
        # فهارس للبحث السريع
        self._name_index: Dict[str, str] = {}       # اسم الملف → مساره
        self._stem_index: Dict[str, str] = {}       # الاسم بدون امتداد → مساره
        self._dir_index: Dict[str, List[str]] = defaultdict(list)  # مجلد → ملفاته
        
        self._build_indexes()
        self._resolve_dependencies()
        self._calculate_danger()
        self._assign_roles()
        self._detect_cycles()
    
    def _build_indexes(self) -> None:
        """بناء فهارس O(1) للبحث السريع"""
        for path in self.files:
            name = os.path.basename(path)
            stem = os.path.splitext(name)[0]
            directory = os.path.dirname(path)
            
            self._name_index[name] = path
            self._stem_index[stem] = path
            self._dir_index[directory].append(path)
            
            # فهرسة بدون امتداد أيضاً
            if stem != name:
                self._name_index[stem] = path
    
    def _resolve_import(self, dep: str, current_file: str) -> str | None:
        """حل import بسرعة O(1)"""
        # 1. بحث مباشر بالمسار
        if dep in self.files:
            return dep
        
        # 2. إضافة .py
        py_file = dep + '.py'
        if py_file in self._name_index:
            return self._name_index[py_file]
        
        # 3. مسار نسبي من موقع الملف الحالي
        cur_dir = os.path.dirname(current_file)
        resolved = os.path.normpath(os.path.join(cur_dir, dep.replace('.', os.sep) + '.py'))
        if resolved in self.files:
            return resolved
        
        # بدون .py
        resolved2 = os.path.normpath(os.path.join(cur_dir, dep.replace('.', os.sep)))
        if resolved2 in self.files:
            return resolved2
        
        # 4. بحث بالاسم فقط
        dep_name = os.path.basename(dep)
        if dep_name in self._name_index:
            return self._name_index[dep_name]
        
        stem = os.path.splitext(dep_name)[0]
        if stem in self._stem_index:
            return self._stem_index[stem]
        
        # 5. بحث في نفس المجلد
        for f in self._dir_index.get(cur_dir, []):
            if os.path.splitext(os.path.basename(f))[0] == dep:
                return f
        
        return None
    
    def _resolve_dependencies(self) -> None:
        """بناء العلاقات بين الملفات"""
        for path, info in self.files.items():
            # دمج كل imports
            all_imports = info.imports_internal | info.imports_external
            
            for dep in all_imports:
                resolved = self._resolve_import(dep, path)
                
                if resolved and resolved in self.files and resolved != path:
                    # إضافة العلاقة
                    if resolved not in info.depends_on:
                        info.depends_on.append(resolved)
                    if path not in self.files[resolved].depended_by:
                        self.files[resolved].depended_by.append(path)
                    
                    # إزالة من imports (صار تبعية داخلية)
                    info.imports_internal.discard(dep)
                    info.imports_external.discard(dep)
    
    def _calculate_danger(self) -> None:
        """حساب درجة الخطورة"""
        if not self.files:
            return
        
        # حساب القيم القصوى
        max_dep_by = max((len(f.depended_by) for f in self.files.values()), default=1)
        max_dep_on = max((len(f.depends_on) for f in self.files.values()), default=1)
        max_lines = max((f.total_lines for f in self.files.values()), default=1)
        max_complexity = max((f.complexity for f in self.files.values()), default=1)
        
        for info in self.files.values():
            score = 0.0
            
            # 40% - عدد الملفات المعتمدة عليه (تأثير الفشل)
            if max_dep_by > 0:
                score += (len(info.depended_by) / max_dep_by) * 40
            
            # 20% - عدد اعتماداته (تعقيد التغيير)
            if max_dep_on > 0:
                score += (len(info.depends_on) / max_dep_on) * 20
            
            # 20% - حجم الملف
            if max_lines > 0:
                score += (info.total_lines / max_lines) * 20
            
            # 20% - التعقيد
            if max_complexity > 0:
                score += (info.complexity / max_complexity) * 20
            
            info.danger_score = min(score, 100.0)
            
            # تصنيف
            if score >= 70:
                info.danger_level = 'critical'
            elif score >= 50:
                info.danger_level = 'high'
            elif score >= 30:
                info.danger_level = 'medium'
            elif score >= 10:
                info.danger_level = 'low'
            else:
                info.danger_level = 'safe'
    
    def _assign_roles(self) -> None:
        """تحديد دور كل ملف"""
        for info in self.files.values():
            dep_by = len(info.depended_by)
            dep_on = len(info.depends_on)
            
            if dep_by == 0 and dep_on == 0:
                info.role = 'isolated'
                info.is_isolated = True
                info.danger_level = 'unknown'
            elif dep_by >= 10 and info.total_lines > 500:
                info.role = 'god_file'
            elif dep_by >= 5:
                info.role = 'hub'
            elif dep_by >= 2 and dep_on >= 2:
                info.role = 'bridge'
                info.is_bridge = True
            elif dep_by == 0 and dep_on > 0:
                info.role = 'leaf'
            else:
                info.role = 'normal'
    
    def _detect_cycles(self) -> List[List[str]]:
        """كشف الدورات في الاعتماديات"""
        visited = set()
        stack = set()
        cycles = []
        
        def dfs(node: str, path: List[str]) -> None:
            if node in stack:
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            stack.add(node)
            path.append(node)
            
            info = self.files.get(node)
            if info:
                for dep in info.depends_on:
                    dfs(dep, path.copy())
            
            stack.discard(node)
        
        for path in self.files:
            if path not in visited:
                dfs(path, [])
        
        return cycles
    
    def graph_data_fast(self) -> dict:
        """توليد بيانات الرسم البياني"""
        nodes = []
        edges = []
        
        # عقد
        for path, info in self.files.items():
            nodes.append(info.to_dict())
        
        # حواف
        seen_edges = set()
        for path, info in self.files.items():
            for dep in info.depends_on:
                edge_key = f"{path}→{dep}"
                if edge_key not in seen_edges:
                    edges.append({'from': path, 'to': dep})
                    seen_edges.add(edge_key)
        
        return {'nodes': nodes, 'edges': edges}
    
    def summary_fast(self) -> dict:
        """إحصائيات سريعة"""
        danger_dist = defaultdict(int)
        role_dist = defaultdict(int)
        lang_dist = defaultdict(int)
        total_lines = 0
        
        for info in self.files.values():
            danger_dist[info.danger_level] += 1
            role_dist[info.role] += 1
            lang_dist[info.language] += 1
            total_lines += info.total_lines
        
        n = max(len(self.files), 1)
        
        return {
            'total_files': len(self.files),
            'total_lines': total_lines,
            'avg_lines': round(total_lines / n, 1),
            'danger_distribution': dict(danger_dist),
            'role_distribution': dict(role_dist),
            'language_distribution': dict(lang_dist),
            'avg_danger': round(
                sum(f.danger_score for f in self.files.values()) / n, 1
            ),
            'god_files': [
                f.name for f in self.files.values() if f.role == 'god_file'
            ],
            'isolated_files': [
                f.name for f in self.files.values() if f.is_isolated
            ]
        }
    
    def get_top_danger(self, n: int = 5) -> List[dict]:
        """أكثر الملفات خطورة"""
        sorted_files = sorted(
            self.files.values(),
            key=lambda x: x.danger_score,
            reverse=True
        )
        return [
            {
                'name': f.name,
                'path': f.path,
                'score': f.danger_score,
                'role': f.role,
                'lines': f.total_lines
            }
            for f in sorted_files[:n]
        ]
