"""D-Map - نقطة الدخول الرئيسية"""
import sys, os, threading, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import STATIC_DIR
from app.api.routes import router
from app.services.storage import Storage

app = FastAPI(title="D-Map", version="9.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(router)

# ============ تنظيف تلقائي للجلسات ============
storage = Storage()

def auto_cleanup():
    """تنظيف الجلسات منتهية الصلاحية كل 30 دقيقة"""
    while True:
        time.sleep(1800)  # 30 دقيقة
        try:
            deleted = storage.cleanup()
            if deleted > 0:
                print(f"🧹 تنظيف تلقائي: حذف {deleted} جلسة منتهية")
        except Exception as e:
            print(f"⚠️ خطأ في التنظيف: {e}")

# تنظيف فوري عند بدء التشغيل
deleted = storage.cleanup()
if deleted > 0:
    print(f"🧹 تنظيف أولي: حذف {deleted} جلسة قديمة")

# بدء خيط التنظيف الدوري
threading.Thread(target=auto_cleanup, daemon=True).start()

if __name__ == "__main__":
    print("🧭 D-Map → http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
