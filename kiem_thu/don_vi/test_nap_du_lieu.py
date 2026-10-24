from __future__ import annotations

from pathlib import Path

import pytest

from goi_xe.du_lieu.cau_truc import LoiCauTrucCsv
from goi_xe.du_lieu.nap_du_lieu import LoiDuLieuCsv, nap_danh_muc


def _ghi_csv(duong_dan: Path, chu: str) -> bytes:
    duong_dan.write_text(chu, encoding="utf-8-sig")
    return duong_dan.read_bytes()


def test_nap_du_lieu_xu_ly_phan_don_vi_trung_va_thieu(tmp_path: Path) -> None:
    duong_dan = tmp_path / "catalog.csv"
    truoc = _ghi_csv(
        duong_dan,
        "\n".join(
            [
                "Hãng,Model,Giá(VND),Công suất tối đa (W),Nhiên liệu,Kiểu xe,"
                "Dung tích cốp (lít),Tình trạng,Năm sản xuất",
                "Honda,SH 125,166.190.000,15.000,Xăng,Xe tay ga,28 L,,",
                ",LEAD 125,40.000.000,8.000,Xăng,Xe tay ga,37 L,Mới,2024",
                ",LEAD 125,40.000.000,8.000,Xăng,Xe tay ga,37 L,Mới,2024",
                "Yamaha,,,,,,,,",
                ",Exciter 155,50.000.000,12.000,Xăng,Xe côn tay,\"5,5 L\",,",
                "",
                "Vinfast,Flazz,40.000.000,5.000,Điện,Xe điện,,,",
            ]
        ),
    )

    danh_muc = nap_danh_muc(duong_dan)
    sau = duong_dan.read_bytes()

    assert truoc == sau
    assert len(danh_muc) == 4
    assert danh_muc.chat_luong.don_vi_cong_suat_nguon == "W"
    assert danh_muc.chat_luong.so_dong_trung == 1
    assert danh_muc.chat_luong.so_dong_tieu_de == 1
    assert danh_muc.chat_luong.so_dong_trong == 1
    assert danh_muc.chat_luong.so_dong_bo_sung_hang == 3
    assert danh_muc.chat_luong.so_dong_hop_le == 4

    cac_hang = dict(zip(danh_muc.bang["model"], danh_muc.bang["brand"], strict=True))
    assert cac_hang["SH 125"] == "Honda"
    assert cac_hang["LEAD 125"] == "Honda"
    assert cac_hang["Exciter 155"] == "Yamaha"
    assert cac_hang["Flazz"] == "Vinfast"

    cac_cong_suat = dict(
        zip(danh_muc.bang["model"], danh_muc.bang["max_power_kw"], strict=True)
    )
    assert cac_cong_suat["SH 125"] == pytest.approx(15.0)
    assert cac_cong_suat["LEAD 125"] == pytest.approx(8.0)
    assert cac_cong_suat["Exciter 155"] == pytest.approx(12.0)

    xe_dien = danh_muc.bang.loc[danh_muc.bang["model"] == "Flazz"].iloc[0]
    assert xe_dien["fuel_type"] == "Điện"
    assert xe_dien["boot_capacity_l"] is None or str(xe_dien["boot_capacity_l"]) == "nan"
    assert danh_muc.chat_luong.dem_gia_tri_thieu["boot_capacity_l"] == 1
    assert danh_muc.chat_luong.dem_gia_tri_thieu["condition"] >= 1


def test_nap_du_lieu_chap_nhan_biet_danh_cac_tieu_de_dau_cham_phay_va_kw(tmp_path: Path) -> None:
    duong_dan = tmp_path / "catalog.csv"
    duong_dan.write_text(
        "\n".join(
            [
                "hãng;model;giá bán;công suất tối đa (kw);nhiên liệu;kiểu xe",
                "Honda;SH 350i;151.390.000;21,5;Xăng;Xe tay ga",
            ]
        ),
        encoding="utf-8-sig",
    )
    danh_muc = nap_danh_muc(duong_dan)
    dong = danh_muc.bang.iloc[0]
    assert dong["brand"] == "Honda"
    assert dong["price_vnd"] == 151_390_000
    assert dong["max_power_kw"] == pytest.approx(21.5)
    assert danh_muc.chat_luong.don_vi_cong_suat_nguon == "kW"


def test_nap_du_lieu_thieu_bat_buoc_tieu_de_la_ro_rang(tmp_path: Path) -> None:
    duong_dan = tmp_path / "catalog.csv"
    duong_dan.write_text("Hãng,Model\nHonda,SH\n", encoding="utf-8")
    with pytest.raises(LoiCauTrucCsv) as loi:
        nap_danh_muc(duong_dan)
    assert "thiếu cột bắt buộc" in str(loi.value)


def test_nap_du_lieu_khong_co_hop_le_cac_dong_loi(tmp_path: Path) -> None:
    duong_dan = tmp_path / "catalog.csv"
    duong_dan.write_text(
        "Hãng,Model,Giá(VND),Công suất tối đa (Kw),Nhiên liệu,Kiểu xe\n"
        "Honda,,,,,\n",
        encoding="utf-8",
    )
    with pytest.raises(LoiDuLieuCsv):
        nap_danh_muc(duong_dan)


def test_nap_du_lieu_thieu_tep_la_ro_rang(tmp_path: Path) -> None:
    with pytest.raises(LoiDuLieuCsv) as loi:
        nap_danh_muc(tmp_path / "missing.csv")
    assert "Không tìm thấy tệp CSV" in str(loi.value)
