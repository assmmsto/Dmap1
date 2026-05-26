"""اختبارات وحدة حقيقية لـ CGPS"""
import sys, os, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestScanner:
    
    def test_scan_python(self):
        from main import Scanner
        code = "import os\nfrom sys import path\n\ndef hello():\n    if True:\n        return 1\n\nclass MyClass:\n    def method(self):\n        pass\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            tmp = f.name
        s = Scanner(os.path.dirname(tmp))
        info = s._scan(tmp, os.path.basename(tmp))
        os.unlink(tmp)
        
        assert info is not None
        assert info.language == 'python'
        assert 'hello' in info.functions
        assert 'MyClass' in info.classes
        print("  ✅ test_scan_python")
    
    def test_scan_js(self):
        from main import Scanner
        code = "import React from 'react';\nfunction App() {}\nclass Comp {}"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            tmp = f.name
        s = Scanner(os.path.dirname(tmp))
        info = s._scan(tmp, os.path.basename(tmp))
        os.unlink(tmp)
        
        assert info is not None
        assert info.language == 'javascript'
        print("  ✅ test_scan_js")

class TestAnalyzer:
    
    def test_danger(self):
        from main import FileInfo, Analyzer
        
        files = {}
        main = FileInfo(path='main.py', name='main.py', language='python', total_lines=500, complexity=50)
        main.depended_by = ['a.py','b.py','c.py','d.py','e.py']
        files['main.py'] = main
        
        iso = FileInfo(path='iso.py', name='iso.py', language='python', total_lines=10, complexity=0)
        files['iso.py'] = iso
        
        a = Analyzer(files)
        assert iso.is_isolated
        assert main.danger_score > 0
        print(f"  ✅ test_danger (main={main.danger_score:.0f}, iso_isolated={iso.is_isolated})")
    
    def test_graph(self):
        from main import FileInfo, Analyzer
        
        a_py = FileInfo(path='a.py', name='a.py', language='python', total_lines=10, complexity=1)
        b_py = FileInfo(path='b.py', name='b.py', language='python', total_lines=10, complexity=1)
        a_py.imports_external = {'b'}
        
        a = Analyzer({'a.py': a_py, 'b.py': b_py})
        gd = a.graph_data()
        assert len(gd['nodes']) == 2
        print(f"  ✅ test_graph ({len(gd['nodes'])}n, {len(gd['edges'])}e)")

class TestStorage:
    
    def test_save_get(self):
        from main import save_sess, get_sess
        sid = 'tu' + str(int(time.time()))
        save_sess(sid, {'ok': True})
        assert get_sess(sid) is not None
        print("  ✅ test_save_get")

class TestFileInfo:
    
    def test_dict(self):
        from main import FileInfo
        info = FileInfo(path='x.py', name='x.py', language='python', total_lines=100, complexity=5)
        info.danger_level = 'high'
        info.functions = ['f1']
        d = info.to_dict()
        assert '🐍' in d['label']
        print("  ✅ test_dict")

if __name__ == '__main__':
    print("=== اختبارات الوحدة ===\n")
    passed = failed = 0
    for cls_name in ['TestScanner', 'TestAnalyzer', 'TestStorage', 'TestFileInfo']:
        obj = globals()[cls_name]()
        for m in dir(obj):
            if m.startswith('test_'):
                try:
                    getattr(obj, m)()
                    passed += 1
                except Exception as e:
                    failed += 1
                    print(f"  ❌ {m}: {e}")
    print(f"\n✅ {passed} | ❌ {failed}")
