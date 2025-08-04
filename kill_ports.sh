#!/bin/bash

PORTS="7860 7861 8000"

for PORT in $PORTS
do
    echo "Attempting to kill processes on port $PORT..."
    # Find PIDs listening on the port, exclude header and grep process itself
    PIDS=$(lsof -t -i :$PORT)

    if [ -z "$PIDS" ]; then
        echo "No processes found listening on port $PORT."
    else
        echo "Found processes on port $PORT with PIDs: $PIDS"
        # Kill the processes forcefully
        kill -9 $PIDS
        echo "Killed processes on port $PORT."
    fi
done

echo "Port cleanup complete."
