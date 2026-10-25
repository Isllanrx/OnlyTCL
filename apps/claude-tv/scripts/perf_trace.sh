#!/usr/bin/env bash
# Captura Perfetto + framestats de um cenário do Claude na TV. Uso: perf_trace.sh <rodada> <cold|warm|overlay|voice>
# Ver .claude/skills/claude-tv-perf/SKILL.md.
set -u
export MSYS_NO_PATHCONV=1
RUN=${1:?rodada}; SC=${2:?cenario}
ADB="${ADB:-/e/Android/Sdk/platform-tools/adb.exe} -s ${TV:-192.168.76.209:5555}"
PKG=com.anthropic.claude
DIR="$(cd "$(dirname "$0")" && pwd)"
OUT=".tv-dumps/perf/$RUN"; mkdir -p "$OUT"
REMOTE=/data/misc/perfetto-traces/claude_$SC.pftrace

$ADB shell input keyevent HOME < /dev/null; sleep 2
# force-stop desvincula o Claude como assistente; am kill só mata o processo em segundo plano.
[ "$SC" = cold ] && { $ADB shell am kill $PKG < /dev/null; sleep 3; }
$ADB shell "dumpsys gfxinfo $PKG reset" < /dev/null > /dev/null
$ADB shell "dumpsys meminfo $PKG" < /dev/null > "$OUT/${SC}_mem_before.txt"
$ADB shell "rm -f $REMOTE"
$ADB shell perfetto --background --txt -c - -o $REMOTE < "$DIR/perf/claude_trace.pbtxt" > /dev/null
sleep 2

T0=$(date +%s%3N)
case "$SC" in
  cold|warm) $ADB shell am start -W -n $PKG/.mainactivity.MainActivity < /dev/null > "$OUT/${SC}_amstart.txt" ;;
  overlay)   $ADB shell am start -W -a android.intent.action.ASSIST < /dev/null > "$OUT/${SC}_amstart.txt" ;;
  voice)     $ADB shell am start -W -n $PKG/.mainactivity.MainActivity \
               --es com.anthropic.claude.intent.extra.START_CHAT_MODE BELL_MODE \
               --es com.anthropic.claude.intent.extra.START_CHAT_VOICE_ENTRY_SOURCE APP_INTENT < /dev/null > "$OUT/${SC}_amstart.txt" ;;
esac
echo "disparo_epoch_ms=$T0" >> "$OUT/${SC}_amstart.txt"

for i in $(seq 1 30); do $ADB shell pidof perfetto < /dev/null | grep -q . || break; sleep 1; done
$ADB shell "dumpsys gfxinfo $PKG framestats" < /dev/null > "$OUT/${SC}_framestats.txt"
L=$($ADB shell dumpsys SurfaceFlinger --list < /dev/null | tr -d '\r' | grep "^[0-9a-f]* $PKG/" | grep -v -E "ActivityRecord|InputSink" | head -1)
[ -n "$L" ] && $ADB shell "dumpsys SurfaceFlinger --latency '$L'" < /dev/null > "$OUT/${SC}_sf_latency.txt"
$ADB shell "dumpsys meminfo $PKG" < /dev/null > "$OUT/${SC}_mem_after.txt"
$ADB pull $REMOTE "$OUT/$SC.pftrace" > /dev/null
$ADB shell input keyevent BACK < /dev/null; $ADB shell input keyevent HOME < /dev/null
grep -E "TotalTime|WaitTime|LaunchState" "$OUT/${SC}_amstart.txt"
ls -la "$OUT/$SC.pftrace"
