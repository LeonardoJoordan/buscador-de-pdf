import sys
import os
import multiprocessing
from pathlib import Path
from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from core.database import DatabaseManager
from bridge import AppBridge, PdfImageProvider

def main():
    # O estilo nativo dos controles varia bastante entre Linux e Windows.
    # Fusion fornece a mesma base visual multiplataforma e se aproxima do
    # visual sóbrio usado pelo aplicativo no GNOME.
    QQuickStyle.setStyle("Fusion")

    app = QGuiApplication(sys.argv)
    app.setApplicationName("LYNXAtlas")
    app.setApplicationDisplayName("LYNX Atlas")
    app.setOrganizationName("LYNX")

    # Program Files não permite escrita por usuários comuns. No Windows, o
    # índice pertence ao usuário e fica em %LOCALAPPDATA%\LYNX\LYNXAtlas.
    if sys.platform == "win32":
        data_dir = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = data_dir / "index.db"
    else:
        db_path = Path("index.db")

    # Inicializa banco de dados e ponte
    db = DatabaseManager(str(db_path))
    bridge = AppBridge(db)
    app.aboutToQuit.connect(bridge.shutdown)

    engine = QQmlApplicationEngine()

    # Registra o provedor de imagens "image://pdf/..."
    image_provider = PdfImageProvider()
    engine.addImageProvider("pdf", image_provider)
    app.aboutToQuit.connect(image_provider.cache.close)

    # Expõe a bridge diretamente para o contexto QML
    engine.rootContext().setContextProperty("Bridge", bridge)

    qml_file = os.path.join(os.path.dirname(__file__), "ui", "main.qml")
    engine.load(qml_file)

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
