"""Lọc điều kiện cứng, tính khoảng cách Euclid có trọng số và trả Top-K."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from ..du_lieu.nap_du_lieu import COT_DU_LIEU, COT_NOI_BO, DanhMucXe
from ..du_lieu.phan_tich import (
    chuan_hoa_khoa,
    chuan_hoa_loai_xe,
    chuan_hoa_nhien_lieu,
    chuan_hoa_tinh_trang,
    lam_sach_chu,
)
from .chuan_hoa import KHOANG_CACH_KHI_THIEU, ChuanHoaSo
from .tieu_chi import (
    DINH_NGHIA_TIEU_CHI,
    GIA_MUC_TIEU,
    GIA_THAP,
    LoiThieuTieuChi,
    LoiTruyVanKhongHopLe,
    TieuChiMem,
    TruyVanGoiY,
    chuan_hoa_ban_do_trong_so,
)

BO_CHUAN_HOA_DANH_MUC = {
    "fuel_type": chuan_hoa_nhien_lieu,
    "vehicle_type": chuan_hoa_loai_xe,
    "condition": chuan_hoa_tinh_trang,
    "brand": lam_sach_chu,
}


@dataclass(frozen=True)
class TieuChiHoatDong:
    khoa: str
    nhan: str
    loai: str
    trong_so: float
    trong_so_chuan_hoa: float
    gia_tri: float | str | None
    che_do: str | None


@dataclass(frozen=True)
class XeDuocCham:
    thu_hang: int
    xe: dict[str, Any]
    khoang_cach: float
    do_tuong_tu: float
    khoang_cach_tieu_chi: dict[str, float]
    truong_thieu: tuple[str, ...]


@dataclass(frozen=True)
class KetQuaXepHang:
    cac_muc: tuple[XeDuocCham, ...]
    tieu_chi_dang_dung: tuple[TieuChiHoatDong, ...]
    trong_so_chuan_hoa: dict[str, float]
    tong_danh_muc: int
    so_xe_sau_loc: int
    so_xe_bi_loai: int
    dem_loc_cung: dict[str, int]
    truy_van: TruyVanGoiY

    @property
    def ma_xe_top_k(self) -> tuple[str, ...]:
        return tuple(muc.xe["vehicle_id"] for muc in self.cac_muc)


def _so_tuy_chon(gia_tri: Any) -> float | None:
    if gia_tri is None:
        return None
    try:
        so = float(gia_tri)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(so):
        return None
    return so


def _chuan_hoa_danh_muc(khoa: str, gia_tri: Any) -> str | None:
    chu = lam_sach_chu(gia_tri)
    if chu is None:
        return None
    ham_chuan_hoa = BO_CHUAN_HOA_DANH_MUC.get(khoa)
    if ham_chuan_hoa is None:
        return chuan_hoa_khoa(chu) or None
    return ham_chuan_hoa(chu)


def _chuan_bi_tieu_chi(
    truy_van: TruyVanGoiY,
) -> tuple[list[TieuChiHoatDong], dict[str, float]]:
    da_gap: set[str] = set()
    cac_trong_so: dict[str, float] = {}
    da_chuan_bi: list[tuple[str, float, float | str | None, str | None]] = []

    for tieu_chi in truy_van.tieu_chi:
        if not isinstance(tieu_chi, TieuChiMem):
            raise LoiTruyVanKhongHopLe("Tiêu chí ưu tiên không đúng định dạng.")
        dinh_nghia = DINH_NGHIA_TIEU_CHI.get(tieu_chi.khoa)
        if dinh_nghia is None:
            raise LoiTruyVanKhongHopLe(f"Tiêu chí không hợp lệ: '{tieu_chi.khoa}'.")
        if tieu_chi.khoa == "brake_system":
            raise LoiTruyVanKhongHopLe(
                "CSV hiện tại không có dữ liệu hệ thống phanh, nên không thể xếp hạng "
                "theo tiêu chí này."
            )
        if tieu_chi.khoa in da_gap:
            raise LoiTruyVanKhongHopLe(
                f"Tiêu chí '{dinh_nghia.nhan}' bị lặp trong truy vấn."
            )
        da_gap.add(tieu_chi.khoa)

        trong_so = _so_tuy_chon(tieu_chi.trong_so)
        if trong_so is None or trong_so <= 0:
            continue

        gia_tri: float | str | None = tieu_chi.gia_tri
        che_do = tieu_chi.che_do
        if dinh_nghia.loai == "categorical":
            gia_tri = _chuan_hoa_danh_muc(tieu_chi.khoa, gia_tri)
            if gia_tri is None:
                continue
        else:
            if tieu_chi.khoa == "price":
                che_do = che_do or GIA_THAP
                if che_do not in {GIA_THAP, GIA_MUC_TIEU}:
                    raise LoiTruyVanKhongHopLe(
                        "Cách ưu tiên giá phải là 'low' hoặc 'target'."
                    )
                if che_do == GIA_MUC_TIEU:
                    so_gia_tri = _so_tuy_chon(gia_tri)
                    if so_gia_tri is None:
                        continue
                    gia_tri = so_gia_tri
                else:
                    gia_tri = None
            else:
                so_gia_tri = _so_tuy_chon(gia_tri)
                if so_gia_tri is None:
                    continue
                gia_tri = so_gia_tri

        cac_trong_so[dinh_nghia.khoa] = trong_so
        da_chuan_bi.append((dinh_nghia.khoa, trong_so, gia_tri, che_do))

    chuan_hoa = chuan_hoa_ban_do_trong_so(cac_trong_so)
    if not chuan_hoa:
        raise LoiThieuTieuChi(
            "Cần chọn ít nhất một tiêu chí ưu tiên và cung cấp giá trị tương ứng."
        )

    dang_dung = [
        TieuChiHoatDong(
            khoa=khoa,
            nhan=DINH_NGHIA_TIEU_CHI[khoa].nhan,
            loai=DINH_NGHIA_TIEU_CHI[khoa].loai,
            trong_so=trong_so,
            trong_so_chuan_hoa=chuan_hoa[khoa],
            gia_tri=gia_tri,
            che_do=che_do,
        )
        for khoa, trong_so, gia_tri, che_do in da_chuan_bi
    ]
    return dang_dung, chuan_hoa


def _mat_na_loc_cung(
    danh_muc: DanhMucXe,
    truy_van: TruyVanGoiY,
) -> tuple[pd.Series, dict[str, int]]:
    bang = danh_muc.bang
    mat_na = pd.Series(True, index=bang.index)
    thong_ke = {"max_price_vnd": 0, "required_fuel": 0, "required_condition": 0}

    if truy_van.gia_toi_da_vnd is not None:
        truoc = int(mat_na.sum())
        mat_na &= bang["price_vnd"].notna() & (bang["price_vnd"] <= truy_van.gia_toi_da_vnd)
        thong_ke["max_price_vnd"] = truoc - int(mat_na.sum())

    if truy_van.dieu_kien_nhien_lieu:
        dieu_kien_nhien_lieu = chuan_hoa_nhien_lieu(truy_van.dieu_kien_nhien_lieu)
        if dieu_kien_nhien_lieu is None:
            raise LoiTruyVanKhongHopLe("Nhiên liệu bắt buộc không hợp lệ.")
        truoc = int(mat_na.sum())
        mat_na &= bang["fuel_type"].notna()
        mat_na &= bang["fuel_type"].map(chuan_hoa_nhien_lieu).eq(dieu_kien_nhien_lieu)
        thong_ke["required_fuel"] = truoc - int(mat_na.sum())

    if truy_van.dieu_kien_tinh_trang:
        dieu_kien_tinh_trang = chuan_hoa_tinh_trang(truy_van.dieu_kien_tinh_trang)
        if dieu_kien_tinh_trang is None:
            raise LoiTruyVanKhongHopLe("Tình trạng bắt buộc không hợp lệ.")
        truoc = int(mat_na.sum())
        mat_na &= bang["condition"].notna()
        mat_na &= bang["condition"].map(chuan_hoa_tinh_trang).eq(dieu_kien_tinh_trang)
        thong_ke["required_condition"] = truoc - int(mat_na.sum())

    return mat_na, thong_ke


def _bo_chuan_hoa_so(danh_muc: DanhMucXe, cot: str, nhan: str) -> ChuanHoaSo:
    if cot not in danh_muc.bang.columns:
        raise LoiTruyVanKhongHopLe(
            f"Catalog không có cột dữ liệu cho tiêu chí '{nhan}'."
        )
    try:
        return ChuanHoaSo.tu_chuoi(danh_muc.bang[cot])
    except ValueError as loi:
        raise LoiTruyVanKhongHopLe(
            f"Tiêu chí '{nhan}' không có dữ liệu số hợp lệ để chuẩn hóa."
        ) from loi


def _khoang_cach_tieu_chi(
    danh_muc: DanhMucXe,
    ung_vien: pd.DataFrame,
    tieu_chi: TieuChiHoatDong,
) -> np.ndarray:
    dinh_nghia = DINH_NGHIA_TIEU_CHI[tieu_chi.khoa]
    cot = dinh_nghia.cot
    if cot not in ung_vien.columns:
        raise LoiTruyVanKhongHopLe(f"Catalog thiếu cột '{cot}'.")

    if tieu_chi.loai == "categorical":
        mong_doi = _chuan_hoa_danh_muc(tieu_chi.khoa, tieu_chi.gia_tri)
        cac_gia_tri = ung_vien[cot].tolist()
        cac_khoang_cach = []
        for gia_tri in cac_gia_tri:
            thuc_te = _chuan_hoa_danh_muc(tieu_chi.khoa, gia_tri)
            if thuc_te is None:
                cac_khoang_cach.append(KHOANG_CACH_KHI_THIEU)
            elif mong_doi is not None and chuan_hoa_khoa(thuc_te) == chuan_hoa_khoa(mong_doi):
                cac_khoang_cach.append(0.0)
            else:
                cac_khoang_cach.append(1.0)
        return np.asarray(cac_khoang_cach, dtype=float)

    bo_chuan_hoa = _bo_chuan_hoa_so(danh_muc, cot, dinh_nghia.nhan)
    cac_gia_tri = ung_vien[cot].tolist()

    if dinh_nghia.khoa == "price" and tieu_chi.che_do == GIA_THAP:
        cac_khoang_cach = []
        for gia_tri in cac_gia_tri:
            da_chuan_hoa = bo_chuan_hoa.chuan_hoa(gia_tri)
            cac_khoang_cach.append(
                KHOANG_CACH_KHI_THIEU if np.isnan(da_chuan_hoa) else da_chuan_hoa
            )
        return np.asarray(cac_khoang_cach, dtype=float)

    if tieu_chi.loai == "numeric_min":
        return np.asarray(
            [
                bo_chuan_hoa.khoang_cach_toi_thieu(gia_tri, float(tieu_chi.gia_tri))
                for gia_tri in cac_gia_tri
            ],
            dtype=float,
        )

    return np.asarray(
        [
            bo_chuan_hoa.khoang_cach_doi_xung(gia_tri, float(tieu_chi.gia_tri))
            for gia_tri in cac_gia_tri
        ],
        dtype=float,
    )


def _gia_tri_python(gia_tri: Any) -> Any:
    if gia_tri is None:
        return None
    if isinstance(gia_tri, float) and math.isnan(gia_tri):
        return None
    if isinstance(gia_tri, (np.integer,)):
        return int(gia_tri)
    if isinstance(gia_tri, (np.floating,)):
        if math.isnan(float(gia_tri)):
            return None
        return float(gia_tri)
    if pd.isna(gia_tri):
        return None
    return gia_tri


def _tu_dien_xe(dong: pd.Series) -> dict[str, Any]:
    return {cot: _gia_tri_python(dong[cot]) for cot in COT_NOI_BO}


def xep_hang_xe(danh_muc: DanhMucXe, truy_van: TruyVanGoiY) -> KetQuaXepHang:
    """Lọc trước theo ràng buộc cứng, sau đó xếp hạng tăng dần theo khoảng cách Euclid có trọng số.

    Công thức khoảng cách:
        D(x, u) = sqrt( sum_{j in A(u)} w_j * d_j(x, u)^2 / sum_{j in A(u)} w_j )

    Quy tắc chuẩn hóa và khoảng cách:
    - Mỗi thuộc tính số được chuẩn hóa độc lập Min-Max về [0, 1] qua min/max của catalog
      và clip truy vấn; tuyệt đối không áp dụng chuẩn hóa L2 trên vector đặc trưng.
    - Thuộc tính phân loại: khoảng cách d_j in {0.0, 1.0}.
    - Xe thiếu dữ liệu ở tiêu chí mềm đang hoạt động: d_j = 0.5 (MISSING_DISTANCE).
    - Cốp tối thiểu và năm tối thiểu dùng khoảng cách bất đối xứng (phạt khi thiếu hụt).
    - Miền hằng số (max = min) được xử lý an toàn không chia cho 0.
    """

    dang_dung, chuan_hoa = _chuan_bi_tieu_chi(truy_van)
    mat_na, dem_loc_cung = _mat_na_loc_cung(danh_muc, truy_van)
    ung_vien = danh_muc.bang.loc[mat_na].copy()
    tong_danh_muc = len(danh_muc.bang)
    so_xe_sau_loc = len(ung_vien)

    ket_qua_goc = {
        "tieu_chi_dang_dung": tuple(dang_dung),
        "trong_so_chuan_hoa": chuan_hoa,
        "tong_danh_muc": tong_danh_muc,
        "so_xe_sau_loc": so_xe_sau_loc,
        "so_xe_bi_loai": tong_danh_muc - so_xe_sau_loc,
        "dem_loc_cung": dem_loc_cung,
        "truy_van": truy_van,
    }

    if ung_vien.empty:
        return KetQuaXepHang(cac_muc=tuple(), **ket_qua_goc)

    co_trong_so_sum = np.zeros(len(ung_vien), dtype=float)
    trong_so_sum = 0.0
    khoang_cach_tieu_chi: dict[str, np.ndarray] = {}
    for tieu_chi in dang_dung:
        khoang_cach = _khoang_cach_tieu_chi(danh_muc, ung_vien, tieu_chi)
        khoang_cach_tieu_chi[tieu_chi.khoa] = khoang_cach
        co_trong_so_sum += tieu_chi.trong_so * np.square(khoang_cach)
        trong_so_sum += tieu_chi.trong_so

    if not math.isfinite(trong_so_sum) or trong_so_sum <= 0:
        raise LoiThieuTieuChi(
            "Cần chọn ít nhất một tiêu chí ưu tiên có trọng số hợp lệ."
        )

    cac_khoang_cach = np.sqrt(co_trong_so_sum / trong_so_sum)
    ung_vien = ung_vien.assign(distance=cac_khoang_cach)
    for khoa, cac_gia_tri in khoang_cach_tieu_chi.items():
        ung_vien[f"distance_{khoa}"] = cac_gia_tri
    ung_vien = ung_vien.sort_values(
        ["distance", "source_row"],
        kind="stable",
    )
    ung_vien = ung_vien.head(truy_van.k)

    cac_muc: list[XeDuocCham] = []
    for thu_hang, (_, dong) in enumerate(ung_vien.iterrows(), start=1):
        truong_thieu = tuple(
            cot for cot in COT_DU_LIEU if _gia_tri_python(dong[cot]) is None
        )
        cac_muc.append(
            XeDuocCham(
                thu_hang=thu_hang,
                xe=_tu_dien_xe(dong),
                khoang_cach=float(dong["distance"]),
                do_tuong_tu=float(1.0 / (1.0 + float(dong["distance"]))),
                khoang_cach_tieu_chi={
                    khoa: float(dong[f"distance_{khoa}"])
                    for khoa in khoang_cach_tieu_chi
                },
                truong_thieu=truong_thieu,
            )
        )

    return KetQuaXepHang(cac_muc=tuple(cac_muc), **ket_qua_goc)
