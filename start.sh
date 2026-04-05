#!/bin/bash

# MiroFish Platform Startup Script
# Usage: ./start.sh [options]
# Options:
#   --skip-install    Skip dependency installation
#   --no-neo4j        Skip Neo4j startup (app will degrade gracefully)
#   --docker          Start everything via Docker Compose instead

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Flags
SKIP_INSTALL=false
NO_NEO4J=false
USE_DOCKER=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --skip-install)
            SKIP_INSTALL=true
            shift
            ;;
        --no-neo4j)
            NO_NEO4J=true
            shift
            ;;
        --docker)
            USE_DOCKER=true
            shift
            ;;
        --help|-h)
            echo -e "${CYAN}MiroFish Platform Startup Script${NC}"
            echo ""
            echo "Usage: ./start.sh [options]"
            echo ""
            echo "Options:"
            echo "  --skip-install    Skip dependency installation"
            echo "  --no-neo4j        Skip Neo4j startup (app will degrade gracefully)"
            echo "  --docker          Start everything via Docker Compose instead"
            echo "  --help, -h        Show this help message"
            exit 0
            ;;
    esac
done

# Print banner
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    MiroFish Platform                         ║"
echo "║          AI-Powered War-Gaming for Consultants              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Helper functions
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if a port is in use
port_in_use() {
    lsof -Pi :"$1" -sTCP:LISTEN -t >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    local missing_deps=()
    
    # Check Node.js
    if command_exists node; then
        NODE_VERSION=$(node --version | cut -d'v' -f2)
        print_success "Node.js found: v${NODE_VERSION}"
    else
        missing_deps+=("Node.js")
        print_error "Node.js not found"
    fi
    
    # Check Python
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        print_success "Python found: ${PYTHON_VERSION}"
        
        # Check Python version (need 3.11+)
        PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
        PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)
        if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
            print_warning "Python 3.11+ recommended (found ${PYTHON_VERSION})"
        fi
    else
        missing_deps+=("Python 3.11+")
        print_error "Python not found"
    fi
    
    # Check uv
    if command_exists uv; then
        UV_VERSION=$(uv --version 2>&1 | head -1)
        print_success "uv found: ${UV_VERSION}"
    else
        missing_deps+=("uv")
        print_error "uv not found (install with: curl -LsSf https://astral.sh/uv/install.sh | sh)"
    fi
    
    # Check Docker (optional) - verify daemon is actually running
    DOCKER_AVAILABLE=false
    if command_exists docker; then
        if docker info >/dev/null 2>&1; then
            DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
            print_success "Docker found: ${DOCKER_VERSION}"
            DOCKER_AVAILABLE=true
        else
            print_warning "Docker daemon not running — skipping Neo4j (using SQLite fallback)"
            DOCKER_AVAILABLE=false
        fi
    else
        print_warning "Docker not found — skipping Neo4j (using SQLite fallback)"
        DOCKER_AVAILABLE=false
    fi
    
    # Check Docker Compose
    if command_exists docker-compose || docker compose version >/dev/null 2>&1; then
        print_success "Docker Compose found"
    else
        print_warning "Docker Compose not found"
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo ""
        print_error "Missing required dependencies:"
        for dep in "${missing_deps[@]}"; do
            echo "  - $dep"
        done
        echo ""
        print_info "Please install the missing dependencies and try again."
        exit 1
    fi
    
    print_success "All required prerequisites found!"
}

# Setup environment file
setup_environment() {
    print_info "Setting up environment..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success "Created .env from .env.example"
            print_warning "Please configure your .env file with your API keys before using the platform"
        else
            print_warning ".env.example not found, creating minimal .env"
            cat > .env << EOF
# LLM Configuration
LLM_PROVIDER=openai
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Miro API
MIRO_API_TOKEN=

# MCP Server
MCP_SERVER_ENABLED=false
EOF
            print_warning "Please configure your .env file with your API keys before using the platform"
        fi
    else
        print_success ".env file already exists"
    fi
}

# Wait for Neo4j to be ready
wait_for_neo4j() {
    local max_attempts=30
    local attempt=1
    
    print_info "Waiting for Neo4j to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        # Neo4j 5.x root endpoint returns JSON with "neo4j_version"
        if curl -s --connect-timeout 2 --max-time 5 http://localhost:7474 2>/dev/null | grep -q "neo4j_version"; then
            print_success "Neo4j is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo ""
    print_warning "Neo4j health check timed out after $((max_attempts * 2)) seconds"
    print_warning "Neo4j may still be starting up. You can check http://localhost:7474 manually"
    return 1
}

# Start Neo4j
start_neo4j() {
    if [ "$NO_NEO4J" = true ]; then
        print_warning "Skipping Neo4j startup (--no-neo4j flag set)"
        print_warning "The application will degrade gracefully without Neo4j"
        return 0
    fi
    
    if [ "$DOCKER_AVAILABLE" = false ]; then
        print_warning "Skipping Neo4j startup — using SQLite fallback"
        return 0
    fi
    
    print_info "Starting Neo4j..."
    
    # Check if Neo4j container is already running
    if docker ps --format "{{.Names}}" | grep -q "^mirofish-neo4j$"; then
        print_success "Neo4j container already running"
        wait_for_neo4j
        return 0
    fi
    
    # Check if Neo4j container exists but is stopped
    if docker ps -a --format "{{.Names}}" | grep -q "^mirofish-neo4j$"; then
        print_info "Starting existing Neo4j container..."
        docker start mirofish-neo4j >/dev/null 2>&1
    else
        print_info "Creating and starting Neo4j container..."
        docker compose up -d neo4j
    fi
    
    wait_for_neo4j
}

# Install dependencies
install_dependencies() {
    if [ "$SKIP_INSTALL" = true ]; then
        print_warning "Skipping dependency installation (--skip-install flag set)"
        return 0
    fi
    
    print_info "Installing dependencies..."
    
    # Backend dependencies
    print_info "Installing backend dependencies (uv sync)..."
    cd backend
    uv sync
    cd ..
    print_success "Backend dependencies installed"
    
    # Frontend dependencies
    print_info "Installing frontend dependencies (npm install)..."
    cd frontend
    npm install
    cd ..
    print_success "Frontend dependencies installed"
}

# Kill process on a given port
kill_port() {
    local port=$1
    local pids
    pids=$(lsof -ti :"$port" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 1
        print_success "Killed process(es) on port $port"
    fi
}

# Free up application ports (never kill Neo4j — it may already be running)
free_ports() {
    print_info "Freeing up required ports..."

    local ports=(3000 5001)

    for port in "${ports[@]}"; do
        if port_in_use "$port"; then
            print_warning "Port $port is in use — killing process"
            kill_port "$port"
        fi
    done

    print_success "All required ports are free"
}

# Check ports
check_ports() {
    print_info "Checking ports..."

    # Auto-kill anything occupying our ports
    free_ports
}

# Start services locally
start_local() {
    print_info "Starting MiroFish services locally..."
    
    # Check ports before starting
    check_ports
    
    # Start Neo4j
    start_neo4j
    
    # Install dependencies
    install_dependencies
    
    print_info "Starting backend and frontend..."
    
    # Function to cleanup on exit
cleanup() {
        echo ""
        print_info "Shutting down services..."
        
        # Kill background processes
        if [ -n "$BACKEND_PID" ]; then
            kill $BACKEND_PID 2>/dev/null || true
            print_success "Backend stopped"
        fi
        
        if [ -n "$FRONTEND_PID" ]; then
            kill $FRONTEND_PID 2>/dev/null || true
            print_success "Frontend stopped"
        fi
        
        # Stop Neo4j if we started it
        if [ "$NO_NEO4J" = false ] && [ "$DOCKER_AVAILABLE" = true ]; then
            read -p "Stop Neo4j container? (y/N) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                docker stop mirofish-neo4j >/dev/null 2>&1 || true
                print_success "Neo4j stopped"
            fi
        fi
        
        print_success "Cleanup complete"
        exit 0
    }
    
    # Trap signals
    trap cleanup SIGINT SIGTERM EXIT
    
    # Start backend
    print_info "Starting backend on http://localhost:5001 ..."
    cd backend
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 5001 &
    BACKEND_PID=$!
    cd ..
    
    # Wait a moment for backend to start
    sleep 2
    
    # Check if backend started successfully
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        print_error "Backend failed to start"
        exit 1
    fi
    
    print_success "Backend started (PID: $BACKEND_PID)"
    
    # Start frontend
    print_info "Starting frontend on http://localhost:3000 ..."
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    cd ..
    
    # Wait a moment for frontend to start
    sleep 3
    
    # Check if frontend started successfully
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        print_error "Frontend failed to start"
        exit 1
    fi
    
    print_success "Frontend started (PID: $FRONTEND_PID)"
    
    # Print status
    echo ""
    echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  MiroFish Platform is running!${NC}"
    echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${CYAN}Frontend:${NC}    http://localhost:3000"
    echo -e "  ${CYAN}Backend:${NC}     http://localhost:5001"
    echo -e "  ${CYAN}Backend API:${NC} http://localhost:5001/docs"
    if [ "$NO_NEO4J" = false ] && [ "$DOCKER_AVAILABLE" = true ]; then
        echo -e "  ${CYAN}Neo4j Browser:${NC} http://localhost:7474"
    fi
    echo ""
    echo -e "  ${YELLOW}Press Ctrl+C to stop all services${NC}"
    echo ""
    
    # Wait for processes
    wait $BACKEND_PID $FRONTEND_PID
}

# Start with Docker Compose
start_docker() {
    print_info "Starting MiroFish with Docker Compose..."
    
    if [ "$DOCKER_AVAILABLE" = false ]; then
        print_error "Docker is not available. Cannot use --docker mode."
        exit 1
    fi
    
    # Setup environment
    setup_environment
    
    print_info "Building and starting all services..."
    docker compose up --build -d
    
    print_info "Waiting for services to be ready..."
    sleep 5
    
    # Wait for Neo4j
    wait_for_neo4j
    
    # Print status
    echo ""
    echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  MiroFish Platform is running with Docker!${NC}"
    echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${CYAN}Frontend:${NC}    http://localhost:3000"
    echo -e "  ${CYAN}Backend:${NC}     http://localhost:5001"
    echo -e "  ${CYAN}Backend API:${NC} http://localhost:5001/docs"
    echo -e "  ${CYAN}Neo4j Browser:${NC} http://localhost:7474"
    echo ""
    echo -e "  ${YELLOW}Run 'docker compose logs -f' to view logs${NC}"
    echo -e "  ${YELLOW}Run 'docker compose down' to stop all services${NC}"
    echo ""
}

# Main execution
main() {
    # Check prerequisites first
    check_prerequisites
    
    # Setup environment
    setup_environment
    
    # Start services based on mode
    if [ "$USE_DOCKER" = true ]; then
        start_docker
    else
        start_local
    fi
}

# Run main function
main
