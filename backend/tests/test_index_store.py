import hashlib
import json
import numpy as np
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.index_store import IndexStore, REQUIRED_HASHED_FILES


# ----------------------------------------------------------------------
# 1. Tests cho _load_jsonl
# ----------------------------------------------------------------------

def test_load_jsonl_corrupt_raises_value_error(tmp_path: Path):
    bad_jsonl = tmp_path / "bad.jsonl"
    bad_jsonl.write_text("{\"valid\": 1}\nNOT_A_JSON_STRING\n", encoding="utf-8")
    
    with pytest.raises(ValueError, match="Corrupt JSON at line 2"):
        IndexStore._load_jsonl(bad_jsonl)


def test_load_jsonl_file_not_found(tmp_path: Path):
    missing_file = tmp_path / "missing.jsonl"
    with pytest.raises(FileNotFoundError):
        IndexStore._load_jsonl(missing_file)


# ----------------------------------------------------------------------
# 2. Tests cho _load_faiss
# ----------------------------------------------------------------------

def test_load_faiss_missing_file_raises_not_found(tmp_path: Path):
    store = IndexStore()
    with pytest.raises(FileNotFoundError, match="Không tìm thấy FAISS index"):
        store._load_faiss(tmp_path)


def test_load_faiss_meta_mismatch_raises_value_error(tmp_path: Path):
    store = IndexStore()
    faiss_file = tmp_path / "faiss.index"
    faiss_file.write_bytes(b"dummy")
    meta_file = tmp_path / "faiss_meta.jsonl"
    meta_file.write_text("{\"chunk_id\": \"c1\"}\n", encoding="utf-8")

    import faiss
    mock_index = MagicMock()
    mock_index.ntotal = 5
    mock_index.d = 768
    mock_index.metric_type = faiss.METRIC_INNER_PRODUCT

    with patch("faiss.read_index", return_value=mock_index):
        with pytest.raises(ValueError, match="FAISS count mismatch"):
            store._load_faiss(tmp_path)


def test_load_faiss_metric_type_mismatch_raises_value_error(tmp_path: Path):
    store = IndexStore()
    faiss_file = tmp_path / "faiss.index"
    faiss_file.write_bytes(b"dummy")
    meta_file = tmp_path / "faiss_meta.jsonl"
    meta_file.write_text("{\"chunk_id\": \"c1\"}\n", encoding="utf-8")

    mock_index = MagicMock()
    mock_index.ntotal = 1
    mock_index.d = 768
    mock_index.metric_type = 1  # Khác METRIC_INNER_PRODUCT (0)

    with patch("faiss.read_index", return_value=mock_index):
        with pytest.raises(ValueError, match="FAISS metric type mismatch"):
            store._load_faiss(tmp_path)


# ----------------------------------------------------------------------
# 3. Tests cho _load_bm25 (JSONL, Thứ tự & Chunk ID 1:1, Không Pickle)
# ----------------------------------------------------------------------

def test_load_bm25_missing_meta_raises_not_found(tmp_path: Path):
    store = IndexStore()
    with pytest.raises(FileNotFoundError, match="Không tìm thấy BM25 meta"):
        store._load_bm25(tmp_path)


def test_load_bm25_missing_corpus_file_raises_not_found(tmp_path: Path):
    store = IndexStore()
    meta_file = tmp_path / "bm25_meta.jsonl"
    meta_file.write_text("{\"chunk_id\": \"c1\"}\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Không tìm thấy .*bm25_corpus.jsonl"):
        store._load_bm25(tmp_path)


def test_load_bm25_meta_mismatch_raises_value_error(tmp_path: Path):
    store = IndexStore()
    meta_file = tmp_path / "bm25_meta.jsonl"
    meta_file.write_text("{\"chunk_id\": \"c1\"}\n", encoding="utf-8")
    jsonl_file = tmp_path / "bm25_corpus.jsonl"
    jsonl_file.write_text(
        "{\"chunk_id\": \"c1\", \"tokens\": [\"a\"]}\n{\"chunk_id\": \"c2\", \"tokens\": [\"b\"]}\n",
        encoding="utf-8"
    )

    # 1 meta vs 2 corpus -> lệch count hoặc lệch chunk_id
    with pytest.raises(ValueError, match="lệch thứ tự|BM25 count mismatch"):
        store._load_bm25(tmp_path)


def test_load_bm25_tokens_key_missing_raises_value_error(tmp_path: Path):
    store = IndexStore()
    meta_file = tmp_path / "bm25_meta.jsonl"
    meta_file.write_text("{\"chunk_id\": \"c1\"}\n", encoding="utf-8")
    jsonl_file = tmp_path / "bm25_corpus.jsonl"
    jsonl_file.write_text("{\"chunk_id\": \"c1\", \"no_tokens\": [\"a\"]}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="dòng 1 thiếu trường 'tokens'"):
        store._load_bm25(tmp_path)


def test_load_bm25_tokens_not_list_raises_value_error(tmp_path: Path):
    store = IndexStore()
    meta_file = tmp_path / "bm25_meta.jsonl"
    meta_file.write_text("{\"chunk_id\": \"c1\"}\n", encoding="utf-8")
    jsonl_file = tmp_path / "bm25_corpus.jsonl"
    jsonl_file.write_text("{\"chunk_id\": \"c1\", \"tokens\": \"not_a_list\"}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="trường 'tokens' phải là list"):
        store._load_bm25(tmp_path)


def test_load_bm25_order_mismatch_raises_value_error(tmp_path: Path):
    store = IndexStore()
    meta_file = tmp_path / "bm25_meta.jsonl"
    meta_file.write_text("{\"chunk_id\": \"c1\"}\n{\"chunk_id\": \"c2\"}\n", encoding="utf-8")
    jsonl_file = tmp_path / "bm25_corpus.jsonl"
    # Ngược thứ tự: c2 rồi đến c1
    jsonl_file.write_text(
        "{\"chunk_id\": \"c2\", \"tokens\": [\"b\"]}\n{\"chunk_id\": \"c1\", \"tokens\": [\"a\"]}\n",
        encoding="utf-8"
    )

    with pytest.raises(ValueError, match="lệch thứ tự hoặc danh sách chunk_id"):
        store._load_bm25(tmp_path)


def test_load_bm25_jsonl_loads_successfully_without_pickle(tmp_path: Path):
    store = IndexStore()
    meta_file = tmp_path / "bm25_meta.jsonl"
    meta_file.write_text("{\"chunk_id\": \"c1\"}\n", encoding="utf-8")
    jsonl_file = tmp_path / "bm25_corpus.jsonl"
    jsonl_file.write_text("{\"chunk_id\": \"c1\", \"tokens\": [\"tuyen\", \"sinh\"]}\n", encoding="utf-8")

    store._load_bm25(tmp_path)
    assert store.bm25 is not None
    assert getattr(store.bm25, "corpus_size", 0) == 1
    assert len(store.bm25_meta) == 1


# ----------------------------------------------------------------------
# 4. Tests cho _verify_index_hashes (Fail-Closed, Path Traversal, 5 Files)
# ----------------------------------------------------------------------

def test_verify_index_hashes_missing_hash_file_fails_closed(tmp_path: Path):
    store = IndexStore()
    with pytest.raises(FileNotFoundError, match="BẮT BUỘC có file kiểm tra tính toàn vẹn"):
        store._verify_index_hashes(tmp_path)


def test_verify_index_hashes_missing_required_key_fails_closed(tmp_path: Path):
    store = IndexStore()
    hash_file = tmp_path / "index_hashes.json"
    # Thiếu index_manifest.json và bm25_corpus.jsonl
    hash_file.write_text(json.dumps({
        "faiss.index": "hash1",
        "faiss_meta.jsonl": "hash2",
        "bm25_meta.jsonl": "hash3"
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="Hash map thiếu tệp bắt buộc"):
        store._verify_index_hashes(tmp_path)


def test_verify_index_hashes_path_traversal_detection(tmp_path: Path):
    store = IndexStore()
    hash_file = tmp_path / "index_hashes.json"
    bad_map = {k: "hash" for k in REQUIRED_HASHED_FILES}
    bad_map["../malicious.txt"] = "evilhash"
    hash_file.write_text(json.dumps(bad_map), encoding="utf-8")

    with pytest.raises(ValueError, match="Tên file không hợp lệ hoặc chứa đường dẫn"):
        store._verify_index_hashes(tmp_path)


def test_verify_index_hashes_detects_mismatch(tmp_path: Path):
    store = IndexStore()
    files = {}
    for k in REQUIRED_HASHED_FILES:
        f = tmp_path / k
        f.write_bytes(b"content_" + k.encode())
        files[k] = hashlib.sha256(b"content_" + k.encode()).hexdigest()

    # Làm sai lệch 1 file hash
    files["faiss.index"] = "incorrect_sha256_hash"
    hash_file = tmp_path / "index_hashes.json"
    hash_file.write_text(json.dumps(files), encoding="utf-8")

    with pytest.raises(ValueError, match="Hash mismatch cho faiss.index"):
        store._verify_index_hashes(tmp_path)


# ----------------------------------------------------------------------
# 5. Tests cho _validate_dimensions_and_metadata (Manifest Bắt buộc)
# ----------------------------------------------------------------------

def test_validate_manifest_missing_manifest_fails_closed(tmp_path: Path):
    store = IndexStore()
    with pytest.raises(FileNotFoundError, match="BẮT BUỘC có file siêu dữ liệu"):
        store._validate_dimensions_and_metadata(tmp_path)


def test_validate_manifest_missing_key_fails_closed(tmp_path: Path):
    store = IndexStore()
    manifest_file = tmp_path / "index_manifest.json"
    # Thiếu dimension và metric_type
    manifest_file.write_text(json.dumps({
        "embed_model": "bkai-foundation-models/vietnamese-bi-encoder",
        "word_segmentation": True,
        "ntotal": 10
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="index_manifest.json thiếu trường bắt buộc"):
        store._validate_dimensions_and_metadata(tmp_path)


def test_validate_manifest_detects_model_mismatch(tmp_path: Path):
    store = IndexStore()
    manifest_file = tmp_path / "index_manifest.json"
    manifest_file.write_text(json.dumps({
        "embed_model": "wrong-model-name",
        "word_segmentation": True,
        "ntotal": 10,
        "dimension": 768,
        "metric_type": "METRIC_INNER_PRODUCT"
    }), encoding="utf-8")

    with patch("app.core.index_store.settings.EMBED_MODEL", "bkai-foundation-models/vietnamese-bi-encoder"):
        with pytest.raises(ValueError, match="Cấu hình EMBED_MODEL .* lệch với mô hình index đã build"):
            store._validate_dimensions_and_metadata(tmp_path)


def test_validate_manifest_detects_word_seg_mismatch(tmp_path: Path):
    store = IndexStore()
    manifest_file = tmp_path / "index_manifest.json"
    manifest_file.write_text(json.dumps({
        "embed_model": "bkai-foundation-models/vietnamese-bi-encoder",
        "word_segmentation": False,
        "ntotal": 10,
        "dimension": 768,
        "metric_type": "METRIC_INNER_PRODUCT"
    }), encoding="utf-8")

    with patch("app.core.index_store.settings.EMBED_MODEL", "bkai-foundation-models/vietnamese-bi-encoder"):
        with patch("app.core.index_store.settings.WORD_SEGMENTATION", True):
            with pytest.raises(ValueError, match="Cấu hình WORD_SEGMENTATION .* lệch với index build"):
                store._validate_dimensions_and_metadata(tmp_path)


def test_validate_manifest_detects_dimension_mismatch(tmp_path: Path):
    store = IndexStore()
    manifest_file = tmp_path / "index_manifest.json"
    manifest_file.write_text(json.dumps({
        "embed_model": "bkai-foundation-models/vietnamese-bi-encoder",
        "word_segmentation": True,
        "ntotal": 10,
        "dimension": 1024,  # Lệch với faiss 768
        "metric_type": "METRIC_INNER_PRODUCT"
    }), encoding="utf-8")

    mock_faiss = MagicMock()
    mock_faiss.ntotal = 10
    mock_faiss.d = 768
    store._faiss_index = mock_faiss

    with patch("app.core.index_store.settings.EMBED_MODEL", "bkai-foundation-models/vietnamese-bi-encoder"):
        with patch("app.core.index_store.settings.WORD_SEGMENTATION", True):
            with pytest.raises(ValueError, match="FAISS dimension .* lệch với index manifest"):
                store._validate_dimensions_and_metadata(tmp_path)


# ----------------------------------------------------------------------
# 6. Tests cho Chunk ID Order & Uniqueness Alignment giữa FAISS và BM25
# ----------------------------------------------------------------------

def test_chunk_id_order_mismatch_between_faiss_and_bm25_raises_error(tmp_path: Path):
    store = IndexStore()
    # Tạo manifest hợp lệ
    manifest_file = tmp_path / "index_manifest.json"
    manifest_file.write_text(json.dumps({
        "embed_model": "bkai-foundation-models/vietnamese-bi-encoder",
        "word_segmentation": True,
        "ntotal": 2,
        "dimension": 768,
        "metric_type": "METRIC_INNER_PRODUCT"
    }), encoding="utf-8")

    mock_faiss = MagicMock()
    mock_faiss.ntotal = 2
    mock_faiss.d = 768
    store._faiss_index = mock_faiss

    # Cùng tập nhưng khác thứ tự
    store._faiss_meta = [{"chunk_id": "c1"}, {"chunk_id": "c2"}]
    store._bm25_meta = [{"chunk_id": "c2"}, {"chunk_id": "c1"}]

    with patch("app.core.index_store.settings.EMBED_MODEL", "bkai-foundation-models/vietnamese-bi-encoder"):
        with patch("app.core.index_store.settings.WORD_SEGMENTATION", True):
            with pytest.raises(ValueError, match="Lệch thứ tự hoặc danh sách chunk_id"):
                store._validate_dimensions_and_metadata(tmp_path)


def test_chunk_id_duplicate_in_faiss_meta_raises_error(tmp_path: Path):
    store = IndexStore()
    manifest_file = tmp_path / "index_manifest.json"
    manifest_file.write_text(json.dumps({
        "embed_model": "bkai-foundation-models/vietnamese-bi-encoder",
        "word_segmentation": True,
        "ntotal": 2,
        "dimension": 768,
        "metric_type": "METRIC_INNER_PRODUCT"
    }), encoding="utf-8")

    mock_faiss = MagicMock()
    mock_faiss.ntotal = 2
    mock_faiss.d = 768
    store._faiss_index = mock_faiss

    # faiss_meta có duplicate
    store._faiss_meta = [{"chunk_id": "c1"}, {"chunk_id": "c1"}]
    store._bm25_meta = [{"chunk_id": "c1"}, {"chunk_id": "c2"}]

    with patch("app.core.index_store.settings.EMBED_MODEL", "bkai-foundation-models/vietnamese-bi-encoder"):
        with patch("app.core.index_store.settings.WORD_SEGMENTATION", True):
            with pytest.raises(ValueError, match="faiss_meta chứa chunk_id trùng lặp"):
                store._validate_dimensions_and_metadata(tmp_path)


# ----------------------------------------------------------------------
# 7. Tests cho Segmenter, Query Guards và Lifespan
# ----------------------------------------------------------------------

def test_load_segmenter_missing_underthesea_raises_import_error():
    store = IndexStore()
    with patch("app.core.index_store.settings.WORD_SEGMENTATION", True):
        with patch.dict("sys.modules", {"underthesea": None}):
            with pytest.raises(ImportError, match="underthesea is required"):
                store._load_segmenter()


def test_encode_and_tokenize_query_guard_before_load():
    store = IndexStore()
    with pytest.raises(RuntimeError, match="IndexStore chưa được load"):
        store.encode_query("tuyển sinh 2026")

    with pytest.raises(RuntimeError, match="IndexStore chưa được load"):
        store.tokenize_query("tuyển sinh 2026")


def test_lifespan_does_not_call_sys_exit_on_load_error():
    """Kiểm tra ngoại lệ nạp index nổi lên tự nhiên mà không bị nuốt hoặc gọi sys.exit."""
    from app.main import lifespan, app
    
    with patch("app.core.index_store.index_store.load", side_effect=ValueError("Test load failure")):
        with patch("sys.exit") as mock_exit:
            with pytest.raises(ValueError, match="Test load failure"):
                # Mô phỏng ASGI lifespan context
                import asyncio
                async def run_lifespan():
                    async with lifespan(app):
                        pass
                asyncio.run(run_lifespan())
            # Khẳng định sys.exit không hề bị gọi
            mock_exit.assert_not_called()


def test_load_jsonl_non_dict_object_raises_value_error(tmp_path):
    fpath = tmp_path / "primitive.jsonl"
    fpath.write_text('"just a string"\n123\n', encoding="utf-8")
    with pytest.raises(ValueError, match="không phải là JSON object"):
        IndexStore._load_jsonl(fpath)


def test_load_faiss_faiss_id_mismatch_raises_value_error(tmp_path):
    store = IndexStore()
    faiss_file = tmp_path / "faiss.index"
    faiss_file.write_bytes(b"dummy")
    meta_file = tmp_path / "faiss_meta.jsonl"
    meta_file.write_text(
        '{"faiss_id": 1, "chunk_id": "c1"}\n{"faiss_id": 0, "chunk_id": "c2"}\n',
        encoding="utf-8",
    )

    mock_faiss_module = MagicMock()
    mock_index = MagicMock()
    mock_index.metric_type = 0  # METRIC_INNER_PRODUCT
    mock_index.ntotal = 2
    mock_faiss_module.METRIC_INNER_PRODUCT = 0
    mock_faiss_module.read_index.return_value = mock_index

    with patch.dict("sys.modules", {"faiss": mock_faiss_module}):
        with pytest.raises(ValueError, match="FAISS metadata index mismatch"):
            store._load_faiss(tmp_path)


# ----------------------------------------------------------------------
# 8. Tests theo phản biện chuyên sâu (CD11 Verification & Hardening)
# ----------------------------------------------------------------------

def test_faiss_meta_missing_or_empty_chunk_id_raises_value_error(tmp_path: Path):
    store = IndexStore()
    faiss_file = tmp_path / "faiss.index"
    faiss_file.write_bytes(b"dummy")
    meta_file = tmp_path / "faiss_meta.jsonl"
    meta_file.write_text('{"faiss_id": 0, "chunk_id": "   "}\n', encoding="utf-8")

    mock_faiss_module = MagicMock()
    mock_index = MagicMock()
    mock_index.metric_type = 0
    mock_index.ntotal = 1
    mock_faiss_module.METRIC_INNER_PRODUCT = 0
    mock_faiss_module.read_index.return_value = mock_index

    with patch.dict("sys.modules", {"faiss": mock_faiss_module}):
        with pytest.raises(ValueError, match="thiếu trường 'chunk_id' hoặc chunk_id rỗng"):
            store._load_faiss(tmp_path)


def test_bm25_meta_missing_or_empty_chunk_id_raises_value_error(tmp_path: Path):
    store = IndexStore()
    meta_file = tmp_path / "bm25_meta.jsonl"
    meta_file.write_text('{"no_chunk_id": 123}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="thiếu trường 'chunk_id' hoặc chunk_id rỗng"):
        store._load_bm25(tmp_path)


def test_bm25_corpus_missing_or_empty_chunk_id_raises_value_error(tmp_path: Path):
    store = IndexStore()
    meta_file = tmp_path / "bm25_meta.jsonl"
    meta_file.write_text('{"chunk_id": "c1"}\n', encoding="utf-8")
    corpus_file = tmp_path / "bm25_corpus.jsonl"
    corpus_file.write_text('{"tokens": ["tuyen", "sinh"]}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="thiếu trường 'chunk_id' hoặc chunk_id rỗng"):
        store._load_bm25(tmp_path)


def test_bm25_corpus_invalid_token_type_raises_value_error(tmp_path: Path):
    store = IndexStore()
    meta_file = tmp_path / "bm25_meta.jsonl"
    meta_file.write_text('{"chunk_id": "c1"}\n', encoding="utf-8")
    corpus_file = tmp_path / "bm25_corpus.jsonl"
    # Token chứa int thay vì string
    corpus_file.write_text('{"chunk_id": "c1", "tokens": [123, "tuyen"]}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="chứa token không hợp lệ"):
        store._load_bm25(tmp_path)


def test_bm25_corpus_empty_tokens_doc_raises_value_error(tmp_path: Path):
    store = IndexStore()
    meta_file = tmp_path / "bm25_meta.jsonl"
    meta_file.write_text('{"chunk_id": "c1"}\n', encoding="utf-8")
    corpus_file = tmp_path / "bm25_corpus.jsonl"
    # Doc có tokens rỗng
    corpus_file.write_text('{"chunk_id": "c1", "tokens": []}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="trường 'tokens' không được rỗng"):
        store._load_bm25(tmp_path)


def test_bm25_corpus_error_reports_exact_physical_line_number(tmp_path: Path):
    store = IndexStore()
    meta_file = tmp_path / "bm25_meta.jsonl"
    meta_file.write_text('{"chunk_id": "c1"}\n{"chunk_id": "c2"}\n', encoding="utf-8")
    corpus_file = tmp_path / "bm25_corpus.jsonl"
    # Dòng 1: hợp lệ, Dòng 2 & 3: dòng trống, Dòng 4: lỗi
    corpus_file.write_text(
        '{"chunk_id": "c1", "tokens": ["ok"]}\n\n\n{"chunk_id": "c2", "tokens": "not_a_list"}\n',
        encoding="utf-8"
    )

    # Phải báo đúng dòng 4 của tệp vật lý, không phải dòng 2
    with pytest.raises(ValueError, match="dòng 4 trường 'tokens' phải là list"):
        store._load_bm25(tmp_path)


def test_load_segmenter_warmup_failure_raises_runtime_error():
    store = IndexStore()
    mock_tokenize = MagicMock(side_effect=Exception("Model weight corrupted"))
    with patch("app.core.index_store.settings.WORD_SEGMENTATION", True), \
         patch.dict("sys.modules", {"underthesea": MagicMock(word_tokenize=mock_tokenize)}):
        with pytest.raises(RuntimeError, match="Lỗi khởi tạo/warmup segmenter underthesea"):
            store._load_segmenter()


def test_verify_index_hashes_empty_filename_raises_value_error(tmp_path: Path):
    store = IndexStore()
    hash_file = tmp_path / "index_hashes.json"
    bad_map = {k: "hash" for k in REQUIRED_HASHED_FILES}
    bad_map[""] = "hash"
    hash_file.write_text(json.dumps(bad_map), encoding="utf-8")

    with pytest.raises(ValueError, match="Tên file trong hash map không được để trống"):
        store._verify_index_hashes(tmp_path)


def test_verify_index_hashes_unknown_file_rejected_by_whitelist(tmp_path: Path):
    store = IndexStore()
    hash_file = tmp_path / "index_hashes.json"
    bad_map = {k: "hash" for k in REQUIRED_HASHED_FILES}
    bad_map["extra_unauthorized.txt"] = "hash"
    hash_file.write_text(json.dumps(bad_map), encoding="utf-8")

    with pytest.raises(ValueError, match="Hash map chứa tệp lạ không nằm trong whitelist bắt buộc"):
        store._verify_index_hashes(tmp_path)


def test_verify_index_hashes_symlink_raises_value_error(tmp_path: Path):
    import os
    store = IndexStore()
    # Tạo các file thật
    for k in REQUIRED_HASHED_FILES:
        (tmp_path / k).write_bytes(b"content_" + k.encode())

    # Thay 1 file bằng symlink
    target_real = tmp_path / "target_real.txt"
    target_real.write_bytes(b"real content")
    symlink_file = tmp_path / "faiss.index"
    symlink_file.unlink()
    try:
        os.symlink(target_real, symlink_file)
    except (OSError, NotImplementedError):
        pytest.skip("Hệ điều hành hiện tại không có quyền tạo symlink không cần admin")

    hashes = {k: "dummy" for k in REQUIRED_HASHED_FILES}
    (tmp_path / "index_hashes.json").write_text(json.dumps(hashes), encoding="utf-8")

    with pytest.raises(ValueError, match="Tệp không được phép là symlink"):
        store._verify_index_hashes(tmp_path)


def test_query_unicode_nfc_normalization():
    import unicodedata
    store = IndexStore()
    store._loaded = True
    store._segmenter = lambda t: t
    mock_model = MagicMock()
    mock_model.encode.return_value = np.zeros((1, 768), dtype=np.float32)
    store._embed_model = mock_model

    # Chuỗi NFD (tổ hợp)
    query_nfd = unicodedata.normalize("NFD", "Điểm chuẩn Toán Tin")
    assert query_nfd != unicodedata.normalize("NFC", "Điểm chuẩn Toán Tin")

    # tokenize_query phải chuẩn hóa thành NFC
    tokens = store.tokenize_query(query_nfd)
    for token in tokens:
        assert unicodedata.is_normalized("NFC", token)

    # encode_query cũng phải chuẩn hóa thành NFC trước khi encode
    store.encode_query(query_nfd)
    encoded_arg = mock_model.encode.call_args[0][0][0]
    assert unicodedata.is_normalized("NFC", encoded_arg)


def test_full_successful_load_pipeline(tmp_path: Path):
    """Happy path đầy đủ: Tạo FAISS IndexFlatIP thật, BM25 corpus thật, hashes thật, load thành công."""
    import faiss

    dim = 768
    index = faiss.IndexFlatIP(dim)
    vectors = np.random.randn(2, dim).astype(np.float32)
    faiss.normalize_L2(vectors)
    index.add(vectors)
    faiss_path = tmp_path / "faiss.index"
    faiss.write_index(index, str(faiss_path))

    (tmp_path / "faiss_meta.jsonl").write_text(
        '{"chunk_id": "c1", "faiss_id": 0}\n{"chunk_id": "c2", "faiss_id": 1}\n',
        encoding="utf-8"
    )
    (tmp_path / "bm25_meta.jsonl").write_text(
        '{"chunk_id": "c1"}\n{"chunk_id": "c2"}\n',
        encoding="utf-8"
    )
    (tmp_path / "bm25_corpus.jsonl").write_text(
        '{"chunk_id": "c1", "tokens": ["tuyen", "sinh"]}\n{"chunk_id": "c2", "tokens": ["diem", "chuan"]}\n',
        encoding="utf-8"
    )
    (tmp_path / "index_manifest.json").write_text(json.dumps({
        "embed_model": "bkai-foundation-models/vietnamese-bi-encoder",
        "word_segmentation": False,
        "ntotal": 2,
        "dimension": 768,
        "metric_type": "METRIC_INNER_PRODUCT"
    }), encoding="utf-8")

    # Sinh index_hashes.json chuẩn
    hashes = {}
    for f in REQUIRED_HASHED_FILES:
        hashes[f] = hashlib.sha256((tmp_path / f).read_bytes()).hexdigest()
    (tmp_path / "index_hashes.json").write_text(json.dumps(hashes), encoding="utf-8")

    mock_model = MagicMock()
    mock_model.get_sentence_embedding_dimension.return_value = 768
    mock_model.get_embedding_dimension.return_value = 768
    mock_model.encode.return_value = np.zeros((1, 768), dtype=np.float32)

    store = IndexStore()
    with patch("app.core.index_store.settings.EMBED_MODEL", "bkai-foundation-models/vietnamese-bi-encoder"), \
         patch("app.core.index_store.settings.WORD_SEGMENTATION", False), \
         patch("sentence_transformers.SentenceTransformer", return_value=mock_model):
        store.load(tmp_path)

    assert store.is_loaded is True
    assert store.faiss_index.ntotal == 2
    assert store.faiss_index.d == 768
    assert store.bm25.corpus_size == 2
    assert len(store.faiss_meta) == 2
    assert len(store.bm25_meta) == 2

    # Thử nghiệm truy vấn
    tokens = store.tokenize_query("tuyển sinh 2026")
    assert tokens == ["tuyển", "sinh", "2026"]
    vec = store.encode_query("tuyển sinh 2026")
    assert vec.shape == (1, 768)


