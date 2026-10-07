"""
index_store.py — Singleton load FAISS + BM25 index khi app startup

Sử dụng pattern module-level singleton để index chỉ load 1 lần.
Được gọi từ FastAPI lifespan event trong main.py.

Quy trình nạp dữ liệu và kiểm tra toàn vẹn fail-closed (CD11):
1. _load_jsonl fail-closed với JSONDecodeError, kiểm tra record là dict,
   và lưu giữ chính xác số dòng vật lý trong file để thông báo lỗi chuẩn xác.
2. Kiểm tra bắt buộc len(meta) == ntotal cho FAISS và len(meta) == corpus_size cho BM25 (fail-closed).
3. Không nuốt lỗi, không gọi sys.exit trong lifespan (để exception nổi lên cho framework ASGI xử lý).
4. Bắt buộc underthesea khi WORD_SEGMENTATION=True (ném ImportError cứng nếu thiếu)
   và thực hiện gọi thử nghiệm (warmup) ngay lúc startup để phát hiện lỗi runtime trước request đầu tiên.
5. Xóa bỏ hoàn toàn pickle: Không import pickle và không nạp pickle.
   Corpus BM25 được nạp và khởi tạo BM25Okapi trực tiếp từ bm25_corpus.jsonl.
   Kiểm tra từng token là chuỗi không rỗng, kiểm tra tổng số token > 0 để ngăn chặn ZeroDivisionError.
6. Kiểm tra toàn vẹn SHA-256 fail-closed bắt buộc với index_hashes.json:
   Khóa cứng whitelist 5 tệp artifact bắt buộc; chặn file rỗng, chặn path traversal,
   chặn symlink, và đọc bytes một lần vào bộ nhớ (in-memory verification) nhằm triệt tiêu
   nguy cơ TOCTOU (Time-of-Check to Time-of-Use) đối với toàn bộ tệp metadata và corpus.
7. Bắt buộc có index_manifest.json và đối chiếu cấu hình:
   embed_model, word_segmentation, ntotal, dimension, metric_type.
8. Kiểm tra faiss_index.metric_type == METRIC_INNER_PRODUCT (vì query vector đã được L2-normalized).
9. Kiểm tra chunk_id bắt buộc là chuỗi không rỗng, không chứa None;
   đối chiếu thứ tự và mã chunk_id khớp chính xác 1:1 giữa faiss_meta, bm25_meta và bm25_corpus;
   kiểm tra faiss_id khớp chỉ số vector nếu trường này tồn tại.
10. Chuẩn hóa Unicode NFC cho truy vấn tiếng Việt trước khi tokenize và encode vector.
11. Guard chặt chẽ cho encode_query và tokenize_query khi chưa load() (ném RuntimeError).

LƯU Ý VỀ PHẠM VI AN NINH (SECURITY BOUNDARY):
- Kiểm tra SHA-256 cục bộ bảo đảm tính toàn vẹn (Integrity Check) chống file hỏng hóc,
  tải dở dang hoặc lệch phiên bản lúc build/deploy.
- Cơ chế nạp trực tiếp từ bytes đã hash trong bộ nhớ loại bỏ hoàn toàn TOCTOU cho metadata/corpus.
  Tuy nhiên, cơ chế kiểm tra cục bộ này không thể thay thế cho phân quyền tệp (File Permissions)
  của hệ điều hành nếu kẻ tấn công đã có quyền ghi trực tiếp vào filesystem server.
  Khi triển khai production, bắt buộc phải phân quyền chỉ-đọc (Read-Only) cho thư mục data/index.
"""

import hashlib
import json
import logging
import unicodedata
from pathlib import Path
from typing import List, Optional, Dict

import numpy as np

from app.core.config import settings

logger = logging.getLogger("index_store")

REQUIRED_HASHED_FILES = (
    "faiss.index",
    "faiss_meta.jsonl",
    "bm25_meta.jsonl",
    "bm25_corpus.jsonl",
    "index_manifest.json",
)


class JsonlRecord(dict):
    """
    Subclass của dict đại diện cho một bản ghi JSONL,
    lưu giữ chính xác số dòng vật lý (1-indexed) trong tệp gốc.
    """
    def __init__(self, mapping: dict, line_no: int):
        super().__init__(mapping)
        self.line_no = line_no


class IndexStore:
    """
    Singleton giữ FAISS index, BM25 object và metadata của cả hai.
    Load từ backend/data/index/ khi app khởi động.
    """

    def __init__(self):
        self._faiss_index = None
        self._faiss_meta: List[JsonlRecord] = []
        self._bm25 = None
        self._bm25_meta: List[JsonlRecord] = []
        self._embed_model = None
        self._segmenter = None
        self._expected_hashes: Dict[str, str] = {}
        self._file_bytes: Dict[str, bytes] = {}
        self._loaded = False

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(self, index_dir: Optional[Path] = None) -> None:
        """Load FAISS, BM25 và embedding model vào memory với quy trình kiểm định fail-closed."""
        if self._loaded:
            logger.info("IndexStore: đã load rồi, bỏ qua.")
            return

        target_dir = index_dir or settings.index_dir_path
        self._verify_index_hashes(target_dir)
        self._load_faiss(target_dir)
        self._load_bm25(target_dir)
        self._load_embed_model()
        self._load_segmenter()
        self._validate_dimensions_and_metadata(target_dir)
        self._loaded = True
        logger.info("IndexStore: nạp index và mô hình thành công.")

    def _verify_index_hashes(self, index_dir: Path) -> None:
        """
        Kiểm tra tính toàn vẹn SHA-256 của toàn bộ index artifacts (Fail-Closed).
        Nạp toàn bộ nội dung bytes vào bộ nhớ để triệt tiêu TOCTOU cho metadata/corpus.
        """
        hash_file = index_dir / "index_hashes.json"
        if not hash_file.exists():
            raise FileNotFoundError(
                f"BẮT BUỘC có file kiểm tra tính toàn vẹn {hash_file}. "
                "Hệ thống từ chối khởi động (fail-closed) để phòng ngừa dữ liệu sai lệch. "
                "Chạy: python backend/pipeline/make_index_manifest.py để tạo index_hashes.json."
            )

        try:
            with open(hash_file, "r", encoding="utf-8") as f:
                expected_hashes = json.load(f)
        except Exception as e:
            raise ValueError(f"File {hash_file} bị hỏng hoặc không đúng chuẩn JSON: {e}") from e

        if not isinstance(expected_hashes, dict) or not expected_hashes:
            raise ValueError(f"File {hash_file} rỗng hoặc cấu trúc không hợp lệ!")

        # 1. Kiểm tra an toàn tên file (trống, path traversal, dấu phân cách đường dẫn)
        for fname in expected_hashes:
            if not isinstance(fname, str) or not fname.strip():
                raise ValueError("Tên file trong hash map không được để trống!")
            if Path(fname).name != fname or ".." in fname or "/" in fname or "\\" in fname:
                raise ValueError(f"Tên file không hợp lệ hoặc chứa đường dẫn trong hash map: '{fname}'")

        # 2. Khóa cứng whitelist bắt buộc: Kiểm tra thiếu file
        for k in REQUIRED_HASHED_FILES:
            if k not in expected_hashes:
                raise ValueError(f"Hash map thiếu tệp bắt buộc: '{k}' trong {hash_file}")

        # 3. Khóa cứng whitelist bắt buộc: Kiểm tra file lạ ngoài danh mục cho phép
        extra_files = set(expected_hashes.keys()) - set(REQUIRED_HASHED_FILES)
        if extra_files:
            raise ValueError(
                f"Hash map chứa tệp lạ không nằm trong whitelist bắt buộc: {extra_files}"
            )

        # 4. Kiểm tra sự tồn tại, symlink, hash SHA-256 và nạp bytes vào bộ nhớ
        file_bytes: Dict[str, bytes] = {}
        for fname, expected_hash in expected_hashes.items():

            fpath = index_dir / fname
            if not fpath.exists():
                raise FileNotFoundError(f"Index file ghi trong hash map không tồn tại: {fpath}")
            if fpath.is_symlink():
                raise ValueError(f"Tệp không được phép là symlink (phòng chống symlink attack): '{fname}'")

            try:
                data = fpath.read_bytes()
            except Exception as e:
                raise ValueError(f"Không thể đọc file {fname}: {e}") from e

            actual_hash = hashlib.sha256(data).hexdigest()
            if actual_hash != expected_hash:
                raise ValueError(
                    f"Hash mismatch cho {fname}: expected {expected_hash}, got {actual_hash}!"
                )
            file_bytes[fname] = data

        self._expected_hashes = expected_hashes
        self._file_bytes = file_bytes
        logger.info(f"Đã xác minh toàn vẹn SHA-256 cho {len(expected_hashes)} index files.")

    def _load_faiss(self, index_dir: Path) -> None:
        try:
            import faiss
        except ImportError as e:
            raise ImportError("faiss-cpu chưa cài. Chạy: pip install faiss-cpu") from e

        faiss_path = index_dir / "faiss.index"
        if not faiss_path.exists():
            raise FileNotFoundError(
                f"Không tìm thấy FAISS index: {faiss_path}. "
                "Chạy: python backend/pipeline/embed_and_index.py"
            )

        self._faiss_index = faiss.read_index(str(faiss_path))

        # Kiểm tra metric_type (Inner Product cho L2-normalized vectors)
        if self._faiss_index.metric_type != faiss.METRIC_INNER_PRODUCT:
            raise ValueError(
                f"FAISS metric type mismatch: got {self._faiss_index.metric_type}, "
                f"expected {faiss.METRIC_INNER_PRODUCT} (METRIC_INNER_PRODUCT)!"
            )

        # Nạp faiss_meta từ bytes đã hash trong bộ nhớ (loại bỏ TOCTOU)
        if "faiss_meta.jsonl" in self._file_bytes:
            self._faiss_meta = self._parse_jsonl_bytes(
                self._file_bytes["faiss_meta.jsonl"], "faiss_meta.jsonl"
            )
        else:
            meta_path = index_dir / "faiss_meta.jsonl"
            if not meta_path.exists():
                raise FileNotFoundError(f"Không tìm thấy FAISS meta: {meta_path}")
            self._faiss_meta = self._load_jsonl(meta_path)

        if len(self._faiss_meta) != self._faiss_index.ntotal:
            raise ValueError(
                f"FAISS count mismatch: {len(self._faiss_meta)} meta records vs {self._faiss_index.ntotal} index vectors"
            )

        # Kiểm tra tính hợp lệ của chunk_id và tính khớp 1:1 giữa chỉ số vector và faiss_id
        for i, m in enumerate(self._faiss_meta):
            line_no = getattr(m, "line_no", i + 1)
            chunk_id = m.get("chunk_id")
            if not isinstance(chunk_id, str) or not chunk_id.strip():
                raise ValueError(
                    f"faiss_meta.jsonl dòng {line_no} (vị trí {i}) thiếu trường 'chunk_id' hoặc chunk_id rỗng!"
                )
            if "faiss_id" in m and m["faiss_id"] != i:
                raise ValueError(
                    f"FAISS metadata index mismatch: record tại vị trí {i} có faiss_id={m['faiss_id']} thay vì {i}!"
                )

        logger.info(
            f"FAISS: {self._faiss_index.ntotal} vectors, "
            f"dim={self._faiss_index.d}, "
            f"meta={len(self._faiss_meta)} chunks"
        )

    def _load_bm25(self, index_dir: Path) -> None:
        """
        Nạp BM25 thuần túy từ bm25_corpus.jsonl (loại bỏ hoàn toàn module pickle).
        Kiểm tra cấu trúc từng record, thứ tự và tính đồng nhất 1:1 theo chunk_id với bm25_meta.jsonl.
        """
        try:
            from rank_bm25 import BM25Okapi
        except ImportError as e:
            raise ImportError("rank-bm25 chưa cài. Chạy: pip install rank-bm25") from e

        # Nạp bm25_meta từ bytes đã hash trong bộ nhớ
        if "bm25_meta.jsonl" in self._file_bytes:
            self._bm25_meta = self._parse_jsonl_bytes(
                self._file_bytes["bm25_meta.jsonl"], "bm25_meta.jsonl"
            )
        else:
            meta_path = index_dir / "bm25_meta.jsonl"
            if not meta_path.exists():
                raise FileNotFoundError(f"Không tìm thấy BM25 meta: {meta_path}")
            self._bm25_meta = self._load_jsonl(meta_path)

        for i, m in enumerate(self._bm25_meta):
            line_no = getattr(m, "line_no", i + 1)
            chunk_id = m.get("chunk_id")
            if not isinstance(chunk_id, str) or not chunk_id.strip():
                raise ValueError(
                    f"bm25_meta.jsonl dòng {line_no} (vị trí {i}) thiếu trường 'chunk_id' hoặc chunk_id rỗng!"
                )

        # Nạp bm25_corpus từ bytes đã hash trong bộ nhớ
        if "bm25_corpus.jsonl" in self._file_bytes:
            corpus_records = self._parse_jsonl_bytes(
                self._file_bytes["bm25_corpus.jsonl"], "bm25_corpus.jsonl"
            )
        else:
            jsonl_path = index_dir / "bm25_corpus.jsonl"
            if not jsonl_path.exists():
                raise FileNotFoundError(f"Không tìm thấy {jsonl_path}")
            corpus_records = self._load_jsonl(jsonl_path)

        if not corpus_records:
            raise ValueError("BM25 corpus rỗng trong bm25_corpus.jsonl")

        tokenized_corpus = []
        for r in corpus_records:
            line_no = getattr(r, "line_no", "?")
            chunk_id = r.get("chunk_id")
            if not isinstance(chunk_id, str) or not chunk_id.strip():
                raise ValueError(
                    f"bm25_corpus.jsonl dòng {line_no} thiếu trường 'chunk_id' hoặc chunk_id rỗng!"
                )
            if "tokens" not in r:
                raise ValueError(f"bm25_corpus.jsonl dòng {line_no} thiếu trường 'tokens'")
            tokens = r["tokens"]
            if not isinstance(tokens, list):
                raise ValueError(f"bm25_corpus.jsonl dòng {line_no} trường 'tokens' phải là list")
            if len(tokens) == 0:
                raise ValueError(f"bm25_corpus.jsonl dòng {line_no} trường 'tokens' không được rỗng!")
            if not all(isinstance(t, str) and t.strip() for t in tokens):
                raise ValueError(
                    f"bm25_corpus.jsonl dòng {line_no} chứa token không hợp lệ (phải là chuỗi không rỗng)"
                )
            tokenized_corpus.append(tokens)

        total_tokens = sum(len(doc) for doc in tokenized_corpus)
        if total_tokens == 0:
            raise ValueError("bm25_corpus.jsonl không chứa token hợp lệ nào (tổng số tokens = 0)!")

        # Kiểm tra khớp 1:1 cả về thứ tự chunk_id giữa corpus JSONL và bm25_meta
        corpus_chunk_ids = [r["chunk_id"] for r in corpus_records]
        meta_chunk_ids = [m["chunk_id"] for m in self._bm25_meta]
        if corpus_chunk_ids != meta_chunk_ids:
            raise ValueError(
                "bm25_corpus.jsonl lệch thứ tự hoặc danh sách chunk_id so với bm25_meta.jsonl!"
            )

        self._bm25 = BM25Okapi(tokenized_corpus)

        # Kiểm tra số lượng Fail-Closed
        n_docs = getattr(self._bm25, "corpus_size", None)
        if n_docs is None or n_docs != len(self._bm25_meta):
            raise ValueError(
                f"BM25 count mismatch hoặc không xác định: meta={len(self._bm25_meta)}, docs={n_docs}"
            )
        logger.info(f"BM25: {len(self._bm25_meta)} docs khởi tạo thành công từ JSONL (an toàn, không pickle).")

    def _load_embed_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "sentence-transformers chưa cài. Chạy: pip install sentence-transformers"
            ) from e

        logger.info(f"Loading embedding model: {settings.EMBED_MODEL}")
        self._embed_model = SentenceTransformer(settings.EMBED_MODEL)
        logger.info("Embedding model loaded.")

    def _load_segmenter(self) -> None:
        """Load segmenter và chạy warmup kiểm tra thực tế lúc startup."""
        if not settings.WORD_SEGMENTATION:
            self._segmenter = lambda text: text
            return

        try:
            from underthesea import word_tokenize
            self._segmenter = lambda text: word_tokenize(text, format="text")
            logger.info("Segmenter: underthesea word_tokenize (WORD_SEGMENTATION=True)")
        except ImportError as e:
            raise ImportError(
                "underthesea is required when WORD_SEGMENTATION is True. Install it with: pip install underthesea"
            ) from e

        # Warmup lúc startup: Gọi thử để bảo đảm mô hình hoạt động ổn định trước khi nhận request
        try:
            test_out = self._segmenter("Trường Đại học Giao thông vận tải")
            if not isinstance(test_out, str) or not test_out.strip():
                raise RuntimeError("Kết quả phân tách từ rỗng hoặc không hợp lệ")
            logger.info("Segmenter: underthesea word_tokenize warmup thành công.")
        except Exception as e:
            raise RuntimeError(f"Lỗi khởi tạo/warmup segmenter underthesea lúc startup: {e}") from e

    def _validate_dimensions_and_metadata(self, index_dir: Path) -> None:
        """Kiểm tra tính nhất quán giữa FAISS, BM25 và embedding model."""
        # Nạp manifest từ bytes đã hash trong bộ nhớ
        if "index_manifest.json" in self._file_bytes:
            try:
                manifest = json.loads(self._file_bytes["index_manifest.json"].decode("utf-8"))
            except Exception as e:
                raise ValueError(f"index_manifest.json bị hỏng hoặc không đúng chuẩn JSON: {e}") from e
        else:
            manifest_path = index_dir / "index_manifest.json"
            if not manifest_path.exists():
                raise FileNotFoundError(
                    f"BẮT BUỘC có file siêu dữ liệu {manifest_path}. "
                    "Hệ thống từ chối khởi động (fail-closed) để phòng ngừa lệch mô hình embedding. "
                    "Chạy: python backend/pipeline/make_index_manifest.py để tạo index_manifest.json."
                )
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            except Exception as e:
                raise ValueError(f"File {manifest_path} bị hỏng hoặc không đúng chuẩn JSON: {e}") from e

        if not isinstance(manifest, dict):
            raise ValueError("index_manifest.json rỗng hoặc cấu trúc không hợp lệ!")

        # Bắt buộc phải có đủ 5 trường cốt lõi
        required_keys = {"embed_model", "word_segmentation", "ntotal", "dimension", "metric_type"}
        missing_keys = required_keys - set(manifest.keys())
        if missing_keys:
            raise ValueError(f"index_manifest.json thiếu trường bắt buộc: {missing_keys}")

        # Kiểm tra khớp cấu hình embedding model
        if manifest["embed_model"] != settings.EMBED_MODEL:
            raise ValueError(
                f"Cấu hình EMBED_MODEL ({settings.EMBED_MODEL}) lệch với mô hình index đã build ({manifest['embed_model']})! "
                "Vui lòng rebuild index bằng backend/pipeline/embed_and_index.py hoặc đổi EMBED_MODEL trong config."
            )

        if manifest["word_segmentation"] != settings.WORD_SEGMENTATION:
            raise ValueError(
                f"Cấu hình WORD_SEGMENTATION ({settings.WORD_SEGMENTATION}) lệch với index build ({manifest['word_segmentation']})!"
            )

        if manifest["ntotal"] != self._faiss_index.ntotal:
            raise ValueError(
                f"Manifest ntotal ({manifest['ntotal']}) mismatch với FAISS index ({self._faiss_index.ntotal})"
            )

        if manifest["dimension"] != self._faiss_index.d:
            raise ValueError(
                f"FAISS dimension ({self._faiss_index.d}) lệch với index manifest ({manifest['dimension']})"
            )

        # Kiểm tra embedding model dimension
        if self._embed_model is not None and self._faiss_index is not None:
            model_dim = None
            dim_fn = getattr(self._embed_model, "get_embedding_dimension", None)
            if callable(dim_fn):
                res = dim_fn()
                if isinstance(res, (int, np.integer)):
                    model_dim = int(res)
            if model_dim is None:
                sent_fn = getattr(self._embed_model, "get_sentence_embedding_dimension", None)
                if callable(sent_fn):
                    res = sent_fn()
                    if isinstance(res, (int, np.integer)):
                        model_dim = int(res)

            index_dim = self._faiss_index.d
            if model_dim is not None and model_dim != index_dim:
                raise ValueError(
                    f"FATAL: Embedding model dimension ({model_dim}) mismatch với FAISS index dimension ({index_dim})! "
                    f"Vui lòng rebuild index bằng `backend/pipeline/embed_and_index.py` hoặc đổi `EMBED_MODEL` trong config."
                )

        # Kiểm tra tính duy nhất và thứ tự chunk_id khớp 1:1 giữa FAISS và BM25 meta
        faiss_ids = [m["chunk_id"] for m in self._faiss_meta]
        bm25_ids = [m["chunk_id"] for m in self._bm25_meta]

        if len(set(faiss_ids)) != len(faiss_ids):
            raise ValueError(f"faiss_meta chứa chunk_id trùng lặp: {len(faiss_ids) - len(set(faiss_ids))} duplicates")
        if len(set(bm25_ids)) != len(bm25_ids):
            raise ValueError(f"bm25_meta chứa chunk_id trùng lặp: {len(bm25_ids) - len(set(bm25_ids))} duplicates")
        if faiss_ids != bm25_ids:
            raise ValueError("Lệch thứ tự hoặc danh sách chunk_id giữa faiss_meta và bm25_meta!")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @classmethod
    def _parse_jsonl_bytes(cls, content_bytes: bytes, file_name: str) -> List[JsonlRecord]:
        """
        Parse JSONL trực tiếp từ bộ nhớ bytes đã được xác thực hash (loại bỏ TOCTOU).
        Bảo đảm fail-closed, lưu chính xác số dòng vật lý (1-indexed).
        """
        records: List[JsonlRecord] = []
        try:
            content_str = content_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ValueError(f"Tệp {file_name} không đúng chuẩn mã hóa UTF-8: {e}") from e

        for line_idx, raw_line in enumerate(content_str.splitlines(), start=1):
            line = raw_line.strip()
            if line:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Corrupt JSON at line {line_idx} in {file_name}: {e}") from e
                if not isinstance(record, dict):
                    raise ValueError(
                        f"Dòng {line_idx} trong {file_name} không phải là JSON object (dict)!"
                    )
                records.append(JsonlRecord(record, line_idx))
        return records

    @classmethod
    def _load_jsonl(cls, path: Path) -> List[JsonlRecord]:
        """Đọc JSONL từ đường dẫn file và parse kèm số dòng vật lý."""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        try:
            data = path.read_bytes()
        except Exception as e:
            raise ValueError(f"Không thể đọc file {path}: {e}") from e
        return cls._parse_jsonl_bytes(data, path.name)

    # ------------------------------------------------------------------
    # Public API cho retrieval_service
    # ------------------------------------------------------------------

    @property
    def faiss_index(self):
        return self._faiss_index

    @property
    def faiss_meta(self) -> List[JsonlRecord]:
        return self._faiss_meta

    @property
    def bm25(self):
        return self._bm25

    @property
    def bm25_meta(self) -> List[JsonlRecord]:
        return self._bm25_meta

    def encode_query(self, query: str) -> np.ndarray:
        """Segment + encode query → L2-normalized vector (chuẩn hóa Unicode NFC)."""
        if not self._loaded or self._segmenter is None or self._embed_model is None:
            raise RuntimeError("IndexStore chưa được load(). Hãy gọi index_store.load() trước khi truy vấn.")
        query_nfc = unicodedata.normalize("NFC", query)
        segmented = self._segmenter(query_nfc)
        vec = self._embed_model.encode(
            [segmented],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return vec.astype(np.float32)

    def tokenize_query(self, query: str) -> List[str]:
        """
        Segment + tokenize query cho BM25 (chuẩn hóa Unicode NFC).
        Quy ước hợp đồng tokenization: lowercase, split sau segmenter (khớp với bm25_corpus.jsonl).
        """
        if not self._loaded or self._segmenter is None:
            raise RuntimeError("IndexStore chưa được load(). Hãy gọi index_store.load() trước khi truy vấn.")
        query_nfc = unicodedata.normalize("NFC", query)
        segmented = self._segmenter(query_nfc)
        return segmented.lower().split()

    @property
    def is_loaded(self) -> bool:
        return self._loaded


# Module-level singleton
index_store = IndexStore()
