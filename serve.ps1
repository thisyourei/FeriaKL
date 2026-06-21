# Servidor estático mínimo para FeriaKL (sin dependencias).
# Uso:  powershell -ExecutionPolicy Bypass -File serve.ps1
# Luego abre http://localhost:8080  (o http://<IP-de-tu-PC>:8080 desde el celular en la misma WiFi)

$port = 8080
$root = $PSScriptRoot
$mime = @{
  '.html'='text/html; charset=utf-8'; '.js'='text/javascript; charset=utf-8'
  '.json'='application/json; charset=utf-8'; '.css'='text/css; charset=utf-8'
  '.svg'='image/svg+xml'; '.png'='image/png'; '.ico'='image/x-icon'
}

$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://+:$port/")
try { $listener.Start() }
catch {
  Write-Host "No se pudo abrir el puerto $port. Probando solo localhost..." -ForegroundColor Yellow
  $listener = New-Object System.Net.HttpListener
  $listener.Prefixes.Add("http://localhost:$port/")
  $listener.Start()
}

Write-Host "FeriaKL sirviendo en http://localhost:$port  (Ctrl+C para detener)" -ForegroundColor Green
$ips = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -notlike '127.*' }).IPAddress
foreach ($ip in $ips) { Write-Host "   Desde el celular (misma WiFi): http://${ip}:$port" -ForegroundColor Cyan }

while ($listener.IsListening) {
  $ctx = $listener.GetContext()
  $rel = [Uri]::UnescapeDataString($ctx.Request.Url.AbsolutePath.TrimStart('/'))
  if ([string]::IsNullOrEmpty($rel)) { $rel = 'index.html' }
  $path = Join-Path $root $rel
  if (Test-Path $path -PathType Leaf) {
    $bytes = [System.IO.File]::ReadAllBytes($path)
    $ext = [System.IO.Path]::GetExtension($path).ToLower()
    if ($mime.ContainsKey($ext)) { $ctx.Response.ContentType = $mime[$ext] }
    $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
  } else {
    $ctx.Response.StatusCode = 404
    $msg = [Text.Encoding]::UTF8.GetBytes('404')
    $ctx.Response.OutputStream.Write($msg, 0, $msg.Length)
  }
  $ctx.Response.Close()
}
