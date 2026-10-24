"""Chuẩn hóa Min-Max dùng chung cho catalog và truy vấn."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

KHOANG_CACH_KHI_THIEU = 0.5


@dataclass(frozen=True)
class ChuanHoaSo:
    toi_thieu: float
    toi_da: float

    @classmethod
    def tu_chuoi(cls, chuoi_gia_tri: pd.Series) -> ChuanHoaSo:
        cac_gia_tri = pd.to_numeric(chuoi_gia_tri, errors="coerce").dropna()
        if cac_gia_tri.empty:
            raise ValueError("Không có giá trị số hợp lệ để chuẩn hóa.")
        return cls(toi_thieu=float(cac_gia_tri.min()), toi_da=float(cac_gia_tri.max()))

    @property
    def la_hang_so(self) -> bool:
        return self.toi_da == self.toi_thieu

    def chuan_hoa(self, gia_tri: float | int | None) -> float:
        if gia_tri is None or (isinstance(gia_tri, float) and np.isnan(gia_tri)):
            return float("nan")
        da_gioi_han = min(max(float(gia_tri), self.toi_thieu), self.toi_da)
        if self.la_hang_so:
            return 0.0
        return (da_gioi_han - self.toi_thieu) / (self.toi_da - self.toi_thieu)

    def khoang_cach_doi_xung(self, xe_gia_tri: float | None, truy_van_gia_tri: float) -> float:
        xe_da_chuan_hoa = self.chuan_hoa(xe_gia_tri)
        if np.isnan(xe_da_chuan_hoa):
            return KHOANG_CACH_KHI_THIEU
        truy_van_da_chuan_hoa = self.chuan_hoa(truy_van_gia_tri)
        return abs(xe_da_chuan_hoa - truy_van_da_chuan_hoa)

    def khoang_cach_toi_thieu(self, xe_gia_tri: float | None, toi_thieu: float) -> float:
        if xe_gia_tri is None or (isinstance(xe_gia_tri, float) and np.isnan(xe_gia_tri)):
            return KHOANG_CACH_KHI_THIEU
        if float(xe_gia_tri) >= float(toi_thieu):
            return 0.0
        if self.la_hang_so:
            return 1.0
        do_thieu = (float(toi_thieu) - float(xe_gia_tri)) / (self.toi_da - self.toi_thieu)
        return float(min(max(do_thieu, 0.0), 1.0))
