#!/bin/bash
echo "Starting Python FastAPI..."
uvicorn api.main:app --app-dir python &
PID=$!
sleep 3
echo "Starting Node.js Gateway..."
timeout 15 npx tsx src/gateway.ts
kill $PID
