$adb = "E:\Android\Sdk\platform-tools\adb.exe"
$device = "192.168.76.209:5555"

Write-Host "1. Conectando via ADB..." -ForegroundColor Cyan
& $adb connect $device

Write-Host "2. Preparando permissoes do VLC..." -ForegroundColor Cyan
& $adb -s $device shell cmd appops set org.videolan.vlc RUN_IN_BACKGROUND allow
& $adb -s $device shell cmd appops set org.videolan.vlc START_FOREGROUND allow
& $adb -s $device shell pm grant org.videolan.vlc android.permission.READ_EXTERNAL_STORAGE

Write-Host "3. Limpando logcat..." -ForegroundColor Cyan
& $adb -s $device shell logcat -c

Write-Host "4. Iniciando reproducao do video 8K (8K_Thetestdata.mp4) no VLC..." -ForegroundColor Green
& $adb -s $device shell am start -W -n org.videolan.vlc/.gui.video.VideoPlayerActivity -a android.intent.action.VIEW -d "file:///sdcard/8K_Thetestdata.mp4" -t "video/mp4"

Write-Host "5. Aguardando 5 segundos para a VPU processar frames..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

Write-Host "6. Capturando screenshot da TV..." -ForegroundColor Cyan
& $adb -s $device shell screencap -p /sdcard/screen_8k_test.png
& $adb -s $device pull /sdcard/screen_8k_test.png "C:\Users\Isllan Toso\.gemini\antigravity-cli\brain\51730dae-5366-4af4-ab18-7de637c4e76e\tv_screen_8k.png"

Write-Host "7. Extraindo logs da VPU Realtek e MediaCodec..." -ForegroundColor Cyan
$logs = & $adb -s $device shell "logcat -d | grep -iE 'realtek|vdec|codec|omx|mediacodec|surfaceflinger|videoplayer|vlc|error|warn'"
$logsPath = "E:\projeto_twitchlit\tv_system_dump\dumps\test_8k_logcat.txt"
[System.IO.File]::WriteAllLines($logsPath, $logs)

Write-Host "8. Status de reproducao SurfaceFlinger..." -ForegroundColor Cyan
& $adb -s $device shell dumpsys SurfaceFlinger --latency

Write-Host "Concluido!" -ForegroundColor Green
