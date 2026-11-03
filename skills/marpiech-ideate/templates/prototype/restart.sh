#!/usr/bin/env bash
# restart.sh — (re)start a local prototype in the background, safely.
#   - binds 127.0.0.1 only; access requires the one-time token in .token
#   - stops ONLY the process listening on $PORT (never pkill -f: the pattern would
#     also match the calling shell)
#   - waits until the app answers, then prints the token URL
#
# Usage: PORT=8101 ./restart.sh
# Edit START_CMD for your stack; it must read HOST, PORT and PROTO_TOKEN from the env
# and reject requests without ?token=$PROTO_TOKEN (or a cookie set from it).

set -euo pipefail
cd "$(dirname "$0")"

: "${PORT:?set PORT (pick the next free one from the adapter port registry)}"
HOST=127.0.0.1
START_CMD=${START_CMD:-"python3 -m uvicorn app:app --host $HOST --port $PORT"}

# One-time token, readable only by the owner.
if [[ ! -s .token ]]; then
  umask 077
  python3 -c 'import secrets; print(secrets.token_urlsafe(24))' > .token
fi
PROTO_TOKEN=$(cat .token)
export HOST PORT PROTO_TOKEN

# Stop whatever listens on $PORT (Linux: ss; macOS/BSD: lsof).
pids=$( (ss -ltnpH "sport = :$PORT" 2>/dev/null | grep -oE 'pid=[0-9]+' | cut -d= -f2) \
        || lsof -t -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)
for pid in $pids; do kill "$pid" 2>/dev/null || true; done
sleep 1

# Detach from this shell so the prototype survives the session's command.
if command -v setsid >/dev/null; then
  setsid nohup bash -c "$START_CMD" > server.log 2>&1 < /dev/null &
else
  nohup bash -c "$START_CMD" > server.log 2>&1 < /dev/null &
fi

for _ in $(seq 1 30); do
  if curl -fs -o /dev/null "http://$HOST:$PORT/?token=$PROTO_TOKEN"; then
    echo "up: http://$HOST:$PORT/?token=$PROTO_TOKEN"
    echo "remote: ssh -L $PORT:$HOST:$PORT <this-host>, then open the URL above"
    exit 0
  fi
  sleep 1
done
echo "did not come up in 30s — see server.log" >&2
tail -20 server.log >&2
exit 1
