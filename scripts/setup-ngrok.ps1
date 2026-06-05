<#
  One-time setup for a STABLE public URL via ngrok (free, no domain needed).

  Steps:
    1. Create a free account at https://dashboard.ngrok.com/signup
    2. Copy your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken
    3. Claim your free static domain at https://dashboard.ngrok.com/domains
       (looks like  xxxx-yyyy-zzzz.ngrok-free.app)
    4. Run:
         powershell -ExecutionPolicy Bypass -File scripts\setup-ngrok.ps1 -AuthToken <TOKEN> -Domain <DOMAIN>
    5. Restart:  powershell -ExecutionPolicy Bypass -File scripts\start.ps1

  After this, start.ps1 always serves the dashboard at https://<DOMAIN> — it never changes.
#>
param(
  [Parameter(Mandatory = $true)][string]$AuthToken,
  [Parameter(Mandatory = $true)][string]$Domain
)
$ErrorActionPreference = "Stop"
$root  = Split-Path $PSScriptRoot -Parent
$tools = Join-Path $root "tools"
$ngrok = Join-Path $tools "ngrok.exe"

if (-not (Test-Path $ngrok)) { throw "ngrok.exe not found in $tools" }

& $ngrok config add-authtoken $AuthToken
$Domain = $Domain -replace '^https?://', ''
Set-Content -Path (Join-Path $tools "ngrok-domain.txt") -Value $Domain -Encoding ASCII

Write-Host "ngrok configured. Stable URL will be: https://$Domain"
Write-Host "Now restart:  powershell -ExecutionPolicy Bypass -File scripts\start.ps1"
