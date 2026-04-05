import json
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Cookie, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, validator
import uvicorn

# ---------- Data Models ----------
class ReviewCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    rating: int = Field(..., ge=1, le=5)
    title: str = Field(..., min_length=3, max_length=100)
    comment: str = Field(..., min_length=5, max_length=500)

    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.replace(" ", "").replace("_", "").isalnum():
            raise ValueError('Username must contain letters, numbers, spaces or underscores')
        return v.strip()

class AdminLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4, max_length=100)

class UIConfig(BaseModel):
    background_url: str = "https://images.unsplash.com/photo-1557682250-33bd709cbe85?q=80&w=2029&auto=format"
    gradient_start: str = "#0f0c29"
    gradient_mid: str = "#302b63"
    gradient_end: str = "#24243e"
    neon_glow: bool = True
    animation_intensity: str = "medium"
    discord_link: str = "https://discord.gg/vectocloud"
    website_link: str = "https://vectocloud.com"
    website_button_text: str = "Visit Our Website"
    site_title: str = "VectoCloud"
    site_subtitle: str = "Advanced Review Intelligence Platform"
    primary_color: str = "#667eea"
    secondary_color: str = "#764ba2"
    enable_analytics: bool = True
    auto_refresh_interval: int = 30
    reviews_per_page: int = 10
    enable_verified_badge: bool = True
    enable_delete_button: bool = True
    theme_mode: str = "dark"
    enable_website_button: bool = True

# ---------- Persistence Layer ----------
DATA_FILE = "reviews.json"
CONFIG_FILE = "ui_config.json"
ADMIN_FILE = "admin.json"

def load_reviews() -> List[dict]:
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError):
        return []

def save_reviews(reviews: List[dict]):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(reviews, f, indent=2, ensure_ascii=False)

def load_ui_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "background_url": "https://images.unsplash.com/photo-1557682250-33bd709cbe85?q=80&w=2029&auto=format",
            "gradient_start": "#0f0c29",
            "gradient_mid": "#302b63",
            "gradient_end": "#24243e",
            "neon_glow": True,
            "animation_intensity": "medium",
            "discord_link": "https://discord.gg/vectocloud",
            "website_link": "https://vectocloud.com",
            "website_button_text": "Visit Our Website",
            "site_title": "VectoCloud",
            "site_subtitle": "Advanced Review Intelligence Platform",
            "primary_color": "#667eea",
            "secondary_color": "#764ba2",
            "enable_analytics": True,
            "auto_refresh_interval": 30,
            "reviews_per_page": 10,
            "enable_verified_badge": True,
            "enable_delete_button": True,
            "theme_mode": "dark",
            "enable_website_button": True
        }
        save_ui_config(default_config)
        return default_config
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_ui_config(config: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def load_admin_config() -> dict:
    if not os.path.exists(ADMIN_FILE):
        default_admin = {
            "username": "admin",
            "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
            "session_token": secrets.token_urlsafe(32)
        }
        with open(ADMIN_FILE, "w", encoding="utf-8") as f:
            json.dump(default_admin, f, indent=2)
        return default_admin
    try:
        with open(ADMIN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_admin_config(config: dict):
    with open(ADMIN_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

# ---------- FastAPI App ----------
app = FastAPI(title="VectoCloud Review Hub", version="4.0")

def get_next_id(reviews: List[dict]) -> int:
    return max([r["id"] for r in reviews], default=0) + 1

def compute_advanced_stats(reviews: List[dict]):
    if not reviews:
        return {
            "total": 0, "avg_rating": 0, "five_star": 0, "four_star": 0, "three_star": 0, "two_star": 0, "one_star": 0,
            "verified_count": 0, "best_rating_percentage": 0, "trend": "stable", "trend_percentage": 0,
            "weekly_growth": 0, "sentiment_score": 0, "response_rate": 0
        }
    
    total = len(reviews)
    five_star = sum(1 for r in reviews if r["rating"] == 5)
    four_star = sum(1 for r in reviews if r["rating"] == 4)
    three_star = sum(1 for r in reviews if r["rating"] == 3)
    two_star = sum(1 for r in reviews if r["rating"] == 2)
    one_star = sum(1 for r in reviews if r["rating"] == 1)
    avg_rating = sum(r["rating"] for r in reviews) / total
    verified_count = sum(1 for r in reviews if r.get("verified", False))
    
    best_rating_percentage = round((five_star / total) * 100, 1)
    
    now = datetime.now()
    last_week = [r for r in reviews if datetime.fromisoformat(r["timestamp"]) > now - timedelta(days=7)]
    previous_week = [r for r in reviews if now - timedelta(days=14) < datetime.fromisoformat(r["timestamp"]) <= now - timedelta(days=7)]
    
    last_week_avg = sum(r["rating"] for r in last_week) / len(last_week) if last_week else 0
    previous_week_avg = sum(r["rating"] for r in previous_week) / len(previous_week) if previous_week else 0
    
    if previous_week_avg == 0:
        trend = "up" if last_week_avg > 0 else "stable"
        trend_percentage = 100 if last_week_avg > 0 else 0
    else:
        trend_change = ((last_week_avg - previous_week_avg) / previous_week_avg) * 100
        trend = "up" if trend_change > 5 else "down" if trend_change < -5 else "stable"
        trend_percentage = abs(round(trend_change, 1))
    
    last_week_count = len(last_week)
    previous_week_count = len(previous_week)
    weekly_growth = round(((last_week_count - previous_week_count) / (previous_week_count or 1)) * 100, 1)
    
    sentiment_score = round((avg_rating / 5) * 100, 1)
    response_rate = round(min(85, 50 + (avg_rating * 7)), 1)
    
    return {
        "total": total,
        "avg_rating": round(avg_rating, 1),
        "five_star": five_star,
        "four_star": four_star,
        "three_star": three_star,
        "two_star": two_star,
        "one_star": one_star,
        "verified_count": verified_count,
        "best_rating_percentage": best_rating_percentage,
        "trend": trend,
        "trend_percentage": trend_percentage,
        "weekly_growth": weekly_growth,
        "sentiment_score": sentiment_score,
        "response_rate": response_rate
    }

# ---------- Authentication ----------
def verify_admin(username: str, password: str) -> bool:
    admin = load_admin_config()
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return username == admin.get("username") and password_hash == admin.get("password_hash")

def verify_session(token: str) -> bool:
    admin = load_admin_config()
    return token == admin.get("session_token")

# ---------- API Endpoints ----------
@app.get("/", response_class=HTMLResponse)
async def main_page():
    return HTMLResponse(content=get_html_content())

@app.get("/admin-login", response_class=HTMLResponse)
async def admin_login_page():
    return HTMLResponse(content=get_admin_login_html())

@app.post("/api/admin/login")
async def admin_login(login_data: AdminLogin):
    if verify_admin(login_data.username, login_data.password):
        admin = load_admin_config()
        response = JSONResponse({"success": True, "token": admin["session_token"]})
        response.set_cookie(key="admin_token", value=admin["session_token"], httponly=True, max_age=86400)
        return response
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/api/admin/logout")
async def admin_logout(response: Response):
    response.delete_cookie("admin_token")
    return {"success": True}

@app.get("/api/admin/verify")
async def verify_admin_session(admin_token: Optional[str] = Cookie(None)):
    if admin_token and verify_session(admin_token):
        return {"authenticated": True}
    return {"authenticated": False}

@app.get("/api/reviews")
async def get_reviews(limit: int = 50, offset: int = 0):
    reviews = load_reviews()
    reviews.sort(key=lambda x: x["id"], reverse=True)
    total = len(reviews)
    paginated = reviews[offset:offset + limit]
    return {"reviews": paginated, "total": total, "limit": limit, "offset": offset}

@app.post("/api/reviews")
async def create_review(review_data: ReviewCreate):
    reviews = load_reviews()
    new_id = get_next_id(reviews)
    
    new_review = {
        "id": new_id,
        "username": review_data.username,
        "rating": review_data.rating,
        "title": review_data.title,
        "comment": review_data.comment,
        "timestamp": datetime.now().isoformat(),
        "verified": True if len(reviews) % 3 == 0 else False
    }
    
    reviews.append(new_review)
    save_reviews(reviews)
    return {"success": True, "review": new_review}

@app.delete("/api/reviews/{review_id}")
async def delete_review(review_id: int, admin_token: Optional[str] = Cookie(None)):
    if not verify_session(admin_token):
        raise HTTPException(status_code=401, detail="Admin access required")
    reviews = load_reviews()
    new_reviews = [r for r in reviews if r["id"] != review_id]
    if len(new_reviews) == len(reviews):
        raise HTTPException(status_code=404, detail="Review not found")
    save_reviews(new_reviews)
    return {"success": True}

@app.get("/api/stats")
async def get_stats():
    reviews = load_reviews()
    return compute_advanced_stats(reviews)

@app.get("/api/ui-config")
async def get_ui_config():
    return load_ui_config()

@app.post("/api/ui-config")
async def update_ui_config(config: UIConfig, admin_token: Optional[str] = Cookie(None)):
    if not verify_session(admin_token):
        raise HTTPException(status_code=401, detail="Admin access required")
    save_ui_config(config.dict())
    return {"success": True, "config": config.dict()}

def get_admin_login_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Login - VectoCloud</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-container {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(12px);
            border-radius: 2rem;
            padding: 2.5rem;
            width: 100%;
            max-width: 420px;
            border: 1px solid rgba(255,255,255,0.2);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }
        .login-header { text-align: center; margin-bottom: 2rem; }
        .login-header i { font-size: 3rem; color: white; margin-bottom: 1rem; }
        .login-header h1 { color: white; font-size: 1.8rem; margin-bottom: 0.5rem; }
        .login-header p { color: rgba(255,255,255,0.7); }
        .input-group { margin-bottom: 1.5rem; }
        .input-group label { display: block; color: white; margin-bottom: 0.5rem; font-weight: 500; }
        .input-group input {
            width: 100%;
            padding: 0.8rem 1rem;
            background: rgba(255,255,255,0.15);
            border: 1px solid rgba(255,255,255,0.3);
            border-radius: 0.75rem;
            color: white;
            font-size: 1rem;
            transition: all 0.3s ease;
        }
        .input-group input:focus { outline: none; border-color: #667eea; background: rgba(255,255,255,0.2); }
        .login-btn {
            width: 100%;
            padding: 0.8rem;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border: none;
            border-radius: 0.75rem;
            color: white;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.3s ease;
        }
        .login-btn:hover { transform: scale(1.02); }
        .error-msg {
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid rgba(239, 68, 68, 0.5);
            border-radius: 0.5rem;
            padding: 0.75rem;
            color: #fca5a5;
            margin-top: 1rem;
            text-align: center;
            display: none;
        }
        .back-link {
            text-align: center;
            margin-top: 1.5rem;
            color: rgba(255,255,255,0.7);
            text-decoration: none;
            display: block;
        }
        .back-link:hover { color: white; }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <i class="fas fa-crown"></i>
            <h1>Admin Portal</h1>
            <p>Enter your credentials to continue</p>
        </div>
        <form id="loginForm">
            <div class="input-group">
                <label><i class="fas fa-user mr-2"></i>Username</label>
                <input type="text" id="username" required placeholder="admin">
            </div>
            <div class="input-group">
                <label><i class="fas fa-lock mr-2"></i>Password</label>
                <input type="password" id="password" required placeholder="••••••">
            </div>
            <button type="submit" class="login-btn"><i class="fas fa-sign-in-alt mr-2"></i>Login</button>
            <div id="errorMsg" class="error-msg"></div>
        </form>
        <a href="/" class="back-link"><i class="fas fa-arrow-left mr-2"></i>Back to Home</a>
    </div>
    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const res = await fetch('/api/admin/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            if(res.ok) {
                window.location.href = '/';
            } else {
                const errorDiv = document.getElementById('errorMsg');
                errorDiv.textContent = 'Invalid username or password';
                errorDiv.style.display = 'block';
                setTimeout(() => errorDiv.style.display = 'none', 3000);
            }
        });
    </script>
</body>
</html>"""

def get_html_content():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VectoCloud | Advanced Review Platform</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            position: relative;
            overflow-x: hidden;
            transition: background 0.3s ease;
        }
        .animated-bg { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -2; background-size: cover; background-position: center; transition: background-image 0.8s ease; }
        .gradient-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1; transition: all 0.6s ease; }
        .floating-particles { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1; pointer-events: none; }
        .particle { position: absolute; background: rgba(255,255,255,0.15); border-radius: 50%; pointer-events: none; animation: floatParticle linear infinite; }
        @keyframes floatParticle { 0% { transform: translateY(100vh) rotate(0deg); opacity: 0; } 10% { opacity: 0.6; } 90% { opacity: 0.6; } 100% { transform: translateY(-20vh) rotate(360deg); opacity: 0; } }
        .container { max-width: 1400px; margin: 0 auto; padding: 2rem; }
        .glass-card { background: rgba(255,255,255,0.08); backdrop-filter: blur(12px); border-radius: 2rem; border: 1px solid rgba(255,255,255,0.2); transition: transform 0.3s ease, box-shadow 0.3s ease; }
        .glass-card:hover { transform: translateY(-5px); box-shadow: 0 20px 40px rgba(0,0,0,0.3); }
        .neon-glow { box-shadow: 0 0 20px rgba(0,255,255,0.3), 0 0 40px rgba(0,255,255,0.1); }
        .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; transition: all 0.3s ease; cursor: pointer; color: white; padding: 0.75rem 1.5rem; border-radius: 0.75rem; font-weight: 600; }
        .btn-primary:hover { transform: scale(1.02); filter: brightness(1.05); }
        .btn-website { background: linear-gradient(135deg, #10b981, #059669); border: none; transition: all 0.3s ease; cursor: pointer; color: white; padding: 0.75rem 1.5rem; border-radius: 0.75rem; font-weight: 600; text-decoration: none; display: inline-flex; align-items: center; gap: 0.5rem; }
        .btn-website:hover { transform: scale(1.02); filter: brightness(1.05); }
        .star-rating i { cursor: pointer; transition: transform 0.2s, color 0.2s; }
        .star-rating i:hover { transform: scale(1.2); }
        .review-card { background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); border-radius: 1.5rem; padding: 1.5rem; transition: all 0.3s ease; }
        .review-card:hover { background: rgba(255,255,255,0.15); transform: translateX(5px); }
        .admin-panel { max-height: 0; overflow: hidden; transition: max-height 0.5s ease; }
        .admin-panel.open { max-height: 1200px; }
        .toast-notif { position: fixed; bottom: 2rem; right: 2rem; background: rgba(0,0,0,0.8); backdrop-filter: blur(8px); padding: 1rem 1.5rem; border-radius: 1rem; color: white; z-index: 1000; transform: translateX(400px); transition: transform 0.3s ease; }
        .toast-notif.show { transform: translateX(0); }
        @media (max-width: 768px) { .container { padding: 1rem; } }
        .monitor-bar-container { background: rgba(0,0,0,0.4); border-radius: 1rem; padding: 0.25rem; position: relative; }
        .monitor-bar-fill { background: linear-gradient(90deg, #10b981, #34d399, #6ee7b7); border-radius: 0.75rem; height: 100%; transition: width 1s ease; position: relative; overflow: hidden; }
        .monitor-bar-fill::after { content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent); animation: shimmer 2s infinite; }
        @keyframes shimmer { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }
        .trend-up { color: #10b981; }
        .trend-down { color: #ef4444; }
        .metric-card { background: rgba(255,255,255,0.05); border-radius: 1rem; padding: 1rem; transition: all 0.3s ease; }
        .metric-card:hover { background: rgba(255,255,255,0.1); transform: translateY(-3px); }
        .dropdown { position: relative; display: inline-block; }
        .dropdown-content { display: none; position: absolute; background: rgba(0,0,0,0.9); backdrop-filter: blur(10px); min-width: 200px; border-radius: 1rem; z-index: 1; right: 0; margin-top: 0.5rem; border: 1px solid rgba(255,255,255,0.2); }
        .dropdown-content a { color: white; padding: 0.75rem 1rem; text-decoration: none; display: flex; align-items: center; gap: 0.75rem; transition: background 0.2s; border-radius: 0.5rem; margin: 0.25rem; }
        .dropdown-content a:hover { background: rgba(255,255,255,0.1); }
        .dropdown:hover .dropdown-content { display: block; animation: fadeIn 0.3s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
        .admin-badge { background: linear-gradient(135deg, #ef4444, #dc2626); padding: 0.25rem 0.75rem; border-radius: 2rem; font-size: 0.75rem; font-weight: 600; }
        .text-6xl { font-size: 4rem; }
        .text-5xl { font-size: 3rem; }
        .text-2xl { font-size: 1.5rem; }
        .text-xl { font-size: 1.25rem; }
        .text-3xl { font-size: 1.875rem; }
        .font-bold { font-weight: 700; }
        .mb-5 { margin-bottom: 2rem; }
        .mb-4 { margin-bottom: 1rem; }
        .mb-6 { margin-bottom: 1.5rem; }
        .mt-2 { margin-top: 0.5rem; }
        .mt-4 { margin-top: 1rem; }
        .grid { display: grid; }
        .grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        .gap-4 { gap: 1rem; }
        .gap-6 { gap: 1.5rem; }
        .text-center { text-align: center; }
        .w-full { width: 100%; }
        .py-3 { padding-top: 0.75rem; padding-bottom: 0.75rem; }
        .px-4 { padding-left: 1rem; padding-right: 1rem; }
        .py-2 { padding-top: 0.5rem; padding-bottom: 0.5rem; }
        .p-6 { padding: 1.5rem; }
        .rounded-xl { border-radius: 0.75rem; }
        .text-white { color: white; }
        .text-gray-300 { color: #d1d5db; }
        .text-gray-400 { color: #9ca3af; }
        .text-purple-400 { color: #a78bfa; }
        .text-yellow-400 { color: #fbbf24; }
        .text-green-400 { color: #4ade80; }
        .text-blue-400 { color: #60a5fa; }
        .text-red-400 { color: #f87171; }
        .bg-purple-600 { background-color: #9333ea; }
        .bg-red-500\\/20 { background-color: rgba(239, 68, 68, 0.2); }
        .font-semibold { font-weight: 600; }
        .space-y-3 > * + * { margin-top: 0.75rem; }
        .max-h-96 { max-height: 24rem; }
        .overflow-y-auto { overflow-y: auto; }
        .bg-gradient-to-r { background-image: linear-gradient(to right, var(--tw-gradient-stops)); }
        .from-purple-400 { --tw-gradient-from: #c084fc; }
        .to-pink-400 { --tw-gradient-to: #f472b6; }
        .bg-clip-text { background-clip: text; }
        .text-transparent { color: transparent; }
        .mr-2 { margin-right: 0.5rem; }
        .h-10 { height: 2.5rem; }
        .w-5 { width: 1.25rem; }
        .h-5 { height: 1.25rem; }
        .cursor-pointer { cursor: pointer; }
        .flex { display: flex; }
        .justify-between { justify-content: space-between; }
        .justify-center { justify-content: center; }
        .items-center { align-items: center; }
        .block { display: block; }
        .text-sm { font-size: 0.875rem; }
        .text-xs { font-size: 0.75rem; }
        .gap-2 { gap: 0.5rem; }
        .ml-auto { margin-left: auto; }
        .relative { position: relative; }
    </style>
</head>
<body>
    <div class="animated-bg" id="animatedBg"></div>
    <div class="gradient-overlay" id="gradientOverlay"></div>
    <div class="floating-particles" id="particles"></div>
    
    <div class="container">
        <!-- Header with Dropdown -->
        <div class="flex justify-between items-center mb-5">
            <div class="text-left">
                <i class="fas fa-cloud-upload-alt text-4xl mb-2" style="color: #667eea;"></i>
                <h1 class="text-3xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent" id="siteTitle">VectoCloud</h1>
                <p class="text-gray-300 text-sm" id="siteSubtitle">Advanced Review Intelligence Platform</p>
            </div>
            <div class="dropdown">
                <button class="btn-primary" style="padding: 0.6rem 1.2rem;">
                    <i class="fas fa-bars mr-2"></i>Menu <i class="fas fa-chevron-down ml-2"></i>
                </button>
                <div class="dropdown-content">
                    <a href="#" id="supportLinkBtn"><i class="fab fa-discord"></i> Support</a>
                    <a href="#" id="websiteLinkBtn" target="_blank"><i class="fas fa-globe"></i> <span id="websiteBtnText">Visit Website</span></a>
                    <a href="/admin-login" id="adminLoginBtn"><i class="fas fa-crown"></i> Admin Login</a>
                    <a href="#" id="adminLogoutBtn" style="display: none;"><i class="fas fa-sign-out-alt"></i> Logout</a>
                </div>
            </div>
        </div>
        
        <!-- Monitor Bar -->
        <div class="glass-card p-6 mb-6">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-2xl font-bold text-white"><i class="fas fa-chart-simple mr-2"></i>Live Performance Monitor</h2>
            </div>
            <div class="mb-5">
                <div class="flex justify-between items-center mb-2">
                    <span class="text-gray-300 font-semibold"><i class="fas fa-star text-yellow-400 mr-2"></i>5-Star Excellence Rate</span>
                    <span class="text-2xl font-bold text-white" id="bestPercentage">0%</span>
                </div>
                <div class="monitor-bar-container" style="height: 48px;">
                    <div class="monitor-bar-fill" id="monitorBarFill" style="width: 0%; height: 100%;"></div>
                </div>
            </div>
            
            <div class="grid grid-cols-3 gap-4">
                <div class="metric-card text-center">
                    <i class="fas fa-trend-up text-xl mb-1"></i>
                    <div class="text-sm text-gray-400">Weekly Trend</div>
                    <div id="trendIndicator" class="text-xl font-bold">0%</div>
                </div>
                <div class="metric-card text-center">
                    <i class="fas fa-chart-line text-xl mb-1"></i>
                    <div class="text-sm text-gray-400">Growth Rate</div>
                    <div class="text-xl font-bold text-green-400" id="weeklyGrowth">0%</div>
                </div>
                <div class="metric-card text-center">
                    <i class="fas fa-heart text-xl mb-1"></i>
                    <div class="text-sm text-gray-400">Sentiment Score</div>
                    <div class="text-xl font-bold text-purple-400" id="sentimentScore">0</div>
                </div>
            </div>
        </div>
        
        <div class="grid gap-6" style="grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));">
            <!-- Left Column -->
            <div>
                <div class="glass-card p-6">
                    <h2 class="text-2xl font-bold mb-4 text-white"><i class="fas fa-pen-alt mr-2"></i>Write Review</h2>
                    <form id="reviewForm">
                        <div class="mb-4">
                            <label class="block text-gray-300 mb-2">Username</label>
                            <input type="text" id="username" class="w-full px-4 py-2 rounded-xl bg-white/10 border border-white/20 text-white focus:outline-none focus:border-purple-500" required>
                        </div>
                        <div class="mb-4">
                            <label class="block text-gray-300 mb-2">Rating</label>
                            <div class="star-rating flex gap-2 text-2xl" id="starRating">
                                <i class="far fa-star" data-rating="1"></i>
                                <i class="far fa-star" data-rating="2"></i>
                                <i class="far fa-star" data-rating="3"></i>
                                <i class="far fa-star" data-rating="4"></i>
                                <i class="far fa-star" data-rating="5"></i>
                            </div>
                            <input type="hidden" id="rating" value="0">
                        </div>
                        <div class="mb-4">
                            <label class="block text-gray-300 mb-2">Title</label>
                            <input type="text" id="title" class="w-full px-4 py-2 rounded-xl bg-white/10 border border-white/20 text-white" required>
                        </div>
                        <div class="mb-4">
                            <label class="block text-gray-300 mb-2">Comment</label>
                            <textarea id="comment" rows="4" class="w-full px-4 py-2 rounded-xl bg-white/10 border border-white/20 text-white" required></textarea>
                        </div>
                        <button type="submit" class="btn-primary w-full"><i class="fas fa-paper-plane mr-2"></i>Submit Review</button>
                    </form>
                </div>
                
                <!-- Website Button Section -->
                <div class="mt-4 text-center" id="websiteButtonContainer">
                    <a href="#" id="mainWebsiteBtn" target="_blank" class="btn-website w-full justify-center"><i class="fas fa-external-link-alt"></i> <span id="mainWebsiteBtnText">Visit Our Website</span></a>
                </div>
                
                <div class="mt-4">
                    <button id="adminToggleBtn" class="w-full py-2 rounded-xl bg-red-500/20 border border-red-500/40 text-red-300 font-semibold hover:bg-red-500/30 transition cursor-pointer">
                        <i class="fas fa-crown mr-2"></i>Admin Panel
                    </button>
                </div>
                
                <div id="adminPanel" class="admin-panel mt-4">
                    <div class="glass-card p-6">
                        <h3 class="text-xl font-bold text-white mb-4"><i class="fas fa-palette mr-2"></i>UI Customization</h3>
                        <div class="space-y-3">
                            <div><input type="text" id="bgUrl" placeholder="Background URL" class="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/20 text-white text-sm"></div>
                            <div><input type="color" id="gradStart" class="w-full h-10 rounded-lg cursor-pointer"></div>
                            <div><input type="color" id="gradMid" class="w-full h-10 rounded-lg cursor-pointer"></div>
                            <div><input type="color" id="gradEnd" class="w-full h-10 rounded-lg cursor-pointer"></div>
                            <div><input type="text" id="siteTitleInput" placeholder="Site Title" class="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/20 text-white text-sm"></div>
                            <div><input type="text" id="siteSubtitleInput" placeholder="Site Subtitle" class="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/20 text-white text-sm"></div>
                            <div><input type="text" id="discordLinkInput" placeholder="Discord Support Link" class="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/20 text-white text-sm"></div>
                            <div><input type="text" id="websiteLinkInput" placeholder="Website Link" class="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/20 text-white text-sm"></div>
                            <div><input type="text" id="websiteButtonTextInput" placeholder="Website Button Text" class="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/20 text-white text-sm"></div>
                            <div class="flex items-center justify-between">
                                <label class="text-gray-300">Neon Glow</label>
                                <input type="checkbox" id="neonGlow" class="w-5 h-5 cursor-pointer">
                            </div>
                            <div class="flex items-center justify-between">
                                <label class="text-gray-300">Show Website Button</label>
                                <input type="checkbox" id="enableWebsiteBtn" class="w-5 h-5 cursor-pointer">
                            </div>
                            <div><select id="animIntensity" class="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/20 text-white">
                                <option value="light">Light</option><option value="medium">Medium</option><option value="intense">Intense</option>
                            </select></div>
                            <button id="saveUiConfig" class="w-full py-2 rounded-lg bg-purple-600 text-white font-semibold mt-2 cursor-pointer"><i class="fas fa-save mr-2"></i>Save All Settings</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Right Column -->
            <div>
                <div class="glass-card p-6 mb-6">
                    <h2 class="text-2xl font-bold mb-4 text-white"><i class="fas fa-chart-line mr-2"></i>Analytics Dashboard</h2>
                    <div class="grid grid-cols-2 gap-4 mb-4">
                        <div class="text-center"><div class="text-3xl font-bold text-purple-400" id="totalReviews">0</div><div class="text-gray-400 text-sm">Total Reviews</div></div>
                        <div class="text-center"><div class="text-3xl font-bold text-yellow-400" id="avgRating">0</div><div class="text-gray-400 text-sm">Avg Rating</div></div>
                        <div class="text-center"><div class="text-3xl font-bold text-green-400" id="verifiedCount">0</div><div class="text-gray-400 text-sm">Verified</div></div>
                        <div class="text-center"><div class="text-3xl font-bold text-blue-400" id="responseRate">0%</div><div class="text-gray-400 text-sm">Response Rate</div></div>
                    </div>
                    <canvas id="ratingChart" height="150"></canvas>
                </div>
                
                <div class="glass-card p-6">
                    <h2 class="text-2xl font-bold mb-4 text-white"><i class="fas fa-comments mr-2"></i>Community Reviews</h2>
                    <div id="reviewsList" class="space-y-3 max-h-96 overflow-y-auto"></div>
                </div>
            </div>
        </div>
    </div>
    
    <div id="toast" class="toast-notif"></div>
    
    <script>
        let currentRating = 0, chart = null, isAdmin = false;
        
        document.querySelectorAll('#starRating i').forEach(star => {
            star.addEventListener('click', function() {
                currentRating = parseInt(this.dataset.rating);
                document.querySelectorAll('#starRating i').forEach((s, idx) => {
                    s.className = idx < currentRating ? 'fas fa-star text-yellow-400' : 'far fa-star text-gray-400';
                });
                document.getElementById('rating').value = currentRating;
            });
        });
        
        async function checkAdminStatus() {
            const res = await fetch('/api/admin/verify');
            const data = await res.json();
            isAdmin = data.authenticated;
            const adminLoginBtn = document.getElementById('adminLoginBtn');
            const adminLogoutBtn = document.getElementById('adminLogoutBtn');
            if(isAdmin) {
                adminLoginBtn.style.display = 'none';
                adminLogoutBtn.style.display = 'flex';
                document.getElementById('adminToggleBtn').style.display = 'block';
            } else {
                adminLoginBtn.style.display = 'flex';
                adminLogoutBtn.style.display = 'none';
                document.getElementById('adminToggleBtn').style.display = 'block';
            }
        }
        
        document.getElementById('adminLogoutBtn')?.addEventListener('click', async (e) => {
            e.preventDefault();
            await fetch('/api/admin/logout', { method: 'POST' });
            window.location.reload();
        });
        
        async function loadUIConfig() {
            const res = await fetch('/api/ui-config');
            const config = await res.json();
            document.getElementById('bgUrl').value = config.background_url;
            document.getElementById('gradStart').value = config.gradient_start;
            document.getElementById('gradMid').value = config.gradient_mid;
            document.getElementById('gradEnd').value = config.gradient_end;
            document.getElementById('neonGlow').checked = config.neon_glow;
            document.getElementById('animIntensity').value = config.animation_intensity;
            document.getElementById('siteTitleInput').value = config.site_title;
            document.getElementById('siteSubtitleInput').value = config.site_subtitle;
            document.getElementById('discordLinkInput').value = config.discord_link;
            document.getElementById('websiteLinkInput').value = config.website_link;
            document.getElementById('websiteButtonTextInput').value = config.website_button_text;
            document.getElementById('enableWebsiteBtn').checked = config.enable_website_button;
            
            document.getElementById('siteTitle').textContent = config.site_title;
            document.getElementById('siteSubtitle').textContent = config.site_subtitle;
            document.getElementById('websiteBtnText').textContent = config.website_button_text;
            document.getElementById('mainWebsiteBtnText').textContent = config.website_button_text;
            
            const supportLink = document.getElementById('supportLinkBtn');
            supportLink.href = config.discord_link;
            supportLink.target = "_blank";
            
            const websiteLink = document.getElementById('websiteLinkBtn');
            websiteLink.href = config.website_link;
            websiteLink.target = "_blank";
            
            const mainWebsiteBtn = document.getElementById('mainWebsiteBtn');
            mainWebsiteBtn.href = config.website_link;
            
            const websiteContainer = document.getElementById('websiteButtonContainer');
            if(config.enable_website_button) {
                websiteContainer.style.display = 'block';
            } else {
                websiteContainer.style.display = 'none';
            }
            
            applyUIConfig(config);
        }
        
        function applyUIConfig(config) {
            document.getElementById('animatedBg').style.backgroundImage = `url(${config.background_url})`;
            document.getElementById('gradientOverlay').style.background = `linear-gradient(135deg, ${config.gradient_start} 0%, ${config.gradient_mid} 50%, ${config.gradient_end} 100%)`;
            if(config.neon_glow) document.querySelectorAll('.glass-card').forEach(c => c.classList.add('neon-glow'));
            else document.querySelectorAll('.glass-card').forEach(c => c.classList.remove('neon-glow'));
            let count = config.animation_intensity === 'light' ? 20 : config.animation_intensity === 'medium' ? 40 : 80;
            generateParticles(count);
        }
        
        function generateParticles(count) {
            const container = document.getElementById('particles');
            container.innerHTML = '';
            for(let i = 0; i < count; i++) {
                const p = document.createElement('div');
                p.className = 'particle';
                const s = Math.random() * 8 + 2;
                p.style.width = s + 'px';
                p.style.height = s + 'px';
                p.style.left = Math.random() * 100 + '%';
                p.style.animationDuration = Math.random() * 10 + 5 + 's';
                p.style.animationDelay = Math.random() * 10 + 's';
                container.appendChild(p);
            }
        }
        
        async function saveUIConfig() {
            if(!isAdmin) { showToast('Admin access required!', 'error'); return; }
            const config = { 
                background_url: document.getElementById('bgUrl').value, 
                gradient_start: document.getElementById('gradStart').value, 
                gradient_mid: document.getElementById('gradMid').value, 
                gradient_end: document.getElementById('gradEnd').value, 
                neon_glow: document.getElementById('neonGlow').checked, 
                animation_intensity: document.getElementById('animIntensity').value,
                discord_link: document.getElementById('discordLinkInput').value,
                website_link: document.getElementById('websiteLinkInput').value,
                website_button_text: document.getElementById('websiteButtonTextInput').value,
                site_title: document.getElementById('siteTitleInput').value,
                site_subtitle: document.getElementById('siteSubtitleInput').value,
                enable_website_button: document.getElementById('enableWebsiteBtn').checked,
                primary_color: "#667eea",
                secondary_color: "#764ba2",
                enable_analytics: true,
                auto_refresh_interval: 30,
                reviews_per_page: 10,
                enable_verified_badge: true,
                enable_delete_button: true,
                theme_mode: "dark"
            };
            const res = await fetch('/api/ui-config', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(config) });
            if(res.ok) { loadUIConfig(); showToast('UI settings saved!', 'success'); }
            else showToast('Error saving settings', 'error');
        }
        
        async function loadReviews() {
            const res = await fetch('/api/reviews');
            const data = await res.json();
            const reviews = data.reviews;
            const container = document.getElementById('reviewsList');
            if(reviews.length === 0) { container.innerHTML = '<div class="text-center text-gray-400 py-8"><i class="fas fa-cloud fa-3x mb-2"></i><p>No reviews yet!</p></div>'; return; }
            container.innerHTML = reviews.map(r => `<div class="review-card"><div class="flex justify-between items-start"><div><i class="fas fa-user-circle text-purple-400 mr-2"></i><span class="font-semibold text-white">${escapeHtml(r.username)}</span> ${r.verified ? '<i class="fas fa-check-circle text-green-400"></i>' : ''}</div><div class="text-yellow-400">${'★'.repeat(r.rating)}${'☆'.repeat(5-r.rating)}</div></div><h3 class="text-white font-bold mt-2">${escapeHtml(r.title)}</h3><p class="text-gray-300 text-sm mt-1">${escapeHtml(r.comment)}</p><div class="text-gray-500 text-xs mt-2 flex justify-between"><span><i class="far fa-clock"></i> ${new Date(r.timestamp).toLocaleDateString()}</span>${isAdmin ? `<button onclick="deleteReview(${r.id})" class="text-red-400 hover:text-red-300"><i class="fas fa-trash-alt"></i></button>` : ''}</div></div>`).join('');
        }
        
        async function deleteReview(id) { if(confirm('Delete this review?')) { await fetch(`/api/reviews/${id}`, {method: 'DELETE'}); loadReviews(); loadStats(); showToast('Review deleted', 'info'); } }
        
        async function loadStats() {
            const res = await fetch('/api/stats');
            const stats = await res.json();
            document.getElementById('totalReviews').innerText = stats.total;
            document.getElementById('avgRating').innerText = stats.avg_rating;
            document.getElementById('verifiedCount').innerText = stats.verified_count;
            document.getElementById('responseRate').innerText = stats.response_rate + '%';
            document.getElementById('bestPercentage').innerHTML = stats.best_rating_percentage + '%';
            document.getElementById('monitorBarFill').style.width = stats.best_rating_percentage + '%';
            const trendDiv = document.getElementById('trendIndicator');
            if(stats.trend === 'up') trendDiv.innerHTML = `<i class="fas fa-arrow-up trend-up"></i> +${stats.trend_percentage}%`;
            else if(stats.trend === 'down') trendDiv.innerHTML = `<i class="fas fa-arrow-down trend-down"></i> -${stats.trend_percentage}%`;
            else trendDiv.innerHTML = `<i class="fas fa-minus-circle"></i> ${stats.trend_percentage}%`;
            document.getElementById('weeklyGrowth').innerHTML = (stats.weekly_growth >= 0 ? '+' : '') + stats.weekly_growth + '%';
            document.getElementById('sentimentScore').innerHTML = stats.sentiment_score;
            if(chart) chart.destroy();
            chart = new Chart(document.getElementById('ratingChart'), { type: 'bar', data: { labels: ['5★', '4★', '3★', '2★', '1★'], datasets: [{ label: 'Reviews', data: [stats.five_star, stats.four_star, stats.three_star, stats.two_star, stats.one_star], backgroundColor: 'rgba(102, 126, 234, 0.6)', borderRadius: 8 }] }, options: { responsive: true, plugins: { legend: { labels: { color: 'white' } } } } });
        }
        
        document.getElementById('reviewForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            if(currentRating === 0) { showToast('Select a rating', 'error'); return; }
            const review = { username: document.getElementById('username').value, rating: currentRating, title: document.getElementById('title').value, comment: document.getElementById('comment').value };
            const res = await fetch('/api/reviews', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(review) });
            if(res.ok) { showToast('Review submitted!', 'success'); document.getElementById('reviewForm').reset(); document.querySelectorAll('#starRating i').forEach(s => s.className = 'far fa-star text-gray-400'); currentRating = 0; loadReviews(); loadStats(); }
            else showToast('Error', 'error');
        });
        
        document.getElementById('saveUiConfig').addEventListener('click', saveUIConfig);
        document.getElementById('adminToggleBtn').addEventListener('click', () => {
            if(!isAdmin) { showToast('Please login as admin first', 'error'); window.location.href = '/admin-login'; return; }
            document.getElementById('adminPanel').classList.toggle('open');
        });
        
        function showToast(msg, type) { const toast = document.getElementById('toast'); toast.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'} mr-2"></i>${msg}`; toast.classList.add('show'); setTimeout(() => toast.classList.remove('show'), 3000); }
        function escapeHtml(str) { if(!str) return ''; return str.replace(/[&<>]/g, m => m === '&' ? '&amp;' : m === '<' ? '&lt;' : '&gt;'); }
        
        checkAdminStatus();
        loadUIConfig();
        loadReviews();
        loadStats();
        setInterval(() => { loadStats(); loadReviews(); }, 30000);
    </script>
</body>
</html>"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
