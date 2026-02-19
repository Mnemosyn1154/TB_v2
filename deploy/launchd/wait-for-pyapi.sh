#!/usr/bin/env bash
# ============================================================
# wait-for-pyapi.sh — pyapi health check 대기 후 명령 실행
#
# 사용법: wait-for-pyapi.sh <command> [args...]
# com.d2trader.tunnel.plist에서 cloudflared 앞에 끼워넣는 wrapper.
#
# launchd는 서비스 간 의존성(After=)을 지원하지 않으므로,
# 이 스크립트가 pyapi가 준비될 때까지 최대 60초 대기한다.
# ============================================================

HEALTH_URL="http://127.0.0.1:8000/py/health"
MAX_WAIT=60
INTERVAL=2

elapsed=0
while ! curl -sf "$HEALTH_URL" > /dev/null 2>&1; do
    if [ "$elapsed" -ge "$MAX_WAIT" ]; then
        echo "[wait-for-pyapi] pyapi did not become ready within ${MAX_WAIT}s, starting tunnel anyway" >&2
        break
    fi
    echo "[wait-for-pyapi] waiting for pyapi... (${elapsed}s)" >&2
    sleep "$INTERVAL"
    elapsed=$((elapsed + INTERVAL))
done

echo "[wait-for-pyapi] pyapi is ready, starting: $*" >&2
exec "$@"
