#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
set -eu
[ "$(id -u)" -ne 0 ] || { echo "Run offline tests as an ordinary user." >&2; exit 2; }
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
cc -std=c11 -Wall -Wextra -Werror -I"$base/drivers/ov7251" "$base/tests/test_gate.c" "$base/drivers/ov7251/ir_gate.c" -o "$tmp/gate"
cc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -I"$base/drivers/ov7251" "$base/tests/test_session.c" "$base/drivers/ov7251/ir_gate.c" -o "$tmp/session"
cc -std=c11 -D_GNU_SOURCE -include time.h -Wall -Wextra -Werror "$base/native/camera-state.c" -o "$tmp/camera-state"
cc -std=c11 -D_GNU_SOURCE -include time.h -Wall -Wextra -Werror -fPIC -shared "$base/tests/mock_camera_state.c" -o "$tmp/mock_camera_state.so"
"$tmp/gate"
"$tmp/session"
cp "$base"/tests/test_*.py "$tmp/"
PYTHONPATH="$base/userspace" python3 -B -m unittest discover -s "$tmp" -p 'test_*.py' -v
