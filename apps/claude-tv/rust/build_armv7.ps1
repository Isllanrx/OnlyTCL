$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$appDir = (Resolve-Path "$ScriptDir\..").Path
$repoRoot = (Resolve-Path "$appDir\..\..").Path

$sdk = if ($env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT } elseif ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { "C:\Android\Sdk" }
$ndkBin = if ($env:ANDROID_NDK_ROOT) { "$env:ANDROID_NDK_ROOT\toolchains\llvm\prebuilt\windows-x86_64\bin" } else { "$sdk\ndk\30.0.16248370\toolchains\llvm\prebuilt\windows-x86_64\bin" }
$linker = "$ndkBin\armv7a-linux-androideabi30-clang.cmd"
$ar = "$ndkBin\llvm-ar.exe"

$env:CARGO_TARGET_ARMV7_LINUX_ANDROIDEABI_LINKER = $linker
$env:CARGO_TARGET_ARMV7_LINUX_ANDROIDEABI_AR = $ar
$env:CC_armv7_linux_androideabi = $linker
$env:AR_armv7_linux_androideabi = $ar

Write-Host "Linker: $linker"
Write-Host "=== Compiling claudetv-rtk for armv7-linux-androideabi (release) ==="
cargo build --release --target armv7-linux-androideabi --manifest-path "$ScriptDir\claudetv-rtk\Cargo.toml"

if ($LASTEXITCODE -ne 0) {
    throw "Cargo cross-compile failed"
}

$soPath = "$ScriptDir\claudetv-rtk\target\armv7-linux-androideabi\release\libclaudetv_rtk.so"
if (Test-Path $soPath) {
    $size = (Get-Item $soPath).Length
    Write-Host "SUCCESS! libclaudetv_rtk.so generated ($size bytes)"
    
    # Copy to decompiled APK lib directory
    $targetLib = "$appDir\claude_full_decompiled\lib\armeabi-v7a"
    if (Test-Path (Split-Path -Parent $targetLib)) {
        if (-not (Test-Path $targetLib)) { New-Item -ItemType Directory -Force -Path $targetLib | Out-Null }
        Copy-Item $soPath -Destination $targetLib -Force
        Write-Host "Copied libclaudetv_rtk.so to $targetLib"
    }
} else {
    throw "Output .so not found at $soPath"
}
