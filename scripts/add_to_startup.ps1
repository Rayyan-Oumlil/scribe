# Registers scribe to run at login with admin rights via Task Scheduler.
# Run this script once as Administrator.

$pyw    = 'C:\Users\rayya\AppData\Local\Programs\Python\Python311\pythonw.exe'
$script = 'C:\Users\rayya\Desktop\scribe\app.py'

schtasks /delete /tn "Scribe" /f 2>$null

schtasks /create `
    /tn  "Scribe" `
    /tr  "`"$pyw`" -X utf8 `"$script`"" `
    /sc  onlogon `
    /rl  highest `
    /f

if ($LASTEXITCODE -eq 0) {
    Write-Host 'Done. Scribe will start automatically on next login.'
    Write-Host 'To remove: schtasks /delete /tn Scribe /f'
} else {
    Write-Host 'Registration failed.'
}
