# publish-grafana-edges.ps1
# This script sets required env vars and runs tools/publish_grafana_edges.py
# It supports BOTH:
#   - Single edge  (EDGE=edge-d, TENANT=p4)
#   - Multiple edges (EDGE=edge-a,edge-b,edge-c, TENANT=edge-a:p1,edge-b:p2,edge-c:p3)

param(
    [string]$GrafanaUrl   = "http://localhost:8000",
    #[string]$GrafanaUrl   = "https://grafana.localhost",
    [string]$MimirUrl     = "https://mimir:9009/prometheus",
    [string]$TemplatePath = "central/grafana/dashboards/Test-B.json",
    [string]$FolderTitle  = "Edges",
    [string]$DatasourcePrefix = "Mimir - "
)

Write-Host "=== Grafana Edge Publisher ===" -ForegroundColor Cyan

# ── Required static env vars ─────────────────────────────────────────────

$env:GRAFANA_URL       = $GrafanaUrl
$env:MIMIR_URL         = $MimirUrl
$env:TEMPLATE_PATH     = $TemplatePath
$env:FOLDER_TITLE      = $FolderTitle
$env:DATASOURCE_PREFIX = $DatasourcePrefix

# TLS / mTLS paths (you said these are required)
$env:CA_CERT_PATH      = "certs/ca.crt"
$env:CLIENT_CERT_PATH  = "central/certs/grafana.crt"
$env:CLIENT_KEY_PATH   = "central/certs/grafana.key"

Write-Host "Using:"
Write-Host "  GRAFANA_URL       = $($env:GRAFANA_URL)"
Write-Host "  MIMIR_URL         = $($env:MIMIR_URL)"
Write-Host "  TEMPLATE_PATH     = $($env:TEMPLATE_PATH)"
Write-Host "  FOLDER_TITLE      = $($env:FOLDER_TITLE)"
Write-Host "  DATASOURCE_PREFIX = $($env:DATASOURCE_PREFIX)"
Write-Host "  CA_CERT_PATH      = $($env:CA_CERT_PATH)"
Write-Host "  CLIENT_CERT_PATH  = $($env:CLIENT_CERT_PATH)"
Write-Host "  CLIENT_KEY_PATH   = $($env:CLIENT_KEY_PATH)"
Write-Host ""

# ── GRAFANA_TOKEN handling ───────────────────────────────────────────────

if (-not $env:GRAFANA_TOKEN) {
    Write-Host "GRAFANA_TOKEN is not set in the environment."
    Write-Host "You need a Grafana API token with Admin/Editor rights."
    $token = Read-Host -Prompt "Paste Grafana API token"
    $env:GRAFANA_TOKEN = $token
    Write-Host "GRAFANA_TOKEN set for this session." -ForegroundColor Yellow
} else {
    $options = Read-Host "There already exist a Grafana Token do you want to continoue using it (Y/N)"
    if($options -match '^[Yy]')
    {
        Write-Host "Using existing GRAFANA_TOKEN from environment." -ForegroundColor Green
    }
    elseif ($options -match '^[Nn]')
    {
        $token = Read-Host -Prompt "Paste Grafana API token"
        $env:GRAFANA_TOKEN = $token
    }
    
}

Write-Host ""

# ── Ask user: single edge vs multiple edges ──────────────────────────────

$mode = Read-Host "Are you adding multiple edges and tenants? (y/n)"

if ($mode -match '^[Yy]') {
    Write-Host ""
    Write-Host "MULTI-EDGE MODE" -ForegroundColor Cyan
    Write-Host "You will set:"
    Write-Host "  EDGE   = comma-separated list of edges"
    Write-Host "           e.g. edge-a,edge-b,edge-c"
    Write-Host "  TENANT = comma-separated edge:tenant pairs"
    Write-Host "           e.g. edge-a:p1,edge-b:p2,edge-c:p3"
    Write-Host ""

    $edgeInput = Read-Host "Enter EDGE value (e.g. edge-a,edge-b,edge-c)"
    $tenantInput = Read-Host "Enter TENANT value (e.g. edge-a:p1,edge-b:p2,edge-c:p3)"

    $env:EDGE   = $edgeInput
    $env:TENANT = $tenantInput
}
else {
    Write-Host ""
    Write-Host "SINGLE-EDGE MODE" -ForegroundColor Cyan
    Write-Host "You will set:"
    Write-Host "  EDGE   = single edge name"
    Write-Host "           e.g. edge-d"
    Write-Host "  TENANT = tenant id for that edge"
    Write-Host "           e.g. p4"
    Write-Host ""

    $edgeInput = Read-Host "Enter EDGE value (single edge, e.g. edge-d)"
    $tenantInput = Read-Host "Enter TENANT value for that edge (e.g. p4)"

    $env:EDGE   = $edgeInput
    $env:TENANT = $tenantInput
}

Write-Host ""
Write-Host "Final values:" -ForegroundColor Cyan
Write-Host "  EDGE   = $($env:EDGE)"
Write-Host "  TENANT = $($env:TENANT)"
Write-Host ""

# ── Confirm and run Python script ────────────────────────────────────────

$confirm = Read-Host "Run tools/publish_grafana_edges.py with these settings? (y/n)"
if ($confirm -notmatch '^[Yy]') {
    Write-Host "Aborted by user."
    exit 0
}

Write-Host ""
Write-Host "Running: python .\tools\publish_grafana_edges.py" -ForegroundColor Yellow
Write-Host ""

python .\tools\publish_grafana_edges.py

Write-Host ""
Write-Host "Done." -ForegroundColor Green
