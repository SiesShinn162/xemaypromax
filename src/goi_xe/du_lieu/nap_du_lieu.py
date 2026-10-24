"""Nạp CSV xe, chuẩn hóa dữ liệu và ghi nhận chất lượng dữ liệu."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from .cau_truc import (
    COT_TUY_CHON,
    NHAN_COT,
    CauTrucCsv,
    giai_tieu_de_cot,
)
from .phan_tich import (
    chuan_hoa_loai_xe,
    chuan_hoa_nhien_lieu,
    chuan_hoa_tinh_trang,
    doc_cong_suat_kw,
    doc_dung_tich_cop_l,
    doc_gia_vnd,
    doc_nam_sx,
    lam_sach_chu,
)

COT_NOI_BO = (
    "vehicle_id",
    "brand",
    "model",
    "price_vnd",
    "max_power_kw",
    "fuel_type",
    "vehicle_type",
    "boot_capacity_l",
    "condition",
    "year",
    "source_row",
)

COT_DU_LIEU = (
    "brand",
    "model",
    "price_vnd",
    "max_power_kw",
    "fuel_type",
    "vehicle_type",
    "boot_capacity_l",
    "condition",
    "year",
)

COT_DEM_LOI = ("price_vnd", "max_power_kw", "boot_capacity_l", "year")


class LoiDuLieuCsv(ValueError):
    """Lỗi dữ liệu CSV với thông báo tiếng Việt."""


@dataclass(frozen=True)
class BaoCaoChatLuongDuLieu:
    so_dong_nguon: int
    so_dong_trong: int
    so_dong_tieu_de: int
    so_dong_thieu_model: int
    so_dong_trung: int
    so_dong_bo_sung_hang: int
    so_dong_hop_le: int
    dem_gia_tri_thieu: dict[str, int]
    dem_gia_tri_loi: dict[str, int]
    don_vi_cong_suat_nguon: str
    ghi_chu: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class DanhMucXe:
    bang: pd.DataFrame
    cau_truc: CauTrucCsv
    chat_luong: BaoCaoChatLuongDuLieu
    duong_dan_nguon: Path

    def __len__(self) -> int:
        return len(self.bang)

    def co_cot(self, cot: str) -> bool:
        return cot in self.bang.columns and self.bang[cot].notna().any()

    def gia_tri_danh_muc(self, cot: str) -> list[str]:
        if cot not in self.bang.columns:
            return []
        cac_gia_tri = {
            str(gia_tri).strip()
            for gia_tri in self.bang[cot].dropna().tolist()
            if str(gia_tri).strip()
        }
        return sorted(cac_gia_tri, key=lambda gia_tri: gia_tri.casefold())


def _nhan_dien_dau_phan_cach(duong_dan: Path) -> str:
    mau = duong_dan.read_text(encoding="utf-8-sig", errors="replace")[:65536]
    try:
        dinh_dang = csv.Sniffer().sniff(mau, delimiters=",;\t")
        return dinh_dang.delimiter
    except csv.Error:
        return ","


def _doc_csv_tho(duong_dan: Path) -> pd.DataFrame:
    if not duong_dan.exists():
        raise LoiDuLieuCsv(f"Không tìm thấy tệp CSV: {duong_dan}.")
    if not duong_dan.is_file():
        raise LoiDuLieuCsv(f"Đường dẫn CSV không phải tệp: {duong_dan}.")
    try:
        return pd.read_csv(
            duong_dan,
            sep=_nhan_dien_dau_phan_cach(duong_dan),
            dtype=str,
            keep_default_na=False,
            na_filter=False,
            skip_blank_lines=False,
            encoding="utf-8-sig",
        )
    except UnicodeDecodeError as loi:
        raise LoiDuLieuCsv(
            "Không đọc được CSV bằng UTF-8. Hãy lưu tệp với bảng mã UTF-8."
        ) from loi
    except pd.errors.EmptyDataError as loi:
        raise LoiDuLieuCsv("Tệp CSV đang trống hoặc không có dòng tiêu đề.") from loi
    except pd.errors.ParserError as loi:
        raise LoiDuLieuCsv(
            "Không phân tích được CSV. Kiểm tra dấu phân cách và số cột trên mỗi dòng."
        ) from loi


def _gia_tri_tho(dong: pd.Series, tieu_de: str | None) -> str | None:
    if tieu_de is None:
        return None
    return lam_sach_chu(dong.get(tieu_de))


def _gia_tri_truong(cau_truc: CauTrucCsv, dong: pd.Series, noi_bo: str) -> str | None:
    return _gia_tri_tho(dong, cau_truc.bang_cot.get(noi_bo))


def nap_danh_muc(duong_dan: str | Path) -> DanhMucXe:
    """Nạp CSV ở chế độ chỉ đọc và trả catalog đã chuẩn hóa."""

    duong_dan_nguon = Path(duong_dan).expanduser().resolve()
    tho = _doc_csv_tho(duong_dan_nguon)
    tho = tho.loc[
        :,
        [cot for cot in tho.columns if not str(cot).startswith("Unnamed:")],
    ]
    cau_truc = giai_tieu_de_cot(tho.columns)

    cac_dong: list[dict[str, Any]] = []
    so_dong_trong = 0
    so_dong_tieu_de = 0
    so_dong_thieu_model = 0
    so_dong_bo_sung_hang = 0
    dem_gia_tri_loi = {cot: 0 for cot in COT_DEM_LOI}
    hang_hien_tai: str | None = None
    tieu_de_hang = cau_truc.bang_cot["brand"]
    khac_cac_tieu_de = [cot for cot in tho.columns if cot != tieu_de_hang]

    for chi_so, dong in tho.iterrows():
        source_row = int(chi_so) + 2
        hang_tho = _gia_tri_tho(dong, tieu_de_hang)
        if hang_tho:
            hang_hien_tai = hang_tho

        tat_ca_cac_gia_tri = [lam_sach_chu(dong.get(cot)) for cot in tho.columns]
        if not any(tat_ca_cac_gia_tri):
            so_dong_trong += 1
            continue

        khac_cac_gia_tri = [lam_sach_chu(dong.get(cot)) for cot in khac_cac_tieu_de]
        if hang_tho and not any(khac_cac_gia_tri):
            so_dong_tieu_de += 1
            continue

        model = _gia_tri_truong(cau_truc, dong, "model")
        if model is None:
            so_dong_thieu_model += 1
            continue

        brand = hang_tho or hang_hien_tai
        if not hang_tho and brand:
            so_dong_bo_sung_hang += 1

        gia_tho = _gia_tri_truong(cau_truc, dong, "price_vnd")
        gia = doc_gia_vnd(gia_tho)
        if gia_tho is not None and gia is None:
            dem_gia_tri_loi["price_vnd"] += 1

        cong_suat_tho = _gia_tri_truong(cau_truc, dong, "max_power_kw")
        cong_suat = doc_cong_suat_kw(cong_suat_tho, nguon_don_vi=cau_truc.don_vi_cong_suat_nguon)
        if cong_suat_tho is not None and cong_suat is None:
            dem_gia_tri_loi["max_power_kw"] += 1

        cop_tho = _gia_tri_truong(cau_truc, dong, "boot_capacity_l")
        cop = doc_dung_tich_cop_l(cop_tho)
        if cop_tho is not None and cop is None:
            dem_gia_tri_loi["boot_capacity_l"] += 1

        nam_tho = _gia_tri_truong(cau_truc, dong, "year")
        year = doc_nam_sx(nam_tho)
        if nam_tho is not None and year is None:
            dem_gia_tri_loi["year"] += 1

        cac_dong.append(
            {
                "vehicle_id": f"vehicle-{source_row:04d}",
                "brand": brand,
                "model": model,
                "price_vnd": gia,
                "max_power_kw": cong_suat,
                "fuel_type": chuan_hoa_nhien_lieu(_gia_tri_truong(cau_truc, dong, "fuel_type")),
                "vehicle_type": chuan_hoa_loai_xe(
                    _gia_tri_truong(cau_truc, dong, "vehicle_type")
                ),
                "boot_capacity_l": cop,
                "condition": chuan_hoa_tinh_trang(_gia_tri_truong(cau_truc, dong, "condition")),
                "year": year,
                "source_row": source_row,
            }
        )

    if not cac_dong:
        raise LoiDuLieuCsv(
            "CSV không có dòng xe hợp lệ. Cần ít nhất một dòng có giá trị ở cột Model."
        )

    bang = pd.DataFrame(cac_dong, columns=list(COT_NOI_BO))
    for cot in ("price_vnd", "max_power_kw", "boot_capacity_l", "year"):
        bang[cot] = pd.to_numeric(bang[cot], errors="coerce")

    mat_na_trung = bang.duplicated(subset=list(COT_DU_LIEU), keep="first")
    so_dong_trung = int(mat_na_trung.sum())
    if so_dong_trung:
        bang = bang.loc[~mat_na_trung].copy()
    bang = bang.reset_index(drop=True)

    dem_gia_tri_thieu = {
        cot: int(bang[cot].isna().sum()) for cot in COT_DU_LIEU
    }

    ghi_chu: list[str] = [
        "Tệp CSV được mở ở chế độ chỉ đọc; ứng dụng không ghi đè dữ liệu nguồn.",
    ]
    if cau_truc.don_vi_cong_suat_nguon == "W":
        ghi_chu.append(
            "Cột công suất nguồn ghi W nên đã được đổi sang kW (chia 1.000) "
            "trước khi đưa vào catalog."
        )
    if so_dong_bo_sung_hang:
        ghi_chu.append(
            f"{so_dong_bo_sung_hang} dòng để trống cột Hãng đã được điền theo khối "
            "tiêu đề gần nhất."
        )
    if so_dong_trung:
        ghi_chu.append(f"Đã bỏ {so_dong_trung} dòng trùng hoàn toàn sau khi chuẩn hóa.")
    ghi_chu.append(
        "CSV hiện tại không có cột hệ thống phanh, nên phanh không phải tiêu chí xếp hạng."
    )
    thieu_tuy_chon = [
        NHAN_COT[cot]
        for cot in COT_TUY_CHON
        if cot not in cau_truc.bang_cot
    ]
    if thieu_tuy_chon:
        ghi_chu.append("Thiếu cột tùy chọn: " + ", ".join(thieu_tuy_chon) + ".")

    chat_luong = BaoCaoChatLuongDuLieu(
        so_dong_nguon=len(tho),
        so_dong_trong=so_dong_trong,
        so_dong_tieu_de=so_dong_tieu_de,
        so_dong_thieu_model=so_dong_thieu_model,
        so_dong_trung=so_dong_trung,
        so_dong_bo_sung_hang=so_dong_bo_sung_hang,
        so_dong_hop_le=len(bang),
        dem_gia_tri_thieu=dem_gia_tri_thieu,
        dem_gia_tri_loi=dem_gia_tri_loi,
        don_vi_cong_suat_nguon=cau_truc.don_vi_cong_suat_nguon,
        ghi_chu=tuple(ghi_chu),
    )
    return DanhMucXe(
        bang=bang,
        cau_truc=cau_truc,
        chat_luong=chat_luong,
        duong_dan_nguon=duong_dan_nguon,
    )
