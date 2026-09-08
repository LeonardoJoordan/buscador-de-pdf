import sys
import os
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from core.database import DatabaseManager
from bridge import AppBridge, PdfImageProvider

def main():
    app = QGuiApplication(sys.argv)
    app.setApplicationName("BuscadorPDF")
    app.setOrganizationName("CustomTools")

    # Inicializa banco de dados e ponte
    db = DatabaseManager("index.db")
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
    main()
