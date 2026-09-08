"""Cache limitado de imagens; pré-renderização isolada em outro processo."""
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from threading import Condition, Thread
import os

import pymupdf
from PySide6.QtGui import QImage

from core.preview_highlight import highlight_query_on_page


def render_page(context, page_number):
    filepath, _mtime, _size, query, mode, threshold = context
    with pymupdf.open(filepath) as doc:
        page = doc[max(0, min(page_number - 1, len(doc) - 1))]
        if query:
            highlight_query_on_page(page, query, mode, threshold)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), colorspace=pymupdf.csRGB, alpha=False)
        return pix.samples, pix.width, pix.height, pix.stride, len(doc)


def _background_priority():
    if hasattr(os, "nice"):
        os.nice(10)


def _image(data):
    samples, width, height, stride, _ = data
    return QImage(samples, width, height, stride, QImage.Format_RGB888).copy()


class PreviewCache:
    def __init__(self, max_bytes=64 * 1024 * 1024):
        self.max_bytes = max_bytes
        self._condition = Condition()
        self._images = {}
        self._bytes = 0
        self._context = None
        self._page = 1
        self._generation = 0
        self._pending = []
        self._closed = False
        self._thread = None

    @staticmethod
    def neighbors(page, total):
        return [p for p in (page + 1, page - 1, page + 2, page - 2, page + 3)
                if 1 <= p <= total]

    def get(self, filepath, page, query="", mode="all", threshold=65):
        stat = os.stat(filepath)
        context = (filepath, stat.st_mtime_ns, stat.st_size, query, mode, threshold)
        with self._condition:
            self._generation += 1
            generation = self._generation
            self._pending = []
            self._context, self._page = context, page
            allowed = {page, page - 2, page - 1, page + 1, page + 2, page + 3}
            for key in list(self._images):
                if key[0] != context or key[1] not in allowed:
                    self._bytes -= self._images.pop(key)[0].sizeInBytes()
            cached = self._images.get((context, page))
        # A página solicitada nunca espera a fila de pré-renderização.
        if cached:
            image, total = cached
        else:
            data = render_page(context, page)
            image, total = _image(data), data[-1]
        with self._condition:
            if generation == self._generation and not self._closed:
                self._put(context, page, image, total)
                self._pending = [(generation, context, p) for p in self.neighbors(page, total)
                                 if (context, p) not in self._images]
                if self._thread is None:
                    self._thread = Thread(target=self._prefetch, name="pdf-prefetch", daemon=True)
                    self._thread.start()
                self._condition.notify_all()
        return image

    def _put(self, context, page, image, total):
        key = (context, page)
        if key in self._images or image.sizeInBytes() > self.max_bytes:
            return
        while self._images and self._bytes + image.sizeInBytes() > self.max_bytes:
            farthest = max(self._images, key=lambda k: abs(k[1] - self._page))
            # Não troca uma página próxima por uma antecipação mais distante.
            if abs(farthest[1] - self._page) <= abs(page - self._page) and page != self._page:
                return
            self._bytes -= self._images.pop(farthest)[0].sizeInBytes()
        self._images[key] = (image, total)
        self._bytes += image.sizeInBytes()

    def _prefetch(self):
        # PyMuPDF não compartilha documentos entre threads: o trabalho
        # antecipado roda em processo próprio, com prioridade menor no Linux.
        with ProcessPoolExecutor(max_workers=1, mp_context=get_context("spawn"),
                                 initializer=_background_priority) as executor:
            while True:
                with self._condition:
                    self._condition.wait_for(lambda: self._closed or self._pending)
                    if self._closed:
                        return
                    generation, context, page = self._pending.pop(0)
                try:
                    data = executor.submit(render_page, context, page).result()
                    with self._condition:
                        if generation == self._generation and not self._closed:
                            self._put(context, page, _image(data), data[-1])
                except Exception as exc:
                    # Uma falha especulativa não impede abrir a página sob demanda.
                    print(f"Pré-carregamento de PDF: {exc}")

    def close(self):
        with self._condition:
            self._closed = True
            self._pending = []
            self._images.clear()
            self._bytes = 0
            self._condition.notify_all()
        if self._thread:
            self._thread.join()
