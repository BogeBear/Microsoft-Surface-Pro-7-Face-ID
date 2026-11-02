// SPDX-License-Identifier: MIT
import QtQuick

// Presentation only. No camera start, credential, presence claim or login grant.
QtObject {
    id: state
    property string phase: "idle"
    property string attemptId: ""
    property string account: ""
    property bool holdRequired: false
    property var consumed: []
    signal passwordFallbackRequired()
    readonly property bool pending: phase === "capturing" || phase === "releasing"
    readonly property bool passwordRequired: phase === "password_required" || phase === "cleanup_unconfirmed"
    function begin(token, login) {
        if (pending || holdRequired || typeof token !== "string" || !/^[a-f0-9]{64}$/.test(token) ||
                typeof login !== "string" || !login.trim() || login.length > 256 ||
                consumed.indexOf(token) >= 0) return false;
        attemptId=token; account=login; phase="capturing";
        expiry.restart();
        return true;
    }
    function releasing(token, login) {
        if (!pending || token !== attemptId || login !== account) return false;
        phase="releasing";
        // Never extend the presentation deadline. The root worker's independent
        // watchdog and shutdown contract cannot be replaced by this UI timer.
        return true;
    }
    function finish(token, login, result) {
        if (!pending || token !== attemptId || login !== account) return false;
        expiry.stop();
        const complete=result && result.authentication_allowed === false &&
            result.password_fallback === true && result.shutdown_confirmed === true &&
            result.hold_required === false;
        consumed=consumed.concat([attemptId]).slice(-16);
        attemptId=""; account="";
        holdRequired=!complete;
        phase=complete ? "password_required" : "cleanup_unconfirmed";
        passwordFallbackRequired();
        return true;
    }
    function expire() {
        if (!pending) return false;
        return finish(attemptId,account,null);
    }
    // No "accepted" state, success signal or administrative hold-clear method.
    property Timer expiry: Timer { interval: 8000; repeat: false; onTriggered: state.expire() }
}
