# Wire0 launcher — uses Python 3.13 explicitly
$py = "C:\Users\i5aan\AppData\Local\Programs\Python\Python313\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

& $py -m pip install -e "$PSScriptRoot" -q 2>$null
& $py -m wire0 @args
