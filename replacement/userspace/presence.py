# SPDX-License-Identifier: GPL-3.0-only
# English publication counterpart; the private SP7 test profile uses Swedish prompts.
"""One-use presence and completion protocol. No device access or camera launch."""
import copy
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import time
import stat

IDLE_STROBE = 'armed=0 remaining_ms=0 cleanup_pending=0 recovery_required=0'
READY_TTL = 120
POWER_NODES = (
    '/sys/bus/pci/devices/0000:00:05.0',
    '/sys/bus/intel-ipu4-bus/devices/intel-ipu4-mmu0',
    '/sys/bus/intel-ipu4-bus/devices/intel-ipu60',
    '/sys/bus/intel-ipu4-bus/devices/intel-ipu4-mmu1',
    '/sys/bus/intel-ipu4-bus/devices/intel-ipu4-psys0',
    '/sys/bus/i2c/devices/i2c-INT347E:00',
    '/sys/bus/i2c/devices/i2c-INT33BE:00',
    '/sys/bus/i2c/devices/i2c-INT347A:00',
)


class GateError(RuntimeError):
    pass


def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def new_session(boot):
    return dict(schema=1, session_id=secrets.token_hex(16), boot_id=boot,
                phase='preparing', plan_sha256=None, ready_at=None,
                stop_requested=False, consumed=False, safe_to_leave=False)


def checked(state, boot):
    if state.get('schema') != 1 or state.get('boot_id') != boot:
        raise GateError("The session belongs to a different boot.")
    return copy.deepcopy(state)


def arm(state, boot, plan_sha256):
    s = checked(state, boot)
    if s['phase'] != 'preparing' or not re.fullmatch('[0-9a-f]{64}', plan_sha256):
        raise GateError("A new reviewed trial is required.")
    s.update(phase='awaiting_presence', plan_sha256=plan_sha256)
    return s


def ready(state, boot, now):
    s = checked(state, boot)
    if s['phase'] != 'awaiting_presence' or s['consumed']:
        raise GateError("This trial cannot be confirmed now.")
    s.update(phase='ready', ready_at=now, confirmation='sp7_dialog_button')
    return s


def expire(state, boot, now):
    s = checked(state, boot)
    if s['phase'] == 'ready' and not 0 <= now - s['ready_at'] <= READY_TTL:
        s.update(phase='awaiting_presence', ready_at=None)
    return s


def claim(state, boot, now, plan_sha256):
    s = expire(state, boot, now)
    if (s['phase'] != 'ready' or s['consumed'] or s['stop_requested'] or
            s['plan_sha256'] != plan_sha256 or
            s.get('confirmation') != 'sp7_dialog_button'):
        raise GateError("Current presence for this exact trial is missing.")
    s.update(phase='running', consumed=True, started_at=now)
    return s


def cancel(state, boot):
    s = checked(state, boot)
    if s['phase'] in ('preparing', 'awaiting_presence', 'ready'):
        s.update(phase='cancelled', stop_requested=True, safe_to_leave=True)
    elif s['phase'] in ('running', 'stopping'):
        s.update(phase='stopping', stop_requested=True)
    return s


def finish(state, boot, receipt, idle, now):
    """Require bound cleanup evidence AND fresh physical idle checks.

    The hardware runner must provide this evidence after closing its existing
    bounded root session. A quality failure may be safe; missing cleanup is not.
    """
    s = checked(state, boot)
    if s['phase'] not in ('running', 'stopping') or not s['consumed']:
        raise GateError("No running trial can be finished.")
    for key in ('session_id', 'boot_id', 'plan_sha256'):
        if receipt.get(key) != s.get(key):
            raise GateError("The closure receipt belongs to a different trial.")
    if (receipt.get('root_session_closed') is not True or
            receipt.get('worker_closed_cleanly') is not True or
            receipt.get('light_disarmed') is not True or
            receipt.get('kernel_closure_verified') is not True or
            receipt.get('cleanup_errors') != []):
        raise GateError("Complete shutdown receipts are missing.")
    require_idle(idle, boot, now)
    s.update(phase='finished', safe_to_leave=True, finished_at=now,
             completion_receipt=receipt, final_idle=idle)
    return s


def require_idle(idle, boot, now):
    """The same visibility and freshness gate applies before and after capture."""
    require_no_clients(idle, boot, now)
    if (idle.get('strobe') != IDLE_STROBE or
            idle.get('power') != {node: 'suspended' for node in POWER_NODES}):
        raise GateError("Camera and IR illumination shutdown is not confirmed.")


def require_no_clients(idle, boot, now):
    """Fresh complete reader evidence; power may settle during configuration."""
    if (idle.get('boot_id') != boot or
            not isinstance(idle.get('checked_at'), (int, float)) or
            not 0 <= now - idle['checked_at'] <= 5 or
            idle.get('camera_holders') != []):
        raise GateError("A complete fresh camera-client check is missing.")


def failure(state, boot, message):
    s = checked(state, boot)
    if s['phase'] in ('finished', 'cancelled'):
        return s
    s.update(phase='needs_check', stop_requested=True, safe_to_leave=False,
             error=str(message))
    return s


def presentation(s):
    phase = s['phase']
    if phase == 'preparing':
        return ("Preparing",
                "You do not need to sit here yet.\nThe development host will announce when the trial is ready.",
                "Ready", False)
    if phase == 'awaiting_presence':
        index=s.get('capture_index')
        if index==1:
            return ("Trial 1/2 — sit to your left",
                    "Keep the SP7 in place. Move yourself slightly to your own left while facing the screen.\nKeep your whole face in front of the camera and look toward it.\nPress Ready when positioned. Stay there until the left trial finishes.",
                    "Ready — left", True)
        if index==2:
            return ("Trial 2/2 — sit to your right",
                    "Keep the SP7 in place. Move yourself slightly to your own right while facing the screen.\nKeep your whole face in front of the camera and look toward it.\nPress Ready when positioned. Stay there until the right trial finishes.",
                    "Ready — right", True)
        return ("Check needed", "The direction for this trial is missing. Do not start it.", "Close", False)
    if phase == 'ready':
        return ("Thank you — stay seated", "Your presence is confirmed.\nWaiting for the prepared trial to start.", "Ready", False)
    if phase == 'running':
        return ("Trial running", "Stay seated and look toward the camera.\nThis window will say when you can leave.", "Ready", False)
    if phase == 'stopping':
        return ("Stopping the trial", "Checking that the sensor and IR illumination are off.", "Ready", False)
    if phase == 'finished' and s.get('safe_to_leave') is True:
        if s.get('capture_index') == 1:
            return ("Left trial finished", "The cameras and illumination are off.\nThe next dialog will ask you to sit to your right. Wait for it to appear.", "Close", True)
        return ("Finished", "The sensor and IR illumination are off.\nYou may leave the SP7. Analysis continues on the development host.", "Close", True)
    if phase == 'cancelled':
        return ("Cancelled", "No trial started. You may leave the SP7.", "Close", True)
    return ("Check needed",
            "Shutdown could not be confirmed.\nMove away from the camera and wait for guidance.\nNo new trial may start.", "Close", True)


class Store:
    """Serialize GUI/controller updates; never reuse a previous run directory."""
    def __init__(self, folder):
        self.folder = Path(folder)
        self.path = self.folder/'session.json'

    def create(self, state):
        self.folder.mkdir(mode=0o700, parents=False, exist_ok=False)
        self._write(state)

    def _write(self, state):
        fd, name = tempfile.mkstemp(prefix='.state-', dir=self.folder)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(state, stream, ensure_ascii=False, indent=2)
                stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name): os.unlink(name)

    def read(self):
        if self.folder.is_symlink() or self.path.is_symlink():
            raise GateError("Session-file symlinks are forbidden.")
        st = self.folder.stat()
        if st.st_uid != os.getuid() or st.st_mode & 0o077:
            raise GateError("The session folder must be private and owned by the user.")
        return json.loads(self.path.read_text())

    def update(self, action):
        self.read()  # Check UID/ownership BEFORE creating any lock file.
        fd = os.open(self.folder/'lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as lock:
            info=os.fstat(lock.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:raise GateError('Invalid private role-owned session lock')
            fcntl.flock(lock, fcntl.LOCK_EX)
            before = self.read()
            after = action(before)
            if after != before: self._write(after)
            return after


def fresh_idle():
    """Require the reviewed root reader; an unreadable process never means idle."""
    import idle_client
    try:
        return idle_client.read_idle()
    except (idle_client.InspectionError, OSError) as exc:
        raise GateError(str(exc)) from exc
