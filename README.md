<p align="center">
  <img src="https://raw.githubusercontent.com/assmmsto/CGPS/main/assets/logo.png" alt="CGPS Logo" width="200">
</p>

<h1 align="center">🧭 CGPS - Code GPS</h1>
<p align="center"><strong>خريطة ذهنية لمشروعك البرمجي في 30 ثانية</strong></p>

<p align="center">
  <a href="https://cgps-uim1.onrender.com"><img src="https://img.shields.io/badge/🚀_Live_Demo-Click_Here-blue?style=for-the-badge" alt="Live Demo"></a>
  <a href="https://github.com/assmmsto/CGPS/stargazers"><img src="https://img.shields.io/github/stars/assmmsto/CGPS?style=for-the-badge&color=yellow" alt="Stars"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python" alt="Python"></a>
</p>

---

## 📖 What is CGPS?

CGPS is a **visual code analysis tool** that transforms your project into an **interactive dependency map**. Upload any Python, JavaScript, or TypeScript project and instantly see:

- 🔴 **Dangerous files** (many files depend on them)
- ⚪ **Isolated files** (no dependencies)
- 📏 **File sizes** (bigger circle = bigger file)
- 🧮 **Complexity metrics** (cyclomatic complexity)
- 🔗 **Dependency graphs** (who depends on who)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📤 **Upload Files** | Drag & drop or select multiple files |
| 📂 **Local Path** | Analyze any folder on your server |
| 🐙 **GitHub Integration** | Clone & analyze any public/private repo |
| 🗺️ **3 Map Layouts** | Force (Cose), Constellation, Concentric |
| 🎨 **Color Coding** | Green→Red based on danger level |
| 📊 **Dashboard** | Stats, danger distribution, file list |
| 🌐 **Bilingual** | Arabic / English |
| 💾 **24h Storage** | Results saved for 24 hours |
| ⚡ **Fast** | GitHub ZIP API (10x faster than git clone) |
| 🏝️ **Isolated Zone** | Separate area for orphan files |

---

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/assmmsto/CGPS.git
cd CGPS

# Install
pip install -r requirements.txt

# Run
python3 main.py
# Open http://localhost:8000
```

---

🐳 Docker

```bash
docker build -t cgps .
docker run -p 8000:8000 cgps
```

Or use docker-compose.yml:

```bash
docker-compose up
```

---

🗺️ Map Types

Layout Description Best For
🕸️ Cose Force-directed (default) Overview
🌌 Constellation Wide spread Large projects
🌐 Concentric By danger level Risk detection

---

🎨 Danger Colors

Color Level Meaning
⚫ Critical 20+ files depend on it
🔴 High 50+ danger score
🟠 Medium 30+ danger score
🟡 Low 10+ danger score
🟢 Safe <10 danger score
⚪ Isolated No dependencies

---

🏗️ Architecture

```
User Input (Upload/Path/GitHub)
        ↓
   Scanner (AST + Regex)
        ↓
   Analyzer (Relations + Danger)
        ↓
   SQLite (24h cache)
        ↓
   Cytoscape.js (Map)
```

---

🛠️ Tech Stack

Layer Technology
Backend Python 3.11 + FastAPI + Uvicorn
Frontend HTML5 + CSS3 + Vanilla JS
Map Cytoscape.js v3.26
Storage SQLite + WAL + zlib
Analysis Python AST + Regex
Deployment Docker + Render

---

📊 Screenshots

<p align="center">
  <img src="https://raw.githubusercontent.com/assmmsto/CGPS/main/assets/screenshot1.png" alt="Dashboard" width="400">
  <img src="https://raw.githubusercontent.com/assmmsto/CGPS/main/assets/screenshot2.png" alt="Map" width="400">
</p>

---

🔥 Why CGPS?

 CGPS SonarQube CodeClimate CodeScene
Price 🆓 Free 💰 Paid 💰 Paid 💰 Paid
Speed ⚡ 30s 🐌 5min 🐌 3min 🐌 2min
Visual Map ✅ ❌ ❌ ✅
GitHub API ✅ ZIP ❌ ❌ ❌
Arabic ✅ ❌ ❌ ❌
Self-Hosted ✅ ✅ ❌ ❌

---

📈 Roadmap

· GitHub ZIP API
· 3 Map Layouts
· Bilingual (AR/EN)
· AI Code Analysis (Gemini)
· Git History Analysis
· PDF Reports
· VS Code Extension
· Team Collaboration
· API Access
· PWA Mobile App

---

🤝 Contributing

Contributions are welcome! See CONTRIBUTING.md

1. Fork the repo
2. Create your feature branch (git checkout -b feature/amazing)
3. Commit your changes (git commit -m 'Add amazing feature')
4. Push to the branch (git push origin feature/amazing)
5. Open a Pull Request

---

⭐ Support

Give a ⭐️ if this project helped you!

https://img.shields.io/github/stars/assmmsto/CGPS?style=social

---

📄 License

MIT © CGPS

---

<p align="center">
  <strong>Made with ❤️ by <a href="https://github.com/assmmsto">assmmsto</a></strong>
</p>
