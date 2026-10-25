$ErrorActionPreference = "Stop"
$sdk = "E:\Android\Sdk"
$buildTools = (Get-ChildItem -Path "$sdk\build-tools" | Sort-Object Name -Descending | Select-Object -First 1).FullName
$zipalign = "$buildTools\zipalign.exe"
$apksigner = "$buildTools\apksigner.bat"

$decompiledDir = "E:\projeto_twitchlit\claude-tv\claude_full_decompiled"
$releaseDir = "E:\projeto_twitchlit\claude-tv\release"
$unsignedApk = "$releaseDir\claude-tv-unsigned.apk"
$alignedApk = "$releaseDir\claude-tv-aligned.apk"
$signedApk = "$releaseDir\claude-tv-1.260930-20-candidate.apk"
$keystore = "E:\projeto_twitchlit\claude-tv\keystore\claudetv-release.jks"
if (-not $env:CLAUDE_TV_KEYSTORE_PASS) { throw "Defina CLAUDE_TV_KEYSTORE_PASS antes de assinar o APK" }

if (-not (Test-Path $releaseDir)) {
    New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
}

Write-Host "=== 1. Recompiling APK with apktool ==="
& apktool.cmd b -f -o "$unsignedApk" "$decompiledDir"
if ($LASTEXITCODE -ne 0) { throw "apktool build failed" }

Write-Host "=== 2. Zipalign ==="
if (Test-Path $alignedApk) { Remove-Item -Force $alignedApk }
& $zipalign -f -p 4 "$unsignedApk" "$alignedApk"
if ($LASTEXITCODE -ne 0) { throw "zipalign failed" }

Write-Host "=== 3. Apksigner ==="
& $apksigner sign --ks "$keystore" --ks-pass env:CLAUDE_TV_KEYSTORE_PASS --key-pass env:CLAUDE_TV_KEYSTORE_PASS --out "$signedApk" "$alignedApk"
if ($LASTEXITCODE -ne 0) { throw "apksigner failed" }
& $apksigner verify --verbose "$signedApk"

Write-Host "LOCAL BUILD & SIGNING COMPLETE: $signedApk"
