from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from goi_xe.du_lieu.cau_truc import CauTrucCsv
from goi_xe.du_lieu.nap_du_lieu import (
    COT_DU_LIEU,
    COT_NOI_BO,
    BaoCaoChatLuongDuLieu,
    DanhMucXe,
)


def tao_danh_muc(cac_ban_ghi: list[dict[str, Any]]) -> DanhMucXe:
    mac_dinh: dict[str, Any] = {
        "brand": "Hãng thử",
        "model": "Mẫu thử",
        "price_vnd": 50_000_000.0,
        "max_power_kw": 10.0,
        "fuel_type": "Xăng",
        "vehicle_type": "Xe số",
        "boot_capacity_l": 20.0,
        "condition": "Mới",
        "year": 2022.0,
    }
    cac_dong: list[dict[str, Any]] = []
    for chi_so, ban_ghi in enumerate(cac_ban_ghi, start=1):
        dong = dict(mac_dinh)
        dong.update(ban_ghi)
        dong.setdefault("vehicle_id", f"vehicle-test-{chi_so:04d}")
        dong.setdefault("source_row", chi_so + 1)
        cac_dong.append(dong)

    bang = pd.DataFrame(cac_dong, columns=list(COT_NOI_BO))
    for cot in ("price_vnd", "max_power_kw", "boot_capacity_l", "year"):
        bang[cot] = pd.to_numeric(bang[cot], errors="coerce")

    chat_luong = BaoCaoChatLuongDuLieu(
        so_dong_nguon=len(bang),
        so_dong_trong=0,
        so_dong_tieu_de=0,
        so_dong_thieu_model=0,
        so_dong_trung=0,
        so_dong_bo_sung_hang=0,
        so_dong_hop_le=len(bang),
        dem_gia_tri_thieu={
            cot: int(bang[cot].isna().sum()) for cot in COT_DU_LIEU
        },
        dem_gia_tri_loi={
            "price_vnd": 0,
            "max_power_kw": 0,
            "boot_capacity_l": 0,
            "year": 0,
        },
        don_vi_cong_suat_nguon="kW",
        ghi_chu=(),
    )
    cau_truc = CauTrucCsv(
        bang_cot={cot: cot for cot in COT_DU_LIEU},
        tieu_de_goc=tuple(COT_DU_LIEU),
        don_vi_cong_suat_nguon="kW",
    )
    return DanhMucXe(
        bang=bang,
        cau_truc=cau_truc,
        chat_luong=chat_luong,
        duong_dan_nguon=Path("fixture.csv"),
    )
