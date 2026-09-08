from PySide6.QtCore import QThread


class SearchWorker(QThread):
    """Calcula resultados fora da interface; search abre sua própria conexão."""

    def __init__(self, db, query, options, parent=None):
        super().__init__(parent)
        self.db = db
        self.query = query
        self.options = options
        self.results = None
        self.error = ""

    def run(self):
        try:
            self.results = self.db.search(
                self.query, **self.options, cancelled=self.isInterruptionRequested
            )
        except Exception as exc:
            self.error = f"Não foi possível concluir a busca: {exc}"
