# Start-All: Backend + Frontend
# Verwendung: .\start-all.ps1

Write-Output "╔════════════════════════════════════════╗"
Write-Output "║ AusschussPlaner - Full Restart        ║"
Write-Output "╚════════════════════════════════════════╝"

# 1. Kill all processes
Write-Output "`n[1/5] Killing all processes..."
Get-Process python, node, chrome -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# 2. Delete old databases
Write-Output "[2/5] Deleting old databases..."
Remove-Item -Path "C:\Projekte\ausschussplaner\ausschussplaner.db" -Force -ErrorAction SilentlyContinue
Remove-Item -Path "C:\Projekte\ausschussplaner\data\ausschussplaner.db" -Force -ErrorAction SilentlyContinue

# 3. Start Backend
Write-Output "[3/5] Starting Backend on port 8000..."
Push-Location 'C:\Projekte\ausschussplaner'
$backendJob = Start-Job -ScriptBlock {
    Set-Location 'C:\Projekte\ausschussplaner'
    & '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
} -Name backend

Start-Sleep -Seconds 8

# 4. Start Frontend
Write-Output "[4/5] Starting Frontend on port 5173..."
$frontendJob = Start-Job -ScriptBlock {
    Set-Location 'C:\Projekte\ausschussplaner\frontend'
    npm run dev
} -Name frontend

Pop-Location
Start-Sleep -Seconds 8

# 5. Verify
Write-Output "[5/5] Verifying services..."
$backend = Get-Job -Name backend -ErrorAction SilentlyContinue
$frontend = Get-Job -Name frontend -ErrorAction SilentlyContinue

if ($backend) { Write-Output "✅ Backend job started" } else { Write-Output "❌ Backend job FAILED" }
if ($frontend) { Write-Output "✅ Frontend job started" } else { Write-Output "❌ Frontend job FAILED" }

Write-Output "`n╔════════════════════════════════════════╗"
Write-Output "║ ✅ Services started!                  ║"
Write-Output "║                                        ║"
Write-Output "║ Backend:  http://localhost:8000        ║"
Write-Output "║ Frontend: http://localhost:5173        ║"
Write-Output "║                                        ║"
Write-Output "║ Login: test@example.com / test123      ║"
Write-Output "╚════════════════════════════════════════╝"
