from __future__ import annotations

import math

import pytest

from goi_xe.goi_y.tieu_chi import (
    LoiThieuTieuChi,
    LoiTruyVanKhongHopLe,
    TieuChiMem,
    TruyVanGoiY,
    tao_tieu_chi_can_bang,
)
from goi_xe.goi_y.xep_hang import xep_hang_xe
from kiem_thu.ho_tro import tao_danh_muc


def _xep_hang(danh_muc, tieu_chi, **tu_khoa):
    truy_van = TruyVanGoiY(tieu_chi=tuple(tieu_chi), **tu_khoa)
    return xep_hang_xe(danh_muc, truy_van)


def test_cung_loc_chay_truoc_xep_hang_va_thieu_cac_gia_tri_duoc_bi_loai() -> None:
    danh_muc = tao_danh_muc(
        [
            {"vehicle_id": "a", "model": "A", "price_vnd": 30_000_000},
            {"vehicle_id": "b", "model": "B", "price_vnd": 70_000_000},
            {
                "vehicle_id": "c",
                "model": "C",
                "price_vnd": 40_000_000,
                "fuel_type": "Điện",
            },
            {"vehicle_id": "d", "model": "D", "price_vnd": None},
            {"vehicle_id": "e", "model": "E", "price_vnd": 40_000_000, "fuel_type": None},
        ]
    )
    ket_qua = _xep_hang(
        danh_muc,
        [TieuChiMem("price", 1.0, che_do="low")],
        gia_toi_da_vnd=50_000_000,
        dieu_kien_nhien_lieu="Xăng",
        k=5,
    )
    assert ket_qua.so_xe_sau_loc == 1
    assert ket_qua.so_xe_bi_loai == 4
    assert ket_qua.ma_xe_top_k == ("a",)
    assert ket_qua.dem_loc_cung["max_price_vnd"] == 2
    assert ket_qua.dem_loc_cung["required_fuel"] == 2


def test_khong_hoat_dong_tieu_chi_duoc_loai_bo_va_cac_trong_so_chuan_hoa_lai() -> None:
    danh_muc = tao_danh_muc(
        [
            {"vehicle_id": "a", "model": "A", "vehicle_type": "Xe số"},
            {"vehicle_id": "b", "model": "B", "vehicle_type": "Xe tay ga"},
        ]
    )
    ket_qua = _xep_hang(
        danh_muc,
        [
            TieuChiMem("price", 0.30, che_do="low"),
            TieuChiMem("brand", 0.02, gia_tri=None),
            TieuChiMem("vehicle_type", 0.02, gia_tri="", che_do=None),
        ],
    )
    assert ket_qua.trong_so_chuan_hoa == {"price": 1.0}

    ket_qua = _xep_hang(
        danh_muc,
        [
            TieuChiMem("price", 0.30, che_do="low"),
            TieuChiMem("vehicle_type", 0.20, gia_tri="Xe số"),
        ],
    )
    assert ket_qua.trong_so_chuan_hoa == pytest.approx(
        {"price": 0.6, "vehicle_type": 0.4}
    )


def test_thieu_mem_gia_tri_nhan_mot_nua_khoang_cach_va_giu_trong_so_mau_so() -> None:
    danh_muc = tao_danh_muc(
        [
            {"vehicle_id": "a", "model": "A", "price_vnd": 10.0},
            {
                "vehicle_id": "b",
                "model": "B",
                "price_vnd": 20.0,
                "vehicle_type": "Xe tay ga",
            },
            {"vehicle_id": "c", "model": "C", "price_vnd": None},
        ]
    )
    ket_qua = _xep_hang(
        danh_muc,
        [
            TieuChiMem("price", 0.30, che_do="low"),
            TieuChiMem("vehicle_type", 0.20, gia_tri="Xe số"),
        ],
        k=3,
    )
    cac_muc = {muc.xe["vehicle_id"]: muc for muc in ket_qua.cac_muc}
    assert cac_muc["a"].khoang_cach == pytest.approx(0.0)
    assert cac_muc["b"].khoang_cach == pytest.approx(1.0)
    assert cac_muc["c"].khoang_cach_tieu_chi["price"] == pytest.approx(0.5)
    assert cac_muc["c"].khoang_cach_tieu_chi["vehicle_type"] == pytest.approx(0.0)
    assert cac_muc["c"].khoang_cach == pytest.approx(math.sqrt(0.15))
    assert ket_qua.ma_xe_top_k == ("a", "c", "b")


def test_co_trong_so_euclid_cong_thuc() -> None:
    danh_muc = tao_danh_muc(
        [
            {
                "vehicle_id": "a",
                "model": "A",
                "price_vnd": 20.0,
                "vehicle_type": "Xe số",
            },
            {
                "vehicle_id": "b",
                "model": "B",
                "price_vnd": 10.0,
                "vehicle_type": "Xe tay ga",
            },
        ]
    )
    ket_qua = _xep_hang(
        danh_muc,
        [
            TieuChiMem("price", 0.30, che_do="low"),
            TieuChiMem("vehicle_type", 0.20, gia_tri="Xe số"),
        ],
        k=2,
    )
    cac_muc = {muc.xe["vehicle_id"]: muc for muc in ket_qua.cac_muc}
    assert cac_muc["a"].khoang_cach == pytest.approx(math.sqrt(0.3 / 0.5))
    assert cac_muc["b"].khoang_cach == pytest.approx(math.sqrt(0.2 / 0.5))
    assert ket_qua.ma_xe_top_k == ("b", "a")


def test_toi_thieu_cop_khoang_cach_la_bat_doi_xung_va_gioi_han() -> None:
    danh_muc = tao_danh_muc(
        [
            {"vehicle_id": "a", "model": "A", "boot_capacity_l": 5.0},
            {"vehicle_id": "b", "model": "B", "boot_capacity_l": 20.0},
            {"vehicle_id": "c", "model": "C", "boot_capacity_l": 50.0},
        ]
    )
    ket_qua = _xep_hang(
        danh_muc,
        [TieuChiMem("boot_capacity_l", 1.0, gia_tri=20.0)],
        k=3,
    )
    cac_muc = {muc.xe["vehicle_id"]: muc for muc in ket_qua.cac_muc}
    assert cac_muc["a"].khoang_cach == pytest.approx(15.0 / 45.0)
    assert cac_muc["b"].khoang_cach == 0.0
    assert cac_muc["c"].khoang_cach == 0.0

    ket_qua = _xep_hang(
        danh_muc,
        [TieuChiMem("boot_capacity_l", 1.0, gia_tri=100.0)],
        k=3,
    )
    assert all(muc.khoang_cach == pytest.approx(1.0) for muc in ket_qua.cac_muc)

    ket_qua = _xep_hang(
        danh_muc,
        [TieuChiMem("boot_capacity_l", 1.0, gia_tri=0.0)],
        k=3,
    )
    assert all(muc.khoang_cach == 0.0 for muc in ket_qua.cac_muc)


def test_hang_so_toi_thieu_truong_dung_khong_hoac_mot() -> None:
    danh_muc = tao_danh_muc(
        [
            {"vehicle_id": "a", "model": "A", "boot_capacity_l": 20.0},
            {"vehicle_id": "b", "model": "B", "boot_capacity_l": 20.0},
        ]
    )
    ket_qua = _xep_hang(
        danh_muc,
        [TieuChiMem("boot_capacity_l", 1.0, gia_tri=25.0)],
        k=2,
    )
    assert all(muc.khoang_cach == 1.0 for muc in ket_qua.cac_muc)

    ket_qua = _xep_hang(
        danh_muc,
        [TieuChiMem("boot_capacity_l", 1.0, gia_tri=20.0)],
        k=2,
    )
    assert all(muc.khoang_cach == 0.0 for muc in ket_qua.cac_muc)


def test_danh_muc_khoang_cach_la_khong_khop_va_thieu_la_mot_nua() -> None:
    danh_muc = tao_danh_muc(
        [
            {"vehicle_id": "a", "model": "A", "fuel_type": "Xăng"},
            {"vehicle_id": "b", "model": "B", "fuel_type": "Điện"},
            {"vehicle_id": "c", "model": "C", "fuel_type": None},
        ]
    )
    ket_qua = _xep_hang(
        danh_muc,
        [TieuChiMem("fuel_type", 1.0, gia_tri="Điện")],
        k=3,
    )
    cac_muc = {muc.xe["vehicle_id"]: muc for muc in ket_qua.cac_muc}
    assert cac_muc["b"].khoang_cach == 0.0
    assert cac_muc["a"].khoang_cach == 1.0
    assert cac_muc["c"].khoang_cach == 0.5


def test_top_k_sap_xep_tang_dan_voi_xac_dinh_hoa_pha() -> None:
    danh_muc = tao_danh_muc(
        [
            {
                "vehicle_id": "a",
                "model": "A",
                "price_vnd": 20.0,
                "source_row": 5,
            },
            {
                "vehicle_id": "b",
                "model": "B",
                "price_vnd": 10.0,
                "source_row": 20,
            },
            {
                "vehicle_id": "c",
                "model": "C",
                "price_vnd": 10.0,
                "source_row": 10,
            },
        ]
    )
    ket_qua = _xep_hang(
        danh_muc,
        [TieuChiMem("price", 1.0, che_do="low")],
        k=2,
    )
    assert ket_qua.ma_xe_top_k == ("c", "b")

    ket_qua = _xep_hang(
        danh_muc,
        [TieuChiMem("price", 1.0, che_do="low")],
        k=10,
    )
    assert ket_qua.ma_xe_top_k == ("c", "b", "a")


def test_gia_muc_tieu_la_da_gioi_han_den_danh_muc_mien() -> None:
    danh_muc = tao_danh_muc(
        [
            {"vehicle_id": "a", "model": "A", "price_vnd": 10.0},
            {"vehicle_id": "b", "model": "B", "price_vnd": 20.0},
        ]
    )
    ket_qua = _xep_hang(
        danh_muc,
        [TieuChiMem("price", 1.0, gia_tri=30.0, che_do="target")],
        k=2,
    )
    cac_muc = {muc.xe["vehicle_id"]: muc for muc in ket_qua.cac_muc}
    assert cac_muc["b"].khoang_cach == 0.0
    assert cac_muc["a"].khoang_cach == 1.0

    ket_qua = _xep_hang(
        danh_muc,
        [TieuChiMem("price", 1.0, gia_tri=5.0, che_do="target")],
        k=2,
    )
    cac_muc = {muc.xe["vehicle_id"]: muc for muc in ket_qua.cac_muc}
    assert cac_muc["a"].khoang_cach == 0.0
    assert cac_muc["b"].khoang_cach == 1.0


def test_khong_dang_dung_tieu_chi_va_khong_hop_le_tieu_chi_loi() -> None:
    danh_muc = tao_danh_muc([{"vehicle_id": "a", "model": "A"}])
    with pytest.raises(LoiThieuTieuChi):
        _xep_hang(
            danh_muc,
            [
                TieuChiMem("price", 0.0, che_do="low"),
                TieuChiMem("brand", 0.5, gia_tri=None),
            ],
        )
    with pytest.raises(LoiTruyVanKhongHopLe):
        _xep_hang(danh_muc, [TieuChiMem("unknown", 1.0, gia_tri="x")])
    with pytest.raises(LoiTruyVanKhongHopLe):
        _xep_hang(danh_muc, [TieuChiMem("brake_system", 1.0, gia_tri="ABS")])


def test_rong_ung_vien_tra_ve_rong_ket_qua() -> None:
    danh_muc = tao_danh_muc([{"vehicle_id": "a", "model": "A", "price_vnd": 100.0}])
    ket_qua = _xep_hang(
        danh_muc,
        [TieuChiMem("price", 1.0, che_do="low")],
        gia_toi_da_vnd=10.0,
        k=3,
    )
    assert ket_qua.cac_muc == ()
    assert ket_qua.so_xe_sau_loc == 0
    assert ket_qua.so_xe_bi_loai == 1


def test_truy_van_kiem_tra_tu_choi_khong_hop_le_k_ngan_sach_va_trong_cung_loc() -> None:
    danh_muc = tao_danh_muc(
        [
            {
                "vehicle_id": "a",
                "model": "A",
                "price_vnd": 10.0,
                "fuel_type": "Xăng",
                "condition": "Mới",
            }
        ]
    )
    tieu_chi = (TieuChiMem("price", 1.0, che_do="low"),)

    for khong_hop_le_k in (0, 1.5, True):
        with pytest.raises(LoiTruyVanKhongHopLe):
            TruyVanGoiY(tieu_chi=tieu_chi, k=khong_hop_le_k)  # type: ignore[arg-type]

    for khong_hop_le_ngan_sach in (-1, float("nan"), float("inf"), "100", 10**400):
        with pytest.raises(LoiTruyVanKhongHopLe):
            TruyVanGoiY(
                tieu_chi=tieu_chi,
                gia_toi_da_vnd=khong_hop_le_ngan_sach,  # type: ignore[arg-type]
            )

    with pytest.raises(LoiTruyVanKhongHopLe):
        _xep_hang(danh_muc, tieu_chi, dieu_kien_nhien_lieu="   ")
    with pytest.raises(LoiTruyVanKhongHopLe):
        _xep_hang(danh_muc, tieu_chi, dieu_kien_tinh_trang="   ")
    with pytest.raises(LoiTruyVanKhongHopLe):
        _xep_hang(
            danh_muc,
            [
                TieuChiMem("price", 0.3, che_do="low"),
                TieuChiMem("brand", 0.2, gia_tri="Honda"),
                TieuChiMem("brand", 0.1, gia_tri="Honda"),
            ],
        )


def test_tao_can_bang_tieu_chi_tao_bang_cac_trong_so_va_danh_muc_trung_vi() -> None:
    danh_muc = tao_danh_muc(
        [
            {
                "vehicle_id": "v1",
                "model": "Alpha",
                "brand": "Honda",
                "price_vnd": 20_000_000.0,
                "vehicle_type": "Xe số",
                "fuel_type": "Xăng",
                "max_power_kw": 6.0,
                "boot_capacity_l": 10.0,
                "condition": "Mới",
                "year": 2020.0,
            },
            {
                "vehicle_id": "v2",
                "model": "Beta",
                "brand": "Honda",
                "price_vnd": 40_000_000.0,
                "vehicle_type": "Xe tay ga",
                "fuel_type": "Xăng",
                "max_power_kw": 8.0,
                "boot_capacity_l": 15.0,
                "condition": "Mới",
                "year": 2022.0,
            },
            {
                "vehicle_id": "v3",
                "model": "Gamma",
                "brand": "Yamaha",
                "price_vnd": 60_000_000.0,
                "vehicle_type": "Xe số",
                "fuel_type": "Điện",
                "max_power_kw": 10.0,
                "boot_capacity_l": 20.0,
                "condition": "Cũ",
                "year": 2024.0,
            },
        ]
    )
    can_bang = tao_tieu_chi_can_bang(danh_muc)
    cho_khoa = {tieu_chi.khoa: tieu_chi for tieu_chi in can_bang}

    # All 8 supported criteria present
    assert len(can_bang) == 8
    bang_trong_so = pytest.approx(1.0 / 8)
    for tieu_chi in can_bang:
        assert tieu_chi.trong_so == bang_trong_so

    # Price has target mode and median value 40,000,000
    assert cho_khoa["price"].che_do == "target"
    assert cho_khoa["price"].gia_tri == pytest.approx(40_000_000.0)

    # Numerics have medians
    assert cho_khoa["max_power_kw"].gia_tri == pytest.approx(8.0)
    assert cho_khoa["boot_capacity_l"].gia_tri == pytest.approx(15.0)
    assert cho_khoa["year"].gia_tri == 2022

    # Categoricals have modes
    assert cho_khoa["brand"].gia_tri == "Honda"
    assert cho_khoa["vehicle_type"].gia_tri == "Xe số"
    assert cho_khoa["fuel_type"].gia_tri == "Xăng"
    assert cho_khoa["condition"].gia_tri == "Mới"


def test_can_bang_ho_so_chay_trong_xep_hang() -> None:
    danh_muc = tao_danh_muc(
        [
            {
                "vehicle_id": "v1",
                "model": "Alpha",
                "brand": "Honda",
                "price_vnd": 20_000_000.0,
                "vehicle_type": "Xe số",
                "fuel_type": "Xăng",
                "max_power_kw": 6.0,
                "boot_capacity_l": 10.0,
                "condition": "Mới",
                "year": 2020.0,
            },
            {
                "vehicle_id": "v2",
                "model": "Beta",
                "brand": "Honda",
                "price_vnd": 40_000_000.0,
                "vehicle_type": "Xe tay ga",
                "fuel_type": "Xăng",
                "max_power_kw": 8.0,
                "boot_capacity_l": 15.0,
                "condition": "Mới",
                "year": 2022.0,
            },
        ]
    )
    can_bang_tieu_chi = tao_tieu_chi_can_bang(danh_muc)
    truy_van = TruyVanGoiY(tieu_chi=can_bang_tieu_chi, k=2)
    ket_qua = xep_hang_xe(danh_muc, truy_van)

    assert len(ket_qua.cac_muc) == 2
    assert len(ket_qua.tieu_chi_dang_dung) == 8
    # All 8 normalized weights equal 1/8 = 0.125
    for dang_dung in ket_qua.tieu_chi_dang_dung:
        assert dang_dung.trong_so_chuan_hoa == pytest.approx(1.0 / 8)


def test_tuy_chinh_tieu_chi_luong_chi_dung_da_chon() -> None:
    danh_muc = tao_danh_muc(
        [
            {
                "vehicle_id": "v1",
                "model": "Alpha",
                "brand": "Honda",
                "price_vnd": 20_000_000.0,
                "vehicle_type": "Xe số",
                "fuel_type": "Xăng",
                "max_power_kw": 6.0,
            },
            {
                "vehicle_id": "v2",
                "model": "Beta",
                "brand": "Yamaha",
                "price_vnd": 40_000_000.0,
                "vehicle_type": "Xe tay ga",
                "fuel_type": "Điện",
                "max_power_kw": 10.0,
            },
        ]
    )
    # Only custom criteria: price and fuel_type
    tuy_chinh_tieu_chi = (
        TieuChiMem("price", 2.0, che_do="low"),
        TieuChiMem("fuel_type", 1.0, gia_tri="Xăng"),
    )
    truy_van = TruyVanGoiY(tieu_chi=tuy_chinh_tieu_chi, k=2)
    ket_qua = xep_hang_xe(danh_muc, truy_van)

    assert len(ket_qua.tieu_chi_dang_dung) == 2
    dang_dung_cac_khoa = {
        tieu_chi_dang_dung.khoa for tieu_chi_dang_dung in ket_qua.tieu_chi_dang_dung
    }
    assert dang_dung_cac_khoa == {"price", "fuel_type"}
    # Normalization: 2/(2+1) = 2/3, 1/(2+1) = 1/3
    cac_trong_so = {
        tieu_chi_dang_dung.khoa: tieu_chi_dang_dung.trong_so_chuan_hoa
        for tieu_chi_dang_dung in ket_qua.tieu_chi_dang_dung
    }
    assert cac_trong_so["price"] == pytest.approx(2 / 3)
    assert cac_trong_so["fuel_type"] == pytest.approx(1 / 3)


def test_doc_lap_toi_thieu_toi_da_chuan_hoa_trong_co_trong_so_euclid() -> None:
    danh_muc = tao_danh_muc(
        [
            {
                "vehicle_id": "v1",
                "model": "V1",
                "price_vnd": 20_000_000.0,
                "max_power_kw": 5.0,
            },
            {
                "vehicle_id": "v2",
                "model": "V2",
                "price_vnd": 60_000_000.0,
                "max_power_kw": 10.0,
            },
            {
                "vehicle_id": "v3",
                "model": "V3",
                "price_vnd": 100_000_000.0,
                "max_power_kw": 15.0,
            },
        ]
    )
    # v2 has price 60m: scaled = (60-20)/(100-20) = 0.5
    # v2 has power 10kW: scaled = (10-5)/(15-5) = 0.5
    # Query targets: price target 20m (scaled 0.0), power 15kW (scaled 1.0)
    # d_price(v2, u) = |0.5 - 0.0| = 0.5
    # d_power(v2, u) = |0.5 - 1.0| = 0.5
    # D(v2, u) = sqrt( (1.0 * 0.5^2 + 1.0 * 0.5^2) / 2.0 ) = 0.5
    ket_qua = _xep_hang(
        danh_muc,
        [
            TieuChiMem("price", 1.0, gia_tri=20_000_000.0, che_do="target"),
            TieuChiMem("max_power_kw", 1.0, gia_tri=15.0),
        ],
        k=3,
    )
    cac_muc = {muc.xe["vehicle_id"]: muc for muc in ket_qua.cac_muc}
    assert cac_muc["v2"].khoang_cach_tieu_chi["price"] == pytest.approx(0.5)
    assert cac_muc["v2"].khoang_cach_tieu_chi["max_power_kw"] == pytest.approx(0.5)
    assert cac_muc["v2"].khoang_cach == pytest.approx(0.5)


def test_co_trong_so_euclid_nho_trong_so_chuan_hoa_bat_bien() -> None:
    danh_muc = tao_danh_muc(
        [
            {
                "vehicle_id": "v1",
                "model": "V1",
                "price_vnd": 20_000_000.0,
                "fuel_type": "Xăng",
            },
            {
                "vehicle_id": "v2",
                "model": "V2",
                "price_vnd": 100_000_000.0,
                "fuel_type": "Điện",
            },
        ]
    )
    # v1 distance: sqrt( (w_price * 0.5^2 + w_fuel * 0.0^2) / (w_price + w_fuel) )
    # When w_price == w_fuel: sqrt( 0.25 / 2 ) = sqrt(0.125)
    # When w_price == w_fuel: v2 distance = sqrt( (0.25 + 1.0) / 2 ) = sqrt(0.625)

    # Standard weight scale
    do_lech_chuan_ket_qua = _xep_hang(
        danh_muc,
        [
            TieuChiMem("price", 1.0, gia_tri=60_000_000.0, che_do="target"),
            TieuChiMem("fuel_type", 1.0, gia_tri="Xăng"),
        ],
        k=2,
    )
    do_lech_chuan_1 = {muc.xe["vehicle_id"]: muc for muc in do_lech_chuan_ket_qua.cac_muc}["v1"]
    do_lech_chuan_2 = {muc.xe["vehicle_id"]: muc for muc in do_lech_chuan_ket_qua.cac_muc}["v2"]
    assert do_lech_chuan_1.khoang_cach == pytest.approx(math.sqrt(0.125))
    assert do_lech_chuan_2.khoang_cach == pytest.approx(math.sqrt(0.625))

    # Very small positive weight scale (e.g. 1e-15) must produce identical distances
    nho_ket_qua = _xep_hang(
        danh_muc,
        [
            TieuChiMem("price", 1e-15, gia_tri=60_000_000.0, che_do="target"),
            TieuChiMem("fuel_type", 1e-15, gia_tri="Xăng"),
        ],
        k=2,
    )
    mau_nho_1 = {muc.xe["vehicle_id"]: muc for muc in nho_ket_qua.cac_muc}["v1"]
    mau_nho_2 = {muc.xe["vehicle_id"]: muc for muc in nho_ket_qua.cac_muc}["v2"]
    assert mau_nho_1.khoang_cach == pytest.approx(do_lech_chuan_1.khoang_cach)
    assert mau_nho_2.khoang_cach == pytest.approx(do_lech_chuan_2.khoang_cach)
    assert mau_nho_1.khoang_cach == pytest.approx(math.sqrt(0.125))
