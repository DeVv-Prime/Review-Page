import json
import os
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
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

class ReviewResponse(ReviewCreate):
    id: int
    timestamp: str
    verified: bool = False

class UIConfig(BaseModel):
    background_url: str = "https://images.unsplash.com/photo-1557682250-33bd709cbe85?q=80&w=2029&auto=format"
    gradient_start: str = "#0f0c29"
    gradient_mid: str = "#302b63"
    gradient_end: str = "#24243e"
    neon_glow: bool = True
    animation_intensity: str = "medium"  # light, medium, intense

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

def compute_stats(reviews: List[dict]):
    if not reviews:
        return {"total": 0, "avg_rating": 0, "five_star": 0, "four_star": 0, "three_star": 0, "two_star": 0, "one_star": 0, "verified_count": 0}
    
    total = len(reviews)
    avg_rating = sum(r["rating"] for r in reviews) / total
    five_star = sum(1 for r in reviews if r["rating"] == 5)
    four_star = sum(1 for r in reviews if r["rating"] == 4)
    three_star = sum(1 for r in reviews if r["rating"] == 3)
    two_star = sum(1 for r in reviews if r["rating"] == 2)
    one_star = sum(1 for r in reviews if r["rating"] == 1)
    verified_count = sum(1 for r in reviews if r.get("verified", False))
    
    return {
        "total": total,
        "avg_rating": round(avg_rating, 1),
        "five_star": five_star,
        "four_star": four_star,
        "three_star": three_star,
        "two_star": two_star,
        "one_star": one_star,
        "verified_count": verified_count
    }

# ---------- API Endpoints ----------
@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    """Serve the main VectoCloud review page"""
    return get_html_response()

@app.get("/api/reviews")
async def get_reviews(limit: int = 50):
    """Get all reviews"""
    reviews = load_reviews()
    # Sort by id descending (newest first)
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
        "verified": False  # In real app, could verify after email, but for demo
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
    """Get review statistics"""
    reviews = load_reviews()
    return compute_stats(reviews)

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
    """Generate the HTML page with embedded CSS/JS"""
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VectoCloud | Immersive Review Experience</title>
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
    </style>
</head>
<body>
    <div class="animated-bg" id="animatedBg"></div>
    <div class="gradient-overlay" id="gradientOverlay"></div>
    <div class="floating-particles" id="particles"></div>
    
    <div class="container">
        <!-- Header -->
        <div class="text-center mb-5 animate-in">
            <i class="fas fa-cloud-upload-alt text-6xl mb-3" style="color: #667eea;"></i>
            <h1 class="text-5xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">VectoCloud</h1>
            <p class="text-gray-300 mt-2">Where innovation meets excellence — share your experience</p>
        </div>
        
        <div class="grid md:grid-cols-3 gap-6">
            <!-- Left: Review Form -->
            <div class="md:col-span-1">
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
                
                <!-- Admin Panel Toggle -->
                <div class="mt-4">
                    <button id="adminToggleBtn" class="w-full py-2 rounded-xl bg-red-500/20 border border-red-500/40 text-red-300 font-semibold hover:bg-red-500/30 transition">
                        <i class="fas fa-crown mr-2"></i>Admin Panel
                    </button>
                </div>
                
                <!-- Admin Panel Content -->
                <div id="adminPanel" class="admin-panel mt-4">
                    <div class="glass-card p-6">
                        <h3 class="text-xl font-bold text-white mb-4"><i class="fas fa-palette mr-2"></i>UI Customization</h3>
                        <div class="space-y-3">
                            <div>
                                <label class="block text-gray-300 text-sm mb-1">Background URL (animation)</label>
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
                                <input type="checkbox" id="neonGlow" class="w-5 h-5">
                            </div>
                            <div>
                                <label class="block text-gray-300 text-sm mb-1">Animation Intensity</label>
                                <select id="animIntensity" class="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/20 text-white">
                                    <option value="light">Light</option>
                                    <option value="medium">Medium</option>
                                    <option value="intense">Intense</option>
                                </select>
                            </div>
                            <button id="saveUiConfig" class="w-full py-2 rounded-lg bg-purple-600 text-white font-semibold mt-2"><i class="fas fa-save mr-2"></i>Save UI Settings</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Right: Reviews & Stats -->
            <div class="md:col-span-2">
                <!-- Stats Dashboard -->
                <div class="glass-card p-6 mb-6 animate-in" style="animation-delay: 0.2s;">
                    <h2 class="text-2xl font-bold mb-4 text-white"><i class="fas fa-chart-line mr-2"></i>Analytics</h2>
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                        <div class="text-center"><div class="text-3xl font-bold text-purple-400" id="totalReviews">0</div><div class="text-gray-400 text-sm">Reviews</div></div>
                        <div class="text-center"><div class="text-3xl font-bold text-yellow-400" id="avgRating">0</div><div class="text-gray-400 text-sm">Avg Rating</div></div>
                        <div class="text-center"><div class="text-3xl font-bold text-green-400" id="verifiedCount">0</div><div class="text-gray-400 text-sm">Verified</div></div>
                        <div class="text-center"><div class="text-3xl font-bold text-blue-400" id="fiveStarCount">0</div><div class="text-gray-400 text-sm">5★</div></div>
                    </div>
                    <canvas id="ratingChart" height="150"></canvas>
                </div>
                
                <!-- Reviews List -->
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
        
        // Star rating handler
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
        
        // Load UI Config
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
            // Adjust particle intensity
            const intensity = config.animation_intensity;
            let particleCount = intensity === 'light' ? 20 : intensity === 'medium' ? 40 : 80;
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
                        <button onclick="deleteReview(${r.id})" class="text-red-400 hover:text-red-300"><i class="fas fa-trash-alt"></i></button>
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
            document.getElementById('fiveStarCount').innerText = stats.five_star;
            if(chart) chart.destroy();
            const ctx = document.getElementById('ratingChart').getContext('2d');
            chart = new Chart(ctx, {
                type: 'bar',
                data: { labels: ['5★', '4★', '3★', '2★', '1★'], datasets: [{ label: 'Reviews', data: [stats.five_star, stats.four_star, stats.three_star, stats.two_star, stats.one_star], backgroundColor: 'rgba(102, 126, 234, 0.6)' }] },
                options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { labels: { color: 'white' } } } }
            });
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
        
        function escapeHtml(str) { return str.replace(/[&<>]/g, function(m) { if(m === '&') return '&amp;'; if(m === '<') return '&lt;'; if(m === '>') return '&gt;'; return m;}); }
        
        loadUIConfig();
        loadReviews();
        loadStats();
        setInterval(() => { loadStats(); loadReviews(); }, 30000);
    </script>
</body>
</html>
    """, status_code=200)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
