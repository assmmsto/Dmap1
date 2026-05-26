"""CGPS v8 - محسن الأداء"""
import os, sys, uuid, json, shutil, subprocess, threading, time, ast, re, sqlite3, pickle, zlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

# ============ نماذج ============
SUPPORTED_EXT = {'.py':'python','.js':'javascript','.ts':'typescript','.html':'html','.css':'css','.json':'json','.md':'markdown','.java':'java','.go':'go','.rs':'rust','.cpp':'cpp','.txt':'text'}
LANG_ICONS = {'python':'🐍','javascript':'💛','typescript':'💙','html':'🟠','css':'🎨','json':'📋','markdown':'📝','java':'☕','go':'🔵','rust':'🦀','cpp':'⚙️','text':'📄','unknown':'📄'}
DANGER_COLORS = {'critical':'#8B0000','high':'#DC143C','medium':'#FF8C00','low':'#FFD700','safe':'#228B22','unknown':'#808080'}
IGNORE = ['node_modules','.git','__pycache__','venv','.venv','dist','build','.next','coverage','.pytest_cache']

@dataclass
class FileInfo:
    path:str;name:str;language:str='unknown';total_lines:int=0;code_lines:int=0;complexity:int=0
    functions:list=field(default_factory=list);classes:list=field(default_factory=list)
    imports_internal:set=field(default_factory=set);imports_external:set=field(default_factory=set)
    danger_level:str='unknown';danger_score:float=0;role:str='normal'
    is_isolated:bool=False;is_bridge:bool=False
    depended_by:list=field(default_factory=list);depends_on:list=field(default_factory=list)
    def to_dict(self):
        return {'id':self.path,'name':self.name,'label':f'{LANG_ICONS.get(self.language,"📄")} {self.name}','language':self.language,'icon':LANG_ICONS.get(self.language,'📄'),'lines':self.total_lines,'complexity':self.complexity,'functions':len(self.functions),'classes':len(self.classes),'danger_level':self.danger_level,'danger_score':round(self.danger_score,1),'role':self.role,'is_isolated':self.is_isolated,'is_bridge':self.is_bridge,'color':DANGER_COLORS.get(self.danger_level,'#808080'),'external_deps':list(self.imports_external),'depended_by':self.depended_by,'depends_on':self.depends_on}

# ============ ماسح سريع ============
class Scanner:
    def __init__(self, path):
        self.path=path;self.files={};self.packages=set()
    def scan(self):
        all_files=[]
        for root,dirs,files in os.walk(self.path):
            dirs[:]=[d for d in dirs if not any(p in d for p in IGNORE)]
            for f in files:
                if os.path.splitext(f)[1].lower() in SUPPORTED_EXT:
                    all_files.append(os.path.join(root,f))
        for fp in all_files:
            rel=os.path.relpath(fp,self.path)
            for part in os.path.dirname(rel).split(os.sep):
                if part:self.packages.add(part)
            self.packages.add(os.path.splitext(os.path.basename(rel))[0])
        for fp in all_files:
            try:
                info=self._scan(fp,os.path.relpath(fp,self.path))
                if info:self.files[info.path]=info
            except:pass
        return self.files
    def _scan(self,fp,rel):
        ext=os.path.splitext(fp)[1].lower();lang=SUPPORTED_EXT.get(ext,'unknown')
        with open(fp,'r',encoding='utf-8',errors='replace') as f:content=f.read()
        lines=content.split('\n');total=len(lines)
        code=sum(1 for l in lines if l.strip() and not l.strip().startswith(('#','//','/*','*')))
        info=FileInfo(path=rel,name=os.path.basename(fp),language=lang,total_lines=total,code_lines=code)
        if lang=='python':self._py(content,info)
        elif lang in('javascript','typescript'):self._js(content,info)
        return info
    def _py(self,content,info):
        try:
            tree=ast.parse(content)
            for n in ast.walk(tree):
                if isinstance(n,ast.Import):
                    for a in n.names:info.imports_external.add(a.name.split('.')[0])
                elif isinstance(n,ast.ImportFrom):
                    if n.module:
                        if n.level>0:info.imports_internal.add(n.module)
                        else:info.imports_external.add(n.module.split('.')[0])
                elif isinstance(n,ast.FunctionDef):info.functions.append(n.name)
                elif isinstance(n,ast.ClassDef):info.classes.append(n.name)
            info.complexity=sum(1+sum(1 for _ in ast.walk(n) if isinstance(_,(ast.If,ast.For,ast.While))) for n in ast.walk(tree) if isinstance(n,ast.FunctionDef))
        except:pass
    def _js(self,content,info):
        for m in re.finditer(r'''import\s+.*?from\s+['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\s*\)''',content):
            src=m.group(1)or m.group(2)
            if src:
                if src.startswith('.'):info.imports_internal.add(src)
                else:info.imports_external.add(src.split('/')[0])
        for m in re.finditer(r'(?:function\s+(\w+)|(\w+)\s*=\s*(?:async\s*)?\(|(\w+)\s*:\s*function)',content):
            name=m.group(1)or m.group(2)or m.group(3)
            if name and name not in('if','for','while','switch','catch','return'):info.functions.append(name)
        for m in re.finditer(r'class\s+(\w+)',content):info.classes.append(m.group(1))

# ============ محلل ============
class Analyzer:
    def __init__(self,files):
        self.files=files
        self._build();self._danger();self._roles()
    def _build(self):
        idx={}
        for p in self.files:
            idx[os.path.splitext(os.path.basename(p))[0]]=p
        for p,info in self.files.items():
            for dep in info.imports_internal:
                r=self._res(dep,p,idx)
                if r and r in self.files and r!=p:
                    info.depends_on.append(r);self.files[r].depended_by.append(p)
            for ext in list(info.imports_external):
                r=idx.get(ext)
                if r and r in self.files and r!=p:
                    info.imports_external.discard(ext);info.depends_on.append(r);self.files[r].depended_by.append(p)
    def _res(self,dep,cur,idx):
        if dep in self.files:return dep
        if dep+'.py' in self.files:return dep+'.py'
        n=dep.replace('.',os.sep)+'.py'
        if n in self.files:return n
        return idx.get(dep.split('.')[-1])
    def _danger(self):
        mi=max((len(f.depended_by)for f in self.files.values()),default=1)
        mo=max((len(f.depends_on)for f in self.files.values()),default=1)
        ml=max((f.total_lines for f in self.files.values()),default=1)
        mc=max((f.complexity for f in self.files.values()),default=1)
        for info in self.files.values():
            s=0
            if mi:s+=(len(info.depended_by)/mi)*40
            if mo:s+=(len(info.depends_on)/mo)*20
            if ml:s+=(info.total_lines/ml)*20
            if mc:s+=(info.complexity/mc)*20
            info.danger_score=min(s,100)
            if info.danger_score>=70:info.danger_level='critical'
            elif info.danger_score>=50:info.danger_level='high'
            elif info.danger_score>=30:info.danger_level='medium'
            elif info.danger_score>=10:info.danger_level='low'
            else:info.danger_level='safe'
    def _roles(self):
        for info in self.files.values():
            if not info.depended_by and not info.depends_on:info.role='isolated';info.is_isolated=True;info.danger_level='unknown'
            elif len(info.depended_by)>=10 and info.total_lines>500:info.role='god_file'
            elif len(info.depended_by)>=5:info.role='hub'
            elif len(info.depended_by)>=2 and len(info.depends_on)>=2:info.role='bridge';info.is_bridge=True
            elif not info.depended_by and info.depends_on:info.role='leaf'
    def graph_data(self):
        return {'nodes':[i.to_dict() for i in self.files.values()],'edges':[{'from':p,'to':d}for p,i in self.files.items()for d in i.depends_on]}
    def summary(self):
        dd=defaultdict(int);rd=defaultdict(int)
        for i in self.files.values():dd[i.danger_level]+=1;rd[i.role]+=1
        return {'total_files':len(self.files),'total_lines':sum(i.total_lines for i in self.files.values()),'danger_distribution':dict(dd),'role_distribution':dict(rd),'avg_danger':round(sum(i.danger_score for i in self.files.values())/max(len(self.files),1),1)}

# ============ تخزين SQLite سريع ============
BASE=Path(__file__).parent
DB_PATH=BASE/"cgps.db"

def get_db():
    conn=sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA cache_size=10000")
    conn.execute('''CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, data BLOB, created REAL)''')
    return conn

def save_sess(sid,data):
    compressed=zlib.compress(pickle.dumps(data))
    conn=get_db()
    conn.execute('INSERT OR REPLACE INTO sessions VALUES (?,?,?)',(sid,compressed,time.time()))
    conn.commit();conn.close()

def get_sess(sid):
    conn=get_db()
    row=conn.execute('SELECT data,created FROM sessions WHERE id=?',(sid,)).fetchone()
    conn.close()
    if row:
        data,created=row
        if time.time()-created<86400:
            return pickle.loads(zlib.decompress(data))
    return None

# ============ تحليل ============
def analyze(sid,path,name):
    try:
        s=Scanner(path);files=s.scan()
        a=Analyzer(files)
        save_sess(sid,{'session_id':sid,'project_name':name,'graph':a.graph_data(),'summary':a.summary(),'total_files':len(files)})
    except Exception as e:print(f"Error:{e}")

def load_html(n):
    with open(BASE/'templates'/n,'r',encoding='utf-8')as f:return f.read()

# ============ FastAPI ============
app=FastAPI(title="CGPS v8")
UPLOADS=BASE/"uploads";UPLOADS.mkdir(exist_ok=True)

@app.get("/logo",response_class=HTMLResponse)
async def logo():
    with open(BASE/"logo.html","r",encoding="utf-8") as f:
        return f.read()

@app.get("/",response_class=HTMLResponse)
async def home():return load_html('home.html')

@app.get("/map/{sid}",response_class=HTMLResponse)
async def vmap(sid:str):return load_html('map.html').replace('__SID__',sid)

@app.post("/api/upload")
async def api_upload(files:List[UploadFile]=File(...)):
    sid=str(uuid.uuid4())[:8];d=UPLOADS/sid;d.mkdir(parents=True,exist_ok=True)
    for f in files:
        if f.filename:
            content=await f.read();p=d/f.filename;p.parent.mkdir(parents=True,exist_ok=True)
            with open(p,'wb')as fh:fh.write(content)
    threading.Thread(target=analyze,args=(sid,str(d),"uploaded"),daemon=True).start()
    return {"session_id":sid}

@app.post("/api/analyze-path")
async def api_path(path:str=Form(...)):
    if not os.path.exists(path):raise HTTPException(400,detail="المسار غير موجود")
    sid=str(uuid.uuid4())[:8]
    threading.Thread(target=analyze,args=(sid,path,os.path.basename(path.rstrip('/\\'))),daemon=True).start()
    return {"session_id":sid}

@app.post("/api/analyze-github")
async def api_github(repo_url:str=Form(...),token:str=Form("")):
    sid=str(uuid.uuid4())[:8]
    def proc():
        try:
            url=repo_url.strip()
            if not url.startswith("http"):url="https://github.com/"+url
            if not url.endswith(".git"):url+=".git"
            
            # إعطاء session_id فوراً، والتحليل في الخلفية
            # استخدام timeout أقصر مع retry
            for attempt in range(2):
                try:
                    r=subprocess.run(
                        ["git","clone","--depth","1","--single-branch","--quiet",url,str(UPLOADS/sid)],
                        capture_output=True,text=True,timeout=60
                    )
                    if r.returncode==0:
                        analyze(sid,str(UPLOADS/sid),repo_url.rstrip('/').split('/')[-1].replace('.git',''))
                        break
                except subprocess.TimeoutExpired:
                    if attempt==0:continue
            shutil.rmtree(UPLOADS/sid,ignore_errors=True)
        except:pass
    threading.Thread(target=proc,daemon=True).start()
    return {"session_id":sid,"status":"cloning"}

@app.get("/api/session/{sid}")
async def api_session(sid:str):
    d=get_sess(sid)
    if not d:raise HTTPException(404,detail="غير موجودة")
    return d

# متغير لتتبع حالة git clone
_clone_status:Dict[str,str]={}

@app.get("/api/progress/{sid}")
async def api_progress(sid:str):
    if get_sess(sid):return {"stage":"done","percent":100}
    if sid in _clone_status:return {"stage":"cloning","percent":30,"message":"جاري استنساخ المستودع..."}
    return {"stage":"processing","percent":50,"message":"جاري تحليل الملفات..."}


@app.get("/api/health")
async def health():
    return {"status":"ok"}


@app.get("/api/health")
async def health():
    return {"status":"ok"}

if __name__=="__main__":
    print("🧭 CGPS v8 → http://localhost:8000")
    uvicorn.run(app,host="0.0.0.0",port=8000,log_level="warning")
