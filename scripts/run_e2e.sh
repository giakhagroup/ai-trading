#!/bin/bash

# Setup colors for easy log viewing
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting End-to-End Soak Test for AI Trading Pipeline${NC}"
echo "=========================================================="

# 1. Start Python Quant Engine
echo -e "${BLUE}[1/2] Starting Python FastAPI Engine (Port 8000)...${NC}"
export PYTHONPATH=./python
python3 python/main.py &
PYTHON_PID=$!

echo "Waiting for Python Engine to boot..."
sleep 5

# 2. Start Node.js Gateway
echo -e "${BLUE}[2/2] Starting Node.js Gateway...${NC}"
# Use tsx instead of ts-node due to TypeScript 5+ incompatibility issues
npx tsx src/index.ts &
NODE_PID=$!

echo -e "${GREEN}Both services are running.${NC}"
echo "Python PID: $PYTHON_PID"
echo "Node PID: $NODE_PID"
echo "=========================================================="
echo "Press [CTRL+C] to stop both services."

# Trap SIGINT and SIGTERM to kill background jobs cleanly
trap "echo 'Shutting down services...'; kill $PYTHON_PID $NODE_PID; exit 0" SIGINT SIGTERM

# Wait indefinitely so the script doesn't exit
wait
