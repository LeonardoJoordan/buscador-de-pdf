import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: root
    width: 1280
    height: 768
    minimumWidth: 1060
    minimumHeight: 600
    visible: true
    title: "Buscador de Conteúdo PDF"

    color: "#1e1e24"

    MouseArea {
        anchors.fill: parent
        z: 1000
        acceptedButtons: Qt.AllButtons
        onPressed: (mouse) => {
            const pointInSearch = searchInput.mapFromItem(this, mouse.x, mouse.y)
            if (searchInput.activeFocus && !searchInput.contains(pointInSearch)) {
                searchInput.focus = false
                focusTarget.forceActiveFocus()
            }
            // Entrega o mesmo clique ao controle abaixo.
            mouse.accepted = false
        }
    }

    Item { id: focusTarget }

    // Cor da borda do card de resultado conforme a categoria do match:
    // verde = frase exata (mesma página), azul = frase exata (entre páginas),
    // roxo = mesmas palavras fora de ordem, laranja = aproximação (fuzzy).
    function matchColor(matchType) {
        switch (matchType) {
            case "green": return "#4caf50";
            case "blue": return "#3d7eff";
            case "purple": return "#9b59b6";
            case "orange": return "#ff9800";
            default: return "#343440";
        }
    }

    readonly property real zoomMin: 0.4
    readonly property real zoomMax: 3.5
    readonly property real zoomStep: 0.15
    property real userZoom: 1.0

    function zoomBy(delta) {
        userZoom = Math.min(zoomMax, Math.max(zoomMin, userZoom + delta))
    }

    function resetZoom() {
        userZoom = 1.0
        Qt.callLater(centerPreview)
    }

    function centerPreview() {
        flick.contentX = Math.max(0, (flick.contentWidth - flick.width) / 2)
        flick.contentY = Math.max(0, (flick.contentHeight - flick.height) / 2)
    }

    onUserZoomChanged: Qt.callLater(centerPreview)

    function navigationReady() {
        return !searchInput.activeFocus && !advancedSettingsDialog.visible
    }

    function openResultAt(index) {
        if (index < 0 || index >= Bridge.searchResults.length)
            return
        resultsList.currentIndex = index
        resultsList.positionViewAtIndex(index, ListView.Contain)
        const item = Bridge.searchResults[index]
        Bridge.setPreview(item.filepath, item.page_number)
    }

    function moveResult(delta) {
        if (Bridge.searchResults.length === 0)
            return
        let idx = resultsList.currentIndex
        if (idx < 0)
            idx = delta > 0 ? 0 : Bridge.searchResults.length - 1
        else
            idx = Math.max(0, Math.min(Bridge.searchResults.length - 1, idx + delta))
        openResultAt(idx)
    }

    Shortcut {
        sequence: "Up"
        enabled: root.navigationReady() && Bridge.searchResults.length > 0
        onActivated: root.moveResult(-1)
    }
    Shortcut {
        sequence: "Down"
        enabled: root.navigationReady() && Bridge.searchResults.length > 0
        onActivated: root.moveResult(1)
    }
    Shortcut {
        sequence: "Left"
        enabled: root.navigationReady() && Bridge.currentFilepath !== ""
        onActivated: Bridge.changePage(-1)
    }
    Shortcut {
        sequence: "Right"
        enabled: root.navigationReady() && Bridge.currentFilepath !== ""
        onActivated: Bridge.changePage(1)
    }

    FolderDialog {
        id: folderPicker
        title: "Selecione a pasta com PDFs"
        onAccepted: {
            Bridge.startIndexing(selectedFolder)
        }
    }

    Dialog {
        id: advancedSettingsDialog
        title: "Configurações Avançadas de Busca"
        modal: true
        standardButtons: Dialog.Close
        anchors.centerIn: parent
        width: 400

        contentItem: ColumnLayout {
            spacing: 14

            Text {
                text: "Ajuste como o buscador deve lidar com pequenas variações no texto pesquisado."
                wrapMode: Text.Wrap
                color: "#c8c8cf"
                font.pixelSize: 12
                Layout.fillWidth: true
            }

            Text {
                text: "Marcar termos no preview"
                color: "#c8c8cf"
                font.bold: true
            }
            ComboBox {
                Layout.fillWidth: true
                model: ["Todos os termos", "Somente termos exatos",
                        "Somente aproximados / fora de ordem"]
                currentIndex: ["all", "exact", "approximate"].indexOf(Bridge.previewHighlightMode)
                onActivated: Bridge.setPreviewHighlightMode(["all", "exact", "approximate"][currentIndex])
            }
            Text {
                text: "Verde claro: palavra completa ou frase na ordem exata (ignora caixa e acentos). Amarelo: termos isolados, fora de ordem ou aproximados. A aproximação usa a semelhança mínima abaixo."
                wrapMode: Text.Wrap
                color: "#8b8b96"
                font.pixelSize: 11
                Layout.fillWidth: true
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                CheckBox {
                    id: outOfOrderCheck
                    text: "Considerar palavras fora de ordem (🟣 roxo)"
                    checked: Bridge.allowOutOfOrder
                    onToggled: Bridge.setAllowOutOfOrder(checked)
                }
                Text {
                    text: "Encontra páginas com todas as palavras buscadas, mesmo que não estejam na ordem exata."
                    wrapMode: Text.Wrap
                    color: "#8b8b96"
                    font.pixelSize: 11
                    Layout.fillWidth: true
                    Layout.leftMargin: 28
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                CheckBox {
                    id: fuzzyCheck
                    text: "Habilitar busca aproximada (🟠 laranja)"
                    checked: Bridge.allowFuzzy
                    onToggled: Bridge.setAllowFuzzy(checked)
                }
                Text {
                    text: "Mostra resultados parecidos mesmo com pequenos erros de digitação."
                    wrapMode: Text.Wrap
                    color: "#8b8b96"
                    font.pixelSize: 11
                    Layout.fillWidth: true
                    Layout.leftMargin: 28
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 28
                    Layout.topMargin: 6
                    enabled: fuzzyCheck.checked
                    opacity: enabled ? 1.0 : 0.4
                    spacing: 4

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Semelhança mínima"
                            color: "#c8c8cf"
                            font.pixelSize: 12
                            Layout.fillWidth: true
                        }
                        Text {
                            text: fuzzySlider.value.toFixed(0) + "%"
                            color: "#ff9800"
                            font.bold: true
                            font.pixelSize: 12
                        }
                    }
                    Slider {
                        id: fuzzySlider
                        Layout.fillWidth: true
                        from: 40
                        to: 95
                        stepSize: 5
                        value: Bridge.fuzzyThreshold
                        onMoved: Bridge.setFuzzyThreshold(value)
                    }
                }
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 1

        // ==========================================
        // PAINEL 1: SIDEBAR (Catálogo e Indexação)
        // ==========================================
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 260
            color: "#25252d"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 10

                Text {
                    text: "Arquivos Indexados"
                    font.pixelSize: 15
                    font.bold: true
                    color: "#e0e0e0"
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: false
                    spacing: 6

                    Button {
                        text: Bridge.isIndexing ? "Indexando..." : "📁 Selecionar Pasta"
                        enabled: !Bridge.isIndexing
                        Layout.fillWidth: true
                        onClicked: folderPicker.open()
                    }

                    Button {
                        text: "🔄"
                        enabled: !Bridge.isIndexing && Bridge.indexedFiles.length > 0
                        implicitWidth: 40
                        ToolTip.visible: hovered
                        ToolTip.text: "Reindexar arquivos já catalogados"
                        onClicked: Bridge.reindexAll()
                    }
                }

                ProgressBar {
                    Layout.fillWidth: true
                    visible: Bridge.isIndexing
                    indeterminate: true
                }

                ListView {
                    id: fileList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: Bridge.indexedFiles
                    spacing: 4
                    ScrollBar.vertical: StyledScrollBar {}

                    delegate: Rectangle {
                        // Deixa folga à direita para a scrollbar overlay não cobrir o item
                        width: fileList.width - 16
                        height: 48
                        color: fileArea.containsMouse ? "#32323c" : "#2a2a34"
                        radius: 4

                        MouseArea {
                            id: fileArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: Bridge.setPreview(modelData.filepath, 1)
                        }

                        Column {
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 2
                            Text {
                                text: modelData.filename
                                color: "#ffffff"
                                font.pixelSize: 12
                                font.bold: true
                                elide: Text.ElideMiddle
                                width: parent.width
                            }
                            Text {
                                text: modelData.page_count + " páginas"
                                color: "#8b8b96"
                                font.pixelSize: 11
                            }
                        }
                    }
                }
            }
        }

        // ==========================================
        // PAINEL 2: BUSCADOR & RESULTADOS
        // ==========================================
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 420
            color: "#1e1e24"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: false
                    spacing: 6

                    TextField {
                        id: searchInput
                        onAccepted: if (!Bridge.isSearching) Bridge.search(text)
                        placeholderText: "Buscar palavra ou frase..."
                        Layout.fillWidth: true
                        font.pixelSize: 14
                        color: "#ffffff"
                        background: Rectangle {
                            color: "#2a2a34"
                            radius: 6
                            border.color: searchInput.activeFocus ? "#3d7eff" : "#3e3e48"
                        }

                    }

                    Button {
                        text: "Buscar"
                        enabled: !Bridge.isSearching
                        Layout.preferredHeight: searchInput.implicitHeight
                        onClicked: Bridge.search(searchInput.text)
                    }

                    Button {
                        text: "⚙"
                        implicitWidth: 40
                        Layout.preferredHeight: searchInput.implicitHeight
                        ToolTip.visible: hovered
                        ToolTip.text: "Configurações avançadas de busca"
                        onClicked: advancedSettingsDialog.open()
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    BusyIndicator {
                        running: Bridge.isSearching
                        visible: running
                        Layout.preferredWidth: 20
                        Layout.preferredHeight: 20
                    }
                    Text {
                        Layout.fillWidth: true
                        text: Bridge.isSearching ? "Buscando…" : (Bridge.searchError || Bridge.searchResults.length + " resultados encontrados")
                        wrapMode: Text.Wrap
                        font.pixelSize: 12
                        color: Bridge.searchError ? "#ff8a80" : "#8b8b96"
                    }
                }

                ListView {
                    id: resultsList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 8
                    model: Bridge.searchResults
                    currentIndex: -1
                    highlightMoveDuration: 0
                    ScrollBar.vertical: StyledScrollBar {}

                    onModelChanged: currentIndex = -1

                    delegate: Rectangle {
                        // Deixa folga à direita para a scrollbar overlay não cobrir o card
                        width: resultsList.width - 16
                        height: textSnippet.implicitHeight + 40
                        color: {
                            if (resultsList.currentIndex === index)
                                return hitArea.containsMouse ? "#3d3d4c" : "#353545"
                            return hitArea.containsMouse ? "#2f2f3d" : "#25252e"
                        }
                        radius: 6
                        border.width: resultsList.currentIndex === index ? 3 : 2
                        border.color: matchColor(modelData.matchType)

                        MouseArea {
                            id: hitArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: root.openResultAt(index)
                        }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: modelData.filepath.split('/').pop()
                                    font.bold: true
                                    font.pixelSize: 12
                                    color: "#5ca0f2"
                                    Layout.fillWidth: true
                                    elide: Text.ElideMiddle
                                }
                                Text {
                                    text: (modelData.page_end && modelData.page_end !== modelData.page_number)
                                          ? "Pág. " + modelData.page_number + "–" + modelData.page_end
                                          : "Pág. " + modelData.page_number
                                    font.pixelSize: 11
                                    color: "#ffca64"
                                }
                                Text {
                                    visible: modelData.matchType === "orange"
                                    text: "~" + modelData.score.toFixed(0) + "%"
                                    font.pixelSize: 11
                                    font.bold: true
                                    color: matchColor(modelData.matchType)
                                }
                            }

                            // Renderiza HTML do snippet retornado pelo FTS5 (com <b>)
                            Text {
                                id: textSnippet
                                text: modelData.snippet
                                textFormat: Text.RichText
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                                font.pixelSize: 12
                                color: "#c8c8cf"
                            }
                        }
                    }
                }
            }
        }

        // ==========================================
        // PAINEL 3: PRÉVIA (Zoom, Pan e Abertura)
        // ==========================================
        Rectangle {
            Layout.fillHeight: true
            Layout.fillWidth: true
            color: "#16161a"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                // Barra superior de paginação centralizada
                RowLayout {
                    Layout.alignment: Qt.AlignHCenter
                    visible: Bridge.currentFilepath !== ""

                    Button {
                        text: "◀"
                        onClicked: Bridge.changePage(-1)
                    }

                    Text {
                        text: "Pág. " + Bridge.currentPage + " de " + Bridge.currentTotalPages
                        color: "#ffffff"
                        font.pixelSize: 13
                    }

                    Button {
                        text: "▶"
                        onClicked: Bridge.changePage(1)
                    }


                }

                // Área rolável: zoom centralizado; arraste com o mouse para mover
                Flickable {
                    id: flick
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    flickableDirection: Flickable.HorizontalAndVerticalFlick
                    contentWidth: Math.max(width, previewImg.width)
                    contentHeight: Math.max(height, previewImg.height)

                    WheelHandler {
                        acceptedButtons: Qt.NoButton
                        onWheel: (event) => {
                            root.zoomBy(event.angleDelta.y > 0 ? root.zoomStep : -root.zoomStep)
                            event.accepted = true
                        }
                    }

                    Image {
                        id: previewImg
                        source: Bridge.previewImagePath
                        asynchronous: true
                        cache: false
                        smooth: true
                        fillMode: Image.Stretch
                        x: Math.max(0, (flick.contentWidth - width) / 2)
                        y: Math.max(0, (flick.contentHeight - height) / 2)
                        width: {
                            if (implicitWidth <= 0 || implicitHeight <= 0)
                                return 0
                            var fit = Math.min(flick.width / implicitWidth, flick.height / implicitHeight)
                            return implicitWidth * fit * root.userZoom
                        }
                        height: {
                            if (implicitWidth <= 0 || implicitHeight <= 0)
                                return 0
                            var fit = Math.min(flick.width / implicitWidth, flick.height / implicitHeight)
                            return implicitHeight * fit * root.userZoom
                        }

                        onStatusChanged: {
                            if (status === Image.Ready)
                                Qt.callLater(root.centerPreview)
                        }
                    }
                }

                // Ações do arquivo e zoom na mesma barra.
                Item {
                    Layout.fillWidth: true
                    implicitHeight: Math.max(openPdfButton.implicitHeight, zoomControls.implicitHeight,
                                             resetZoomButton.implicitHeight)
                    visible: Bridge.currentFilepath !== ""

                    Button {
                        id: openPdfButton
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Abrir PDF"
                        ToolTip.visible: hovered
                        ToolTip.text: "Abrir no visualizador do sistema"
                        onClicked: Bridge.openInSystemViewer(Bridge.currentFilepath, Bridge.currentPage)
                    }

                    RowLayout {
                        id: zoomControls
                        anchors.centerIn: parent
                        spacing: 4

                        Button {
                            text: "−"
                            implicitWidth: 32
                            enabled: root.userZoom > root.zoomMin + 0.001
                            ToolTip.visible: hovered
                            ToolTip.text: "Diminuir zoom"
                            onClicked: root.zoomBy(-root.zoomStep)
                        }
                        Text {
                            text: Math.round(root.userZoom * 100) + "%"
                            color: "#c8c8cf"
                            font.pixelSize: 12
                            Layout.preferredWidth: 44
                            horizontalAlignment: Text.AlignHCenter
                        }
                        Button {
                            text: "+"
                            implicitWidth: 32
                            enabled: root.userZoom < root.zoomMax - 0.001
                            ToolTip.visible: hovered
                            ToolTip.text: "Aumentar zoom"
                            onClicked: root.zoomBy(root.zoomStep)
                        }
                    }

                    Button {
                        id: resetZoomButton
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Resetar Zoom"
                        enabled: Math.abs(root.userZoom - 1.0) > 0.001
                        onClicked: root.resetZoom()
                    }
                }
            }
        }
    }
}
