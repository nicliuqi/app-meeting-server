#!/usr/bin/env bash
set -e

# Check if we are in the correct directory before running commands.
if [[ ! $(pwd) == '/home/meetingserver/app-meeting-server' ]]; then
	echo "Running in the wrong directory...switching to..."
	cd /home/meetingserver/app-meeting-server
fi


python3 manage.py migrate


exec $@