<# Stop the RAINMUMBAI Terminal (backend, frontend, tunnel). #>
$ErrorActionPreference = "SilentlyContinue"
function Stop-Port($port) {
  Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}
Stop-Port 8000
Stop-Port 3001
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "RAINMUMBAI Terminal stopped."
