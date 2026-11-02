# SPDX-License-Identifier: GPL-3.0-or-later
"""Inactive, dependency-injected research attempt. Never authorizes login.

No image, template, password, wallet or camera implementation is imported here.
All evidence comes from the local trusted adapter, never from a GUI message.
The clock and adapter deadlines must share CLOCK_MONOTONIC on the same boot.
"""
from dataclasses import dataclass
import math
import secrets
from typing import Protocol


@dataclass(frozen=True)
class Request:
    nonce: str
    boot: str
    uid: int
    service: str
    started: float
    deadline: float


@dataclass(frozen=True)
class Evidence:
    nonce: str
    boot: str
    uid: int
    captured: float
    complete_rgb_ir: bool
    verified_timebase: bool
    quality_passed: bool
    geometry_qualified: bool
    identity_qualified: bool
    pad_qualified: bool
    single_candidate: bool
    identity_matches_account: bool
    versions_match: bool


@dataclass(frozen=True)
class Closure:
    worker_stopped: bool
    light_off: bool
    native_closed: bool
    kernel_stopped: bool
    root_closed: bool


@dataclass(frozen=True)
class Idle:
    boot: str
    complete: bool
    camera_clients_empty: bool
    all_eight_suspended: bool
    strobe_off: bool


@dataclass(frozen=True)
class Result:
    authentication_allowed: bool
    password_fallback: bool
    evidence_eligible_for_future_validation: bool
    shutdown_confirmed: bool
    hold_required: bool
    reasons: tuple[str, ...]


class Adapter(Protocol):
    def preflight(self, request: Request) -> Idle: ...
    def acquire(self, request: Request) -> Evidence: ...
    def stop(self, request: Request) -> Closure: ...
    def restore(self, request: Request) -> bool: ...
    def idle(self, request: Request) -> Idle: ...


class Attempts:
    """Single-owner in-memory challenges. No IPC or production daemon yet.

    Expired or failed claims are burned, not reusable. An interrupted process
    loses all challenges; no stored success or reboot-spanning ticket exists.
    """
    def __init__(self, boot, clock):
        self.boot = boot
        self.clock = clock
        self.pending = {}

    def issue(self, uid, service, ttl=8.0):
        now = self.clock()
        if (type(uid) is not int or uid < 1000 or uid >= 2**32 or
                service not in ('sddm', 'kde') or not self.boot or
                not math.isfinite(now) or type(ttl) not in (int, float) or
                not math.isfinite(ttl) or not 0 < ttl <= 8):
            raise ValueError('unsupported local research request')
        if len(self.pending) >= 16:
            # Bound memory even if no caller claims its old request.
            self.pending = {n: r for n, r in self.pending.items() if now < r.deadline}
        if len(self.pending) >= 16:
            raise ValueError('pending request limit')
        r = Request(secrets.token_hex(32), self.boot, uid, service, now, now + ttl)
        self.pending[r.nonce] = r
        return r

    def claim(self, request):
        if not isinstance(request, Request):
            raise ValueError('invalid request')
        original = self.pending.pop(request.nonce, None)
        now = self.clock()
        if (original != request or request.boot != self.boot or
                not math.isfinite(now) or not request.started <= now < request.deadline):
            raise ValueError('stale, altered or consumed request')


def exact_true_fields(value, expected_type, fields):
    return type(value) is expected_type and all(getattr(value, f) is True for f in fields)


def idle_ok(value, boot):
    return (exact_true_fields(value, Idle, ('complete', 'camera_clients_empty',
                'all_eight_suspended', 'strobe_off')) and value.boot == boot)


def evaluate(e, r, now):
    if type(e) is not Evidence:
        return ('missing_evidence',)
    reasons = []
    if (e.nonce, e.boot, e.uid) != (r.nonce, r.boot, r.uid):
        reasons.append('evidence_binding')
    if (type(e.uid) is not int or type(e.captured) not in (int, float) or
            not math.isfinite(e.captured) or not math.isfinite(now) or
            not r.started <= e.captured <= now < r.deadline):
        reasons.append('evidence_time')
    for field in ('complete_rgb_ir', 'verified_timebase', 'quality_passed',
                  'geometry_qualified', 'identity_qualified', 'pad_qualified',
                  'single_candidate', 'identity_matches_account', 'versions_match'):
        if getattr(e, field) is not True:
            reasons.append(field)
    return tuple(reasons)


def run(attempts, request, adapter, cancelled=lambda: False):
    """One attempt, no automatic retry. Release is attempted even on failure.

    This contract is testable, but cannot kill an uncooperative adapter. A real
    worker must run in a bounded process and retain its independent light stop.
    Adapter stop/restore/idle each need their own reviewed bounded deadlines.
    The production adapter is deliberately unavailable in this delivery.
    """
    reasons = []
    try:
        attempts.claim(request)
    except Exception:
        return Result(False, True, False, False, False, ('claim_rejected',))
    preflight_ok = False
    touched = False
    closed = restored = final_idle = False
    eligible = False
    try:
        if cancelled():
            reasons.append('cancelled_before_preflight')
        elif not idle_ok(adapter.preflight(request), request.boot):
            reasons.append('preflight_unknown_or_busy')
        else:
            preflight_ok = True
            if cancelled():
                reasons.append('cancelled_before_acquire')
            elif not request.started <= attempts.clock() < request.deadline:
                reasons.append('deadline_before_acquire')
            else:
                # Set before invoking: even a partly failed start needs stop.
                touched = True
                evidence = adapter.acquire(request)
                if cancelled():
                    reasons.append('cancelled_after_acquire')
                else:
                    reasons.extend(evaluate(evidence, request, attempts.clock()))
                    eligible = not reasons
    except Exception:
        reasons.append('adapter_failure')
    finally:
        if touched:
            try:
                closed = exact_true_fields(adapter.stop(request), Closure,
                    ('worker_stopped', 'light_off', 'native_closed', 'kernel_stopped', 'root_closed'))
            except Exception:
                pass
            if not closed:
                reasons.append('shutdown_unconfirmed')
            # Restoration may touch ioctl: only after a complete stop contract.
            if closed:
                try:
                    restored = adapter.restore(request) is True
                except Exception:
                    pass
                if not restored:
                    reasons.append('restoration_unconfirmed')
            try:
                final_idle = idle_ok(adapter.idle(request), request.boot)
            except Exception:
                pass
            if not final_idle:
                reasons.append('final_idle_unconfirmed')
    complete = closed and restored and final_idle if touched else False
    try:
        final_now = attempts.clock()
        fresh = (math.isfinite(final_now) and
                 request.started <= final_now < request.deadline and not cancelled())
    except Exception:
        fresh = False
    if touched and not fresh:
        reasons.append('expired_or_cancelled_during_release')
    eligible = eligible and complete and fresh
    # There is intentionally no success return and no qualified identity/PAD
    # backend. Even a synthetic all-true fixture only exercises the contract.
    reasons.append('research_profile_authentication_disabled')
    return Result(False, True, eligible, complete, touched and not complete, tuple(reasons))
