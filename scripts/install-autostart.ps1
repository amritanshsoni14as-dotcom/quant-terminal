<#
  Make the RAINMUMBAI Terminal auto-start at every login — no admin needed.
  Drops a hidden launcher into the per-user Startup folder. Run once.
  To remove autostart: delete the .vbs file printed below.

  (A Scheduled-Task version exists too but needs admin rights; see README.)
#>
$ErrorActionPreference = "Stop"
$root  = Split-Path $PSScriptRoot -Parent
$start = Join-Path $root "scripts\start.ps1"

$startupDir = [Environment]::GetFolderPath("Startup")
$vbs = Join-Path $startupDir "RainmumbaiTerminal.vbs"

# .vbs wrapper launches PowerShell fully hidden (no console flash).
$content = @"
Set sh = CreateObject("WScript.Shell")
sh.Run "powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File ""$start""", 0, False
"@
Set-Content -Path $vbs -Value $content -Encoding ASCII

Write-Host "Autostart installed:"
Write-Host "  $vbs"
Write-Host ""
Write-Host "The terminal (backend + frontend + tunnel + data refresh) will now"
Write-Host "launch automatically at every login."
Write-Host ""
Write-Host "Start it right now without logging out:"
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$start`""
