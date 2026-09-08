import sqlite3
from contextlib import closing
from typing import List, Tuple, Dict, Any, Optional

from core.text_utils import normalize_for_match, build_document_text
from core import matching


class DatabaseManager:
    def __init__(self, db_path: str = "index.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode = WAL;")  # Alta concorrência de leitura
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self):
        with closing(self._get_connection()) as conn, conn:
            # Tabela de controle de arquivos indexados
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filepath TEXT UNIQUE NOT NULL,
                    filename TEXT NOT NULL,
                    page_count INTEGER NOT NULL,
                    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            self._create_new_schema(conn)
            self._migrate_legacy_schema(conn)
            conn.commit()

    def _create_new_schema(self, conn: sqlite3.Connection):
        # Tabela virtual FTS5: 1 linha por DOCUMENTO (texto de todas as páginas
        # concatenado), permitindo localizar frases que atravessam a quebra
        # de página. A granularidade de página é recuperada via page_offsets.
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
                filepath UNINDEXED,
                content,
                tokenize = 'unicode61 remove_diacritics 2'
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS page_offsets (
                filepath TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                start_char INTEGER NOT NULL,
                end_char INTEGER NOT NULL
            );
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_page_offsets_filepath
            ON page_offsets (filepath);
        """)

    def _migrate_legacy_schema(self, conn: sqlite3.Connection):
        """
        Bancos criados antes da indexação por documento guardavam 1 linha de
        FTS5 por página (tabela `pages_fts`). Migra esses dados para o novo
        formato (docs_fts + page_offsets) sem precisar reabrir os PDFs.
        """
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pages_fts'")
        if cursor.fetchone() is None:
            return

        cursor.execute("SELECT DISTINCT filepath FROM pages_fts")
        filepaths = [row[0] for row in cursor.fetchall()]

        for filepath in filepaths:
            cursor.execute(
                "SELECT page_number, content FROM pages_fts WHERE filepath = ? ORDER BY page_number ASC",
                (filepath,),
            )
            pages = [(int(page_number), content) for page_number, content in cursor.fetchall()]
            full_text, page_offsets = build_document_text(pages)

            cursor.execute("DELETE FROM docs_fts WHERE filepath = ?", (filepath,))
            cursor.execute("DELETE FROM page_offsets WHERE filepath = ?", (filepath,))
            cursor.execute("INSERT INTO docs_fts (filepath, content) VALUES (?, ?)", (filepath, full_text))
            cursor.executemany(
                "INSERT INTO page_offsets (filepath, page_number, start_char, end_char) VALUES (?, ?, ?, ?)",
                [(filepath, pn, s, e) for pn, s, e in page_offsets],
            )

        cursor.execute("DROP TABLE pages_fts")

    def insert_document(
        self,
        filepath: str,
        filename: str,
        total_pages: int,
        full_text: str,
        page_offsets: List[Tuple[int, int, int]],
    ):
        """Insere o arquivo e o texto completo (com offsets de página) em uma única transação."""
        with closing(self._get_connection()) as conn, conn:
            cursor = conn.cursor()
            # Limpa registros antigos caso o arquivo já tenha sido indexado
            cursor.execute("DELETE FROM docs_fts WHERE filepath = ?", (filepath,))
            cursor.execute("DELETE FROM page_offsets WHERE filepath = ?", (filepath,))
            cursor.execute("DELETE FROM files WHERE filepath = ?", (filepath,))

            cursor.execute(
                "INSERT INTO files (filepath, filename, page_count) VALUES (?, ?, ?)",
                (filepath, filename, total_pages),
            )
            cursor.execute(
                "INSERT INTO docs_fts (filepath, content) VALUES (?, ?)",
                (filepath, full_text),
            )
            cursor.executemany(
                "INSERT INTO page_offsets (filepath, page_number, start_char, end_char) VALUES (?, ?, ?, ?)",
                [(filepath, pn, s, e) for pn, s, e in page_offsets],
            )
            conn.commit()

    def search(
        self,
        query_term: str,
        allow_out_of_order: bool = True,
        allow_fuzzy: bool = True,
        fuzzy_threshold: float = 65.0,
        result_limit: Optional[int] = None,
        cancelled=None,
    ) -> List[Dict[str, Any]]:
        """
        Busca em camadas: recall amplo via FTS5, depois classificação de cada
        candidato em verde (frase exata/mesma página), azul (frase exata entre
        páginas), roxo (mesmas palavras fora de ordem) ou laranja (aproximação).
        """
        query_term = query_term.strip()
        if not query_term:
            return []

        normalized_query = normalize_for_match(query_term)
        words = matching.extract_words(normalized_query)
        if not words:
            return []

        fts_query = matching.build_broad_fts_query(words)
        if not fts_query:
            return []

        all_results: List[Dict[str, Any]] = []

        with closing(self._get_connection()) as conn, conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT filepath, content FROM docs_fts
                    WHERE docs_fts MATCH ?
                    ORDER BY rank;
                    """,
                    (fts_query,),
                )
                candidates = cursor.fetchall()
            except sqlite3.OperationalError:
                raise

            if not candidates:
                return []

            cursor.execute(
                """
                SELECT filepath, page_number, start_char, end_char
                FROM page_offsets
                WHERE filepath IN (
                    SELECT filepath FROM docs_fts WHERE docs_fts MATCH ?
                )
                ORDER BY filepath, start_char ASC;
                """,
                (fts_query,),
            )
            offsets_by_file: Dict[str, List[Tuple[int, int, int]]] = {}
            for filepath, page_number, start_char, end_char in cursor.fetchall():
                offsets_by_file.setdefault(filepath, []).append((page_number, start_char, end_char))

        single_word = len(words) == 1

        for filepath, content in candidates:
            if cancelled is not None and cancelled():
                return []
            page_offsets = offsets_by_file.get(filepath, [])
            if not page_offsets:
                continue

            normalized_content = normalize_for_match(content)

            exact_results, claimed_pages = matching.find_exact_phrase_matches(
                filepath, content, normalized_content, normalized_query, page_offsets, single_word
            )
            all_results.extend(exact_results)

            if allow_out_of_order:
                all_results.extend(
                    matching.find_out_of_order_matches(
                        filepath, content, normalized_content, words, page_offsets, claimed_pages
                    )
                )

            if allow_fuzzy:
                all_results.extend(
                    matching.find_fuzzy_matches(
                        filepath, content, normalized_content, normalized_query,
                        page_offsets, claimed_pages, fuzzy_threshold
                    )
                )

        return matching.sort_and_limit(all_results, result_limit)

    def get_indexed_files(self) -> List[Dict[str, Any]]:
        with closing(self._get_connection()) as conn, conn:
            cursor = conn.cursor()
            cursor.execute("SELECT filepath, filename, page_count FROM files ORDER BY filename ASC;")
            return [
                {"filepath": row[0], "filename": row[1], "page_count": row[2]}
                for row in cursor.fetchall()
            ]
