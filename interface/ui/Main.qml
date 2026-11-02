import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQml.Models

Rectangle {
    id: root
    width: 1280; height: 900; color: "#090d11"
    property QtObject authBackend: typeof sddm === "undefined" ? null : sddm
    property var accounts: typeof userModel === "undefined" ? null : userModel
    property var sessions: typeof sessionModel === "undefined" ? null : sessionModel
    readonly property string phase: cameraResearch.pending && !auth.pending && auth.phase !== "accepted" ? "verifying" : auth.phase
    readonly property string cameraResearchPhase: cameraResearch.phase
    property string attemptDisplayName: ""
    Instantiator {
        id: accountNames
        model: root.accounts
        delegate: QtObject {
            required property string name
            required property string realName
        }
    }
    function displayName(login) {
        for (let i=0; i<accountNames.count; i++) {
            const account=accountNames.objectAt(i);
            if (account && account.name === login)
                return account.realName.trim() || login;
        }
        return login;
    }
    AuthStatus { id: auth; backend: root.authBackend }
    CameraResearchStatus {
        id: cameraResearch
        objectName: "cameraResearchStatus"
        onPasswordFallbackRequired: root.presentPasswordFallback()
    }
    LoginSurface {
        anchors.fill: parent; anchors.bottomMargin: 220
        phase: root.phase
        statusDetail: auth.phase === "accepted" ? "" : cameraResearch.pending ?
            "Camera research is running. Authentication remains disabled." :
            cameraResearch.holdRequired ? "Camera shutdown is unconfirmed. Use your password." : ""
        identity: username.text
        welcomeName: root.attemptDisplayName
    }
    function submit() {
        if (cameraResearch.pending) return;
        if (!root.authBackend || !username.text.trim() || session.currentIndex < 0 || !auth.begin()) return;
        // Bind the greeting to this submitted account, not a later selection.
        root.attemptDisplayName=root.displayName(username.text.trim());
        // No password/biometric data is logged, persisted or sent to artwork.
        root.authBackend.login(username.text.trim(), secret.text, session.currentIndex);
        secret.clear();
    }
    function presentPasswordFallback() {
        if (!auth.presentPasswordFallback()) return false;
        root.attemptDisplayName="";
        secret.clear();
        secret.forceActiveFocus();
        return true;
    }
    function beginCameraResearch(token, login) {
        if (auth.pending || auth.phase === "accepted" || username.text.trim() !== login) return false;
        return cameraResearch.begin(token,login);
    }
    function finishCameraResearch(token, login, result) {
        if (!cameraResearch.finish(token,login,result)) return false;
        return true;
    }
    // No automatic backend is attached. This is a future trusted-controller
    // hook, not a GUI authority to start hardware or accept an identity.
    ColumnLayout {
        width: Math.min(420, root.width-48)
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom; anchors.bottomMargin: 28
        spacing: 10
        TextField {
            id: username; objectName: "username"; Layout.fillWidth: true; placeholderText: "Username"
            text: root.accounts ? root.accounts.lastUser : ""; enabled: !auth.pending && !cameraResearch.pending && auth.phase !== "accepted"
            Accessible.name: "Username"; onAccepted: secret.forceActiveFocus()
        }
        TextField {
            id: secret; objectName: "secret"; Layout.fillWidth: true; placeholderText: "Password"
            echoMode: TextInput.Password; selectByMouse: false
            enabled: !auth.pending && !cameraResearch.pending && auth.phase !== "accepted"
            Accessible.name: "Password"; onAccepted: root.submit()
            Component.onCompleted: forceActiveFocus()
        }
        RowLayout {
            ComboBox {
                id: session; Layout.fillWidth: true; model: root.sessions
                textRole: "name"; currentIndex: root.sessions ? root.sessions.lastIndex : -1
                enabled: !auth.pending && !cameraResearch.pending && auth.phase !== "accepted"
                Accessible.name: "Desktop session"
            }
            Button {
                text: auth.pending ? "Verifying…" : "Log in"
                enabled: !auth.pending && !cameraResearch.pending && auth.phase !== "accepted" && username.text.trim().length>0 && session.currentIndex>=0
                onClicked: root.submit()
            }
        }
        Label { text: "Password"; color: "#87949e"; font.pixelSize: 11; Layout.alignment: Qt.AlignHCenter }
    }
}
