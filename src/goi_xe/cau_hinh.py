"""Cấu hình đường dẫn và Gemini, đọc từ biến môi trường khi cần."""

from __future__ import annotations

import math
import os
from pathlib import Path

DUONG_DAN_GOC = Path(__file__).resolve().parents[2]
DUONG_DAN_DANH_MUC_MAC_DINH = DUONG_DAN_GOC / "data" / "dataset-done.csv"
MO_HINH_GEMINI_MAC_DINH = "gemini-3.5-flash-lite"
THOI_GIAN_CHO_GEMINI_MAC_DINH = 30.0
TOP_K_MAC_DINH = 5


def lay_duong_dan_danh_muc() -> Path:
    tho = os.environ.get("MOTORCYCLE_CSV_PATH", "").strip()
    duong_dan = Path(tho).expanduser() if tho else DUONG_DAN_DANH_MUC_MAC_DINH
    if not duong_dan.is_absolute():
        duong_dan = DUONG_DAN_GOC / duong_dan
    return duong_dan


def lay_mo_hinh_gemini() -> str:
    return os.environ.get("GEMINI_MODEL", "").strip() or MO_HINH_GEMINI_MAC_DINH


def lay_thoi_gian_cho_gemini() -> float:
    tho = os.environ.get("GEMINI_TIMEOUT_SECONDS", "").strip()
    if not tho:
        return THOI_GIAN_CHO_GEMINI_MAC_DINH
    try:
        gia_tri = float(tho)
    except ValueError:
        return THOI_GIAN_CHO_GEMINI_MAC_DINH
    if not math.isfinite(gia_tri) or gia_tri <= 0:
        return THOI_GIAN_CHO_GEMINI_MAC_DINH
    return gia_tri
