#!/bin/bash

set -e

if [ -z "${EK_WEBPASS}" ]; then
    exec "embykeeper" "--basedir" "/app" "$@"
else
    exec "embykeeper-web" "--basedir" "/app" "--wait" "$@"
fi
