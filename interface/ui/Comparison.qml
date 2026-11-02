import QtQuick
import QtQuick.Window

Window {
    visible: true; width: 1400; height: 470; color: "#090d11"
    title: "Surface HAL — design preview"
    Item {
        id: comparison; anchors.fill: parent
        LoginSurface { x: 0; width: 700; height: 470; phase: "verifying"; demoMode: true; reducedMotion: true }
        LoginSurface { x: 700; width: 700; height: 470; phase: "accepted"; welcomeName: "Example User"; demoMode: true; reducedMotion: true }
        Rectangle { x: 699; width: 1; height: 390; y: 40; color: "#263039" }
    }
    Timer {
        interval: 500; running: Qt.application.arguments.indexOf("--output") >= 0
        onTriggered: comparison.grabToImage(function(result) {
            const args=Qt.application.arguments; const i=args.indexOf("--output");
            Qt.exit(result.saveToFile(args[i+1]) ? 0 : 1);
        })
    }
}
