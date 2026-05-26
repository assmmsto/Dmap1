"""اختبار تكامل حقيقي - يتطلب خادم شغال"""
import sys, os, json, time, urllib.request, urllib.error, urllib.parse

BASE = 'http://127.0.0.1:8000'

def wait_for_server(timeout=10):
    for i in range(timeout):
        try:
            urllib.request.urlopen(f'{BASE}/', timeout=2)
            return True
        except:
            time.sleep(1)
    return False

def test_homepage():
    r = urllib.request.urlopen(f'{BASE}/')
    assert r.status == 200
    html = r.read().decode()
    assert 'CGPS' in html
    print("  ✅ test_homepage")

def test_health():
    r = urllib.request.urlopen(f'{BASE}/api/health')
    assert r.status == 200
    print("  ✅ test_health")

def test_analyze_path():
    project = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data = urllib.parse.urlencode({'path': project, 'language': 'ar'}).encode()
    r = urllib.request.urlopen(f'{BASE}/api/analyze-path', data=data)
    assert r.status == 200
    result = json.loads(r.read())
    assert 'session_id' in result
    sid = result['session_id']
    
    # انتظار التحليل
    for i in range(30):
        time.sleep(1)
        r = urllib.request.urlopen(f'{BASE}/api/progress/{sid}')
        p = json.loads(r.read())
        if p.get('stage') == 'done':
            break
    
    r = urllib.request.urlopen(f'{BASE}/api/session/{sid}')
    assert r.status == 200
    data = json.loads(r.read())
    assert 'graph' in data
    assert len(data['graph']['nodes']) > 0
    print(f"  ✅ test_analyze_path ({len(data['graph']['nodes'])} nodes)")

def test_map_page():
    r = urllib.request.urlopen(f'{BASE}/map/test123')
    assert r.status == 200
    html = r.read().decode()
    assert 'cytoscape' in html.lower()
    print("  ✅ test_map_page")

def test_404():
    try:
        urllib.request.urlopen(f'{BASE}/api/session/nonexistent')
        assert False
    except urllib.error.HTTPError as e:
        assert e.code == 404
    print("  ✅ test_404")

def test_static_files():
    for f in ['/static/style.css', '/static/app.js', '/static/map.js']:
        try:
            r = urllib.request.urlopen(f'{BASE}{f}')
            assert r.status == 200
        except:
            pass
    print("  ✅ test_static_files")

if __name__ == '__main__':
    print("=== اختبارات التكامل ===\n")
    
    if not wait_for_server():
        print("❌ الخادم غير متاح - شغل python3 main.py أولاً")
        sys.exit(1)
    
    passed = 0
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            try:
                fn()
                passed += 1
            except Exception as e:
                failed += 1
                print(f"  ❌ {name}: {e}")
    
    print(f"\n✅ {passed} نجاح | ❌ {failed} فشل")
