<#
  RAINMUMBAI Terminal — start everything (production mode).
  Launches: FastAPI backend (:8000), Next.js frontend (:3001), and optionally a
  Cloudflare public tunnel. All run hidden; logs go to <root>\logs.

  Usage:
    powershell -ExecutionPolicy Bypass -File scripts\start.ps1            # LAN + tunnel
    powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -NoTunnel  # LAN only
#>
param([switch]$NoTunnel)

$ErrorActionPreference = "SilentlyContinue"
$root     = Split-Path $PSScriptRoot -Parent
$backend  = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$logs     = Join-Path $root "logs"
$tools    = Join-Path $root "tools"
$python   = Join-Path $backend ".venv\Scripts\python.exe"
$cflared  = Join-Path $tools "cloudflared.exe"
New-Item -ItemType Directory -Force -Path $logs | Out-Null

function Stop-Port($port) {
  Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

Write-Host "Stopping any previous instance..."
Stop-Port 8000; Stop-Port 3001
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "Starting backend (FastAPI :8000)..."
Start-Process -FilePath $python `
  -ArgumentList "-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000" `
  -WorkingDirectory $backend -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $logs "backend.out.log") `
  -RedirectStandardError  (Join-Path $logs "backend.err.log")

Write-Host "Refreshing data (incremental, background)..."
Start-Process -FilePath $python -ArgumentList "-m","app.ingest.backfill","--daily" `
  -WorkingDirectory $backend -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $logs "refresh.out.log") `
  -RedirectStandardError  (Join-Path $logs "refresh.err.log")

Write-Host "Starting frontend (Next.js :3001)..."
$npm = (Get-Command npm.cmd).Source
Start-Process -FilePath $npm `
  -ArgumentList "run","start","--","-H","0.0.0.0","-p","3001" `
  -WorkingDirectory $frontend -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $logs "frontend.out.log") `
  -RedirectStandardError  (Join-Path $logs "frontend.err.log")

$ngrok       = Join-Path $tools "ngrok.exe"
$ngrokDomain = Join-Path $tools "ngrok-domain.txt"
$usingNgrok  = $false
if (-not $NoTunnel) {
  if ((Test-Path $ngrok) -and (Test-Path $ngrokDomain)) {
    # Stable public URL via ngrok reserved domain (see scripts\setup-ngrok.ps1).
    $dom = (Get-Content $ngrokDomain -Raw).Trim()
    Write-Host "Starting ngrok tunnel ($dom)..."
    Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Process -FilePath $ngrok `
      -ArgumentList "http","--url=$dom","3001" -WindowStyle Hidden `
      -RedirectStandardOutput (Join-Path $logs "tunnel.out.log") `
      -RedirectStandardError  (Join-Path $logs "tunnel.err.log")
    $usingNgrok = $true
    Set-Content -Path (Join-Path $logs "public-url.txt") -Value "https://$dom" -Encoding ASCII
  } elseif (Test-Path $cflared) {
    # Fallback: Cloudflare quick tunnel (ephemeral URL).
    Write-Host "Starting Cloudflare tunnel (ephemeral URL)..."
    Start-Process -FilePath $cflared `
      -ArgumentList "tunnel","--no-autoupdate","--url","http://localhost:3001" `
      -WindowStyle Hidden `
      -RedirectStandardOutput (Join-Path $logs "tunnel.out.log") `
      -RedirectStandardError  (Join-Path $logs "tunnel.err.log")
  }
}

Start-Sleep -Seconds 6
$ip = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
       Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } |
       Select-Object -First 1).IPAddress
Write-Host ""
Write-Host "==================== RAINMUMBAI Terminal ===================="
Write-Host "  This PC      : http://localhost:3001"
if ($ip) { Write-Host "  On your LAN  : http://$($ip):3001" }
if (-not $NoTunnel) {
  if ($usingNgrok) {
    Write-Host "  Public URL   : https://$dom  (stable)"
  } else {
    $url = (Select-String -Path (Join-Path $logs "tunnel.err.log"),(Join-Path $logs "tunnel.out.log") `
            -Pattern "https://[-a-z0-9]+\.trycloudflare\.com" -ErrorAction SilentlyContinue |
            Select-Object -First 1).Matches.Value
    if ($url) {
      Write-Host "  Public URL   : $url  (ephemeral)"
      Set-Content -Path (Join-Path $logs "public-url.txt") -Value $url -Encoding ASCII
    } else { Write-Host "  Public URL   : (starting... see logs\public-url.txt in ~10s)" }
  }
}
Write-Host "  Login        : user 'rain' / your DASHBOARD_PASSWORD"
Write-Host "============================================================="
