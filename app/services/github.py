"""
خدمة GitHub - git clone مباشر (أبسط وأسرع لاتصال ضعيف)
"""
import os, subprocess, shutil, time
from pathlib import Path
from app.config import UPLOADS_DIR


class GitHubFast:
    def analyze_repo(self, repo_url: str, sid: str, token: str = "") -> dict:
        # تأكد من أن الرابط كامل
        if not repo_url.startswith("http"):
            repo_url = "https://github.com/" + repo_url
        if not repo_url.endswith(".git"):
            repo_url += ".git"
        
        repo_dir = UPLOADS_DIR / sid
        
        # تنظيف
        if repo_dir.exists():
            shutil.rmtree(repo_dir, ignore_errors=True)
        
        try:
            start = time.time()
            
            cmd = [
                "git", "clone",
                "--depth", "1",
                "--single-branch",
                "--quiet",
                repo_url, str(repo_dir)
            ]
            
            # إضافة token إذا وجد
            env = os.environ.copy()
            if token:
                cmd.insert(1, f"https://{token}@")
                # الطريقة الصحيحة: تعديل الرابط
                if repo_url.startswith("https://"):
                    auth_url = repo_url.replace("https://", f"https://{token}@")
                    cmd[cmd.index(repo_url)] = auth_url
            
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            clone_time = time.time() - start
            
            if r.returncode != 0:
                return {"error": r.stderr[:200], "time": round(clone_time, 1)}
            
            # عد الملفات البرمجية
            code_exts = {'.py', '.js', '.ts', '.html', '.css', '.json', 
                        '.md', '.java', '.go', '.rs', '.cpp'}
            count = 0
            for root, dirs, files in os.walk(str(repo_dir)):
                dirs[:] = [d for d in dirs if d != '.git']
                for f in files:
                    if os.path.splitext(f)[1].lower() in code_exts:
                        count += 1
            
            return {
                "total": count,
                "time": round(clone_time, 1)
            }
            
        except subprocess.TimeoutExpired:
            return {"error": "الاستنساخ بطيء - جرب مستودع أصغر"}
        except Exception as e:
            return {"error": str(e)}


github = GitHubFast()
