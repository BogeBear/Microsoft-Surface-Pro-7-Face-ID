import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true; width: 1060; height: 790
    minimumWidth: 600; minimumHeight: 500
    title: "Surface IR — HAL design (simulation)"
    color: "#090d11"
    property string phase: "verifying"
    LoginSurface {
        id: surface; anchors.fill: parent; anchors.bottomMargin: 100
        phase: window.phase; demoMode: true; reducedMotion: motion.checked
        welcomeName: "Example User"
    }
    ColumnLayout {
        anchors.bottom: parent.bottom; anchors.bottomMargin: 16
        anchors.horizontalCenter: parent.horizontalCenter; spacing: 8
        RowLayout {
            Button { text: "Waiting"; onClicked: window.phase="idle" }
            Button { text: "Verifying"; onClicked: window.phase="verifying" }
            Button { text: "Show accepted"; onClicked: window.phase="accepted" }
            Button { text: "Show denied"; onClicked: window.phase="denied" }
            Button { text: "Show password fallback"; onClicked: window.phase="password_required" }
            CheckBox { id: motion; text: "Reduced motion" }
        }
        Label { Layout.alignment: Qt.AlignHCenter; text: "Design preview only. These buttons neither log in nor open cameras."; color: "#95a3ad" }
    }
    // Optional deterministic screenshots, only inside this explicit demo.
    Timer {
        interval: 800; running: Qt.application.arguments.indexOf("--snapshots") >= 0; repeat: false
        onTriggered: surface.grabToImage(function(result) {
            const args=Qt.application.arguments; const i=args.indexOf("--snapshots");
            if (!result.saveToFile(args[i+1]+"/hal-verifying.png")) Qt.exit(1);
            window.phase="accepted"; snapshotGreen.start();
        })
    }
    Timer {
        id: snapshotGreen; interval: 150
        onTriggered: surface.grabToImage(function(result) {
            const args=Qt.application.arguments; const i=args.indexOf("--snapshots");
            Qt.exit(result.saveToFile(args[i+1]+"/hal-accepted.png") ? 0 : 1);
        })
    }
}
