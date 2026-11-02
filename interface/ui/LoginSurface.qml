import QtQuick
import QtQuick.Controls

Rectangle {
    id: surface
    color: "#090d11"
    property string phase: "idle"
    property bool demoMode: false
    property bool reducedMotion: false
    property string identity: ""
    property string welcomeName: ""
    readonly property color accent: phase === "accepted" ? "#68f7a5" : "#ff665b"
    readonly property string heading: phase === "accepted" ?
        (welcomeName.trim() ? "Welcome, " + welcomeName.trim() : "Welcome back.") :
        phase === "password_required" ? "Log in with a password" :
        phase === "verifying" ? "Verifying login" : phase === "denied" ? "Try again" :
        phase === "error" ? "Login cancelled" : "Ready when you are."
    readonly property string description: phase === "accepted" ? "Login accepted" :
        phase === "password_required" ? "Biometrics could not be verified. Use your password." :
        phase === "verifying" ? "Wait while your identity is checked." :
        phase === "denied" ? "Login could not be accepted." :
        phase === "error" ? "You can try again." : "Choose how to log in."
    // Only the artwork is reused. This item cannot authorize or start a camera.
    Item {
        id: design
        width: 1000; height: 660
        anchors.centerIn: parent
        scale: Math.min(surface.width/1000, surface.height/660)
        Text {
            x: 42; y: 30; text: "SURFACE / IR"; color: "#d7dfe5"
            font.family: "sans-serif"; font.pixelSize: 14; font.letterSpacing: 3
        }
        Text {
            anchors.right: parent.right; anchors.rightMargin: 42; y: 32
            text: surface.demoMode ? "DESIGN PREVIEW" : "LOGIN"
            color: "#87949e"; font.pixelSize: 11; font.letterSpacing: 2
        }
        Rectangle { x: 42; y: 67; width: 916; height: 1; color: "#263039" }
        HalEye {
            id: eye; objectName: "halEye"
            x: 330; y: 91; width: 340; height: 340
            phase: surface.phase; reducedMotion: surface.reducedMotion
        }
        Text {
            x: 60; y: 434; width: 880; horizontalAlignment: Text.AlignHCenter
            text: surface.identity; visible: text.length > 0 && surface.phase !== "accepted"
            textFormat: Text.PlainText
            color: "#87949e"; font.pixelSize: 14
        }
        Text {
            x: 40; y: 464; width: 920; horizontalAlignment: Text.AlignHCenter
            objectName: "welcomeHeading"
            text: surface.heading; textFormat: Text.PlainText
            color: "#f4f6f8"; font.pixelSize: 32; font.weight: Font.Light
            fontSizeMode: Text.HorizontalFit; minimumPixelSize: 20; elide: Text.ElideRight
            Accessible.role: Accessible.StaticText; Accessible.name: text
        }
        Row {
            anchors.horizontalCenter: parent.horizontalCenter; y: 520; spacing: 10
            Rectangle { width: 5; height: 5; radius: 3; color: surface.accent; anchors.verticalCenter: parent.verticalCenter }
            Text { text: surface.description; color: "#9ba8b1"; font.pixelSize: 14 }
        }
        Text {
            x: 42; y: 611; color: "#65737e"; font.pixelSize: 11; font.letterSpacing: 1
            text: surface.demoMode ? "SIMULATION · NO CAMERA ACTIVE" : "SURFACE · MANJARO"
        }
    }
}
