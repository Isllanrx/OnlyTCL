$ndkBin = "E:\Android\Sdk\ndk\30.0.16248370\toolchains\llvm\prebuilt\windows-x86_64\bin"
$linker = "$ndkBin\armv7a-linux-androideabi30-clang.cmd"
$ar = "$ndkBin\llvm-ar.exe"

$env:CARGO_TARGET_ARMV7_LINUX_ANDROIDEABI_LINKER = $linker
$env:CARGO_TARGET_ARMV7_LINUX_ANDROIDEABI_AR = $ar
$env:CC_armv7_linux_androideabi = $linker
$env:AR_armv7_linux_androideabi = $ar

Write-Host "Linker: $linker"
Write-Host "=== Compiling claudetv-rtk for armv7-linux-androideabi (release) ==="
cargo build --release --target armv7-linux-androideabi --manifest-path "E:\projeto_twitchlit\claude-tv\rust\claudetv-rtk\Cargo.toml"

if ($LASTEXITCODE -ne 0) {
    throw "Cargo cross-compile failed"
}

$soPath = "E:\projeto_twitchlit\claude-tv\rust\claudetv-rtk\target\armv7-linux-androideabi\release\libclaudetv_rtk.so"
if (Test-Path $soPath) {
    $size = (Get-Item $soPath).Length
    Write-Host "SUCCESS! libclaudetv_rtk.so generated ($size bytes)"
    
    # Copy to decompiled APK lib directory
    $targetLib = "E:\projeto_twitchlit\claude-tv\claude_full_decompiled\lib\armeabi-v7a"
    Copy-Item $soPath -Destination $targetLib -Force
    Write-Host "Copied libclaudetv_rtk.so to $targetLib"
} else {
    throw "Output .so not found at $soPath"
}
