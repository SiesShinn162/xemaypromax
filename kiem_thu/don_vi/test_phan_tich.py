from __future__ import annotations

import math

import pytest

from goi_xe.du_lieu.phan_tich import (
    chuan_hoa_khoa,
    chuan_hoa_loai_xe,
    chuan_hoa_nhien_lieu,
    chuan_hoa_tinh_trang,
    doc_cong_suat_kw,
    doc_dung_tich_cop_l,
    doc_gia_vnd,
    doc_nam_sx,
    doc_so_dinh_dang_dia_phuong,
    la_gia_tri_thieu,
)


@pytest.mark.parametrize(
    ("tho", "mong_doi"),
    [
        ("166.190.000", 166_190_000),
        ("14.400.000 ₫", 14_400_000),
        ("1.231.500.000", 1_231_500_000),
        ("166,190,000", 166_190_000),
        ("166190000", 166_190_000),
    ],
)
def test_doc_gia_tieng_viet_dia_phuong(tho: str, mong_doi: int) -> None:
    assert doc_gia_vnd(tho) == mong_doi


@pytest.mark.parametrize(
    ("tho", "nguon_don_vi", "mong_doi"),
    [
        ("21,5", "kW", 21.5),
        ("1.5", "kW", 1.5),
        ("5.000", "W", 5.0),
        ("5.000 W", "kW", 5.0),
        ("21,5 kW", "W", 21.5),
    ],
)
def test_doc_cong_suat_kw_va_nguon_don_vi(
    tho: str, nguon_don_vi: str, mong_doi: float
) -> None:
    assert doc_cong_suat_kw(tho, nguon_don_vi=nguon_don_vi) == pytest.approx(mong_doi)


def test_doc_cop_va_nam() -> None:
    assert doc_dung_tich_cop_l("28 L") == pytest.approx(28.0)
    assert doc_dung_tich_cop_l("22,5 L") == pytest.approx(22.5)
    assert doc_dung_tich_cop_l("0 L") == 0.0
    assert doc_nam_sx("2.024") == 2024
    assert doc_nam_sx("2024") == 2024


def test_thieu_va_khong_hop_le_cac_gia_tri() -> None:
    assert doc_gia_vnd("") is None
    assert doc_gia_vnd("0") is None
    assert doc_cong_suat_kw("0") is None
    assert doc_nam_sx("1800") is None
    assert doc_so_dinh_dang_dia_phuong("không có") is None
    assert la_gia_tri_thieu("N/A")
    assert la_gia_tri_thieu(None)
    assert not la_gia_tri_thieu("0 L")
    assert math.isnan(doc_so_dinh_dang_dia_phuong("--") or math.nan)


def test_chuan_hoa_khoa_va_cac_biet_danh() -> None:
    assert chuan_hoa_khoa("  Giá(VND) ") == "gia vnd"
    assert chuan_hoa_khoa("Công suất tối đa (kW)") == "cong suat toi da kw"
    assert chuan_hoa_nhien_lieu("điện") == "Điện"
    assert chuan_hoa_nhien_lieu("XĂNG") == "Xăng"
    assert chuan_hoa_loai_xe("Tay ga (50cc)") == "Xe tay ga (50cc)"
    assert chuan_hoa_loai_xe("xe số") == "Xe số"
    assert chuan_hoa_tinh_trang("xe mới") == "Mới"
    assert chuan_hoa_tinh_trang("đã qua sử dụng") == "Cũ"
