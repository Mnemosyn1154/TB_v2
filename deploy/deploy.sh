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

# OS 감지
OS="$(uname -s)"

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

    # 5. macOS: LaunchAgents 설정
    if [ "$OS" = "Darwin" ]; then
        _setup_macos_launchd
    fi

    info "설정 완료. 다음 단계:"
    echo "  1. .env 파일 편집 (KIS API 키 등)"
    echo "  2. web/.env.local 편집 (PYTHON_API_SECRET)"
    echo "  3. Cloudflare Tunnel 설정 (deploy/cloudflared/config.yml)"
    echo "  4. ./deploy/deploy.sh build"
    echo "  5. ./deploy/deploy.sh start"
}

# macOS: plist를 LaunchAgents에 복사하고 플레이스홀더 치환
_setup_macos_launchd() {
    local launch_agents="$HOME/Library/LaunchAgents"
    local log_dir="$HOME/Library/Logs/d2trader"
    local launchd_src="$SCRIPT_DIR/launchd"

    info "macOS LaunchAgents 설정 중..."
    mkdir -p "$launch_agents" "$log_dir"
    chmod +x "$launchd_src/wait-for-pyapi.sh"

    local node_bin
    node_bin="$(command -v node 2>/dev/null || echo "/usr/local/bin/node")"
    local cloudflared_bin
    cloudflared_bin="$(command -v cloudflared 2>/dev/null || echo "cloudflared")"

    for plist in com.d2trader.pyapi.plist com.d2trader.nextjs.plist com.d2trader.tunnel.plist; do
        local dest="$launch_agents/$plist"
        # 이미 로드된 경우 먼저 unload
        launchctl unload "$dest" 2>/dev/null || true

        sed -e "s|<USER>|${USER}|g" \
            -e "s|<PROJECT_DIR>|${PROJECT_ROOT}|g" \
            -e "s|<NODE_BIN>|${node_bin}|g" \
            -e "s|<CLOUDFLARED_BIN>|${cloudflared_bin}|g" \
            "$launchd_src/$plist" > "$dest"
        info "  $plist → $dest"
    done

    warn "plist 설치 완료. 'deploy.sh start'로 서비스를 시작하세요."
    warn "pyapi plist의 환경변수는 직접 편집이 필요할 수 있습니다:"
    warn "  $launch_agents/com.d2trader.pyapi.plist"
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

    if [ "$OS" = "Darwin" ]; then
        _start_macos
    else
        _start_linux
    fi
}

_start_macos() {
    local launch_agents="$HOME/Library/LaunchAgents"

    for plist in com.d2trader.pyapi.plist com.d2trader.nextjs.plist com.d2trader.tunnel.plist; do
        local dest="$launch_agents/$plist"
        if [ ! -f "$dest" ]; then
            warn "$plist 미설치. 먼저 'deploy.sh setup'을 실행하세요."
            continue
        fi
        local label="${plist%.plist}"
        if launchctl list "$label" &>/dev/null; then
            info "$label 이미 실행 중"
        else
            launchctl load "$dest"
            info "$label 시작됨"
        fi
    done
}

_start_linux() {
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

    if [ "$OS" = "Darwin" ]; then
        _stop_macos
    else
        _stop_linux
    fi
}

_stop_macos() {
    local launch_agents="$HOME/Library/LaunchAgents"

    for plist in com.d2trader.tunnel.plist com.d2trader.nextjs.plist com.d2trader.pyapi.plist; do
        local dest="$launch_agents/$plist"
        local label="${plist%.plist}"
        if launchctl list "$label" &>/dev/null; then
            launchctl unload "$dest"
            info "$label 중지됨"
        fi
    done
}

_stop_linux() {
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

    if [ "$OS" = "Darwin" ]; then
        _status_macos
    else
        _status_linux
    fi
}

_status_macos() {
    # launchd 서비스 목록
    echo "launchd 서비스:"
    launchctl list | grep d2trader || echo "  (등록된 d2trader 서비스 없음)"
    echo ""

    # HTTP health check
    echo -n "Python API (port 8000): "
    if curl -sf http://localhost:8000/py/health > /dev/null 2>&1; then
        echo -e "${GREEN}Running${NC}"
    else
        echo -e "${RED}Stopped${NC}"
    fi

    echo -n "Next.js (port 3000):    "
    if curl -sf http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}Running${NC}"
    else
        echo -e "${RED}Stopped${NC}"
    fi

    echo -n "Cloudflare Tunnel:      "
    if pgrep -f cloudflared > /dev/null 2>&1; then
        echo -e "${GREEN}Running${NC}"
    else
        echo -e "${RED}Stopped${NC}"
    fi
}

_status_linux() {
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

    if [ "$OS" = "Darwin" ]; then
        _logs_macos "$service"
    else
        _logs_linux "$service"
    fi
}

_logs_macos() {
    local service="$1"
    local log_dir="$HOME/Library/Logs/d2trader"
    case "$service" in
        pyapi)  tail -f "$log_dir/pyapi.stdout.log" "$log_dir/pyapi.stderr.log" ;;
        nextjs) tail -f "$log_dir/nextjs.stdout.log" "$log_dir/nextjs.stderr.log" ;;
        tunnel) tail -f "$log_dir/tunnel.stdout.log" "$log_dir/tunnel.stderr.log" ;;
        *)      error "사용법: deploy.sh logs [pyapi|nextjs|tunnel]" ;;
    esac
}

_logs_linux() {
    local service="$1"
    case "$service" in
        pyapi)   sudo journalctl -u d2trader-pyapi -f --no-pager ;;
        tunnel)  sudo journalctl -u d2trader-tunnel -f --no-pager ;;
        nextjs)  error "Linux에서 Next.js 로그는 systemd로 관리되지 않습니다." ;;
        *)       error "사용법: deploy.sh logs [pyapi|nextjs|tunnel]" ;;
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
        echo "  logs    로그 확인 (pyapi|nextjs|tunnel)"
        exit 1
        ;;
esac
