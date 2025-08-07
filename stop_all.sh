#!/bin/bash

echo "Stopping RLCF applications..."
kill 65383 65384
rm stop_all.sh
echo "Applications stopped."
