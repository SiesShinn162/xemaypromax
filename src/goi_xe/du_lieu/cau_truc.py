"""Hợp đồng cột CSV và ánh xạ tiêu đề linh hoạt."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .phan_tich import chuan_hoa_tieu_de

COT_BAT_BUOC = (
    "brand",
    "model",
    "price_vnd",
    "max_power_kw",
    "fuel_type",
    "vehicle_type",
)

COT_TUY_CHON = (
    "boot_capacity_l",
    "condition",
    "year",
)

NHAN_COT = {
    "brand": "Hãng",
    "model": "Model",
    "price_vnd": "Giá (VND)",
    "max_power_kw": "Công suất tối đa (kW)",
    "fuel_type": "Nhiên liệu",
    "vehicle_type": "Kiểu xe",
    "boot_capacity_l": "Dung tích cốp (lít)",
    "condition": "Tình trạng",
    "year": "Năm sản xuất",
}

BIET_DANH_COT: dict[str, tuple[str, ...]] = {
    "brand": (
        "hang",
        "hang xe",
        "brand",
        "thuong hieu",
        "nhan hieu",
    ),
    "model": (
        "model",
        "model name",
        "ten xe",
        "mau xe",
        "dong xe",
    ),
    "price_vnd": (
        "gia",
        "gia vnd",
        "gia ban",
        "gia ban vnd",
        "gia niem yet",
        "price",
        "price vnd",
    ),
    "max_power_kw": (
        "cong suat",
        "cong suat toi da",
        "cong suat toi da kw",
        "cong suat toi da w",
        "cong suat kw",
        "cong suat w",
        "cong suat dong co",
        "cong suat dong co kw",
        "cong suat dong co w",
        "max power",
        "max power kw",
        "max power w",
        "max_power_kw",
    ),
    "fuel_type": (
        "nhien lieu",
        "loai nhien lieu",
        "nhien lieu su dung",
        "fuel",
        "fuel type",
        "fuel_type",
    ),
    "vehicle_type": (
        "kieu xe",
        "loai xe",
        "kieu dang",
        "vehicle type",
        "vehicle_type",
    ),
    "boot_capacity_l": (
        "dung tich cop",
        "dung tich cop lit",
        "dung tich cop l",
        "the tich cop",
        "cop",
        "boot",
        "boot capacity",
        "boot capacity l",
        "boot_capacity_l",
    ),
    "condition": (
        "tinh trang",
        "tinh trang xe",
        "trang thai",
        "condition",
    ),
    "year": (
        "nam san xuat",
        "nam sx",
        "nam",
        "doi xe",
        "model year",
        "year",
    ),
}

_BIET_DANH_SANG_COT = {
    chuan_hoa_tieu_de(biet_danh): noi_bo
    for noi_bo, cac_biet_danh in BIET_DANH_COT.items()
    for biet_danh in cac_biet_danh
}


class LoiCauTrucCsv(ValueError):
    """Lỗi cấu trúc CSV với thông báo dành cho người dùng."""


@dataclass(frozen=True)
class CauTrucCsv:
    bang_cot: dict[str, str]
    tieu_de_goc: tuple[str, ...]
    don_vi_cong_suat_nguon: str

    @property
    def cot_tuy_chon_hien_co(self) -> tuple[str, ...]:
        return tuple(
            cot
            for cot in COT_TUY_CHON
            if cot in self.bang_cot
        )

    def tieu_de_nguon(self, noi_bo_cot: str) -> str | None:
        return self.bang_cot.get(noi_bo_cot)


def _don_vi_cong_suat_tu_tieu_de(tieu_de: str) -> str:
    khoa = chuan_hoa_tieu_de(tieu_de)
    cac_tu = khoa.split()
    if "kw" in cac_tu:
        return "kW"
    if "w" in cac_tu:
        return "W"
    return "kW"


def giai_tieu_de_cot(cac_tieu_de: Iterable[str]) -> CauTrucCsv:
    tieu_de_goc = tuple(str(tieu_de) for tieu_de in cac_tieu_de if str(tieu_de).strip())
    bang_cot: dict[str, str] = {}

    for tieu_de in tieu_de_goc:
        khoa = chuan_hoa_tieu_de(tieu_de)
        noi_bo = _BIET_DANH_SANG_COT.get(khoa)
        if noi_bo is None:
            continue
        if noi_bo in bang_cot:
            raise LoiCauTrucCsv(
                "CSV có nhiều cột cùng ánh xạ tới "
                f"'{NHAN_COT[noi_bo]}': "
                f"'{bang_cot[noi_bo]}' và '{tieu_de}'. "
                "Hãy giữ lại một cột duy nhất."
            )
        bang_cot[noi_bo] = tieu_de

    thieu = [
        NHAN_COT[cot]
        for cot in COT_BAT_BUOC
        if cot not in bang_cot
    ]
    if thieu:
        hien_tai = ", ".join(f"'{tieu_de}'" for tieu_de in tieu_de_goc) or "(trống)"
        raise LoiCauTrucCsv(
            "CSV thiếu cột bắt buộc: "
            + ", ".join(thieu)
            + ". Các cột hiện có: "
            + hien_tai
            + "."
        )

    cong_suat_tieu_de = bang_cot["max_power_kw"]
    return CauTrucCsv(
        bang_cot=bang_cot,
        tieu_de_goc=tieu_de_goc,
        don_vi_cong_suat_nguon=_don_vi_cong_suat_tu_tieu_de(cong_suat_tieu_de),
    )
