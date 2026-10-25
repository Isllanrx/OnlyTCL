$sdk = "E:\Android\Sdk"
$androidJar = (Get-ChildItem -Path "$sdk\platforms" -Filter "android.jar" -Recurse | Select-Object -First 1).FullName
$d8 = (Get-ChildItem -Path "$sdk\build-tools" -Filter "d8.bat" -Recurse | Select-Object -First 1).FullName

Write-Host "android.jar: $androidJar"
Write-Host "d8: $d8"

$buildDir = "E:\projeto_twitchlit\claude-tv\build_tmp"
if (-not ([IO.Path]::GetFullPath($buildDir).StartsWith("E:\projeto_twitchlit\claude-tv\", [StringComparison]::OrdinalIgnoreCase))) {
    throw "Unsafe build target"
}
$decompiledDir = "E:\projeto_twitchlit\claude-tv\claude_full_decompiled"
if (-not (Test-Path -LiteralPath $decompiledDir)) {
    $baseApk = "E:\projeto_twitchlit\claude-tv\release\claude-tv-1.260930-20-release.apk"
    if (-not (Test-Path -LiteralPath $baseApk)) { throw "APK base não encontrado: $baseApk" }
    & apktool.cmd d -f -o $decompiledDir $baseApk
    if ($LASTEXITCODE -ne 0) { throw "Falha ao decodificar o APK base" }
}
if (Test-Path $buildDir) { Remove-Item -Recurse -Force $buildDir }
New-Item -ItemType Directory -Force -Path $buildDir | Out-Null

Write-Host "=== 1. Compiling TV integration ==="
javac -encoding UTF-8 -cp $androidJar -d $buildDir "E:\projeto_twitchlit\claude-tv\src\ClaudeTvHelper.java" "E:\projeto_twitchlit\claude-tv\src\ClaudeTvAccessibilityService.java" "E:\projeto_twitchlit\claude-tv\src\VoicePanel.java"
if ($LASTEXITCODE -ne 0) { throw "javac failed" }

Write-Host "=== 2. Running D8 ==="
$classes = (Get-ChildItem -Path $buildDir -Recurse -Filter "*.class").FullName
& $d8 --min-api 30 --output $buildDir $classes
if ($LASTEXITCODE -ne 0) { throw "d8 failed" }

Write-Host "=== 3. Wrapping in dummy zip and decompiling to Smali with apktool ==="
python -c "import zipfile, os; z = zipfile.ZipFile(r'$buildDir\dummy.zip', 'w'); z.write(r'$buildDir\classes.dex', 'classes.dex'); z.close()"

& apktool.cmd d -f -o "$buildDir\smali_out" "$buildDir\dummy.zip"

Write-Host "=== 4. Copying smali to decompiled project ==="
$targetDir = "E:\projeto_twitchlit\claude-tv\claude_full_decompiled\smali\com\anthropic\claude\tv"
if (-not ([IO.Path]::GetFullPath($targetDir).StartsWith("E:\projeto_twitchlit\claude-tv\claude_full_decompiled\smali\", [StringComparison]::OrdinalIgnoreCase))) {
    throw "Unsafe smali target"
}
Get-ChildItem -LiteralPath $targetDir -Filter "*.smali" -File | ForEach-Object {
    Remove-Item -LiteralPath $_.FullName -Force
}
Get-ChildItem -Path "$buildDir\smali_out\smali\com\anthropic\claude\tv" -Filter "*.smali" | ForEach-Object {
    Copy-Item $_.FullName -Destination $targetDir -Force
    Write-Host "Copied: $($_.Name)"
}

Write-Host "=== 5. Applying/validating TV overlay and composer patches ==="
python "E:\projeto_twitchlit\claude-tv\src\patches\apply_tv_hooks.py" "E:\projeto_twitchlit\claude-tv\claude_full_decompiled"
if ($LASTEXITCODE -ne 0) { throw "apply_tv_hooks.py failed (hooks inconsistentes com ClaudeTvHelper)" }

Write-Host "BUILD SUCCESSFUL!"
