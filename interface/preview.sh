#!/bin/sh
set -eu
task_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ ! -x /usr/lib/qt6/bin/qml ]; then
    echo 'Qt 6 QML is missing. Manjaro package: qt6-declarative.' >&2
    exit 1
fi
exec /usr/lib/qt6/bin/qml "$task_dir/ui/Demo.qml"
