import os
from typing import Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
from PySide6.QtCore import QThread, Signal
from core.extractor import extract_pdf_data
from core.database import DatabaseManager


def scan_folder(folder_path):
    """Retorna PDFs absolutos e extensões não suportadas encontradas."""
    pdf_paths = []
    unsupported_extensions = set()
    for root, _, files in os.walk(folder_path):
        for filename in files:
            path = os.path.abspath(os.path.join(root, filename))
            if filename.lower().endswith(".pdf"):
                pdf_paths.append(path)
            else:
                extension = os.path.splitext(filename)[1].lower()
                unsupported_extensions.add(extension or "sem extensão")
    pdf_paths.sort(key=os.path.normcase)
    return pdf_paths, sorted(unsupported_extensions, key=str.casefold)


class IndexerWorker(QThread):
    # Sinais emitidos para a UI
    progress_changed = Signal(int, int)   # (processados, total)
    file_finished = Signal(str)           # nome do arquivo
    unsupported_extensions_found = Signal(list)
    indexing_finished = Signal()          # conclusão de tudo

    def __init__(
        self,
        db_manager: DatabaseManager,
        folder_path: Optional[str] = None,
        report_unsupported: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.folder_path = folder_path
        self.report_unsupported = report_unsupported
        self.db = db_manager
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        # A pasta é a fonte da verdade: a cada execução descobrimos novamente
        # todos os PDFs, inclusive em subpastas.
        pdf_paths, unsupported_extensions = scan_folder(self.folder_path)
        if self.report_unsupported and unsupported_extensions:
            self.unsupported_extensions_found.emit(unsupported_extensions)

        # Remove registros de arquivos apagados ou que pertenciam à pasta
        # selecionada anteriormente. Também limpa o índice se a pasta estiver vazia.
        self.db.remove_documents_except(pdf_paths)

        total_files = len(pdf_paths)
        if total_files == 0:
            self.indexing_finished.emit()
            return

        processed_count = 0

        # 2. Dispara a extração usando todos os núcleos da CPU
        # os.cpu_count() define o número ótimo de processos paralelos
        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            future_to_file = {executor.submit(extract_pdf_data, path): path for path in pdf_paths}

            for future in as_completed(future_to_file):
                if not self._is_running:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                result = future.result()
                if result:
                    filepath, filename, total_pages, full_text, page_offsets = result

                    # 3. O coordenador faz a escrita segura e rápida no banco
                    self.db.insert_document(filepath, filename, total_pages, full_text, page_offsets)
                    self.file_finished.emit(filename)

                processed_count += 1
                self.progress_changed.emit(processed_count, total_files)

        self.indexing_finished.emit()
