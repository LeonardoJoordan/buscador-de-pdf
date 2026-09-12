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
    title: "LYNX Atlas — Fast PDF Search & Indexing"

    color: "#1e1e24"

    // Mantém os controles Fusion no mesmo tema escuro em qualquer sistema.
    palette.window: "#1e1e24"
    palette.windowText: "#e0e0e0"
    palette.base: "#2a2a34"
    palette.alternateBase: "#25252d"
    palette.text: "#e0e0e0"
    palette.button: "#343440"
    palette.buttonText: "#ffffff"
    palette.highlight: "#3d7eff"
    palette.highlightedText: "#ffffff"
    palette.placeholderText: "#8b8b96"
    palette.toolTipBase: "#343440"
    palette.toolTipText: "#ffffff"

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

    function fileName(filepath) {
        return filepath.replace(/\\/g, "/").split("/").pop()
    }

    readonly property real zoomMin: 0.4
    readonly property real zoomMax: 3.5
    readonly property real zoomStep: 0.15
    property real userZoom: 1.0
    property real savedPreviewX: 0
    property real savedPreviewY: 0
    property bool restoringGeneralPreview: false
    property int selectedManualCount: 0
    property var generalViewState: null
    property var directedViewState: null
    property var unsupportedExtensions: []

    ListModel { id: directedManualsModel }

    function refreshDirectedManuals() {
        if (Bridge.isDirectedSearch)
            return
        directedManualsModel.clear()
        selectedManualCount = 0
        for (let i = 0; i < Bridge.resultManuals.length; ++i) {
            const manual = Bridge.resultManuals[i]
            const selected = Bridge.directedFilepaths.indexOf(manual.filepath) >= 0
            directedManualsModel.append({
                filepath: manual.filepath,
                filename: manual.filename,
                result_count: manual.result_count,
                selected: selected
            })
            if (selected)
                selectedManualCount++
        }
    }

    function selectedManualPaths() {
        let paths = []
        for (let i = 0; i < directedManualsModel.count; ++i) {
            if (directedManualsModel.get(i).selected)
                paths.push(directedManualsModel.get(i).filepath)
        }
        return paths
    }

    function captureViewState() {
        return {text: searchInput.text, index: resultsList.currentIndex,
                resultsY: resultsList.contentY, zoom: userZoom,
                previewX: flick.contentX, previewY: flick.contentY}
    }

    function restoreViewState(state) {
        searchInput.text = state ? state.text : Bridge.currentQuery
        if (!state)
            return
        savedPreviewX = state.previewX
        savedPreviewY = state.previewY
        restoringGeneralPreview = true
        userZoom = state.zoom
        Qt.callLater(function() {
            resultsList.currentIndex = state.index
            resultsList.forceLayout()
            resultsList.contentY = state.resultsY
            root.finishPreviewRestore()
        })
    }

    function finishPreviewRestore() {
        if (!restoringGeneralPreview || previewImg.status === Image.Loading)
            return
        flick.contentX = savedPreviewX
        flick.contentY = savedPreviewY
        restoringGeneralPreview = false
    }

    function beginDirectedSearch() {
        const state = captureViewState()
        const paths = selectedManualPaths()
        const previousPaths = Bridge.directedFilepaths
        const scopeChanged = paths.length !== previousPaths.length ||
                             paths.some(path => previousPaths.indexOf(path) < 0)
        if (Bridge.beginDirectedSearch(paths)) {
            generalViewState = state
            let view = directedViewState
            if (view && scopeChanged) {
                view = Object.assign({}, view, {text: Bridge.currentQuery, index: -1, resultsY: 0})
            }
            restoreViewState(view)
            if (!directedViewState)
                searchInput.forceActiveFocus()
        }
    }

    function returnToGeneralSearch() {
        const state = captureViewState()
        if (!Bridge.returnToGeneralSearch())
            return
        directedViewState = state
        restoreViewState(generalViewState)
    }

    Connections {
        target: Bridge
        function onSearchResultsChanged() { root.refreshDirectedManuals() }
        function onGeneralSearchReplaced() {
            root.directedViewState = null
            root.generalViewState = null
            root.restoringGeneralPreview = false
        }
        function onDirectedSearchChanged() {
            if (!Bridge.isDirectedSearch)
                root.refreshDirectedManuals()
        }
        function onUnsupportedExtensionsFound(extensions) {
            root.unsupportedExtensions = extensions
            unsupportedFilesDialog.open()
        }
    }

    Component.onCompleted: refreshDirectedManuals()

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

    onUserZoomChanged: {
        if (!restoringGeneralPreview)
            Qt.callLater(centerPreview)
    }

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
        id: unsupportedFilesDialog
        title: "Formatos não indexados"
        modal: true
        standardButtons: Dialog.Ok
        anchors.centerIn: parent
        width: Math.min(620, root.width - 48)

        contentItem: ColumnLayout {
            spacing: 12

            Text {
                Layout.fillWidth: true
                text: "A pasta selecionada contém arquivos "
                      + root.unsupportedExtensions.join(", ") + "."
                wrapMode: Text.Wrap
                color: "#e0e0e0"
                font.pixelSize: 12
            }

            Text {
                Layout.fillWidth: true
                text: "Esses formatos não serão indexados. Para pesquisar o conteúdo "
                      + "desses arquivos, exporte-os para PDF usando o aplicativo de "
                      + "origem, coloque as versões em PDF nesta pasta e clique no "
                      + "botão Reindexar do programa."
                wrapMode: Text.Wrap
                color: "#c8c8cf"
                font.pixelSize: 12
            }

            Text {
                Layout.fillWidth: true
                text: "Os arquivos PDF encontrados já estão sendo indexados normalmente."
                wrapMode: Text.Wrap
                color: "#8b8b96"
                font.pixelSize: 11
            }
        }
    }

    Dialog {
        id: aboutDialog
        title: "Sobre o LYNX Atlas"
        modal: true
        standardButtons: Dialog.Close
        anchors.centerIn: parent
        width: Math.min(520, root.width - 48)

        contentItem: ColumnLayout {
            spacing: 10
            Text {
                text: "LYNX Atlas"
                color: "#ffffff"
                font.pixelSize: 20
                font.bold: true
            }
            Text {
                text: "Fast PDF Search & Indexing"
                color: "#8b8b96"
                font.pixelSize: 11
            }
            Text {
                Layout.fillWidth: true
                text: "Software livre sob GNU AGPL v3.0. Este programa é fornecido "
                      + "sem qualquer garantia. Você pode redistribuí-lo e modificá-lo "
                      + "nos termos da licença."
                wrapMode: Text.Wrap
                color: "#c8c8cf"
                font.pixelSize: 12
            }
            Text {
                text: "Código-fonte e licenças"
                color: linkArea.containsMouse ? "#82b1ff" : "#5ca0f2"
                font.pixelSize: 12
                font.underline: true
                MouseArea {
                    id: linkArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: Qt.openUrlExternally("https://github.com/LeonardoJoordan/buscador-de-pdf")
                }
            }
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
                id: sidebarLayout
                anchors.fill: parent
                anchors.margins: 12
                spacing: 10

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 1

                    Text {
                        text: "LYNX Atlas"
                        color: "#ffffff"
                        font.pixelSize: 21
                        font.bold: true
                    }
                    Text {
                        text: "Fast PDF Search & Indexing"
                        color: "#8b8b96"
                        font.pixelSize: 10
                    }
                }

                ColumnLayout {
                    id: directedSearchPanel
                    property bool expanded: false
                    Layout.fillWidth: true
                    Layout.fillHeight: false
                    spacing: 6

                        ToolButton {
                            id: directedHeader
                            Layout.fillWidth: true
                            implicitHeight: 32
                            padding: 4
                            onClicked: directedSearchPanel.expanded = !directedSearchPanel.expanded
                            contentItem: Text {
                                text: (directedSearchPanel.expanded ? "▾  " : "▸  ") + "Busca direcionada"
                                color: "#ffffff"
                                font.pixelSize: 14
                                font.bold: true
                                elide: Text.ElideRight
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        Text {
                            visible: directedSearchPanel.expanded && directedManualsModel.count === 0
                            text: "Faça uma busca geral para escolher os manuais."
                            wrapMode: Text.Wrap
                            color: "#8b8b96"
                            font.pixelSize: 11
                            Layout.fillWidth: true
                        }

                        ListView {
                            id: directedManualsList
                            visible: directedSearchPanel.expanded && directedManualsModel.count > 0
                            Layout.fillWidth: true
                            Layout.fillHeight: false
                            Layout.preferredHeight: Math.min(
                                directedManualsModel.count * 40 + Math.max(0, directedManualsModel.count - 1) * spacing,
                                Math.max(0, sidebarLayout.height / 2 - directedHeader.implicitHeight
                                         - directedSearchButton.implicitHeight
                                         - (manualSelectionActions.visible ? manualSelectionActions.implicitHeight : 0)
                                         - directedSearchPanel.spacing * (manualSelectionActions.visible ? 3 : 2)))
                            clip: true
                            spacing: 2
                            model: directedManualsModel
                            ScrollBar.vertical: StyledScrollBar {
                                id: directedScrollBar
                                policy: ScrollBar.AsNeeded
                                visible: directedManualsList.contentHeight > directedManualsList.height + 0.5
                            }

                            delegate: CheckBox {
                                id: manualCheck
                                width: directedManualsList.width - (directedScrollBar.visible ? 12 : 0)
                                height: 40
                                padding: 6
                                spacing: 6
                                checked: model.selected
                                enabled: !Bridge.isDirectedSearch && !Bridge.isSearching
                                onToggled: {
                                    if (model.selected === checked)
                                        return
                                    directedManualsModel.setProperty(index, "selected", checked)
                                    root.selectedManualCount += checked ? 1 : -1
                                }
                                contentItem: RowLayout {
                                    spacing: 4
                                    Item { Layout.preferredWidth: 22 }
                                    Text {
                                        text: model.filename
                                        color: parent.parent.enabled ? "#e0e0e0" : "#9999a3"
                                        font.pixelSize: 11
                                        elide: Text.ElideMiddle
                                        Layout.fillWidth: true
                                    }
                                    Text {
                                        text: model.result_count
                                        color: "#8b8b96"
                                        font.pixelSize: 11
                                    }
                                }
                                indicator: Rectangle {
                                    x: manualCheck.leftPadding
                                    y: (manualCheck.height - height) / 2
                                    width: 16
                                    height: 16
                                    radius: 3
                                    color: manualCheck.checked ? "#3d7eff" : "#25252d"
                                    border.color: manualCheck.checked ? "#3d7eff" : "#777783"
                                    Text {
                                        anchors.centerIn: parent
                                        text: manualCheck.checked ? "✓" : ""
                                        color: "white"
                                        font.pixelSize: 12
                                    }
                                }
                                background: Rectangle {
                                    color: manualCheck.hovered ? "#32323c" : "#2a2a34"
                                    radius: 4
                                }
                                ToolTip.visible: hovered
                                ToolTip.text: model.filepath
                            }
                        }

                        RowLayout {
                            id: manualSelectionActions
                            enabled: !Bridge.isDirectedSearch && !Bridge.isSearching
                            visible: directedSearchPanel.expanded && directedManualsModel.count > 0
                                     && !Bridge.isDirectedSearch
                            Layout.fillWidth: true
                            spacing: 6
                            Button {
                                text: "Todos"
                                Layout.fillWidth: true
                                Layout.preferredWidth: 0
                                onClicked: {
                                    for (let i = 0; i < directedManualsModel.count; ++i)
                                        directedManualsModel.setProperty(i, "selected", true)
                                    root.selectedManualCount = directedManualsModel.count
                                }
                            }
                            Button {
                                text: "Limpar"
                                Layout.fillWidth: true
                                Layout.preferredWidth: 0
                                onClicked: {
                                    for (let i = 0; i < directedManualsModel.count; ++i)
                                        directedManualsModel.setProperty(i, "selected", false)
                                    root.selectedManualCount = 0
                                }
                            }
                        }

                        Button {
                            id: directedSearchButton
                            visible: directedSearchPanel.expanded
                            Layout.fillWidth: true
                            text: Bridge.isDirectedSearch ? "Retornar à busca geral"
                                  : Bridge.hasSavedDirectedSearch ? "Retomar busca direcionada" : "Buscar nos selecionados"
                            enabled: !Bridge.isSearching &&
                                     (Bridge.isDirectedSearch || root.selectedManualCount > 0)
                            onClicked: Bridge.isDirectedSearch
                                       ? root.returnToGeneralSearch()
                                       : root.beginDirectedSearch()
                        }
                }

                ToolButton {
                    id: indexedHeader
                    property bool expanded: false
                    Layout.fillWidth: true
                    implicitHeight: 32
                    padding: 4
                    onClicked: expanded = !expanded
                    contentItem: Text {
                        text: (indexedHeader.expanded ? "▾  " : "▸  ") + "Arquivos indexados"
                        font.pixelSize: 14
                        font.bold: true
                        color: "#ffffff"
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                RowLayout {
                    visible: indexedHeader.expanded
                    Layout.fillWidth: true
                    Layout.fillHeight: false
                    spacing: 6

                    Button {
                        text: Bridge.isIndexing ? "Indexando..." : "Pasta"
                        enabled: !Bridge.isIndexing
                        Layout.fillWidth: true
                        Layout.preferredWidth: 0
                        ToolTip.visible: hovered
                        ToolTip.text: "Selecionar pasta com PDFs"
                        onClicked: folderPicker.open()
                    }

                    Button {
                        text: "Reindexar"
                        enabled: !Bridge.isIndexing
                        Layout.fillWidth: true
                        Layout.preferredWidth: 0
                        ToolTip.visible: hovered
                        ToolTip.text: "Sincronizar novamente a pasta selecionada"
                        onClicked: if (!Bridge.reindexAll()) folderPicker.open()
                    }
                }

                ProgressBar {
                    Layout.fillWidth: true
                    visible: indexedHeader.expanded && Bridge.isIndexing
                    indeterminate: true
                }

                ListView {
                    id: fileList
                    visible: indexedHeader.expanded
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: 0
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
                Item {
                    visible: !indexedHeader.expanded
                    Layout.fillHeight: true
                }

                ToolButton {
                    Layout.fillWidth: true
                    text: "Sobre e licenças"
                    onClicked: aboutDialog.open()
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
                        placeholderText: Bridge.isDirectedSearch
                                         ? "Buscar nos manuais selecionados..."
                                         : "Buscar palavra ou frase..."
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
                                    text: root.fileName(modelData.filepath)
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
                            if (status === Image.Ready) {
                                if (root.restoringGeneralPreview) {
                                    Qt.callLater(root.finishPreviewRestore)
                                } else {
                                    Qt.callLater(root.centerPreview)
                                }
                            }
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
