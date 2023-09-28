#!/usr/bin/env bash
set -e

# Check if we are in the correct directory before running commands.
if [[ ! $(pwd) == '/work/app-meeting-server' ]]; then
	echo "Running in the wrong directory...switching to /work/app-meeting-server"
	cd /work/app-meeting-server
fi

# collect static
python3 manage.py collectstatic --noinput

python3 manage.py migrate


exec $@
