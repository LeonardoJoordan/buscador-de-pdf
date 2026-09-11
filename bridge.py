import os
import subprocess
import base64
import pymupdf
from PySide6.QtCore import QObject, Signal, Slot, Property, QSettings, QUrl
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider
from core.database import DatabaseManager
from core.indexer import IndexerWorker
from core.preview_highlight import HIGHLIGHT_MODES
from core.preview_cache import PreviewCache
from core.search_worker import SearchWorker


def _b64url_encode(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def _b64url_decode(text: str) -> str:
    pad = "=" * ((4 - len(text) % 4) % 4)
    return base64.urlsafe_b64decode(text + pad).decode("utf-8")

class PdfImageProvider(QQuickImageProvider):
    """
    Renderiza páginas do PDF como QImage para o QML sob demanda.
    Formato da URI no QML: image://pdf/<caminho_em_base64>/<numero_pagina>
    """
    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self.cache = PreviewCache()

    def requestImage(self, id_str, size, requestedSize):
        try:
            # URI: <caminho_b64url>/<pagina>/<query_b64url?>
            parts = id_str.split("/")
            encoded_path = parts[0]
            page_num = int(parts[1]) if len(parts) > 1 else 1
            query = _b64url_decode(parts[2]) if len(parts) > 2 and parts[2] else ""

            mode = parts[3] if len(parts) > 3 else "all"
            threshold = float(parts[4]) if len(parts) > 4 else 65.0
            filepath = _b64url_decode(encoded_path)

            if not os.path.exists(filepath):
                return QImage()

            return self.cache.get(filepath, page_num, query, mode, threshold)

        except Exception as e:
            print(f"Erro ao renderizar imagem da página: {e}")
            return QImage()


class AppBridge(QObject):
    # Sinais para atualizar a interface QML
    searchResultsChanged = Signal()
    indexedFilesChanged = Signal()
    indexingProgressChanged = Signal(int, int)  # atual, total
    isIndexingChanged = Signal(bool)
    previewChanged = Signal()
    advancedSettingsChanged = Signal()
    searchStateChanged = Signal()
    directedSearchChanged = Signal()
    generalSearchReplaced = Signal()

    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db = db_manager
        self.worker = None
        self._search_worker = None
        self._is_searching = False
        self._search_error = ""

        self._search_results = []
        self._indexed_files = []
        self._is_indexing = False
        self._last_query = ""
        self._directed_filepaths = []
        self._general_search_snapshot = None
        self._directed_search_snapshot = None
        self._directed_refresh_required = False

        # Estado da prévia atual
        self._current_preview_path = ""
        self._current_preview_page = 1
        self._current_total_pages = 1

        # Configurações avançadas de busca, persistidas entre sessões
        self._settings = QSettings("CustomTools", "BuscadorPDF")
        self._allow_out_of_order = self._settings.value("search/allowOutOfOrder", True, type=bool)
        self._allow_fuzzy = self._settings.value("search/allowFuzzy", True, type=bool)
        self._fuzzy_threshold = self._settings.value("search/fuzzyThreshold", 65, type=int)

        self._preview_highlight_mode = self._settings.value("preview/highlightMode", "all")
        if self._preview_highlight_mode not in HIGHLIGHT_MODES:
            self._preview_highlight_mode = "all"

        self.refresh_indexed_files()

    # --- Propriedades acessadas pelo QML ---

    @Property(bool, notify=searchStateChanged)
    def isSearching(self):
        return self._is_searching

    @Property(str, notify=searchStateChanged)
    def searchError(self):
        return self._search_error

    @Property(list, notify=searchResultsChanged)
    def searchResults(self):
        return self._search_results

    @Property(str, notify=searchResultsChanged)
    def currentQuery(self):
        return self._last_query

    @Property(bool, notify=directedSearchChanged)
    def isDirectedSearch(self):
        return self._general_search_snapshot is not None

    @Property(list, notify=directedSearchChanged)
    def directedFilepaths(self):
        return self._directed_filepaths

    @Property(bool, notify=directedSearchChanged)
    def hasSavedDirectedSearch(self):
        return self.isDirectedSearch or self._directed_search_snapshot is not None

    @Property(list, notify=searchResultsChanged)
    def resultManuals(self):
        results = (self._general_search_snapshot["results"]
                   if self._general_search_snapshot is not None
                   else self._search_results)
        counts = {}
        for result in results:
            path = result.get("filepath", "")
            if path:
                counts[path] = counts.get(path, 0) + 1
        return [
            {"filepath": path, "filename": os.path.basename(path), "result_count": count}
            for path, count in sorted(counts.items(), key=lambda item: os.path.basename(item[0]).lower())
        ]

    @Property(list, notify=indexedFilesChanged)
    def indexedFiles(self):
        return self._indexed_files

    @Property(bool, notify=isIndexingChanged)
    def isIndexing(self):
        return self._is_indexing

    @Property(str, notify=previewChanged)
    def previewImagePath(self):
        if not self._current_preview_path:
            return ""
        # urlsafe b64 evita "/" no id da imagem (o Qt separa o id por barras)
        enc = _b64url_encode(self._current_preview_path)
        url = f"image://pdf/{enc}/{self._current_preview_page}"
        if self._last_query:
            url += f"/{_b64url_encode(self._last_query)}/{self._preview_highlight_mode}/{self._fuzzy_threshold}"
        return url

    @Property(str, notify=previewChanged)
    def currentFilepath(self):
        return self._current_preview_path

    @Property(int, notify=previewChanged)
    def currentPage(self):
        return self._current_preview_page

    @Property(int, notify=previewChanged)
    def currentTotalPages(self):
        return self._current_total_pages

    # --- Configurações avançadas de busca ---

    @Property(str, notify=advancedSettingsChanged)
    def previewHighlightMode(self):
        return self._preview_highlight_mode

    @Slot(str)
    def setPreviewHighlightMode(self, value):
        if value not in HIGHLIGHT_MODES or value == self._preview_highlight_mode:
            return
        self._preview_highlight_mode = value
        self._settings.setValue("preview/highlightMode", value)
        self.advancedSettingsChanged.emit()
        self.previewChanged.emit()

    @Property(bool, notify=advancedSettingsChanged)
    def allowOutOfOrder(self):
        return self._allow_out_of_order

    @Property(bool, notify=advancedSettingsChanged)
    def allowFuzzy(self):
        return self._allow_fuzzy

    @Property(int, notify=advancedSettingsChanged)
    def fuzzyThreshold(self):
        return self._fuzzy_threshold

    @Slot(bool)
    def setAllowOutOfOrder(self, value: bool):
        if self._allow_out_of_order == value:
            return
        self._allow_out_of_order = value
        self._settings.setValue("search/allowOutOfOrder", value)
        self.advancedSettingsChanged.emit()

    @Slot(bool)
    def setAllowFuzzy(self, value: bool):
        if self._allow_fuzzy == value:
            return
        self._allow_fuzzy = value
        self._settings.setValue("search/allowFuzzy", value)
        self.advancedSettingsChanged.emit()

    @Slot(int)
    def setFuzzyThreshold(self, value: int):
        value = max(0, min(100, value))
        if self._fuzzy_threshold == value:
            return
        self._fuzzy_threshold = value
        self._settings.setValue("search/fuzzyThreshold", value)
        self.advancedSettingsChanged.emit()

    # --- Slots chamados pelo QML ---

    @Slot(str)
    def search(self, query: str):
        if self._is_searching:
            return
        query = query.strip()
        self._search_error = ""
        if not query:
            if not self.isDirectedSearch:
                self._reset_directed_search()
            self._last_query = ""
            self._search_results = []
            self.searchResultsChanged.emit()
            self.previewChanged.emit()
            self.searchStateChanged.emit()
            return
        self._search_worker = SearchWorker(self.db, query, {
            "allow_out_of_order": self._allow_out_of_order,
            "allow_fuzzy": self._allow_fuzzy,
            "fuzzy_threshold": self._fuzzy_threshold,
            "filepaths": self._directed_filepaths if self.isDirectedSearch else None,
        }, self)
        self._search_worker.finished.connect(self._on_search_finished)
        self._is_searching = True
        self.searchStateChanged.emit()
        self._search_worker.start()

    @Slot(list, result=bool)
    def beginDirectedSearch(self, filepaths):
        if self._is_searching or self.isDirectedSearch:
            return False
        available = {item["filepath"] for item in self.resultManuals}
        selected = list(dict.fromkeys(path for path in filepaths if path in available))
        if not selected:
            return False
        added = set(selected) - set(self._directed_filepaths)
        self._general_search_snapshot = self._capture_search()
        self._directed_filepaths = selected
        if self._directed_search_snapshot is not None:
            self._restore_search(self._directed_search_snapshot)
            self._search_results = [result for result in self._search_results
                                    if result["filepath"] in selected]
            if self._current_preview_path not in selected:
                self._current_preview_path = ""
                self._current_preview_page = 1
                self._current_total_pages = 1
            self._directed_refresh_required = self._directed_refresh_required or bool(added)
        else:
            self._last_query = ""
            self._search_results = []
            self._search_error = ""
        self.searchResultsChanged.emit()
        self.searchStateChanged.emit()
        self.previewChanged.emit()
        self.directedSearchChanged.emit()
        if self._directed_refresh_required and self._last_query:
            self.search(self._last_query)
        return True

    def _capture_search(self):
        return {
            "query": self._last_query,
            "results": self._search_results,
            "error": self._search_error,
            "preview_path": self._current_preview_path,
            "preview_page": self._current_preview_page,
            "preview_total": self._current_total_pages,
        }

    def _restore_search(self, snapshot):
        self._last_query = snapshot["query"]
        self._search_results = snapshot["results"]
        self._search_error = snapshot["error"]
        self._current_preview_path = snapshot["preview_path"]
        self._current_preview_page = snapshot["preview_page"]
        self._current_total_pages = snapshot["preview_total"]

    def _reset_directed_search(self):
        self._directed_search_snapshot = None
        self._directed_refresh_required = False
        self._directed_filepaths = []
        self.generalSearchReplaced.emit()
        self.directedSearchChanged.emit()

    @Slot(result=bool)
    def returnToGeneralSearch(self):
        if self._is_searching or self._general_search_snapshot is None:
            return False
        snapshot = self._general_search_snapshot
        self._directed_search_snapshot = self._capture_search()
        self._general_search_snapshot = None
        self._restore_search(snapshot)
        self.searchResultsChanged.emit()
        self.searchStateChanged.emit()
        self.previewChanged.emit()
        self.directedSearchChanged.emit()
        return True

    @Slot()
    def _on_search_finished(self):
        worker = self._search_worker
        if worker is None:
            return
        self._search_error = worker.error
        if not worker.error:
            if not self.isDirectedSearch:
                self._reset_directed_search()
            else:
                self._directed_refresh_required = False
            self._last_query = worker.query
            self._search_results = worker.results
            self.searchResultsChanged.emit()
            self.previewChanged.emit()
        self._search_worker = None
        worker.deleteLater()
        self._is_searching = False
        self.searchStateChanged.emit()

    @Slot()
    def shutdown(self):
        if self._search_worker is not None:
            self._search_worker.requestInterruption()
            self._search_worker.wait()

    @Slot(str)
    def startIndexing(self, folder_url: str):
        # QML envia URLs do tipo "file:///caminho"
        if self._is_indexing:
            return
        folder_path = QUrl(folder_url).toLocalFile()
        if not os.path.isdir(folder_path):
            return

        self._is_indexing = True
        self.isIndexingChanged.emit(True)

        self.worker = IndexerWorker(self.db, folder_path=folder_path)
        self.worker.progress_changed.connect(self._on_indexing_progress)
        self.worker.indexing_finished.connect(self._on_indexing_finished)
        self.worker.start()

    @Slot()
    def reindexAll(self):
        """Reprocessa apenas os arquivos já presentes em 'Arquivos Indexados',
        sem exigir escolher a pasta novamente (não descobre arquivos novos)."""
        if self._is_indexing:
            return

        file_paths = [item["filepath"] for item in self._indexed_files]
        if not file_paths:
            return

        self._is_indexing = True
        self.isIndexingChanged.emit(True)

        self.worker = IndexerWorker(self.db, file_paths=file_paths)
        self.worker.progress_changed.connect(self._on_indexing_progress)
        self.worker.indexing_finished.connect(self._on_indexing_finished)
        self.worker.start()

    def _on_indexing_progress(self, current: int, total: int):
        self.indexingProgressChanged.emit(current, total)

    def _on_indexing_finished(self):
        self._is_indexing = False
        self.isIndexingChanged.emit(False)
        self.refresh_indexed_files()

    @Slot()
    def refresh_indexed_files(self):
        self._indexed_files = self.db.get_indexed_files()
        self.indexedFilesChanged.emit()

    @Slot(str, int)
    def setPreview(self, filepath: str, page: int):
        self._current_preview_path = filepath
        self._current_preview_page = max(1, page)
        
        # Pega a contagem total de páginas rápida via fitz
        try:
            doc = pymupdf.open(filepath)
            self._current_total_pages = len(doc)
            doc.close()
        except Exception:
            self._current_total_pages = 1

        self.previewChanged.emit()

    @Slot(int)
    def changePage(self, delta: int):
        """Avança ou volta páginas na prévia."""
        if not self._current_preview_path:
            return
        new_page = self._current_preview_page + delta
        if 1 <= new_page <= self._current_total_pages:
            self._current_preview_page = new_page
            self.previewChanged.emit()

    @Slot(str, int)
    def openInSystemViewer(self, filepath: str, page: int):
        """
        Tenta abrir no leitor nativo apontando a página (-p).
        Fallback direto para xdg-open se nenhum leitor específico responder.
        """
        if not os.path.exists(filepath):
            return

        # Lista de leitores comuns no Linux que suportam `-p <pagina>`
        viewers = ["xreader", "evince", "atril", "okular"]
        opened = False

        for viewer in viewers:
            try:
                # Se for o okular a sintaxe é `-p`, para os outros baseados em evince também
                subprocess.Popen([viewer, "-p", str(page), filepath])
                opened = True
                break
            except FileNotFoundError:
                continue

        if not opened:
            # Fallback universal
            subprocess.Popen(["xdg-open", filepath])
