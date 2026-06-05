# Hosting — run it like a website, reachable anywhere

The terminal runs as two production servers on this PC, exposed to the internet
through a Cloudflare Tunnel, and starts automatically at login.

## URLs

| Where | URL | Notes |
|-------|-----|-------|
| This PC | http://localhost:3001 | always |
| Your Wi-Fi / LAN | http://192.168.103.159:3001 | any device on the same network |
| **Anywhere (internet)** | **https://frays-outsider-frigidity.ngrok-free.dev** | permanent — never changes |

**Login:** none — the password gate is currently **disabled** (opens directly). To re-enable it,
uncomment `DASHBOARD_PASSWORD` in `frontend/.env.local`, then `npm run build` and re-run `scripts/start.ps1`.

> ✅ The public URL above is a **stable ngrok reserved domain** — it stays the same across
> reboots/logins. (If ngrok is ever unconfigured, `start.ps1` falls back to an ephemeral
> Cloudflare URL written to `logs\public-url.txt`.) To change the domain or token, re-run
> `scripts\setup-ngrok.ps1 -AuthToken <T> -Domain <D>`.

## Day-to-day commands

```powershell
# Start everything (backend :8000, frontend :3001, tunnel, data refresh)
powershell -ExecutionPolicy Bypass -File scripts\start.ps1

# LAN only, no public tunnel
powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -NoTunnel

# Stop everything
powershell -ExecutionPolicy Bypass -File scripts\stop.ps1
```

Logs live in `logs\` (`backend.*.log`, `frontend.*.log`, `tunnel.log`, `public-url.txt`).

## Auto-start at login

Already installed via `scripts\install-autostart.ps1` — it dropped a hidden launcher at:
`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\RainmumbaiTerminal.vbs`.
Delete that file to turn autostart off. Each login also runs an incremental data refresh.

## Change the password

Edit `frontend\.env.local` → `DASHBOARD_PASSWORD=...`, then rebuild and restart:

```powershell
cd frontend ; npm run build ; cd ..
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

To turn the password gate **off**, remove the `DASHBOARD_PASSWORD` line and rebuild.

## Permanent public URL (optional upgrade)

The quick tunnel is great but its URL is random and ephemeral. For a stable URL like
`https://rain.yourdomain.com`:

1. Create a free Cloudflare account and add a domain to it.
2. `tools\cloudflared.exe tunnel login` → `tunnel create rainmumbai`.
3. Map a hostname: `tunnel route dns rainmumbai rain.yourdomain.com`.
4. Run with a config file pointing the hostname at `http://localhost:3001`.

Tell me when you have a domain on Cloudflare and I'll wire this up and bake it into the
start script so the URL never changes.

## Security notes (internet-facing)

- The password gate (HTTP Basic Auth) is the only thing standing between the public URL
  and your dashboard — pick a strong password.
- Only port 3001 is exposed through the tunnel; the API (:8000) and database stay local
  (the frontend reaches them server-side on 127.0.0.1).
- The dashboard is read-only research data — no trading actions are taken.
