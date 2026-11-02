import QtQuick

QtObject {
    id: state
    required property QtObject backend
    property string phase: "idle"
    readonly property bool pending: phase === "verifying"
    function presentPasswordFallback() {
        // Presentation hook for the future biometric coordinator, before a
        // password request. Existing SDDM requests cannot be locally cancelled.
        if (pending || phase === "accepted") return false;
        phase = "password_required";
        return true;
    }
    // SDDM has no per-attempt ID in its public proxy. Never overlap attempts,
    // never locally cancel an outstanding request and accept a late reply.
    function begin() {
        if (pending || phase === "accepted") return false;
        phase = "verifying";
        return true;
    }
    property Connections resultSignals: Connections {
        target: state.backend
        function onLoginSucceeded() { if (state.pending) state.phase="accepted" }
        function onLoginFailed() { if (state.pending) state.phase="denied" }
    }
}
