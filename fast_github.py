"""Fast GitHub Analyzer - 10 seconds or less"""
import requests, zipfile, io, os, re, uuid, threading, time
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
import uvicorn

MAX_FILES = 100
READ_SIZE = 50000

app = FastAPI()

def fast_analyze(repo_url, token=""):
    start = time.time()
    
    # Parse URL
    repo_url = repo_url.replace('https://github.com/', '').replace('.git', '')
    parts = repo_url.split('/')
    if len(parts) < 2:
        return {'error': 'Invalid repo URL'}
    owner, repo = parts[0], parts[1]
    
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if token:
        headers['Authorization'] = f'token {token}'
    
    # Download ZIP
    try:
        resp = requests.get(
            f'https://api.github.com/repos/{owner}/{repo}/zipball',
            headers=headers, timeout=10
        )
        if resp.status_code != 200:
            return {'error': f'GitHub returned {resp.status_code}'}
    except Exception as e:
        return {'error': f'Download failed: {str(e)[:100]}'}
    
    # Extract and scan
    try:
        z = zipfile.ZipFile(io.BytesIO(resp.content))
    except:
        return {'error': 'Invalid ZIP file'}
    
    files = []
    scanned = 0
    
    for f in z.filelist:
        if scanned >= MAX_FILES:
            break
        if not f.filename.endswith(('.py', '.js', '.ts', '.tsx', '.jsx')):
            continue
        
        try:
            content = z.read(f.filename).decode('utf-8', errors='replace')[:READ_SIZE]
        except:
            continue
        
        files.append({
            'name': os.path.basename(f.filename),
            'path': f.filename.split('/', 1)[-1] if '/' in f.filename else f.filename,
            'lines': content.count('\n') + 1,
            'functions': len(re.findall(r'def\s+\w+|function\s+\w+|\w+\s*=\s*\(', content)),
            'classes': len(re.findall(r'class\s+\w+', content)),
            'imports': len(re.findall(r'import\s+\w+|from\s+\w+\s+import|require\s*\(', content))
        })
        scanned += 1
    
    return {
        'repo': f'{owner}/{repo}',
        'total_files': len(files),
        'time': round(time.time() - start, 1),
        'files': files[:10],  # First 10 only in response
        'sample_count': min(len(files), 10)
    }

@app.post("/fast")
async def fast(repo_url: str = Form(...), token: str = Form("")):
    return fast_analyze(repo_url, token)

@app.get("/")
async def home():
    return {"status": "ok", "usage": "POST /fast with repo_url"}

if __name__ == "__main__":
    print("⚡ Fast GitHub Analyzer → http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="warning")
