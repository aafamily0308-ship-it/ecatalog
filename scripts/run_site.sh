#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT_DIR/.ecatalog.pid"
LOG_FILE="${ECATALOG_LOG_FILE:-$ROOT_DIR/ecatalog.log}"

start() {
  if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "eCatalog already running with PID $(cat "$PID_FILE")"
    return 0
  fi

  echo "Starting eCatalog..."
  ECATALOG_LOG_FILE="$LOG_FILE" nohup python -m apps.api.main >/tmp/ecatalog_stdout.log 2>&1 &
  echo $! > "$PID_FILE"
  sleep 1
  echo "Started PID $(cat "$PID_FILE")"
  echo "Log file: $LOG_FILE"
}

stop() {
  if [[ ! -f "$PID_FILE" ]]; then
    echo "No PID file found"
    return 0
  fi

  PID="$(cat "$PID_FILE")"
  if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    echo "Stopped PID $PID"
  else
    echo "Process $PID not running"
  fi
  rm -f "$PID_FILE"
}

status() {
  if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "RUNNING PID=$(cat "$PID_FILE")"
  else
    echo "STOPPED"
  fi
}

logs() {
  tail -n 80 "$LOG_FILE"
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  restart) stop || true; start ;;
  status) status ;;
  logs) logs ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs}"
    exit 1
    ;;
esac
