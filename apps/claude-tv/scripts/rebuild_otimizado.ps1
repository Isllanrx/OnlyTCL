. "$PSScriptRoot\load_env.ps1"
$ErrorActionPreference = "Stop"

$appDir = (Resolve-Path "$PSScriptRoot\..").Path
$sdk = if ($env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT } elseif ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { "C:\Android\Sdk" }
$buildTools = (Get-ChildItem -Path "$sdk\build-tools" | Sort-Object Name -Descending | Select-Object -First 1).FullName
$zipalign = "$buildTools\zipalign.exe"
$apksigner = "$buildTools\apksigner.bat"

$decompiledDir = "$appDir\claude_full_decompiled"
$releaseDir = "$appDir\release"
$unsignedApk = "$releaseDir\claude-tv-otimizado-unsigned.apk"
$alignedApk = "$releaseDir\claude-tv-otimizado-aligned.apk"
$signedApk = "$releaseDir\claude-tv-1.260930-20-otimizado.apk"
$keystore = "$appDir\keystore\claudetv-release.jks"
$keystorePass = if ($env:CLAUDE_TV_KEYSTORE_PASS) { $env:CLAUDE_TV_KEYSTORE_PASS } else { "claudetv2026" }

if (-not (Test-Path $releaseDir)) {
    New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
}

Write-Host "=== 1. Recompiling OTIMIZADO APK with apktool ==="
& apktool.cmd b -f -o "$unsignedApk" "$decompiledDir"
if ($LASTEXITCODE -ne 0) { throw "apktool build failed" }

Write-Host "=== 2. Zipalign ==="
if (Test-Path $alignedApk) { Remove-Item -Force $alignedApk }
& $zipalign -f -p 4 "$unsignedApk" "$alignedApk"
if ($LASTEXITCODE -ne 0) { throw "zipalign failed" }

Write-Host "=== 3. Apksigner ==="
& $apksigner sign --ks "$keystore" --ks-pass "pass:$keystorePass" --key-pass "pass:$keystorePass" --out "$signedApk" "$alignedApk"
if ($LASTEXITCODE -ne 0) { throw "apksigner failed" }
& $apksigner verify --verbose "$signedApk"

Write-Host "OTIMIZADO BUILD & SIGNING COMPLETE: $signedApk"
