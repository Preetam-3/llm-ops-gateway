#!/usr/bin/env bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     LLM Ops Gateway — Setup                    ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════╝${NC}"
echo ""

# ── Check prerequisites ──────────────────────────────────
echo -e "${YELLOW}[1/4] Checking prerequisites...${NC}"

command -v docker >/dev/null 2>&1 || { echo -e "${RED}✗ Docker is required. Install from https://docs.docker.com/get-docker/${NC}"; exit 1; }
echo -e "${GREEN}  ✓ Docker found${NC}"

command -v python3 >/dev/null 2>&1 || { echo -e "${RED}✗ Python 3 is required.${NC}"; exit 1; }
echo -e "${GREEN}  ✓ Python $(python3 --version | cut -d' ' -f2) found${NC}"

docker compose version >/dev/null 2>&1 || echo -e "${YELLOW}  ⚠ docker compose not found — install Docker Compose plugin${NC}"
echo ""

# ── Configure .env ──────────────────────────────────────
echo -e "${YELLOW}[2/4] Configuring environment...${NC}"

if [ -f .env ]; then
    echo -e "${GREEN}  ✓ .env already exists${NC}"
else
    cp .env.example .env
    echo -e "${CYAN}  No .env file found. Created from .env.example${NC}"

    # Prompt for Groq API key
    read -p "  Enter your Groq API key (required): " groq_key
    if [ -n "$groq_key" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/your_groq_api_key_here/$groq_key/" .env
        else
            sed -i "s/your_groq_api_key_here/$groq_key/" .env
        fi
        echo -e "${GREEN}  ✓ Groq API key saved${NC}"
    else
        echo -e "${YELLOW}  ⚠ Skipped. Edit .env later to set GROQ_API_KEY${NC}"
    fi

    # Prompt for gateway key
    read -p "  Choose a gateway API key (default: my-gateway-key): " gw_key
    gw_key="${gw_key:-my-gateway-key}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/your_chosen_key_for_clients/$gw_key/" .env
    else
        sed -i "s/your_chosen_key_for_clients/$gw_key/" .env
    fi
    echo -e "${GREEN}  ✓ Gateway API key saved${NC}"
fi
echo ""

# ── Create virtual environment ──────────────────────────
echo -e "${YELLOW}[3/4] Setting up Python virtual environment...${NC}"

if [ -d .venv ]; then
    echo -e "${GREEN}  ✓ .venv already exists${NC}"
else
    python3 -m venv .venv
    echo -e "${GREEN}  ✓ Virtual environment created${NC}"
fi

source .venv/bin/activate
pip install -q -r requirements.txt
echo -e "${GREEN}  ✓ Dependencies installed${NC}"
echo ""

# ── Success ─────────────────────────────────────────────
echo -e "${YELLOW}[4/4] Setup complete!${NC}"
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Ready to go!                                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${CYAN}Quick start:${NC}"
echo ""
echo -e "  ${GREEN}1.${NC} Start all services:"
echo -e "     ${YELLOW}make run${NC}"
echo ""
echo -e "  ${GREEN}2.${NC} Send a chat message:"
echo -e "     ${YELLOW}./chat.py \"What is Docker?\"${NC}"
echo ""
echo -e "  ${GREEN}3.${NC} Open Grafana dashboard:"
echo -e "     ${YELLOW}http://localhost:4000${NC} (admin/admin)"
echo ""
echo -e "  ${GREEN}4.${NC} View metrics:"
echo -e "     ${YELLOW}http://localhost:8000/metrics${NC}"
echo ""
echo -e "  ${GREEN}5.${NC} Run tests:"
echo -e "     ${YELLOW}make test${NC}"
echo ""
echo -e "  ${GREEN}6.${NC} Stop everything:"
echo -e "     ${YELLOW}make stop${NC}"
echo ""
