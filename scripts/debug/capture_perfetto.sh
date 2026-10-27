#!/usr/bin/env bash
ADB="${ADB:-adb} -s ${TV:-${TV_IP:-192.168.1.100}:5555}"
OUT="${1:-trace_tcl.pftrace}"
echo "Iniciando captura de 10s via Perfetto na TV TCL..."
$ADB shell "perfetto -c - --txt -o /data/misc/perfetto-traces/trace.pftrace" <<EOF
buffers: { size_kb: 32768 }
data_sources: {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "power/cpu_frequency"
      atrace_categories: "gfx"
      atrace_categories: "view"
      atrace_categories: "audio"
    }
  }
}
duration_ms: 10000
EOF
$ADB pull /data/misc/perfetto-traces/trace.pftrace "$OUT"
echo "Trace salvo em: $OUT"
