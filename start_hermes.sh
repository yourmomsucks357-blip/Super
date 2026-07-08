#!/bin/bash
echo "Starting Hermes Main Agent Server..."
echo "====================================="
npm install
echo "Starting Hermes server on port 3000..."
npm run start &
HERMES_PID=$!
echo "Hermes server PID: $HERMES_PID"
echo "Starting Python server..."
python main.py &
PYTHON_PID=$!
echo "Python server PID: $PYTHON_PID"
echo "Both servers running!"
echo "- Hermes: http://localhost:3000"
echo "- Python: http://localhost:8000"
wait $HERMES_PID $PYTHON_PID