#!/bin/bash

LOG_DIR="$(dirname "$0")"/logs
mkdir -p "$LOG_DIR"

echo "Starting RLCF Admin Interface (app_interface.py) on http://localhost:7860..."
python app_interface.py > "$LOG_DIR/admin_interface.log" 2>&1 & 
ADMIN_PID=$!

echo "Starting RLCF User Dashboard (user_dashboard.py) on http://localhost:7861..."
python user_dashboard.py > "$LOG_DIR/user_interface.log" 2>&1 & 
USER_PID=$!

# Placeholder for server operations log. 
# Actual server logs would need to be configured within the RLCF framework modules.
echo "Starting RLCF Server Operations (placeholder) logging..."
touch "$LOG_DIR/server_operations.log"

echo "\nRLCF applications started. Logs are being written to $LOG_DIR"
echo "Admin Interface: http://localhost:7860"
echo "User Dashboard:  http://localhost:7861"
echo "\nTo stop the applications, run: kill $ADMIN_PID $USER_PID"
echo "Or simply run: ./stop_all.sh"

# Create a stop script for convenience
cat <<EOF > stop_all.sh
#!/bin/bash

echo "Stopping RLCF applications..."
kill $ADMIN_PID $USER_PID
rm stop_all.sh
echo "Applications stopped."
EOF

chmod +x stop_all.sh