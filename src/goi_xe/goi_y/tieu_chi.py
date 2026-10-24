"""Định nghĩa tiêu chí mềm, trọng số baseline và truy vấn xếp hạng."""

from __future__ import annotations

import math
import statistics
from collections import Counter
from dataclasses import dataclass
from typing import Literal

from ..du_lieu.nap_du_lieu import DanhMucXe

LoaiTieuChi = Literal["numeric", "numeric_min", "categorical"]


class LoiTruyVanKhongHopLe(ValueError):
    """Truy vấn không hợp lệ với thông báo tiếng Việt."""


class LoiThieuTieuChi(LoiTruyVanKhongHopLe):
    """Không có tiêu chí mềm nào đang hoạt động."""


@dataclass(frozen=True)
class DinhNghiaTieuChi:
    khoa: str
    nhan: str
    cot: str
    trong_so: float
    loai: LoaiTieuChi
    mo_ta: str


DINH_NGHIA_TIEU_CHI: dict[str, DinhNghiaTieuChi] = {
    "price": DinhNghiaTieuChi(
        khoa="price",
        nhan="Giá",
        cot="price_vnd",
        trong_so=0.30,
        loai="numeric",
        mo_ta=(
            "Chọn giá thấp để ưu tiên xe rẻ hơn, hoặc nhập giá mục tiêu để tìm xe "
            "gần mức giá mong muốn."
        ),
    ),
    "vehicle_type": DinhNghiaTieuChi(
        khoa="vehicle_type",
        nhan="Kiểu xe",
        cot="vehicle_type",
        trong_so=0.20,
        loai="categorical",
        mo_ta="Xe tay ga, xe số, xe côn tay, xe điện hoặc phân khối lớn.",
    ),
    "fuel_type": DinhNghiaTieuChi(
        khoa="fuel_type",
        nhan="Nhiên liệu",
        cot="fuel_type",
        trong_so=0.15,
        loai="categorical",
        mo_ta="Ưu tiên xe xăng hoặc xe điện; có thể dùng làm điều kiện bắt buộc.",
    ),
    "max_power_kw": DinhNghiaTieuChi(
        khoa="max_power_kw",
        nhan="Công suất tối đa",
        cot="max_power_kw",
        trong_so=0.12,
        loai="numeric",
        mo_ta="Một trường kW chung cho cả xe xăng và xe điện.",
    ),
    "boot_capacity_l": DinhNghiaTieuChi(
        khoa="boot_capacity_l",
        nhan="Dung tích cốp",
        cot="boot_capacity_l",
        trong_so=0.08,
        loai="numeric_min",
        mo_ta=(
            "Nhập mức cốp tối thiểu; xe đạt hoặc vượt mức nhận khoảng cách 0, "
            "xe thiếu bị phạt theo độ hụt."
        ),
    ),
    "condition": DinhNghiaTieuChi(
        khoa="condition",
        nhan="Tình trạng",
        cot="condition",
        trong_so=0.06,
        loai="categorical",
        mo_ta="Ưu tiên xe mới hoặc xe cũ theo dữ liệu CSV.",
    ),
    "year": DinhNghiaTieuChi(
        khoa="year",
        nhan="Năm sản xuất",
        cot="year",
        trong_so=0.04,
        loai="numeric_min",
        mo_ta="Nhập năm sản xuất tối thiểu; xe cũ hơn bị phạt theo độ lệch năm.",
    ),
    "brake_system": DinhNghiaTieuChi(
        khoa="brake_system",
        nhan="Hệ thống phanh",
        cot="brake_system",
        trong_so=0.03,
        loai="categorical",
        mo_ta="Chưa có trong CSV hiện tại nên không đưa vào xếp hạng.",
    ),
    "brand": DinhNghiaTieuChi(
        khoa="brand",
        nhan="Hãng",
        cot="brand",
        trong_so=0.02,
        loai="categorical",
        mo_ta="Ưu tiên thương hiệu nếu người dùng có sở thích cụ thể.",
    ),
}

TRONG_SO_CO_SO = {
    khoa: dinh_nghia.trong_so
    for khoa, dinh_nghia in DINH_NGHIA_TIEU_CHI.items()
}

GIA_THAP = "low"
GIA_MUC_TIEU = "target"


@dataclass(frozen=True)
class TieuChiMem:
    khoa: str
    trong_so: float
    gia_tri: float | str | None = None
    che_do: str | None = None


@dataclass(frozen=True)
class TruyVanGoiY:
    tieu_chi: tuple[TieuChiMem, ...]
    gia_toi_da_vnd: float | None = None
    dieu_kien_nhien_lieu: str | None = None
    dieu_kien_tinh_trang: str | None = None
    k: int = 5

    def __post_init__(self) -> None:
        if isinstance(self.k, bool) or not isinstance(self.k, int) or self.k < 1:
            raise LoiTruyVanKhongHopLe(
                "Số lượng kết quả K phải là số nguyên lớn hơn hoặc bằng 1."
            )
        if self.gia_toi_da_vnd is not None:
            if isinstance(self.gia_toi_da_vnd, bool) or not isinstance(
                self.gia_toi_da_vnd, (int, float)
            ):
                raise LoiTruyVanKhongHopLe("Ngân sách tối đa phải là số.")
            try:
                toi_da_gia_gia_tri = float(self.gia_toi_da_vnd)
            except (OverflowError, TypeError, ValueError) as loi:
                raise LoiTruyVanKhongHopLe("Ngân sách tối đa không hợp lệ.") from loi
            if not math.isfinite(toi_da_gia_gia_tri) or toi_da_gia_gia_tri < 0:
                raise LoiTruyVanKhongHopLe(
                    "Ngân sách tối đa phải là số hữu hạn không âm."
                )


def khoa_tieu_chi_kha_dung(danh_muc: DanhMucXe) -> list[str]:
    cac_khoa: list[str] = []
    for khoa, dinh_nghia in DINH_NGHIA_TIEU_CHI.items():
        if khoa == "brake_system":
            continue
        if danh_muc.co_cot(dinh_nghia.cot):
            cac_khoa.append(khoa)
    return cac_khoa


def chuan_hoa_ban_do_trong_so(cac_trong_so: dict[str, float]) -> dict[str, float]:
    tong = sum(trong_so for trong_so in cac_trong_so.values() if trong_so > 0)
    if tong <= 0:
        return {}
    return {
        khoa: trong_so / tong
        for khoa, trong_so in cac_trong_so.items()
        if trong_so > 0
    }


def tao_tieu_chi_can_bang(danh_muc: DanhMucXe) -> tuple[TieuChiMem, ...]:
    """Tạo hồ sơ Cân bằng (mặc định) với trọng số chuẩn hóa bằng nhau cho mọi tiêu chí hỗ trợ."""

    cac_khoa = khoa_tieu_chi_kha_dung(danh_muc)
    if not cac_khoa:
        return ()

    bang_trong_so = 1.0 / len(cac_khoa)
    tieu_chi: list[TieuChiMem] = []
    for khoa in cac_khoa:
        dinh_nghia = DINH_NGHIA_TIEU_CHI[khoa]
        cot = dinh_nghia.cot
        if khoa == "price":
            cac_gia_tri = [
                float(gia_tri)
                for gia_tri in danh_muc.bang[cot].dropna().tolist()
                if math.isfinite(float(gia_tri))
            ]
            trung_vi = float(statistics.median(cac_gia_tri)) if cac_gia_tri else 0.0
            tieu_chi.append(
                TieuChiMem(
                    khoa=khoa,
                    trong_so=bang_trong_so,
                    gia_tri=trung_vi,
                    che_do=GIA_MUC_TIEU,
                )
            )
        elif dinh_nghia.loai == "numeric":
            cac_gia_tri = [
                float(gia_tri)
                for gia_tri in danh_muc.bang[cot].dropna().tolist()
                if math.isfinite(float(gia_tri))
            ]
            trung_vi = float(statistics.median(cac_gia_tri)) if cac_gia_tri else 0.0
            tieu_chi.append(
                TieuChiMem(
                    khoa=khoa,
                    trong_so=bang_trong_so,
                    gia_tri=trung_vi,
                )
            )
        elif dinh_nghia.loai == "numeric_min":
            cac_gia_tri = [
                float(gia_tri)
                for gia_tri in danh_muc.bang[cot].dropna().tolist()
                if math.isfinite(float(gia_tri))
            ]
            trung_vi = float(statistics.median(cac_gia_tri)) if cac_gia_tri else 0.0
            if khoa == "year":
                trung_vi = int(round(trung_vi))
            tieu_chi.append(
                TieuChiMem(
                    khoa=khoa,
                    trong_so=bang_trong_so,
                    gia_tri=trung_vi,
                )
            )
        else:  # categorical
            cac_gia_tri = [
                str(gia_tri).strip()
                for gia_tri in danh_muc.bang[cot].dropna().tolist()
                if str(gia_tri).strip()
            ]
            gia_tri_che_do = Counter(cac_gia_tri).most_common(1)[0][0] if cac_gia_tri else ""
            tieu_chi.append(
                TieuChiMem(
                    khoa=khoa,
                    trong_so=bang_trong_so,
                    gia_tri=gia_tri_che_do,
                )
            )
    return tuple(tieu_chi)
