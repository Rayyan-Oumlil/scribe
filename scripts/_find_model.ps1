Get-ChildItem -Path $env:USERPROFILE -Recurse -Directory -ErrorAction SilentlyContinue -Filter 'models--Systran--faster-whisper*' |
  Select-Object FullName
Write-Host '---'
Get-ChildItem -Path $env:USERPROFILE -Recurse -File -ErrorAction SilentlyContinue -Filter 'model.bin' |
  Where-Object { $_.Length -gt 100MB } |
  Select-Object FullName, @{N='SizeMB';E={[math]::Round($_.Length/1MB)}} |
  Format-Table -AutoSize
