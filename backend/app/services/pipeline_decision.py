"""
pipeline_decision.py — Single Source of Truth (SSoT) cho logic phân định tiền sinh (Pre-generation).

Dùng chung cho cả:
1. Production Chat Runtime: backend/app/api/endpoints/chat.py
2. Offline / Regression Evaluation: backend/eval/pipeline_union_eval.py, backend/eval/tune_retrieval_gate.py

Các lớp lọc tuần tự (Pre-generation 3-Layer Filter):
  Lớp 1: year_filter      (phát hiện năm không hỗ trợ -> refused / fallback)
  Lớp 2: oos_filter       (phát hiện ý định ngoài phạm vi Hướng C -> refused)
  Lớp 3: retrieval_gate   (kiểm soát chất lượng tài liệu hybrid -> refused nếu dưới ngưỡng)
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.services.year_filter import (
    analyze as year_filter_analyze,
    OUT_OF_SCOPE_MESSAGE,
    YEAR_NOT_SUPPORTED_MESSAGE,
)
from app.services.oos_filter import check_oos
from app.services.retrieval_service import retrieve_with_dynamic_routing, ScoredChunk
from app.services.retrieval_gate import check_retrieval_quality

logger = logging.getLogger("pipeline_decision")

GATE_CONFIG_PATH = Path(__file__).resolve().parent.parent / "core" / "gate_config.json"


def load_gate_config() -> dict:
    """Nạp cấu hình Retrieval Gate từ gate_config.json."""
    if GATE_CONFIG_PATH.exists():
        try:
            with open(GATE_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Không thể đọc gate_config.json: {e}")
    return {
        "enabled": False,
        "consensus_type": "file",
        "threshold_default": 0.0,
        "threshold_consensus": 0.0,
        "margin_threshold": None,
    }


@dataclass
class DecisionResult:
    """Kết quả quyết định sau 3 lớp lọc tiền sinh."""
    behavior: str  # "answer" | "fallback_warning" | "refused" | "clarify"
    message: Optional[str] = None
    chunks: List[ScoredChunk] = field(default_factory=list)
    response_meta: Dict[str, Any] = field(default_factory=dict)
    filter_year: Optional[int] = None
    is_fallback: bool = False
    flagged_year_filter: bool = False
    flagged_oos: bool = False
    flagged_gate: bool = False
    refused_reason: Optional[str] = None
    oos_categories: List[str] = field(default_factory=list)
    gate_details: Optional[dict] = None

    @property
    def status(self) -> str:
        """Thuộc tính tương thích: 'refused' nếu bị chặn, 'proceed' nếu được tiếp tục."""
        return "refused" if self.behavior == "refused" else "proceed"

    @property
    def refusal_source(self) -> Optional[str]:
        """Thuộc tính tương thích: tên nguồn chặn ('year_filter' | 'oos_filter' | 'retrieval_gate')."""
        if self.flagged_year_filter:
            return "year_filter"
        if self.flagged_oos:
            return "oos_filter"
        if self.flagged_gate:
            return "retrieval_gate"
        return None


def apply_gate(
    chunks: List[ScoredChunk],
    response_meta: dict,
    gate_cfg: dict,
) -> Tuple[str, Optional[dict]]:
    """
    Hàm dùng chung kiểm tra chất lượng Retrieval Gate.
    Chỉ chạy khi gate_cfg['enabled'] is True.
    """
    if not gate_cfg.get("enabled", False):
        return "proceed", None

    th_default = float(gate_cfg.get("threshold_default", 0.0))
    th_consensus = float(gate_cfg.get("threshold_consensus", 0.0))
    c_type = gate_cfg.get("consensus_type", "file")
    margin_th = gate_cfg.get("margin_threshold")
    if margin_th is not None:
        margin_th = float(margin_th)

    if th_default <= 0.0 and th_consensus <= 0.0:
        logger.warning("Retrieval Gate đang bật nhưng ngưỡng <= 0.0; mọi truy xuất đều qua.")

    return check_retrieval_quality(
        chunks=chunks,
        response_meta=response_meta,
        threshold_default=th_default,
        threshold_consensus=th_consensus,
        consensus_type=c_type,
        margin_threshold=margin_th,
    )


def decide_query(
    query: str,
    top_k: int = 5,
    gate_enabled: Optional[bool] = None,
    gate_config: Optional[dict] = None,
    retriever_fn: Optional[Callable[..., Tuple[List[ScoredChunk], dict]]] = None,
    enable_boost: bool = True,
) -> DecisionResult:
    """
    Thực hiện quyết định tuần tự 3 lớp lọc tiền sinh.

    Args:
        query: Câu hỏi người dùng.
        top_k: Số chunk cần truy xuất.
        gate_enabled: Ghi đè bật/tắt Gate. Nếu None -> đọc từ gate_config.json.
        gate_config: Ghi đè cấu hình Gate. Nếu None -> đọc từ gate_config.json.
        retriever_fn: Hàm truy xuất tài liệu (mặc định: retrieve_with_dynamic_routing).
        enable_boost: Bật/tắt trọng số 1.2x cho tài liệu năm 2026.
    """
    gate_cfg = dict(gate_config or load_gate_config())
    if gate_enabled is not None:
        gate_cfg["enabled"] = gate_enabled

    # -------------------------------------------------------------------
    # Lớp 1: Year Filter
    # -------------------------------------------------------------------
    yr = year_filter_analyze(query)

    if yr.status == "refused":
        return DecisionResult(
            behavior="refused",
            message=yr.message or YEAR_NOT_SUPPORTED_MESSAGE,
            filter_year=yr.filter_year,
            flagged_year_filter=True,
            refused_reason="year_not_supported",
        )

    if yr.status == "clarification_needed":
        return DecisionResult(
            behavior="clarify",
            message=yr.message,
            filter_year=yr.filter_year,
            flagged_year_filter=False,
            refused_reason="year_clarification_required",
        )

    is_fallback = yr.warning is not None

    # -------------------------------------------------------------------
    # Lớp 2: OOS Filter (Hướng C)
    # -------------------------------------------------------------------
    is_oos, oos_categories = check_oos(
        query,
        year_filter_status=yr.status,
        year_filter_doc_type=yr.document_type,
    )

    if is_oos:
        return DecisionResult(
            behavior="refused",
            message=OUT_OF_SCOPE_MESSAGE,
            filter_year=yr.filter_year,
            is_fallback=is_fallback,
            flagged_oos=True,
            refused_reason="out_of_scope",
            oos_categories=oos_categories,
        )

    # -------------------------------------------------------------------
    # Lớp 3: Retrieval + Retrieval Gate
    # -------------------------------------------------------------------
    _retrieve = retriever_fn if retriever_fn is not None else retrieve_with_dynamic_routing
    try:
        chunks, resp_meta = _retrieve(
            query=query,
            filter_year=yr.filter_year,
            top_k=top_k,
            enable_boost=enable_boost,
        )
    except TypeError:
        try:
            chunks, resp_meta = _retrieve(
                query=query,
                filter_year=yr.filter_year,
                top_k=top_k,
            )
        except TypeError:
            chunks, resp_meta = _retrieve(query=query, top_k=top_k)

    status_gate, gate_data = apply_gate(chunks, resp_meta, gate_cfg)

    if status_gate == "refused":
        return DecisionResult(
            behavior="refused",
            message=OUT_OF_SCOPE_MESSAGE,
            chunks=chunks,
            response_meta=resp_meta,
            filter_year=yr.filter_year,
            is_fallback=is_fallback,
            flagged_gate=True,
            refused_reason="retrieval_gate_low_score",
            gate_details=gate_data,
        )

    # Vượt qua cả 3 lớp thành công -> Cho phép thế hệ văn bản (Generation)
    behavior = "fallback_warning" if is_fallback else "answer"
    return DecisionResult(
        behavior=behavior,
        message=yr.warning if is_fallback else None,
        chunks=chunks,
        response_meta=resp_meta,
        filter_year=yr.filter_year,
        is_fallback=is_fallback,
    )
