import os
from typing import List, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
from PySide6.QtCore import QThread, Signal
from core.extractor import extract_pdf_data
from core.database import DatabaseManager

class IndexerWorker(QThread):
    # Sinais emitidos para a UI
    progress_changed = Signal(int, int)   # (processados, total)
    file_finished = Signal(str)           # nome do arquivo
    indexing_finished = Signal()          # conclusão de tudo

    def __init__(
        self,
        db_manager: DatabaseManager,
        folder_path: Optional[str] = None,
        file_paths: Optional[List[str]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.folder_path = folder_path
        self.file_paths = file_paths
        self.db = db_manager
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        if self.file_paths is not None:
            # Reindexação: reprocessa apenas os arquivos já conhecidos, sem
            # varrer nenhuma pasta (útil quando o conteúdo de um PDF mudou).
            pdf_paths = list(self.file_paths)
        else:
            # Indexação normal: coleta todos os PDFs da pasta (inclusive subpastas)
            pdf_paths = []
            for root, _, files in os.walk(self.folder_path):
                for file in files:
                    if file.lower().endswith(".pdf"):
                        pdf_paths.append(os.path.join(root, file))

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