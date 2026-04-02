# 🚀 SkillSwap — Start Guide

A peer-to-peer skill exchange platform with real-time video calling, chat, and collaborative whiteboard.

---

## 📋 Prerequisites

Make sure the following are installed on your machine:

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.10+ | `python --version` |
| pip | latest | `pip --version` |
| Git | any | `git --version` |

---

## ⚙️ First-Time Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd test
```

### 2. Create a Virtual Environment

```bash
# Windows
python -m venv .venv

# Mac / Linux
python3 -m venv .venv
```

### 3. Activate the Virtual Environment

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (CMD)
.venv\Scripts\activate.bat

# Mac / Linux
source .venv/bin/activate
```

> You should see `(.venv)` at the start of your terminal prompt.

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Windows note:** If `psycopg2-binary` fails (it needs PostgreSQL headers), skip it — the project uses SQLite locally:
> ```bash
> pip install django channels daphne pillow whitenoise djangorestframework dj-database-url
> ```

### 5. Apply Database Migrations

```bash
python manage.py migrate
```

### 6. (Optional) Create a Superuser

```bash
python manage.py createsuperuser
```

---

## ▶️ Running the Project

> ⚠️ **Important:** Always use **Daphne** — not `python manage.py runserver`.  
> Daphne supports WebSockets required for video calls and chat.

### Start the Server

```bash
# Windows PowerShell
$env:DEBUG='True'; daphne -b 127.0.0.1 -p 8000 skill_swap.asgi:application

# Mac / Linux
DEBUG=True daphne -b 127.0.0.1 -p 8000 skill_swap.asgi:application
```

### Open in Browser

```
http://127.0.0.1:8000
```

---

## 🧪 Testing Video Calls

1. **Open two browser windows** (one normal, one incognito / private)
2. Register / log in as **User A** in one window
3. Register / log in as **User B** in the other
4. As User A, go to User B's profile and click **Start Video Call**
5. User B will see an **incoming call popup** — click **Accept**
6. Both users will be in the video room with two-way video ✅

---

## 🗂️ Project Structure

```
skill_swap/          ← Django project settings & ASGI config
users/               ← Auth, profiles, notification WebSocket
chat/                ← Real-time chat (WebSocket)
video/               ← WebRTC video calls
dashboard/           ← Home dashboard
templates/           ← Global HTML templates (base.html, etc.)
static/              ← CSS, JS, images
media/               ← User-uploaded files (avatars, etc.)
manage.py
requirements.txt
render.yaml          ← Render.com deployment config
```

---

## 🔑 Key Environment Variables

Create a `.env` file in the project root for local overrides:

```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
```

> The project reads these automatically via `os.environ.get(...)` in `settings.py`.

---

## 🌐 WebRTC / Video Call Architecture

| Component | Technology |
|-----------|-----------|
| Signaling | Django Channels (WebSocket) |
| ASGI Server | Daphne |
| ICE/STUN | Google STUN (`stun.l.google.com`) |
| TURN (fallback) | Configured in `render.yaml` |
| Channel Layer | In-Memory (local) / Redis (production) |

> For cross-network calls (different Wi-Fi / mobile networks), a TURN server is required.  
> See `TURN_CREDENTIAL_REPLACEMENT_GUIDE.md` for setup instructions.

---

## 🚢 Deployment (Render.com)

Refer to `DEPLOYMENT_CHECKLIST.md` for full deployment steps.

Quick overview:
1. Push code to GitHub
2. Connect repo to [render.com](https://render.com)
3. Set environment variables in Render dashboard (`SECRET_KEY`, `DATABASE_URL`, `TURN_*`)
4. Render will use `render.yaml` to configure the web service automatically

---

## 🛠️ Common Issues & Fixes

| Problem | Fix |
|---------|-----|
| `ERR_CONNECTION_REFUSED` | Server not running — start Daphne |
| Page redirects to HTTPS | Missing `DEBUG=True` — add it to the run command |
| One-way video | Ensure camera permission is granted in both browsers |
| No incoming call popup | WebSocket blocked — check browser console for WS errors |
| `psycopg2` install fails | Normal on Windows local dev — SQLite is used locally |
| Port 8000 already in use | Kill old server: `Get-Process -Name "daphne" \| Stop-Process` |

---

## 📚 Other Docs in This Project

| File | Contents |
|------|----------|
| `README.md` | Full project overview |
| `DEPLOYMENT_CHECKLIST.md` | Step-by-step production deployment |
| `QUICK_REFERENCE.md` | Common commands cheat sheet |
| `TESTING_AND_TROUBLESHOOTING.md` | Debug tips for WebRTC & WebSockets |
| `TURN_CREDENTIAL_REPLACEMENT_GUIDE.md` | How to upgrade TURN servers |
| `WEBRTC_SETUP_VERIFIED.md` | WebRTC configuration reference |

---

## 📞 Support

If you hit any issues, check the browser **console (F12)** and the **Daphne terminal output** for error messages — they'll point to the root cause 99% of the time.
