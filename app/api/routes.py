"""جميع مسارات API"""
import os
import uuid
import shutil
import subprocess
import threading
import re
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import (
    TEMPLATES_DIR, STATIC_DIR, UPLOADS_DIR,
    SUPPORTED_EXTENSIONS, ALLOWED_PATHS
)
from app.core.scanner import FastScanner
from app.core.analyzer import FastAnalyzer
from app.services.storage import Storage
from app.services.github import GitHubFast
from app.services.ai_analyzer import AIAnalyzer

router = APIRouter()
storage = Storage()
ai_analyzer = AIAnalyzer()
github_fast = GitHubFast()

UPLOADS_DIR.mkdir(exist_ok=True)

# ============ صفحات HTML ============

def _load_html(name: str) -> str:
    with open(TEMPLATES_DIR / name, 'r', encoding='utf-8') as f:
        return f.read()

@router.get("/", response_class=HTMLResponse)
async def home():
    return _load_html('home.html')

@router.get("/logo", response_class=HTMLResponse)
async def logo():
    with open(TEMPLATES_DIR / "logo.html", "r", encoding="utf-8") as f:
        return f.read()

@router.get("/map/{sid}", response_class=HTMLResponse)
async def view_map(sid: str):
    return _load_html('map.html').replace('__SID__', sid)

# ============ API تحليل ============

def _analyze_project(sid: str, path: str, name: str, lang: str = "ar") -> None:
    """تحليل مشروع كامل في الخلفية"""
    try:
        scanner = FastScanner(path)
        files = scanner.scan_parallel()
        analyzer = FastAnalyzer(files)

        # تحليل ذكي للملفات المهمة
        ai_results = {}
        for file_path, info in files.items():
            if False:  # AI عند الطلب فقط
                try:
                    with open(Path(path) / file_path, 'r') as f:
                        content = f.read()[:4000]
                    result = ai_analyzer.analyze_file(file_path, content, info.language)
    
                    ai_results[file_path] = {
                        'summary': result.summary,
                        'score': result.quality_score,
                        'security': result.security_issues,
                        'suggestions': result.suggestions,
                        'architecture': result.architecture_note
                    }
                except:
                    pass

        result = {
            'project_path': path,
            'session_id': sid,
            'project_name': name,
            'graph': analyzer.graph_data_fast(),
            'summary': analyzer.summary_fast(),
            'total_files': len(files),
            'ai_analysis': ai_results
        }

        # وصف عام للمشروع
        overview = ai_analyzer.analyze_project(result['summary'])
        result['project_overview'] = overview

        storage.save(sid, result)
    except Exception as e:
        storage.save(sid, {'session_id': sid, 'error': str(e)})

@router.post("/api/upload")
async def api_upload(files: List[UploadFile] = File(...)):
    sid = str(uuid.uuid4())[:8]
    d = UPLOADS_DIR / sid
    d.mkdir(parents=True, exist_ok=True)

    for f in files:
        if f.filename:
            content = await f.read()
            p = d / f.filename
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, 'wb') as fh:
                fh.write(content)

    threading.Thread(
        target=_analyze_project,
        args=(sid, str(d), "uploaded"),
        daemon=True
    ).start()
    return {"session_id": sid}

@router.post("/api/analyze-path")
async def api_path(path: str = Form(...)):
    real = os.path.realpath(path)
    if not os.path.exists(real):
        raise HTTPException(400, detail="المسار غير موجود")
    if not any(real.startswith(r) for r in ALLOWED_PATHS):
        raise HTTPException(403, detail="المسار غير مسموح به")

    sid = str(uuid.uuid4())[:8]
    threading.Thread(
        target=_analyze_project,
        args=(sid, real, os.path.basename(real.rstrip('/\\'))),
        daemon=True
    ).start()
    return {"session_id": sid}

@router.post("/api/analyze-github")
async def api_github(repo_url: str = Form(...), token: str = Form("")):
    """تحليل GitHub سريع"""
    sid = str(uuid.uuid4())[:8]
    
    repo_path = UPLOADS_DIR / sid

    def proc():
        try:
            result = github_fast.analyze_repo(repo_url, sid, token)
            if result.get("error"):
                storage.save(sid, {"session_id": sid,
            "project_path": str(repo_path), "error": result["error"]})
                return
            
            # repo_path = UPLOADS_DIR / sid
            scanner = FastScanner(str(repo_path))
            files = scanner.scan_parallel()
            analyzer = FastAnalyzer(files)
            
            # تحليل ذكي للملفات الخطرة
            ai_results = {}
            all_files = [f for f in files.values() if f.role != 'isolated' and f.language == 'python']
            for f in all_files[:5]:
                try:
                    with open(repo_path / f["path"], "r") as fp:
                        code = fp.read()[:4000]
                    r = ai_analyzer.analyze_file(f["path"], code, "python")
                    if r.summary:
                        ai_results[f["path"]] = {
                            "summary": r.summary,
                            "score": r.quality_score,
                            "security": r.security_issues,
                            "suggestions": r.suggestions,
                            "architecture": r.architecture_note
                        }
                except:
                    pass
            
            data = {
                "session_id": sid,
            "project_path": str(repo_path),
                "project_name": repo_url.rstrip("/").split("/")[-1].replace(".git", ""),
                "graph": analyzer.graph_data_fast(),
                "summary": analyzer.summary_fast(),
                "total_files": len(files),
                "clone_time": result.get("time", 0),
                "ai_analysis": ai_results
            }
            
            storage.save(sid, data)
            # shutil.rmtree(repo_path, ignore_errors=True)
        except Exception as e:
            storage.save(sid, {"session_id": sid,
            "project_path": str(repo_path), "error": str(e)})
    
    threading.Thread(target=proc, daemon=True).start()
    return {"session_id": sid,
            "project_path": str(repo_path), "status": "cloning"}

@router.get("/api/session/{sid}")
async def api_session(sid: str):
    data = storage.get(sid)
    if not data:
        raise HTTPException(404, detail="الجلسة غير موجودة")
    return data

@router.get("/api/progress/{sid}")
async def api_progress(sid: str):
    data = storage.get(sid)
    if data:
        if data.get('error'):
            return {"stage": "error", "message": data['error']}
        return {"stage": "done", "percent": 100}
    return {"stage": "processing", "percent": 50}

@router.get("/api/health")
async def health():
    return {"status": "ok", "version": "9.0.0"}

# ============ تحليل AI لملف واحد (منقول من v8) ============
@router.post("/api/ai-analyze/{sid}/{path:path}")


async def ai_analyze_file(sid: str, path: str, request: Request, lang: str = "ar"):
    data = storage.get(sid)
    if not data:
        return JSONResponse({"error": "الجلسة غير موجودة"}, status_code=404)

    content = ""
    pp = data.get('project_path', '')
    fp = os.path.join(pp, path) if pp else ""
    if os.path.exists(fp):
        try:
            with open(fp, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()[:5000]
        except:
            pass

    if not content:
        return JSONResponse({"error": "لا يوجد محتوى"}, status_code=400)

    ext = os.path.splitext(path)[1].lower()
    prog_lang = {'.py': 'python', '.js': 'javascript', '.ts': 'typescript'}.get(ext, 'unknown')
    result = ai_analyzer.analyze_file(path, content, prog_lang)
    summary = str(getattr(result, 'summary', ''))[:500]
    security = getattr(result, 'security_issues', [])
    suggestions = getattr(result, 'suggestions', [])

    query_lang = request.query_params.get("lang", lang)
    if query_lang == "en":
        summary = _translate_text(summary, "English")
        security = [_translate_text(s, "English") for s in security]
        suggestions = [_translate_text(s, "English") for s in suggestions]

    return JSONResponse({
        'summary': summary,
        'score': getattr(result, 'quality_score', 0),
        'security': security,
        'suggestions': suggestions,
    })
def _translate_text(text: str, target_lang: str) -> str:
    import urllib.request, json, base64
    try:
        keys = ["c2stb3ItdjEtZjM5ZTUzNWZkZDAzYzhjZmRkNmUxN2VjNzFiODM3N2M4YjM1NDU4NjRmNTc0N2EwODI5Mjg0Mzg4MmQ4ZDBiOA=="]
        key = base64.b64decode(keys[0]).decode()
        prompt = f"Translate this to {target_lang}. Return ONLY the translation: {text[:2000]}"
        data = json.dumps({"model": "google/gemini-2.0-flash-001", "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=data, headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}", "HTTP-Referer": "http://localhost:8000"})
        r = urllib.request.urlopen(req, timeout=10)
        resp = json.loads(r.read())
        return resp["choices"][0]["message"]["content"]
    except:
        return text
