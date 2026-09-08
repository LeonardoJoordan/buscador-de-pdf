import QtQuick
import QtQuick.Controls

// Scrollbar customizada: mais larga e com bom contraste no tema escuro,
// sempre visível (não só ao passar o mouse), para ficar fácil de arrastar.
ScrollBar {
    id: control
    policy: ScrollBar.AlwaysOn
    implicitWidth: 12

    contentItem: Rectangle {
        implicitWidth: 8
        radius: 4
        color: control.pressed ? "#5ca0f2" : "#4a4a58"
    }

    background: Rectangle {
        implicitWidth: 8
        radius: 4
        color: "#242430"
    }
}
