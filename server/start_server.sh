#! /bin/bash
touch controller.log
touch controller.debug
CONTROLLER_PORT=${CONTROLLER_PORT:-8088}
python3 -u controller.py ${CONTROLLER_PORT} 2>&1 >controller.log &
tail -f controller.log -f controller.debug
