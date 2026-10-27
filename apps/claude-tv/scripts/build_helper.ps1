. "$PSScriptRoot\load_env.ps1"

$appDir = (Resolve-Path "$PSScriptRoot\..").Path
$sdk = if ($env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT } elseif ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { "C:\Android\Sdk" }
$androidJar = (Get-ChildItem -Path "$sdk\platforms" -Filter "android.jar" -Recurse | Select-Object -First 1).FullName
$d8 = (Get-ChildItem -Path "$sdk\build-tools" -Filter "d8.bat" -Recurse | Select-Object -First 1).FullName

Write-Host "android.jar: $androidJar"
Write-Host "d8: $d8"

$buildDir = "$appDir\build_tmp"
if (-not ([IO.Path]::GetFullPath($buildDir).StartsWith("$appDir\", [StringComparison]::OrdinalIgnoreCase))) {
    throw "Unsafe build target"
}
$decompiledDir = "$appDir\claude_full_decompiled"
if (-not (Test-Path -LiteralPath $decompiledDir)) {
    $baseApk = "$appDir\release\claude-tv-1.260930-20-release.apk"
    if (-not (Test-Path -LiteralPath $baseApk)) { throw "APK base não encontrado: $baseApk" }
    & apktool.cmd d -f -o $decompiledDir $baseApk
    if ($LASTEXITCODE -ne 0) { throw "Falha ao decodificar o APK base" }
}
if (Test-Path $buildDir) { Remove-Item -Recurse -Force $buildDir }
New-Item -ItemType Directory -Force -Path $buildDir | Out-Null

Write-Host "=== 1. Compiling TV integration ==="
javac -encoding UTF-8 -cp $androidJar -d $buildDir "$appDir\src\ClaudeTvHelper.java" "$appDir\src\ClaudeTvAccessibilityService.java" "$appDir\src\VoicePanel.java"
if ($LASTEXITCODE -ne 0) { throw "javac failed" }

Write-Host "=== 2. Running D8 ==="
$classes = (Get-ChildItem -Path $buildDir -Recurse -Filter "*.class").FullName
& $d8 --min-api 30 --output $buildDir $classes
if ($LASTEXITCODE -ne 0) { throw "d8 failed" }

Write-Host "=== 3. Wrapping in dummy zip and decompiling to Smali with apktool ==="
python -c "import zipfile, os; z = zipfile.ZipFile(r'$buildDir\dummy.zip', 'w'); z.write(r'$buildDir\classes.dex', 'classes.dex'); z.close()"

& apktool.cmd d -f -o "$buildDir\smali_out" "$buildDir\dummy.zip"

Write-Host "=== 4. Copying smali to decompiled project ==="
$targetDir = "$decompiledDir\smali\com\anthropic\claude\tv"
if (-not ([IO.Path]::GetFullPath($targetDir).StartsWith("$decompiledDir\smali\", [StringComparison]::OrdinalIgnoreCase))) {
    throw "Unsafe smali target"
}
Get-ChildItem -LiteralPath $targetDir -Filter "*.smali" -File | ForEach-Object {
    Remove-Item -LiteralPath $_.FullName -Force
}
Get-ChildItem -Path "$buildDir\smali_out\smali\com\anthropic\claude\tv" -Filter "*.smali" | ForEach-Object {
    Copy-Item $_.FullName -Destination $targetDir -Force
}

Write-Host "=== 5. Applying bytecode patches to Claude TV classes ==="
python "$appDir\src\patches\apply_tv_hooks.py" "$decompiledDir"
if ($LASTEXITCODE -ne 0) { throw "Falha ao aplicar hooks do Claude TV" }

Write-Host "=== Build helper completed successfully ==="
