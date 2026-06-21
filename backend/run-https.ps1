# Levanta FeriaKL en HTTPS (necesario para usar la cámara desde el celular).
# Uso:  powershell -ExecutionPolicy Bypass -File run-https.ps1
# PC:      https://localhost:8443
# Celular: https://<IP-de-tu-PC>:8443   (misma WiFi; acepta el aviso de certificado)

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$py = Join-Path $here ".venv\Scripts\python.exe"

$ips = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
  $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.*'
}).IPAddress
Write-Host "FeriaKL (HTTPS) iniciando..." -ForegroundColor Green
Write-Host "  PC:      https://localhost:8443"
foreach ($ip in $ips) { Write-Host "  Celular: https://${ip}:8443" -ForegroundColor Cyan }
Write-Host ""

& $py -m uvicorn app.main:app --host 0.0.0.0 --port 8443 `
  --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem
