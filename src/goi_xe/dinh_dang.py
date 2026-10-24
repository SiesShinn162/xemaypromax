"""Định dạng số và giá theo tiếng Việt để dùng chung ở UI và fallback."""

from __future__ import annotations

import math
from typing import Any

CHU_THIEU = "Chưa có dữ liệu"


def _la_gia_tri_thieu(gia_tri: Any) -> bool:
    return gia_tri is None or (isinstance(gia_tri, float) and math.isnan(gia_tri))


def dinh_dang_vnd(gia_tri: Any) -> str:
    if _la_gia_tri_thieu(gia_tri):
        return CHU_THIEU
    try:
        so = float(gia_tri)
    except (TypeError, ValueError):
        return CHU_THIEU
    return f"{so:,.0f}".replace(",", ".") + " ₫"


def dinh_dang_so(gia_tri: Any, *, chu_so: int = 1, hau_to: str = "") -> str:
    if _la_gia_tri_thieu(gia_tri):
        return CHU_THIEU
    try:
        so = float(gia_tri)
    except (TypeError, ValueError):
        return CHU_THIEU
    chu = f"{so:,.0f}" if chu_so == 0 else f"{so:,.{chu_so}f}"
    chu = chu.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{chu}{hau_to}"


def dinh_dang_nam(gia_tri: Any) -> str:
    if _la_gia_tri_thieu(gia_tri):
        return CHU_THIEU
    try:
        return str(int(float(gia_tri)))
    except (TypeError, ValueError):
        return CHU_THIEU


def dinh_dang_khoang_cach(gia_tri: Any) -> str:
    return dinh_dang_so(gia_tri, chu_so=3)


def chu_hoac_thieu(gia_tri: Any) -> str:
    if _la_gia_tri_thieu(gia_tri):
        return CHU_THIEU
    chu = str(gia_tri).strip()
    return chu or CHU_THIEU
