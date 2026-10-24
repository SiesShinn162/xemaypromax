from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from goi_xe.dinh_dang import dinh_dang_vnd

DUONG_DAN_UNG_DUNG = Path(__file__).resolve().parents[2] / "app.py"


@pytest.fixture
def ung_dung(monkeypatch: pytest.MonkeyPatch) -> AppTest:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(
        "goi_xe.giao_dien.ung_dung.lay_khoa_api",
        lambda *tham_so, **tu_khoa: None,
    )
    tai = AppTest.from_file(
        str(DUONG_DAN_UNG_DUNG), default_timeout=90
    ).run()
    assert not tai.exception
    return tai


def test_mot_trang_cau_truc_khong_thanh_ben_khong_tab_khong_du_lieu_tab(ung_dung: AppTest) -> None:
    # 1. Page title
    assert [tieu_de.value for tieu_de in ung_dung.title] == ["Tư vấn chọn xe"]

    # 2. Absolutely NO tabs (no "Kết quả", no "Dữ liệu" tab)
    assert len(ung_dung.tabs) == 0

    # 3. Absolutely NO sidebar / rail buttons
    assert len(ung_dung.sidebar) == 0

    # 4. Buttons on the single page
    nut_cac_nhan = [nut.label for nut in ung_dung.button]
    assert "Gợi ý xe" in nut_cac_nhan
    assert "Đặt lại lựa chọn" in nut_cac_nhan
    assert "Giải thích bằng Gemini" in nut_cac_nhan

    # 5. Subheaders
    cac_tieu_de_phu = [muc.value for muc in ung_dung.subheader]
    assert "Điều kiện bắt buộc" in cac_tieu_de_phu
    assert "Tiêu chí ưu tiên" in cac_tieu_de_phu
    assert "Chất lượng dữ liệu" not in cac_tieu_de_phu

    # 6. Default preference profile is balanced
    ho_so_thanh_phan = ung_dung.segmented_control(key="preference_profile")
    assert ho_so_thanh_phan.value == "balanced"

    # 7. Absolutely NO purpose or distance inputs, textareas, or rail clutter
    assert len(ung_dung.text_area) == 0
    assert len(ung_dung.text_input) == 0
    tat_ca_nhap_cac_nhan = [
        thanh_phan.label
        for thanh_phan in list(ung_dung.checkbox)
        + list(ung_dung.number_input)
        + list(ung_dung.selectbox)
        + list(ung_dung.multiselect)
    ]
    for nhan in tat_ca_nhap_cac_nhan:
        assert "mục đích" not in nhan.lower()
        assert "quãng đường" not in nhan.lower()


def test_can_bang_mac_dinh_luong(ung_dung: AppTest) -> None:
    # Default submit without touching preferences uses Cân bằng (mặc định)
    ung_dung.button(key="submit_recommendation").click().run()

    assert not ung_dung.exception
    assert "Kết quả gợi ý" in [muc.value for muc in ung_dung.subheader]

    ket_qua = ung_dung.session_state["motorcycle_recommendation"]
    giai_thich = ung_dung.session_state["motorcycle_explanation"]

    assert len(ket_qua.cac_muc) == 5
    # All 8 supported criteria are active in balanced profile
    assert len(ket_qua.tieu_chi_dang_dung) == 8
    bang_trong_so = pytest.approx(1.0 / 8)
    for tieu_chi in ket_qua.tieu_chi_dang_dung:
        assert tieu_chi.trong_so_chuan_hoa == bang_trong_so

    # Fallback is shown only through vehicle-specific reasons.
    assert giai_thich.nguon == "fallback"
    assert giai_thich.summary == ""
    hien_thi_chu = [muc.value for muc in ung_dung.caption] + [
        muc.value for muc in ung_dung.markdown
    ]
    assert not any("Giải thích cục bộ từ dữ liệu CSV" in chu for chu in hien_thi_chu)
    assert not any("Kết quả KNN được giữ nguyên" in chu for chu in hien_thi_chu)

    # Metrics displayed inline
    assert any(
        chi_so_danh_gia.label == "Xe trong catalog" and chi_so_danh_gia.value == "225"
        for chi_so_danh_gia in ung_dung.metric
    )
    mong_doi_gia = dinh_dang_vnd(ket_qua.cac_muc[0].xe["price_vnd"])
    assert any(
        chi_so_danh_gia.label == "Giá" and chi_so_danh_gia.value == mong_doi_gia
        for chi_so_danh_gia in ung_dung.metric
    )
    assert len(ung_dung.table) == len(ket_qua.cac_muc)


def test_ngan_sach_nhap_hien_thi_day_du_tieng_viet_tien_te_gia_tri(ung_dung: AppTest) -> None:
    ung_dung.checkbox(key="use_budget").set_value(True).run()
    assert any("nấc 100.000 ₫" in chu_thich.value for chu_thich in ung_dung.caption)
    ung_dung.slider(key="budget_slider_vnd").set_value(15_000_000).run()

    assert ung_dung.number_input(key="budget_input_vnd").value == 15_000_000
    assert ung_dung.session_state["max_budget_vnd"] == 15_000_000

    ung_dung.number_input(key="budget_input_vnd").set_value(36_808_360).run()

    assert any(
        chi_so_danh_gia.label == "Mức trần đang áp dụng"
        and chi_so_danh_gia.value == "36.808.360 ₫"
        for chi_so_danh_gia in ung_dung.metric
    )
    assert ung_dung.number_input(key="budget_input_vnd").value == 36_808_360
    assert ung_dung.slider(key="budget_slider_vnd").value == 36_800_000


def test_rong_tuy_chinh_du_phong_luong(ung_dung: AppTest) -> None:
    # User switches to custom profile but leaves priority_keys empty
    ung_dung.segmented_control(key="preference_profile").set_value("custom").run()
    ung_dung.multiselect(key="priority_keys").set_value([]).run()

    assert any(
        "Chưa chọn tiêu chí tùy chỉnh" in chu_thich.value
        for chu_thich in ung_dung.caption
    )

    ung_dung.button(key="submit_recommendation").click().run()

    assert not ung_dung.exception
    # Should not produce error, but fallback to balanced default profile
    assert not ung_dung.error
    assert "Kết quả gợi ý" in [muc.value for muc in ung_dung.subheader]

    ket_qua = ung_dung.session_state["motorcycle_recommendation"]
    assert len(ket_qua.tieu_chi_dang_dung) == 8


def test_tuy_chinh_luong_voi_gia_che_do(ung_dung: AppTest) -> None:
    ung_dung.segmented_control(key="preference_profile").set_value("custom").run()
    ung_dung.multiselect(key="priority_keys").set_value(["price"]).run()

    # Price mode low (default)
    gia_che_do = ung_dung.segmented_control(key="price_mode")
    assert gia_che_do.value == "low"
    assert not any(muc.label == "Giá mục tiêu (VND)" for muc in ung_dung.number_input)

    # Switch to target price mode
    gia_che_do.set_value("target").run()
    assert not ung_dung.exception
    muc_tieu_nhap = ung_dung.number_input(key="criterion_value_price")
    assert muc_tieu_nhap.label == "Giá mục tiêu (VND)"

    muc_tieu_nhap.set_value(40_000_000).run()
    ung_dung.button(key="submit_recommendation").click().run()

    assert not ung_dung.exception
    ket_qua = ung_dung.session_state["motorcycle_recommendation"]
    assert len(ket_qua.tieu_chi_dang_dung) == 1
    assert ket_qua.tieu_chi_dang_dung[0].khoa == "price"
    assert ket_qua.tieu_chi_dang_dung[0].che_do == "target"
    assert ket_qua.tieu_chi_dang_dung[0].gia_tri == pytest.approx(40_000_000)

    # Switch back to low mode
    ung_dung.segmented_control(key="price_mode").set_value("low").run()
    assert not any(muc.label == "Giá mục tiêu (VND)" for muc in ung_dung.number_input)
    assert "criterion_value_price" not in ung_dung.session_state

    ung_dung.button(key="submit_recommendation").click().run()
    ket_qua = ung_dung.session_state["motorcycle_recommendation"]
    assert ket_qua.tieu_chi_dang_dung[0].che_do == "low"
    assert ket_qua.tieu_chi_dang_dung[0].gia_tri is None


def test_cung_loc_hanh_vi(ung_dung: AppTest) -> None:
    ung_dung.checkbox(key="use_budget").set_value(True).run()
    ung_dung.number_input(key="budget_input_vnd").set_value(25_000_000).run()
    ung_dung.selectbox(key="required_fuel_choice").set_value("Xăng").run()

    ung_dung.button(key="submit_recommendation").click().run()

    assert not ung_dung.exception
    ket_qua = ung_dung.session_state["motorcycle_recommendation"]
    assert ket_qua.so_xe_sau_loc > 0
    for muc in ket_qua.cac_muc:
        assert float(muc.xe["price_vnd"]) <= 25_000_000
        assert muc.xe["fuel_type"] == "Xăng"


def test_dat_lai_khoi_phuc_mac_dinh_va_xoa_cac_ket_qua(ung_dung: AppTest) -> None:
    # First submit to get results
    ung_dung.button(key="submit_recommendation").click().run()
    assert "motorcycle_recommendation" in ung_dung.session_state
    assert "Kết quả gợi ý" in [muc.value for muc in ung_dung.subheader]

    # Change some settings
    ung_dung.checkbox(key="use_budget").set_value(True).run()
    ung_dung.segmented_control(key="preference_profile").set_value("custom").run()

    # Click reset
    ung_dung.button(key="reset_inputs").click().run()

    assert not ung_dung.exception
    assert "motorcycle_recommendation" not in ung_dung.session_state
    assert "motorcycle_explanation" not in ung_dung.session_state
    assert "Kết quả gợi ý" not in [muc.value for muc in ung_dung.subheader]
    assert ung_dung.segmented_control(key="preference_profile").value == "balanced"


def test_thieu_khoa_gemini_thao_tac_bao_loi_thong_bao(ung_dung: AppTest) -> None:
    ung_dung.button(key="request_gemini").click().run()

    assert not ung_dung.exception
    assert any(
        "GEMINI_API_KEY trong tệp .env" in thong_bao.value
        for thong_bao in ung_dung.toast
    )
