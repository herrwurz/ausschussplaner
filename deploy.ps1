<#
.SYNOPSIS
    Prueft, committet und veroeffentlicht den aktuellen Stand.
.DESCRIPTION
    Ablauf: Tests -> Frontend-Build -> Uebersicht -> Bestaetigung -> Commit -> Push.
    Coolify zieht den neuen Stand anschliessend selbst (Auto-Deploy) oder wird
    ueber einen Deploy-Hook angestossen.

    Der Deploy-Hook gehoert NICHT ins Repository. Einmalig setzen mit:
      [Environment]::SetEnvironmentVariable('COOLIFY_DEPLOY_HOOK','<URL>','User')
    Danach Terminal neu starten.
.EXAMPLE
    .\deploy.ps1 -Message "Parteien korrigiert"
    .\deploy.ps1 -DryRun
    .\deploy.ps1 -SkipTests -Message "nur Doku"
#>

[CmdletBinding()]
param(
    [string]$Message,
    [switch]$SkipTests,
    [switch]$SkipBuild,
    [switch]$DryRun
)

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

function Write-Step { param($m) Write-Host "`n=== $m ===" -ForegroundColor Cyan }
function Write-Ok   { param($m) Write-Host "  [OK]   $m" -ForegroundColor Green }
function Write-Skip { param($m) Write-Host "  [SKIP] $m" -ForegroundColor DarkGray }
function Write-Warn { param($m) Write-Host "  [!]    $m" -ForegroundColor Yellow }
function Write-Info { param($m) Write-Host "  ->     $m" -ForegroundColor Gray }
function Write-Fail { param($m) Write-Host "  [FEHLER] $m" -ForegroundColor Red }

function Confirm-Step {
    param([string]$Question)
    $a = Read-Host "  $Question [j/N]"
    return ($a -match '^[jJyY]')
}

# ---------------------------------------------------------------- Vorbedingungen

Write-Host @"

+------------------------------------------------------+
|   AusschussPlaner - Deploy                            |
+------------------------------------------------------+
"@ -ForegroundColor Magenta

if ($DryRun) { Write-Warn "DRY-RUN: es wird nichts committet oder gepusht." }

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path (Join-Path $root '.git'))) {
    Write-Fail "Kein Git-Repository in $root"
    exit 1
}

Write-Step "1. Repository-Status"

$branch = (git rev-parse --abbrev-ref HEAD).Trim()
Write-Info "Branch: $branch"

# Nicht versehentlich von einem Feature-Branch deployen
$mainBranches = @('main', 'master')
if ($mainBranches -notcontains $branch) {
    Write-Warn "Aktueller Branch ist nicht main/master."
    if (-not (Confirm-Step "Trotzdem von '$branch' deployen?")) { exit 0 }
}

# Sind wir hinter dem Remote?
git fetch --quiet 2>$null
$behind = (git rev-list --count "HEAD..origin/$branch" 2>$null)
if ($behind -and [int]$behind -gt 0) {
    Write-Warn "Lokaler Stand ist $behind Commit(s) hinter origin/$branch."
    Write-Info "Erst 'git pull' ausfuehren, sonst entsteht ein unnoetiger Merge."
    if (-not (Confirm-Step "Trotzdem fortfahren?")) { exit 0 }
}

$dirty = @(git status --porcelain)
if ($dirty.Count -eq 0) {
    Write-Skip "Keine lokalen Aenderungen"
} else {
    Write-Info "$($dirty.Count) geaenderte Datei(en):"
    $dirty | Select-Object -First 20 | ForEach-Object { Write-Host "         $_" -ForegroundColor DarkGray }
    if ($dirty.Count -gt 20) { Write-Info "... und $($dirty.Count - 20) weitere" }
}

# Warnen, wenn sensible Dateien mitgehen wuerden
$sensitive = $dirty | Where-Object { $_ -match '\.env$|\.db$|\.sqlite|secret|credential' }
if ($sensitive) {
    Write-Warn "Moeglicherweise sensible Dateien im Staging-Bereich:"
    $sensitive | ForEach-Object { Write-Host "         $_" -ForegroundColor Yellow }
    Write-Info "Diese gehoeren normalerweise in .gitignore."
    if (-not (Confirm-Step "Wirklich fortfahren?")) { exit 0 }
}

# ---------------------------------------------------------------- Tests

Write-Step "2. Tests"

if ($SkipTests) {
    Write-Skip "Uebersprungen (-SkipTests)"
} else {
    $pytest = Join-Path $root '.venv\Scripts\pytest.exe'
    if (-not (Test-Path $pytest)) {
        Write-Warn "pytest nicht gefunden unter .venv - uebersprungen"
    } else {
        Write-Info "pytest laeuft ..."
        & $pytest -q
        if ($LASTEXITCODE -ne 0) {
            Write-Fail "Tests fehlgeschlagen - Deploy abgebrochen"
            Write-Info "Mit -SkipTests laesst sich das umgehen, aber pruefe erst die Ursache."
            exit 1
        }
        Write-Ok "Alle Tests bestanden"
    }
}

# ---------------------------------------------------------------- Frontend

Write-Step "3. Frontend-Build"

$frontend = Join-Path $root 'frontend'
if ($SkipBuild) {
    Write-Skip "Uebersprungen (-SkipBuild)"
} elseif (-not (Test-Path (Join-Path $frontend 'package.json'))) {
    Write-Skip "Kein Frontend gefunden"
} else {
    Write-Info "npm run build ..."
    Push-Location $frontend
    npm run build
    $buildOk = ($LASTEXITCODE -eq 0)
    Pop-Location

    if (-not $buildOk) {
        Write-Fail "Frontend-Build fehlgeschlagen - Deploy abgebrochen"
        exit 1
    }
    Write-Ok "Frontend gebaut"
}

# ---------------------------------------------------------------- Commit

Write-Step "4. Commit"

$dirty = @(git status --porcelain)

if ($dirty.Count -eq 0) {
    Write-Skip "Nichts zu committen"
} else {
    if (-not $Message) {
        Write-Info "Kurze Beschreibung der Aenderung:"
        $Message = Read-Host "  Commit-Nachricht"
        if ([string]::IsNullOrWhiteSpace($Message)) {
            Write-Fail "Ohne Nachricht kein Commit"
            exit 1
        }
    }

    if ($DryRun) {
        Write-Info "[DryRun] git add -A; git commit -m `"$Message`""
    } else {
        git add -A
        git commit -m "$Message"
        if ($LASTEXITCODE -ne 0) {
            Write-Fail "Commit fehlgeschlagen"
            exit 1
        }
        Write-Ok "Committet: $Message"
    }
}

# ---------------------------------------------------------------- Push

Write-Step "5. Veroeffentlichen"

$ahead = (git rev-list --count "origin/$branch..HEAD" 2>$null)
if (-not $ahead) { $ahead = 0 }

if ([int]$ahead -eq 0) {
    Write-Skip "Nichts zu pushen - Remote ist aktuell"
    exit 0
}

Write-Info "$ahead Commit(s) werden veroeffentlicht:"
git log --oneline "origin/$branch..HEAD" | ForEach-Object {
    Write-Host "         $_" -ForegroundColor DarkGray
}

Write-Host ""
Write-Warn "Der naechste Schritt veraendert das Produktivsystem."
if (-not (Confirm-Step "Nach origin/$branch pushen?")) {
    Write-Info "Abgebrochen. Die Commits bleiben lokal erhalten."
    exit 0
}

if ($DryRun) {
    Write-Info "[DryRun] git push origin $branch"
} else {
    git push origin $branch
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Push fehlgeschlagen"
        exit 1
    }
    Write-Ok "Nach origin/$branch veroeffentlicht"
}

# ---------------------------------------------------------------- Coolify

Write-Step "6. Coolify"

$hook = $env:COOLIFY_DEPLOY_HOOK

if (-not $hook) {
    Write-Info "Kein Deploy-Hook hinterlegt."
    Write-Info "Bei aktiviertem Auto-Deploy startet Coolify jetzt von selbst."
    Write-Info "Andernfalls in Coolify auf 'Redeploy' klicken - oder einmalig setzen:"
    Write-Info "  [Environment]::SetEnvironmentVariable('COOLIFY_DEPLOY_HOOK','<URL>','User')"
} elseif ($DryRun) {
    Write-Info "[DryRun] Deploy-Hook wuerde aufgerufen"
} else {
    Write-Info "Rufe Deploy-Hook auf ..."
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $resp = Invoke-RestMethod -Uri $hook -Method Post -TimeoutSec 30
        Write-Ok "Deployment angestossen"
        if ($resp) { Write-Info ($resp | ConvertTo-Json -Compress) }
    } catch {
        Write-Warn "Hook-Aufruf fehlgeschlagen: $($_.Exception.Message)"
        Write-Info "Der Push war erfolgreich - in Coolify manuell 'Redeploy' ausloesen."
    }
}

# ---------------------------------------------------------------- Abschluss

Write-Host @"

Fertig.

  Coolify-Dashboard oeffnen und die Deployment-Logs pruefen.
  Danach die Anwendung im Browser testen.

Hinweis zu Daten:
  seed_data() laeuft nur bei LEERER Datenbank. Aenderungen an
  Seed-Daten (Personen, Parteien, Mitgliedschaften) erreichen die
  Produktion daher NICHT automatisch - dafuer braucht es ein
  Migrationsskript oder einen manuellen Eingriff.

"@ -ForegroundColor Magenta
