from __future__ import annotations

import math

import pytest

from goi_xe.goi_y.chuan_hoa import (
    KHOANG_CACH_KHI_THIEU,
    ChuanHoaSo,
)


def test_toi_thieu_toi_da_va_gioi_han() -> None:
    bo_chuan_hoa = ChuanHoaSo(10.0, 20.0)
    assert bo_chuan_hoa.chuan_hoa(10) == 0.0
    assert bo_chuan_hoa.chuan_hoa(15) == pytest.approx(0.5)
    assert bo_chuan_hoa.chuan_hoa(20) == 1.0
    assert bo_chuan_hoa.chuan_hoa(5) == 0.0
    assert bo_chuan_hoa.chuan_hoa(30) == 1.0
    assert math.isnan(bo_chuan_hoa.chuan_hoa(None))


def test_hang_so_truong_co_khong_chia_cho_khong() -> None:
    bo_chuan_hoa = ChuanHoaSo(5.0, 5.0)
    assert bo_chuan_hoa.la_hang_so
    assert bo_chuan_hoa.chuan_hoa(5) == 0.0
    assert bo_chuan_hoa.chuan_hoa(100) == 0.0
    assert bo_chuan_hoa.khoang_cach_doi_xung(5, 5) == 0.0
    assert bo_chuan_hoa.khoang_cach_doi_xung(5, 100) == 0.0
    assert bo_chuan_hoa.khoang_cach_toi_thieu(5, 6) == 1.0
    assert bo_chuan_hoa.khoang_cach_toi_thieu(5, 5) == 0.0


def test_doi_xung_khoang_cach_gioi_han_truy_van_va_xu_ly_thieu() -> None:
    bo_chuan_hoa = ChuanHoaSo(10.0, 20.0)
    assert bo_chuan_hoa.khoang_cach_doi_xung(20, 30) == 0.0
    assert bo_chuan_hoa.khoang_cach_doi_xung(10, 30) == 1.0
    assert bo_chuan_hoa.khoang_cach_doi_xung(10, 5) == 0.0
    assert bo_chuan_hoa.khoang_cach_doi_xung(None, 15) == KHOANG_CACH_KHI_THIEU


def test_toi_thieu_khoang_cach_la_bat_doi_xung_va_gioi_han() -> None:
    bo_chuan_hoa = ChuanHoaSo(0.0, 100.0)
    assert bo_chuan_hoa.khoang_cach_toi_thieu(20, 20) == 0.0
    assert bo_chuan_hoa.khoang_cach_toi_thieu(100, 20) == 0.0
    assert bo_chuan_hoa.khoang_cach_toi_thieu(5, 20) == pytest.approx(0.15)
    assert bo_chuan_hoa.khoang_cach_toi_thieu(100, 150) == pytest.approx(0.5)
    assert bo_chuan_hoa.khoang_cach_toi_thieu(0, 150) == pytest.approx(1.0)
    assert bo_chuan_hoa.khoang_cach_toi_thieu(None, 20) == KHOANG_CACH_KHI_THIEU
