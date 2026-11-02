import QtQuick

Item {
    id: eye
    property string phase: "idle"
    property bool reducedMotion: false
    readonly property bool busy: phase === "verifying"
    readonly property color light: phase === "accepted" ? "#68f7a5" :
                                   phase === "error" ? "#ffc573" : "#ff4439"
    implicitWidth: 340
    implicitHeight: 340
    Accessible.role: Accessible.Indicator
    Accessible.name: phase === "accepted" ? "Login accepted" :
                     busy ? "Login in progress" : "Login pending"

    Canvas {
        id: lens
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        Connections {
            target: eye
            function onLightChanged() { lens.requestPaint() }
        }
        onPaint: {
            const c = getContext("2d"); c.reset();
            const x = width/2, y = height/2, r = Math.min(width,height)*0.44;
            function disc(radius, fill) {
                c.beginPath(); c.arc(x,y,radius,0,Math.PI*2); c.fillStyle=fill; c.fill();
            }
            let halo = c.createRadialGradient(x,y,r*.7,x,y,r*1.13);
            halo.addColorStop(0, "#00000000"); halo.addColorStop(.62,"#192027"); halo.addColorStop(1,"#00000000");
            disc(r*1.13,halo);
            let metal=c.createLinearGradient(x-r,y-r,x+r,y+r);
            metal.addColorStop(0,"#778087"); metal.addColorStop(.18,"#252d33");
            metal.addColorStop(.48,"#0e1216"); metal.addColorStop(.77,"#6c7276"); metal.addColorStop(1,"#151a1e");
            disc(r,metal); disc(r*.956,"#090b0e");
            c.strokeStyle="#4c5358"; c.lineWidth=1;
            c.beginPath(); c.arc(x,y,r*.924,0,2*Math.PI); c.stroke();
            disc(r*.89,"#050607");
            let glass=c.createRadialGradient(x-r*.17,y-r*.21,0,x,y,r*.87);
            glass.addColorStop(0,"#29171a"); glass.addColorStop(.5,"#0e0c11"); glass.addColorStop(1,"#020304");
            disc(r*.87,glass);
            const rgb=eye.light;
            let glow=c.createRadialGradient(x,y,0,x,y,r*.70);
            glow.addColorStop(0,Qt.rgba(rgb.r,rgb.g,rgb.b,.96));
            glow.addColorStop(.14,Qt.rgba(rgb.r,rgb.g,rgb.b,.92));
            glow.addColorStop(.24,Qt.rgba(rgb.r,rgb.g,rgb.b,.56));
            glow.addColorStop(.47,Qt.rgba(rgb.r,rgb.g,rgb.b,.13));
            glow.addColorStop(1,Qt.rgba(rgb.r,rgb.g,rgb.b,0));
            disc(r*.70,glow);
            let core=c.createRadialGradient(x-r*.035,y-r*.04,0,x,y,r*.17);
            core.addColorStop(0,"#fffbe1"); core.addColorStop(.2,"#fff1b8");
            core.addColorStop(.7,eye.light); core.addColorStop(1,Qt.rgba(rgb.r,rgb.g,rgb.b,0));
            disc(r*.17,core);
            // A quiet crescent reflection, painted once rather than an animated video.
            c.save(); c.translate(x-r*.12,y-r*.48); c.rotate(-.45); c.scale(1,.26);
            c.beginPath(); c.arc(0,0,r*.38,0,2*Math.PI);
            c.fillStyle="#14ffffff"; c.fill(); c.restore();
            c.strokeStyle="#0dffffff"; c.lineWidth=1;
            for(let i=0;i<7;i++) { c.beginPath(); c.arc(x,y,r*(.61+i*.031),.1,Math.PI*.83); c.stroke(); }
        }
    }
    Item {
        anchors.fill: parent
        visible: eye.busy
        NumberAnimation on rotation {
            from: 0; to: 360; duration: 4200; loops: Animation.Infinite
            running: eye.visible && eye.busy && !eye.reducedMotion
        }
        Canvas {
            anchors.fill: parent
            onPaint: {
                const c=getContext("2d"); c.reset(); c.lineWidth=2;
                c.strokeStyle="#a5b6be";
                c.beginPath(); c.arc(width/2,height/2,Math.min(width,height)*.482,-.45,.45); c.stroke();
            }
        }
    }
}
