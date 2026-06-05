# Cloud Deployment Guide — Vercel + Render + Neon + Groq (all free)

This hosts the terminal online so it works **anytime, anywhere — even with your PC off**.

```
  Browser ──▶ Vercel (Next.js frontend) ──▶ Render (FastAPI backend) ──▶ Neon (Postgres)
                                                     │
                                                     └──▶ Groq (free AI) for Copilot / Alt-Data
```

**Free-tier notes (read once):**
- Render's free backend **sleeps after ~15 min idle** → the first visit after idle takes ~30–60s to wake. A free keep-alive (step 7) avoids this.
- The cloud ML lab runs the **4 lighter models** (LinearReg, RandomForest, XGBoost, LightGBM). The LSTM/Transformer + Prophet are skipped (too heavy for free RAM) — your local copy keeps all 7.
- On first boot the backend **auto-backfills 25 years of data** from the free APIs (takes a few minutes); the site is up immediately and fills in as it goes.

---

## 1. Put the code on GitHub
The repo is already git-initialised locally. Create an **empty** repo on github.com (e.g. `quant-terminal`), then:
```powershell
cd C:\Users\Amritansh.Soni\rainmumbai-terminal
git remote add origin https://github.com/<you>/quant-terminal.git
git branch -M main
git push -u origin main
```

## 2. Database — Neon (free Postgres)
1. Sign up at **neon.tech** → create a project.
2. Copy the **connection string** (looks like `postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`).
3. Keep it for step 4. (The code auto-rewrites it for the psycopg driver — paste it as-is.)

## 3. Free AI — Groq
1. Sign up at **console.groq.com** (no card) → **API Keys** → Create key.
2. Copy the key (`gsk_...`). Keep it for step 4.

## 4. Backend — Render
1. Sign up at **render.com** → **New + → Blueprint** → connect your GitHub repo.
   Render reads `render.yaml` automatically.
2. When prompted, set these env vars (marked `sync:false`):
   - `DATABASE_URL` = your Neon string (step 2)
   - `GROQ_API_KEY` = your Groq key (step 3)
   - `CORS_ORIGINS` = `*`  (tighten to your Vercel URL after step 5)
3. Deploy. Wait for it to go live; note the URL, e.g. `https://rainmumbai-backend.onrender.com`.
4. Check `https://<backend>/api/v1/health` → `{"status":"ok"}`. (Data backfills over the next few minutes.)

## 5. Frontend — Vercel
1. Sign up at **vercel.com** → **Add New → Project** → import your GitHub repo.
2. Set **Root Directory** = `frontend`.
3. Add an **Environment Variable**:
   - `NEXT_PUBLIC_API_BASE` = `https://<your-render-backend>/api/v1`
4. Deploy. You get a permanent URL like `https://quant-terminal.vercel.app`.

## 6. Lock down CORS
Back in Render → your service → Environment → set `CORS_ORIGINS` to your exact Vercel URL
(`https://quant-terminal.vercel.app`) → save (it redeploys).

## 7. Keep it awake (optional, free)
So the backend doesn't sleep: go to **cron-job.org** (free) → create a job that GETs
`https://<your-render-backend>/api/v1/health` every **10 minutes**.

---

## Done
Your terminal is now at the Vercel URL, reachable from any device, anytime — independent of your PC
and of Claude. Pushing new commits to GitHub auto-redeploys both Vercel and Render.

### Updating later
```powershell
git add -A && git commit -m "update" && git push
```
Vercel + Render redeploy automatically.

### Local vs cloud
Your local Windows setup (`scripts\start.ps1`, full 7-model ML, ngrok) still works unchanged for
development. The cloud is a separate, always-on copy that reads the same free data sources.
