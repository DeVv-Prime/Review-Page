import json
import os
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, validator
import uvicorn

# ---------- Data Models (Pydantic v1 compatible) ----------
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

class UIConfig(BaseModel):
    background_url: str = "https://images.unsplash.com/photo-1557682250-33bd709cbe85?q=80&w=2029&auto=format"
    gradient_start: str = "#0f0c29"
    gradient_mid: str = "#302b63"
    gradient_end: str = "#24243e"
    neon_glow: bool = True
    animation_intensity: str = "medium"

# ---------- Persistence Layer ----------
DATA_FILE = "reviews.json"
CONFIG_FILE = "ui_config.json"

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
            "animation_intensity": "medium"
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

# ---------- FastAPI App ----------
app = FastAPI(title="VectoCloud Review Hub", version="3.0")

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
    
    # Best rating percentage (5-star percentage)
    best_rating_percentage = round((five_star / total) * 100, 1)
    
    # Calculate trend by comparing last 7 days vs previous 7 days
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
    
    # Weekly growth rate
    last_week_count = len(last_week)
    previous_week_count = len(previous_week)
    weekly_growth = round(((last_week_count - previous_week_count) / (previous_week_count or 1)) * 100, 1)
    
    # Sentiment score (0-100 based on ratings)
    sentiment_score = round((avg_rating / 5) * 100, 1)
    
    # Response rate (assuming 80% of reviews get responses in real scenario)
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

# ---------- API Endpoints ----------
@app.get("/", response_class=HTMLResponse)
async def main_page():
    """Serve the main VectoCloud review page"""
    return get_html_response()

@app.get("/api/reviews")
async def get_reviews(limit: int = 50):
    """Get all reviews"""
    reviews = load_reviews()
    reviews.sort(key=lambda x: x["id"], reverse=True)
    return {"reviews": reviews[:limit], "total": len(reviews)}

@app.post("/api/reviews")
async def create_review(review_data: ReviewCreate):
    """Create a new review"""
    reviews = load_reviews()
    new_id = get_next_id(reviews)
    
    new_review = {
        "id": new_id,
        "username": review_data.username,
        "rating": review_data.rating,
        "title": review_data.title,
        "comment": review_data.comment,
        "timestamp": datetime.now().isoformat(),
        "verified": True if len(reviews) % 3 == 0 else False  # Auto-verify every 3rd review for demo
    }
    
    reviews.append(new_review)
    save_reviews(reviews)
    return {"success": True, "review": new_review}

@app.delete("/api/reviews/{review_id}")
async def delete_review(review_id: int):
    """Delete a review (admin feature)"""
    reviews = load_reviews()
    new_reviews = [r for r in reviews if r["id"] != review_id]
    if len(new_reviews) == len(reviews):
        raise HTTPException(status_code=404, detail="Review not found")
    save_reviews(new_reviews)
    return {"success": True}

@app.get("/api/stats")
async def get_stats():
    """Get advanced review statistics"""
    reviews = load_reviews()
    return compute_advanced_stats(reviews)

@app.get("/api/ui-config")
async def get_ui_config():
    """Get current UI configuration"""
    return load_ui_config()

@app.post("/api/ui-config")
async def update_ui_config(config: UIConfig):
    """Update UI configuration (admin panel)"""
    save_ui_config(config.dict())
    return {"success": True, "config": config.dict()}

def get_html_response():
    """Generate the HTML page with embedded CSS/JS - Advanced Monitor Bar included"""
    return HTMLResponse(content="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VectoCloud | Advanced Review Monitor</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            transition: background 0.5s ease;
            position: relative;
            overflow-x: hidden;
        }
        .animated-bg {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -2;
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            transition: background-image 0.8s cubic-bezier(0.2, 0.9, 0.4, 1.1);
        }
        .gradient-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            transition: all 0.6s ease;
        }
        .floating-particles {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            pointer-events: none;
        }
        .particle {
            position: absolute;
            background: rgba(255,255,255,0.15);
            border-radius: 50%;
            pointer-events: none;
            animation: floatParticle linear infinite;
        }
        @keyframes floatParticle {
            0% { transform: translateY(100vh) rotate(0deg); opacity: 0; }
            10% { opacity: 0.6; }
            90% { opacity: 0.6; }
            100% { transform: translateY(-20vh) rotate(360deg); opacity: 0; }
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 2rem; }
        .glass-card {
            background: rgba(255,255,255,0.08);
            backdrop-filter: blur(12px);
            border-radius: 2rem;
            border: 1px solid rgba(255,255,255,0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .glass-card:hover { transform: translateY(-5px); box-shadow: 0 20px 40px rgba(0,0,0,0.3); }
        .neon-glow { box-shadow: 0 0 20px rgba(0,255,255,0.3), 0 0 40px rgba(0,255,255,0.1); }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        .btn-primary:hover { transform: scale(1.02); filter: brightness(1.05); }
        .star-rating i { cursor: pointer; transition: transform 0.2s, color 0.2s; }
        .star-rating i:hover { transform: scale(1.2); }
        .review-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 1.5rem;
            padding: 1.5rem;
            transition: all 0.3s ease;
        }
        .review-card:hover { background: rgba(255,255,255,0.15); transform: translateX(5px); }
        .admin-panel {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.5s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .admin-panel.open { max-height: 800px; }
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .animate-in { animation: fadeInUp 0.6s ease forwards; }
        .toast-notif {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: rgba(0,0,0,0.8);
            backdrop-filter: blur(8px);
            padding: 1rem 1.5rem;
            border-radius: 1rem;
            color: white;
            z-index: 1000;
            transform: translateX(400px);
            transition: transform 0.3s ease;
        }
        .toast-notif.show { transform: translateX(0); }
        @media (max-width: 768px) { .container { padding: 1rem; } }
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
        .rounded-lg { border-radius: 0.5rem; }
        .text-white { color: white; }
        .text-gray-300 { color: #d1d5db; }
        .text-gray-400 { color: #9ca3af; }
        .text-purple-400 { color: #a78bfa; }
        .text-yellow-400 { color: #fbbf24; }
        .text-green-400 { color: #4ade80; }
        .text-blue-400 { color: #60a5fa; }
        .text-red-400 { color: #f87171; }
        .text-red-300 { color: #fca5a5; }
        .bg-purple-600 { background-color: #9333ea; }
        .bg-red-500\\/20 { background-color: rgba(239, 68, 68, 0.2); }
        .border-red-500\\/40 { border-color: rgba(239, 68, 68, 0.4); }
        .font-semibold { font-weight: 600; }
        .space-y-3 > * + * { margin-top: 0.75rem; }
        .space-y-4 > * + * { margin-top: 1rem; }
        .max-h-96 { max-height: 24rem; }
        .overflow-y-auto { overflow-y: auto; }
        .bg-gradient-to-r { background-image: linear-gradient(to right, var(--tw-gradient-stops)); }
        .from-purple-400 { --tw-gradient-from: #c084fc; --tw-gradient-stops: var(--tw-gradient-from), var(--tw-gradient-to, rgba(192, 132, 252, 0)); }
        .to-pink-400 { --tw-gradient-to: #f472b6; }
        .bg-clip-text { background-clip: text; }
        .text-transparent { color: transparent; }
        .mr-2 { margin-right: 0.5rem; }
        .ml-2 { margin-left: 0.5rem; }
        .h-10 { height: 2.5rem; }
        .w-5 { width: 1.25rem; }
        .h-5 { height: 1.25rem; }
        .cursor-pointer { cursor: pointer; }
        .transition { transition: all 0.3s ease; }
        .flex { display: flex; }
        .justify-between { justify-content: space-between; }
        .items-center { align-items: center; }
        .items-start { align-items: flex-start; }
        .block { display: block; }
        .text-sm { font-size: 0.875rem; }
        .text-xs { font-size: 0.75rem; }
        .gap-2 { gap: 0.5rem; }
        
        /* Monitor Bar Styles */
        .monitor-bar-container {
            background: rgba(0,0,0,0.4);
            border-radius: 1rem;
            padding: 0.25rem;
            position: relative;
        }
        .monitor-bar-fill {
            background: linear-gradient(90deg, #10b981, #34d399, #6ee7b7);
            border-radius: 0.75rem;
            height: 100%;
            transition: width 1s cubic-bezier(0.34, 1.2, 0.64, 1);
            position: relative;
            overflow: hidden;
        }
        .monitor-bar-fill::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            animation: shimmer 2s infinite;
        }
        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }
        .trend-up { color: #10b981; animation: pulse-green 1s ease; }
        .trend-down { color: #ef4444; animation: pulse-red 1s ease; }
        .trend-stable { color: #f59e0b; }
        @keyframes pulse-green {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); text-shadow: 0 0 10px #10b981; }
        }
        @keyframes pulse-red {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); text-shadow: 0 0 10px #ef4444; }
        }
        .metric-card {
            background: rgba(255,255,255,0.05);
            border-radius: 1rem;
            padding: 1rem;
            transition: all 0.3s ease;
        }
        .metric-card:hover { background: rgba(255,255,255,0.1); transform: translateY(-3px); }
        .percentage-badge {
            font-size: 2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #fff, #a78bfa);
            background-clip: text;
            -webkit-background-clip: text;
            color: transparent;
        }
    </style>
</head>
<body>
    <div class="animated-bg" id="animatedBg"></div>
    <div class="gradient-overlay" id="gradientOverlay"></div>
    <div class="floating-particles" id="particles"></div>
    
    <div class="container">
        <div class="text-center mb-5 animate-in">
            <i class="fas fa-cloud-upload-alt text-6xl mb-3" style="color: #667eea;"></i>
            <h1 class="text-5xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">VectoCloud</h1>
            <p class="text-gray-300 mt-2">Advanced Review Intelligence Platform</p>
        </div>
        
        <!-- Advanced Monitor Bar Section -->
        <div class="glass-card p-6 mb-6 animate-in" style="animation-delay: 0.05s;">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-2xl font-bold text-white"><i class="fas fa-chart-simple mr-2"></i>Live Performance Monitor</h2>
                <div class="flex gap-2">
                    <span class="text-xs text-gray-400"><i class="fas fa-chart-line mr-1"></i>Real-time</span>
                    <span class="text-xs text-gray-400"><i class="fas fa-bolt mr-1"></i>Auto-refresh</span>
                </div>
            </div>
            
            <!-- Best Rating Percentage Monitor Bar -->
            <div class="mb-5">
                <div class="flex justify-between items-center mb-2">
                    <span class="text-gray-300 font-semibold"><i class="fas fa-star text-yellow-400 mr-2"></i>5-Star Excellence Rate</span>
                    <span class="text-2xl font-bold text-white" id="bestPercentage">0%</span>
                </div>
                <div class="monitor-bar-container" style="height: 48px;">
                    <div class="monitor-bar-fill" id="monitorBarFill" style="width: 0%; height: 100%;"></div>
                </div>
                <div class="flex justify-between mt-2 text-xs text-gray-400">
                    <span>Poor (0%)</span>
                    <span>Average (50%)</span>
                    <span>Excellent (100%)</span>
                </div>
            </div>
            
            <!-- Trend Indicator with Up/Down Animation -->
            <div class="grid grid-cols-3 gap-4 mb-4">
                <div class="metric-card text-center">
                    <i class="fas fa-trend-up text-xl mb-1"></i>
                    <div class="text-sm text-gray-400">Weekly Trend</div>
                    <div class="flex items-center justify-center gap-1 mt-1" id="trendIndicator">
                        <i class="fas fa-minus-circle"></i>
                        <span class="text-xl font-bold">0%</span>
                    </div>
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
                <div class="glass-card p-6 animate-in" style="animation-delay: 0.1s;">
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
                        <button type="submit" class="btn-primary w-full py-3 rounded-xl text-white font-semibold"><i class="fas fa-paper-plane mr-2"></i>Submit Review</button>
                    </form>
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
                            <div>
                                <label class="block text-gray-300 text-sm mb-1">Background URL</label>
                                <input type="text" id="bgUrl" class="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/20 text-white text-sm">
                            </div>
                            <div>
                                <label class="block text-gray-300 text-sm mb-1">Gradient Start</label>
                                <input type="color" id="gradStart" class="w-full h-10 rounded-lg cursor-pointer">
                            </div>
                            <div>
                                <label class="block text-gray-300 text-sm mb-1">Gradient Mid</label>
                                <input type="color" id="gradMid" class="w-full h-10 rounded-lg cursor-pointer">
                            </div>
                            <div>
                                <label class="block text-gray-300 text-sm mb-1">Gradient End</label>
                                <input type="color" id="gradEnd" class="w-full h-10 rounded-lg cursor-pointer">
                            </div>
                            <div class="flex items-center justify-between">
                                <label class="text-gray-300">Neon Glow Effect</label>
                                <input type="checkbox" id="neonGlow" class="w-5 h-5 cursor-pointer">
                            </div>
                            <div>
                                <label class="block text-gray-300 text-sm mb-1">Animation Intensity</label>
                                <select id="animIntensity" class="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/20 text-white">
                                    <option value="light">Light</option>
                                    <option value="medium">Medium</option>
                                    <option value="intense">Intense</option>
                                </select>
                            </div>
                            <button id="saveUiConfig" class="w-full py-2 rounded-lg bg-purple-600 text-white font-semibold mt-2 cursor-pointer"><i class="fas fa-save mr-2"></i>Save UI Settings</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Right Column -->
            <div>
                <div class="glass-card p-6 mb-6 animate-in" style="animation-delay: 0.2s;">
                    <h2 class="text-2xl font-bold mb-4 text-white"><i class="fas fa-chart-line mr-2"></i>Analytics Dashboard</h2>
                    <div class="grid grid-cols-2 gap-4 mb-4">
                        <div class="text-center"><div class="text-3xl font-bold text-purple-400" id="totalReviews">0</div><div class="text-gray-400 text-sm">Total Reviews</div></div>
                        <div class="text-center"><div class="text-3xl font-bold text-yellow-400" id="avgRating">0</div><div class="text-gray-400 text-sm">Avg Rating</div></div>
                        <div class="text-center"><div class="text-3xl font-bold text-green-400" id="verifiedCount">0</div><div class="text-gray-400 text-sm">Verified</div></div>
                        <div class="text-center"><div class="text-3xl font-bold text-blue-400" id="responseRate">0%</div><div class="text-gray-400 text-sm">Response Rate</div></div>
                    </div>
                    <canvas id="ratingChart" height="150"></canvas>
                </div>
                
                <div class="glass-card p-6 animate-in" style="animation-delay: 0.3s;">
                    <h2 class="text-2xl font-bold mb-4 text-white"><i class="fas fa-comments mr-2"></i>Community Reviews</h2>
                    <div id="reviewsList" class="space-y-3 max-h-96 overflow-y-auto"></div>
                </div>
            </div>
        </div>
    </div>
    
    <div id="toast" class="toast-notif"></div>
    
    <script>
        let currentRating = 0;
        let chart = null;
        
        document.querySelectorAll('#starRating i').forEach(star => {
            star.addEventListener('click', function() {
                currentRating = parseInt(this.dataset.rating);
                document.querySelectorAll('#starRating i').forEach((s, idx) => {
                    if(idx < currentRating) {
                        s.className = 'fas fa-star text-yellow-400';
                    } else {
                        s.className = 'far fa-star text-gray-400';
                    }
                });
                document.getElementById('rating').value = currentRating;
            });
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
            applyUIConfig(config);
        }
        
        function applyUIConfig(config) {
            document.getElementById('animatedBg').style.backgroundImage = `url(${config.background_url})`;
            const gradient = `linear-gradient(135deg, ${config.gradient_start} 0%, ${config.gradient_mid} 50%, ${config.gradient_end} 100%)`;
            document.getElementById('gradientOverlay').style.background = gradient;
            if(config.neon_glow) {
                document.querySelectorAll('.glass-card').forEach(card => card.classList.add('neon-glow'));
            } else {
                document.querySelectorAll('.glass-card').forEach(card => card.classList.remove('neon-glow'));
            }
            let particleCount = config.animation_intensity === 'light' ? 20 : config.animation_intensity === 'medium' ? 40 : 80;
            generateParticles(particleCount);
        }
        
        function generateParticles(count) {
            const container = document.getElementById('particles');
            container.innerHTML = '';
            for(let i = 0; i < count; i++) {
                const particle = document.createElement('div');
                particle.className = 'particle';
                const size = Math.random() * 8 + 2;
                particle.style.width = size + 'px';
                particle.style.height = size + 'px';
                particle.style.left = Math.random() * 100 + '%';
                particle.style.animationDuration = Math.random() * 10 + 5 + 's';
                particle.style.animationDelay = Math.random() * 10 + 's';
                container.appendChild(particle);
            }
        }
        
        async function saveUIConfig() {
            const config = {
                background_url: document.getElementById('bgUrl').value,
                gradient_start: document.getElementById('gradStart').value,
                gradient_mid: document.getElementById('gradMid').value,
                gradient_end: document.getElementById('gradEnd').value,
                neon_glow: document.getElementById('neonGlow').checked,
                animation_intensity: document.getElementById('animIntensity').value
            };
            const res = await fetch('/api/ui-config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            });
            if(res.ok) {
                applyUIConfig(config);
                showToast('UI updated with animation!', 'success');
            }
        }
        
        async function loadReviews() {
            const res = await fetch('/api/reviews');
            const data = await res.json();
            const reviews = data.reviews;
            const container = document.getElementById('reviewsList');
            if(reviews.length === 0) {
                container.innerHTML = '<div class="text-center text-gray-400 py-8"><i class="fas fa-cloud fa-3x mb-2"></i><p>No reviews yet. Be the first!</p></div>';
                return;
            }
            container.innerHTML = reviews.map(r => `
                <div class="review-card">
                    <div class="flex justify-between items-start">
                        <div><i class="fas fa-user-circle text-purple-400 mr-2"></i><span class="font-semibold text-white">${escapeHtml(r.username)}</span> ${r.verified ? '<i class="fas fa-check-circle text-green-400" title="Verified"></i>' : ''}</div>
                        <div class="text-yellow-400">${'★'.repeat(r.rating)}${'☆'.repeat(5-r.rating)}</div>
                    </div>
                    <h3 class="text-white font-bold mt-2">${escapeHtml(r.title)}</h3>
                    <p class="text-gray-300 text-sm mt-1">${escapeHtml(r.comment)}</p>
                    <div class="text-gray-500 text-xs mt-2 flex justify-between">
                        <span><i class="far fa-clock"></i> ${new Date(r.timestamp).toLocaleDateString()}</span>
                        <button onclick="deleteReview(${r.id})" class="text-red-400 hover:text-red-300 cursor-pointer"><i class="fas fa-trash-alt"></i></button>
                    </div>
                </div>
            `).join('');
        }
        
        async function deleteReview(id) {
            if(confirm('Delete this review?')) {
                await fetch(`/api/reviews/${id}`, {method: 'DELETE'});
                loadReviews();
                loadStats();
                showToast('Review deleted', 'info');
            }
        }
        
        async function loadStats() {
            const res = await fetch('/api/stats');
            const stats = await res.json();
            document.getElementById('totalReviews').innerText = stats.total;
            document.getElementById('avgRating').innerText = stats.avg_rating;
            document.getElementById('verifiedCount').innerText = stats.verified_count;
            document.getElementById('responseRate').innerText = stats.response_rate + '%';
            
            // Update Monitor Bar
            const bestPercentage = stats.best_rating_percentage;
            document.getElementById('bestPercentage').innerHTML = bestPercentage + '%';
            const barFill = document.getElementById('monitorBarFill');
            barFill.style.width = bestPercentage + '%';
            
            // Update Trend Indicator with animation
            const trend = stats.trend;
            const trendPercent = stats.trend_percentage;
            const trendDiv = document.getElementById('trendIndicator');
            if(trend === 'up') {
                trendDiv.innerHTML = `<i class="fas fa-arrow-up trend-up"></i><span class="text-xl font-bold text-green-400">+${trendPercent}%</span>`;
                gsap.fromTo('#trendIndicator', {scale: 0.8, opacity: 0}, {scale: 1, opacity: 1, duration: 0.5, ease: "back.out(1.2)"});
            } else if(trend === 'down') {
                trendDiv.innerHTML = `<i class="fas fa-arrow-down trend-down"></i><span class="text-xl font-bold text-red-400">-${trendPercent}%</span>`;
                gsap.fromTo('#trendIndicator', {scale: 0.8, opacity: 0}, {scale: 1, opacity: 1, duration: 0.5, ease: "back.out(1.2)"});
            } else {
                trendDiv.innerHTML = `<i class="fas fa-minus-circle trend-stable"></i><span class="text-xl font-bold text-yellow-400">${trendPercent}%</span>`;
            }
            
            document.getElementById('weeklyGrowth').innerHTML = (stats.weekly_growth >= 0 ? '+' : '') + stats.weekly_growth + '%';
            document.getElementById('sentimentScore').innerHTML = stats.sentiment_score;
            
            if(chart) chart.destroy();
            const ctx = document.getElementById('ratingChart').getContext('2d');
            chart = new Chart(ctx, {
                type: 'bar',
                data: { labels: ['5★', '4★', '3★', '2★', '1★'], datasets: [{ label: 'Reviews', data: [stats.five_star, stats.four_star, stats.three_star, stats.two_star, stats.one_star], backgroundColor: 'rgba(102, 126, 234, 0.6)', borderRadius: 8 }] },
                options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { labels: { color: 'white' } } } }
            });
            
            // Animate bar fill with GSAP
            gsap.fromTo('.monitor-bar-fill', {width: '0%'}, {width: bestPercentage + '%', duration: 1, ease: "power2.out"});
        }
        
        document.getElementById('reviewForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            if(currentRating === 0) { showToast('Please select a rating', 'error'); return; }
            const review = {
                username: document.getElementById('username').value,
                rating: currentRating,
                title: document.getElementById('title').value,
                comment: document.getElementById('comment').value
            };
            const res = await fetch('/api/reviews', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(review)
            });
            if(res.ok) {
                showToast('Review submitted! Thank you!', 'success');
                document.getElementById('reviewForm').reset();
                document.querySelectorAll('#starRating i').forEach(s => s.className = 'far fa-star text-gray-400');
                currentRating = 0;
                loadReviews();
                loadStats();
                gsap.fromTo('.review-card:first-child', {opacity:0, y:20}, {opacity:1, y:0, duration:0.5});
            } else showToast('Error submitting review', 'error');
        });
        
        document.getElementById('saveUiConfig').addEventListener('click', saveUIConfig);
        document.getElementById('adminToggleBtn').addEventListener('click', () => {
            document.getElementById('adminPanel').classList.toggle('open');
        });
        
        function showToast(msg, type) {
            const toast = document.getElementById('toast');
            toast.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'} mr-2"></i>${msg}`;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3000);
        }
        
        function escapeHtml(str) { 
            if(!str) return '';
            return str.replace(/[&<>]/g, function(m) { 
                if(m === '&') return '&amp;'; 
                if(m === '<') return '&lt;'; 
                if(m === '>') return '&gt;'; 
                return m;
            }); 
        }
        
        loadUIConfig();
        loadReviews();
        loadStats();
        setInterval(() => { loadStats(); loadReviews(); }, 30000);
    </script>
</body>
</html>""", status_code=200)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
