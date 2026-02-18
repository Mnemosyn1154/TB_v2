#!/usr/bin/env bash
# ============================================================
# D2trader 배포 스크립트
# ============================================================
#
# 사용법:
#   ./deploy/deploy.sh setup    — 초기 설정 (최초 1회)
#   ./deploy/deploy.sh build    — Next.js 빌드
#   ./deploy/deploy.sh start    — 전체 서비스 시작
#   ./deploy/deploy.sh stop     — 전체 서비스 중지
#   ./deploy/deploy.sh status   — 서비스 상태 확인
#   ./deploy/deploy.sh logs     — 로그 확인
#
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── 초기 설정 ──
cmd_setup() {
    info "D2trader 배포 환경 설정 시작..."

    # 1. 환경변수 파일 확인
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        warn ".env 파일이 없습니다. 템플릿에서 복사합니다."
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        warn ".env 파일을 편집하여 실제 값을 입력하세요."
    fi

    if [ ! -f "$PROJECT_ROOT/web/.env.local" ]; then
        warn "web/.env.local 파일이 없습니다. 템플릿에서 복사합니다."
        cp "$PROJECT_ROOT/web/.env.example" "$PROJECT_ROOT/web/.env.local"
        warn "web/.env.local 파일을 편집하여 실제 값을 입력하세요."
    fi

    # 2. Python 가상환경
    if [ ! -d "$PROJECT_ROOT/.venv" ]; then
        info "Python 가상환경 생성 중..."
        python3 -m venv "$PROJECT_ROOT/.venv"
    fi
    info "Python 패키지 설치 중..."
    "$PROJECT_ROOT/.venv/bin/pip" install -r "$PROJECT_ROOT/requirements.txt" -q

    # 3. Node.js 의존성
    info "Node.js 패키지 설치 중..."
    cd "$PROJECT_ROOT/web" && npm install --silent

    # 4. cloudflared 확인
    if command -v cloudflared &> /dev/null; then
        info "cloudflared 설치됨: $(cloudflared --version)"
    else
        warn "cloudflared가 설치되어 있지 않습니다."
        warn "설치: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
    fi

    info "설정 완료. 다음 단계:"
    echo "  1. .env 파일 편집 (KIS API 키 등)"
    echo "  2. web/.env.local 편집 (PYTHON_API_SECRET)"
    echo "  3. Cloudflare Tunnel 설정 (deploy/cloudflared/config.yml)"
    echo "  4. ./deploy/deploy.sh build"
    echo "  5. ./deploy/deploy.sh start"
}

# ── Next.js 빌드 ──
cmd_build() {
    info "Next.js 프로덕션 빌드 시작..."
    cd "$PROJECT_ROOT/web"
    npm run build
    info "빌드 완료. 출력: web/.next/"
}

# ── 서비스 시작 ──
cmd_start() {
    info "D2trader 서비스 시작..."

    # Python API
    if systemctl is-active --quiet d2trader-pyapi 2>/dev/null; then
        info "Python API 이미 실행 중"
    else
        info "Python API 시작..."
        if [ -f /etc/systemd/system/d2trader-pyapi.service ]; then
            sudo systemctl start d2trader-pyapi
        else
            warn "systemd 서비스 미설치. 수동 시작:"
            echo "  cd $PROJECT_ROOT && .venv/bin/uvicorn pyapi.main:app --host 127.0.0.1 --port 8000"
        fi
    fi

    # Cloudflare Tunnel
    if systemctl is-active --quiet d2trader-tunnel 2>/dev/null; then
        info "Cloudflare Tunnel 이미 실행 중"
    else
        info "Cloudflare Tunnel 시작..."
        if [ -f /etc/systemd/system/d2trader-tunnel.service ]; then
            sudo systemctl start d2trader-tunnel
        else
            warn "systemd 서비스 미설치. 수동 시작:"
            echo "  cloudflared tunnel run d2trader-api"
        fi
    fi

    # Next.js (standalone)
    info "Next.js 서버 시작..."
    if [ -d "$PROJECT_ROOT/web/.next/standalone" ]; then
        cd "$PROJECT_ROOT/web/.next/standalone"
        NODE_ENV=production node server.js &
        info "Next.js 서버 시작됨 (PID: $!)"
    else
        warn "standalone 빌드를 찾을 수 없습니다. 먼저 빌드하세요: ./deploy/deploy.sh build"
    fi
}

# ── 서비스 중지 ──
cmd_stop() {
    info "D2trader 서비스 중지..."

    if systemctl is-active --quiet d2trader-pyapi 2>/dev/null; then
        sudo systemctl stop d2trader-pyapi
        info "Python API 중지됨"
    fi

    if systemctl is-active --quiet d2trader-tunnel 2>/dev/null; then
        sudo systemctl stop d2trader-tunnel
        info "Cloudflare Tunnel 중지됨"
    fi

    # Next.js 프로세스 종료
    pkill -f "node.*server.js" 2>/dev/null && info "Next.js 서버 중지됨" || true
}

# ── 상태 확인 ──
cmd_status() {
    echo "=== D2trader 서비스 상태 ==="
    echo ""

    # Python API
    echo -n "Python API (port 8000): "
    if curl -s http://localhost:8000/py/health > /dev/null 2>&1; then
        echo -e "${GREEN}Running${NC}"
    else
        echo -e "${RED}Stopped${NC}"
    fi

    # Cloudflare Tunnel
    echo -n "Cloudflare Tunnel:      "
    if systemctl is-active --quiet d2trader-tunnel 2>/dev/null; then
        echo -e "${GREEN}Running${NC}"
    elif pgrep -f cloudflared > /dev/null 2>&1; then
        echo -e "${GREEN}Running (manual)${NC}"
    else
        echo -e "${RED}Stopped${NC}"
    fi

    # Next.js
    echo -n "Next.js (port 3000):    "
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}Running${NC}"
    else
        echo -e "${RED}Stopped${NC}"
    fi
}

# ── 로그 확인 ──
cmd_logs() {
    local service="${1:-pyapi}"
    case "$service" in
        pyapi)   sudo journalctl -u d2trader-pyapi -f --no-pager ;;
        tunnel)  sudo journalctl -u d2trader-tunnel -f --no-pager ;;
        *)       error "사용법: deploy.sh logs [pyapi|tunnel]" ;;
    esac
}

# ── 메인 ──
case "${1:-}" in
    setup)  cmd_setup ;;
    build)  cmd_build ;;
    start)  cmd_start ;;
    stop)   cmd_stop ;;
    status) cmd_status ;;
    logs)   cmd_logs "${2:-}" ;;
    *)
        echo "사용법: $0 {setup|build|start|stop|status|logs}"
        echo ""
        echo "  setup   초기 설정 (환경변수, 의존성 설치)"
        echo "  build   Next.js 프로덕션 빌드"
        echo "  start   전체 서비스 시작"
        echo "  stop    전체 서비스 중지"
        echo "  status  서비스 상태 확인"
        echo "  logs    로그 확인 (pyapi|tunnel)"
        exit 1
        ;;
esac
