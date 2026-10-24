from __future__ import annotations

import hashlib
from pathlib import Path

from goi_xe.cau_hinh import DUONG_DAN_DANH_MUC_MAC_DINH
from goi_xe.du_lieu.nap_du_lieu import nap_danh_muc
from goi_xe.goi_y.tieu_chi import (
    TieuChiMem,
    TruyVanGoiY,
)
from goi_xe.goi_y.xep_hang import xep_hang_xe

DUONG_DAN_CSV = Path(__file__).resolve().parents[2] / "data" / "dataset-done.csv"


def _ma_bam(duong_dan: Path) -> str:
    return hashlib.sha256(duong_dan.read_bytes()).hexdigest()


def test_thuc_te_csv_la_doc_chi_va_co_mong_doi_gioi_han() -> None:
    truoc = _ma_bam(DUONG_DAN_CSV)
    danh_muc = nap_danh_muc(DUONG_DAN_CSV)
    sau = _ma_bam(DUONG_DAN_CSV)

    assert truoc == sau
    assert DUONG_DAN_CSV.resolve() == DUONG_DAN_DANH_MUC_MAC_DINH
    assert len(danh_muc) == 225
    assert danh_muc.duong_dan_nguon == DUONG_DAN_CSV.resolve()
    assert "brake_system" not in danh_muc.bang.columns
    assert danh_muc.chat_luong.don_vi_cong_suat_nguon == "kW"
    assert danh_muc.chat_luong.so_dong_nguon == 225
    assert danh_muc.chat_luong.so_dong_hop_le == 225
    assert danh_muc.chat_luong.so_dong_trong == 0
    assert danh_muc.chat_luong.so_dong_tieu_de == 0
    assert danh_muc.chat_luong.so_dong_thieu_model == 0
    assert danh_muc.chat_luong.so_dong_trung == 0
    assert danh_muc.chat_luong.so_dong_bo_sung_hang == 216
    assert all(
        so_luong == 0 for so_luong in danh_muc.chat_luong.dem_gia_tri_thieu.values()
    )
    assert all(
        so_luong == 0 for so_luong in danh_muc.chat_luong.dem_gia_tri_loi.values()
    )
    assert "Xăng" in danh_muc.gia_tri_danh_muc("fuel_type")
    assert "Điện" in danh_muc.gia_tri_danh_muc("fuel_type")
    assert danh_muc.bang["fuel_type"].value_counts().to_dict() == {
        "Xăng": 163,
        "Điện": 62,
    }
    assert danh_muc.bang["condition"].value_counts().to_dict() == {"Mới": 225}

    cac_muc_gia = danh_muc.bang["price_vnd"].dropna()
    cac_cong_suat = danh_muc.bang["max_power_kw"].dropna()
    dung_tich_cop = danh_muc.bang["boot_capacity_l"].dropna()
    cac_nam = danh_muc.bang["year"].dropna()
    assert (cac_muc_gia > 0).all()
    assert (cac_cong_suat > 0).all()
    assert (dung_tich_cop >= 0).all()
    assert cac_nam.between(1900, 2100).all()


def test_thuc_te_danh_muc_xep_hang_tuan_thu_cung_loc() -> None:
    danh_muc = nap_danh_muc(DUONG_DAN_CSV)
    truy_van = TruyVanGoiY(
        tieu_chi=(
            TieuChiMem("price", 0.30, che_do="low"),
            TieuChiMem("vehicle_type", 0.20, gia_tri="Xe tay ga"),
        ),
        gia_toi_da_vnd=60_000_000,
        dieu_kien_nhien_lieu="Xăng",
        k=5,
    )
    ket_qua = xep_hang_xe(danh_muc, truy_van)

    assert ket_qua.so_xe_sau_loc > 0
    assert len(ket_qua.cac_muc) <= 5
    assert len({muc.xe["vehicle_id"] for muc in ket_qua.cac_muc}) == len(
        ket_qua.cac_muc
    )
    assert all(muc.xe["price_vnd"] <= 60_000_000 for muc in ket_qua.cac_muc)
    assert all(muc.xe["fuel_type"] == "Xăng" for muc in ket_qua.cac_muc)
    assert any(muc.xe["vehicle_type"] == "Xe tay ga" for muc in ket_qua.cac_muc)
    cac_khoang_cach = [muc.khoang_cach for muc in ket_qua.cac_muc]
    assert cac_khoang_cach == sorted(cac_khoang_cach)
    assert all(0.0 <= khoang_cach <= 1.0 for khoang_cach in cac_khoang_cach)


def test_thuc_te_danh_muc_xep_hang_dien_cac_xe_cho_dung_chung_kw_truong() -> None:
    danh_muc = nap_danh_muc(DUONG_DAN_CSV)
    truy_van = TruyVanGoiY(
        tieu_chi=(TieuChiMem("max_power_kw", 1.0, gia_tri=3.0),),
        dieu_kien_nhien_lieu="Điện",
        k=5,
    )

    ket_qua = xep_hang_xe(danh_muc, truy_van)

    assert ket_qua.so_xe_sau_loc == 62
    assert len(ket_qua.cac_muc) == 5
    assert all(muc.xe["fuel_type"] == "Điện" for muc in ket_qua.cac_muc)
    assert all(muc.xe["max_power_kw"] > 0 for muc in ket_qua.cac_muc)
