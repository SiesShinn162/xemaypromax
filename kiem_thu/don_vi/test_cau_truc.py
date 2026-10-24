from __future__ import annotations

import pytest

from goi_xe.du_lieu.cau_truc import (
    LoiCauTrucCsv,
    giai_tieu_de_cot,
)

TIEU_DE_BAT_BUOC = [
    "Hãng",
    "Model",
    "Giá(VND)",
    "Công suất tối đa (Kw)",
    "Nhiên liệu",
    "Kiểu xe",
]


def test_giai_thuc_te_cac_tieu_de_va_tuy_chon_cac_cot() -> None:
    cau_truc = giai_tieu_de_cot(
        TIEU_DE_BAT_BUOC
        + ["Dung tích cốp (lít)", "Tình trạng", "Năm sản xuất"]
    )
    assert cau_truc.bang_cot["brand"] == "Hãng"
    assert cau_truc.bang_cot["price_vnd"] == "Giá(VND)"
    assert cau_truc.bang_cot["max_power_kw"] == "Công suất tối đa (Kw)"
    assert cau_truc.bang_cot["boot_capacity_l"] == "Dung tích cốp (lít)"
    assert cau_truc.don_vi_cong_suat_nguon == "kW"


def test_giai_w_don_vi_va_biet_danh_cach_viet() -> None:
    cau_truc = giai_tieu_de_cot(
        [
            "hang",
            "MODEL",
            "price_vnd",
            "max_power_kw",
            "fuel_type",
            "vehicle_type",
            "boot_capacity_l",
            "year",
        ]
    )
    assert cau_truc.bang_cot["brand"] == "hang"
    assert cau_truc.bang_cot["price_vnd"] == "price_vnd"
    assert cau_truc.bang_cot["max_power_kw"] == "max_power_kw"
    assert cau_truc.bang_cot["boot_capacity_l"] == "boot_capacity_l"
    assert cau_truc.bang_cot["year"] == "year"

    cau_truc_w = giai_tieu_de_cot(
        [
            "Hãng",
            "Model",
            "Giá (VND)",
            "Công suất tối đa (W)",
            "Nhiên liệu",
            "Kiểu xe",
        ]
    )
    assert cau_truc_w.don_vi_cong_suat_nguon == "W"


def test_thieu_bat_buoc_cot_co_tieng_viet_loi() -> None:
    with pytest.raises(LoiCauTrucCsv) as loi:
        giai_tieu_de_cot(["Hãng", "Model", "Nhiên liệu", "Kiểu xe"])
    thong_bao = str(loi.value)
    assert "thiếu cột bắt buộc" in thong_bao
    assert "Giá" in thong_bao
    assert "Công suất" in thong_bao


def test_trung_anh_xa_la_bi_tu_choi() -> None:
    with pytest.raises(LoiCauTrucCsv) as loi:
        giai_tieu_de_cot(
            TIEU_DE_BAT_BUOC + ["Giá bán (VND)"]
        )
    assert "nhiều cột" in str(loi.value)
    assert "Giá" in str(loi.value)
