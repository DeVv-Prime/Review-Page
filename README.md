# Review-Page
# ☁️ DeVv-Prime Review  Studio

<div align="center">

![VectoCloud Banner](https://images.unsplash.com/photo-1557682250-33bd709cbe85?q=80&w=2029&auto=format&h=200&fit=crop)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688?logo=fastapi&style=flat-square)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&style=flat-square)](https://python.org)
[![Render](https://img.shields.io/badge/Render-Deploy-46E3B7?logo=render&style=flat-square)](https://render.com)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

**A modern, animated review management system with real-time admin panel and dynamic UI customization.**

</div>

---

## ✨ Features

### 🎨 Dynamic UI Customization (Admin Panel)
- **Live Background Animation** – Set any image/video URL as animated background
- **Custom Gradient Overlays** – Full control over start, mid, and end gradient colors
- **Neon Glow Effect** – Toggle modern glassmorphism neon borders
- **Particle Animation** – Adjust intensity (Light / Medium / Intense) for floating particles

### ⭐ Review System
- Submit reviews with username, rating (1-5★), title, and detailed comment
- Real-time star rating selector with hover effects
- Automatic timestamps and review IDs
- Delete reviews (admin feature)

### 📊 Analytics Dashboard
- Total reviews count
- Average rating calculation
- Verified reviews counter
- Rating distribution bar chart (Chart.js)
- 5-star breakdown visualization

### 🚀 Performance & Design
- Glassmorphism UI with backdrop blur
- GSAP smooth animations
- Fully responsive (mobile, tablet, desktop)
- Persistent JSON storage (no database required)
- Auto-refresh stats every 30 seconds

---

## 🛠️ Tech Stack

| Category | Technology |
|----------|------------|
| **Backend** | FastAPI (Python 3.11+) |
| **Frontend** | HTML5, Custom CSS, JavaScript |
| **Animations** | GSAP, CSS keyframes |
| **Charts** | Chart.js |
| **Icons** | Font Awesome 6 |
| **Storage** | JSON file-based persistence |
| **Deployment** | Render (via render.yaml blueprint) |

---

## 📁 Project Structure
vectocloud-review/
├── review.py # FastAPI application (backend + frontend)
├── requirements.txt # Python dependencies
├── render.yaml # Render Blueprint (Infrastructure as Code)
├── .gitignore # Ignore local & temporary files
├── reviews.json # Auto-created on first run (persistent storage)
└── ui_config.json # Auto-created on first run (UI settings)

text

---

## 🚀 Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/DeVv-Prime/Review-Page.git
   cd Review-Page
Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install dependencies

```bash
pip install -r requirements.txt
Run the application

```bash
python review.py
# OR
uvicorn review:app --reload --port 8000
Open your browser

```

text
http://localhost:8000
Deploy to Render
Push code to GitHub repository

Log in to Render.com

Click "New +" → "Blueprint"

Connect your GitHub repo

Render automatically detects render.yaml and deploys
