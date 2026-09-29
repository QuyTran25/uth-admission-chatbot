import os
from pathlib import Path
import pytest
from app.core.config import settings

def test_project_root_and_index_path_resolution():
    """Kiểm tra đường dẫn index luôn phân giải từ thư mục gốc dự án."""
    index_path = settings.index_dir_path
    assert index_path.is_absolute()
    assert index_path.name == "index"
    assert "backend" in str(index_path)
    # Đảm bảo không bị lồng backend/backend
    assert "backend/backend" not in str(index_path).replace("\\", "/")

def test_path_resolution_invariant_to_cwd(tmp_path):
    """Đảm bảo đổi working directory không làm sai lệch index_dir_path."""
    orig_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        index_path = settings.index_dir_path
        assert index_path.is_absolute()
        assert "backend/backend" not in str(index_path).replace("\\", "/")
    finally:
        os.chdir(orig_cwd)

def test_canonical_index_files_exist():
    """Kiểm tra các file index chuẩn tồn tại trong backend/data/index."""
    index_dir = settings.index_dir_path
    assert (index_dir / "faiss.index").exists(), f"Thiếu faiss.index tại {index_dir}"
    assert (index_dir / "faiss_meta.jsonl").exists(), f"Thiếu faiss_meta.jsonl tại {index_dir}"
    assert (index_dir / "bm25_corpus.pkl").exists(), f"Thiếu bm25_corpus.pkl tại {index_dir}"
    assert (index_dir / "bm25_meta.jsonl").exists(), f"Thiếu bm25_meta.jsonl tại {index_dir}"
