# BN Collateral Tracker

A shared Kanban board for BusinessNext marketing collateral tracking.

## Deploy to Render (Free)

1. Push this folder to a GitHub repo (can be private)
2. Go to render.com → New → Web Service
3. Connect your GitHub repo
4. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --preload`
   - **Instance Type:** Free
5. Click Deploy — your team URL will be: `https://your-app-name.onrender.com`

## Features
- Kanban board with 7 stages: Not Started → Research → Ideation → Draft → Design In Progress → Review → Closed
- Drag-and-drop cards between stages
- Filter by Category (Product / Customer / Analyst) and Type (Video / Pitch Deck etc.)
- Add, edit, delete cards
- Shared state — all team members see the same board
- Pre-loaded with 19 items from the BN tracker CSV

## Making Changes / New Features
Come back to Claude, describe what you want changed, get an updated app.py, push to GitHub → Render auto-redeploys.
