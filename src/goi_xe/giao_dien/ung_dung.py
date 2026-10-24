"""Giao diện Streamlit tinh gọn: một trang duy nhất, form nhu cầu và kết quả KNN liền kề."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import streamlit as st

from ..cau_hinh import TOP_K_MAC_DINH, lay_duong_dan_danh_muc
from ..dinh_dang import (
    CHU_THIEU,
    chu_hoac_thieu,
    dinh_dang_khoang_cach,
    dinh_dang_nam,
    dinh_dang_so,
    dinh_dang_vnd,
)
from ..du_lieu.cau_truc import LoiCauTrucCsv
from ..du_lieu.nap_du_lieu import DanhMucXe, LoiDuLieuCsv, nap_danh_muc
from ..giai_thich import (
    BoGiaiThichGemini,
    KetQuaGiaiThich,
    lay_khoa_api,
    tao_giai_thich_du_phong,
)
from ..goi_y.tieu_chi import (
    DINH_NGHIA_TIEU_CHI,
    GIA_MUC_TIEU,
    GIA_THAP,
    LoiThieuTieuChi,
    LoiTruyVanKhongHopLe,
    TieuChiMem,
    TruyVanGoiY,
    khoa_tieu_chi_kha_dung,
    tao_tieu_chi_can_bang,
)
from ..goi_y.xep_hang import KetQuaXepHang, XeDuocCham, xep_hang_xe

KHONG_LOC = "Không lọc"
HO_SO_CAN_BANG = "balanced"
HO_SO_TUY_CHINH = "custom"

KHOA_KET_QUA = "motorcycle_recommendation"
KHOA_GIAI_THICH = "motorcycle_explanation"
KHOA_DUONG_DAN_DANH_MUC = "motorcycle_catalog_path"
KHOA_THOI_DIEM_DANH_MUC = "motorcycle_catalog_mtime_ns"
KHOA_LOI = "motorcycle_error"

KHOA_HO_SO_UU_TIEN = "preference_profile"
KHOA_TIEU_CHI_UU_TIEN = "priority_keys"
KHOA_CHE_DO_GIA = "price_mode"
KHOA_DUNG_NGAN_SACH = "use_budget"
KHOA_NGAN_SACH_TOI_DA = "max_budget_vnd"
KHOA_THANH_TRUOT_NGAN_SACH = "budget_slider_vnd"
KHOA_O_NHAP_NGAN_SACH = "budget_input_vnd"
KHOA_CHON_NHIEN_LIEU = "required_fuel_choice"
KHOA_CHON_TINH_TRANG = "required_condition_choice"
KHOA_SO_LUONG_KET_QUA = "result_count"
TIEN_TO_KHOA_GIA_TRI = "criterion_value_"
TIEN_TO_KHOA_TRONG_SO = "criterion_weight_"

NGAN_SACH_TOI_THIEU_VND = 1_000_000
NGAN_SACH_TOI_DA_VND = 2_000_000_000
BUOC_NGAN_SACH_VND = 100_000
NGAN_SACH_MAC_DINH_VND = 40_000_000

KHOA_CO_THE_XOA = (
    KHOA_HO_SO_UU_TIEN,
    KHOA_TIEU_CHI_UU_TIEN,
    KHOA_CHE_DO_GIA,
    KHOA_DUNG_NGAN_SACH,
    KHOA_NGAN_SACH_TOI_DA,
    KHOA_THANH_TRUOT_NGAN_SACH,
    KHOA_O_NHAP_NGAN_SACH,
    KHOA_CHON_NHIEN_LIEU,
    KHOA_CHON_TINH_TRANG,
    KHOA_SO_LUONG_KET_QUA,
    KHOA_KET_QUA,
    KHOA_GIAI_THICH,
    KHOA_LOI,
    KHOA_DUONG_DAN_DANH_MUC,
    KHOA_THOI_DIEM_DANH_MUC,
)


@st.cache_data(ttl=300, max_entries=4, show_spinner=False)
def _nap_danh_muc_tam(duong_dan: str, thoi_diem_sua_ns: int) -> DanhMucXe:
    del thoi_diem_sua_ns
    return nap_danh_muc(duong_dan)


def _thoi_diem_danh_muc(duong_dan: Path) -> int:
    return duong_dan.stat().st_mtime_ns


def _muc_tran_thanh_truot(danh_muc: DanhMucXe, ngan_sach: int) -> int:
    cac_muc_gia = danh_muc.bang["price_vnd"].dropna()
    danh_muc_toi_da = (
        float(cac_muc_gia.max()) if not cac_muc_gia.empty else NGAN_SACH_TOI_THIEU_VND
    )
    mien_toi_da = max(danh_muc_toi_da, ngan_sach)
    buoc = math.ceil((mien_toi_da - NGAN_SACH_TOI_THIEU_VND) / BUOC_NGAN_SACH_VND)
    thanh_truot_toi_da = max(
        NGAN_SACH_TOI_THIEU_VND + BUOC_NGAN_SACH_VND,
        NGAN_SACH_TOI_THIEU_VND + buoc * BUOC_NGAN_SACH_VND,
    )
    return min(NGAN_SACH_TOI_DA_VND, thanh_truot_toi_da)


def _gia_tri_thanh_truot(ngan_sach: int) -> int:
    buoc = round((ngan_sach - NGAN_SACH_TOI_THIEU_VND) / BUOC_NGAN_SACH_VND)
    return min(
        NGAN_SACH_TOI_DA_VND,
        max(NGAN_SACH_TOI_THIEU_VND, NGAN_SACH_TOI_THIEU_VND + buoc * BUOC_NGAN_SACH_VND),
    )


def _dong_bo_ngan_sach_tu_thanh_truot() -> None:
    ngan_sach = int(st.session_state[KHOA_THANH_TRUOT_NGAN_SACH])
    st.session_state[KHOA_NGAN_SACH_TOI_DA] = ngan_sach
    st.session_state[KHOA_O_NHAP_NGAN_SACH] = ngan_sach


def _dong_bo_ngan_sach_tu_o_nhap() -> None:
    ngan_sach = int(st.session_state[KHOA_O_NHAP_NGAN_SACH])
    st.session_state[KHOA_NGAN_SACH_TOI_DA] = ngan_sach
    st.session_state[KHOA_THANH_TRUOT_NGAN_SACH] = _gia_tri_thanh_truot(ngan_sach)


def _lay_khoa_api() -> str | None:
    return lay_khoa_api()


def _xoa_ket_qua_phien() -> None:
    for khoa in (
        KHOA_KET_QUA,
        KHOA_GIAI_THICH,
        KHOA_DUONG_DAN_DANH_MUC,
        KHOA_THOI_DIEM_DANH_MUC,
        KHOA_LOI,
    ):
        st.session_state.pop(khoa, None)


def _dat_lai_trang_thai() -> None:
    for khoa in list(st.session_state):
        if (
            khoa in KHOA_CO_THE_XOA
            or khoa.startswith(TIEN_TO_KHOA_GIA_TRI)
            or khoa.startswith(TIEN_TO_KHOA_TRONG_SO)
        ):
            st.session_state.pop(khoa, None)
    st.session_state[KHOA_HO_SO_UU_TIEN] = HO_SO_CAN_BANG
    st.session_state[KHOA_TIEU_CHI_UU_TIEN] = ["price"]
    st.session_state[KHOA_CHE_DO_GIA] = GIA_THAP


def _ten_hien_thi_xe(xe: Any) -> str:
    brand = chu_hoac_thieu(xe.get("brand"))
    model = chu_hoac_thieu(xe.get("model"))
    if brand == CHU_THIEU:
        return model
    if model == CHU_THIEU:
        return brand
    if model.casefold().startswith(brand.casefold()):
        return model
    return f"{brand} {model}"


def _tao_tieu_chi_tuy_chinh(
    da_chon_cac_khoa: list[str],
    *,
    gia_che_do: str,
) -> tuple[TieuChiMem, ...]:
    tieu_chi: list[TieuChiMem] = []
    for khoa in da_chon_cac_khoa:
        dinh_nghia = DINH_NGHIA_TIEU_CHI[khoa]
        tho_trong_so = st.session_state.get(TIEN_TO_KHOA_TRONG_SO + khoa, dinh_nghia.trong_so)
        try:
            trong_so = float(tho_trong_so)
        except (TypeError, ValueError):
            trong_so = dinh_nghia.trong_so

        if khoa == "price":
            muc_tieu_gia_tri = None
            if gia_che_do == GIA_MUC_TIEU:
                tho_muc_tieu = st.session_state.get(TIEN_TO_KHOA_GIA_TRI + khoa)
                if tho_muc_tieu is not None:
                    try:
                        muc_tieu_gia_tri = float(tho_muc_tieu)
                    except (TypeError, ValueError):
                        muc_tieu_gia_tri = None
            tieu_chi.append(
                TieuChiMem(
                    khoa=khoa,
                    trong_so=trong_so,
                    gia_tri=muc_tieu_gia_tri,
                    che_do=gia_che_do,
                )
            )
            continue

        gia_tri_tho = st.session_state.get(TIEN_TO_KHOA_GIA_TRI + khoa)
        if dinh_nghia.loai in {"numeric", "numeric_min"}:
            gia_tri_so = None
            if gia_tri_tho is not None:
                try:
                    gia_tri_so = float(gia_tri_tho)
                except (TypeError, ValueError):
                    gia_tri_so = None
            tieu_chi.append(TieuChiMem(khoa=khoa, trong_so=trong_so, gia_tri=gia_tri_so))
        else:
            tieu_chi.append(TieuChiMem(khoa=khoa, trong_so=trong_so, gia_tri=gia_tri_tho))
    return tuple(tieu_chi)


def _gui_tu_trang_thai(
    danh_muc: DanhMucXe,
    danh_muc_duong_dan: Path,
    thoi_diem_ns: int,
    *,
    khoa_api: str | None,
) -> None:
    st.session_state.pop(KHOA_LOI, None)

    # 1. Hard filters
    toi_da_gia: float | None = None
    if st.session_state.get(KHOA_DUNG_NGAN_SACH):
        gia_tho = st.session_state.get(KHOA_NGAN_SACH_TOI_DA)
        if gia_tho is not None:
            try:
                toi_da_gia = float(gia_tho)
            except (TypeError, ValueError):
                toi_da_gia = None

    tho_nhien_lieu = st.session_state.get(KHOA_CHON_NHIEN_LIEU)
    dieu_kien_nhien_lieu = (
        None
        if tho_nhien_lieu in (None, KHONG_LOC)
        else str(tho_nhien_lieu).strip() or None
    )

    tinh_trang_tho = st.session_state.get(KHOA_CHON_TINH_TRANG)
    dieu_kien_tinh_trang = (
        None
        if tinh_trang_tho in (None, KHONG_LOC)
        else str(tinh_trang_tho).strip() or None
    )

    # 2. Preference profile
    ho_so = st.session_state.get(KHOA_HO_SO_UU_TIEN, HO_SO_CAN_BANG)
    da_chon_cac_khoa = st.session_state.get(KHOA_TIEU_CHI_UU_TIEN, [])
    gia_che_do = st.session_state.get(KHOA_CHE_DO_GIA, GIA_THAP)

    if ho_so == HO_SO_CAN_BANG or not da_chon_cac_khoa:
        # Fallback to balanced default profile if balanced chosen or custom selection is empty
        tieu_chi = tao_tieu_chi_can_bang(danh_muc)
    else:
        tieu_chi = _tao_tieu_chi_tuy_chinh(da_chon_cac_khoa, gia_che_do=gia_che_do)

    try:
        tho_k = st.session_state.get(KHOA_SO_LUONG_KET_QUA, TOP_K_MAC_DINH)
        k = max(1, int(tho_k))
        truy_van = TruyVanGoiY(
            tieu_chi=tieu_chi,
            gia_toi_da_vnd=toi_da_gia,
            dieu_kien_nhien_lieu=dieu_kien_nhien_lieu,
            dieu_kien_tinh_trang=dieu_kien_tinh_trang,
            k=k,
        )
        ket_qua = xep_hang_xe(danh_muc, truy_van)
    except (LoiThieuTieuChi, LoiTruyVanKhongHopLe) as loi:
        st.session_state[KHOA_LOI] = str(loi)
        _xoa_ket_qua_phien()
        return

    st.session_state[KHOA_KET_QUA] = ket_qua
    st.session_state[KHOA_DUONG_DAN_DANH_MUC] = str(danh_muc_duong_dan)
    st.session_state[KHOA_THOI_DIEM_DANH_MUC] = thoi_diem_ns

    # Compute explanation
    if khoa_api:
        bo_giai_thich = BoGiaiThichGemini(khoa_api=khoa_api)
        st.session_state[KHOA_GIAI_THICH] = bo_giai_thich.giai_thich(ket_qua, truy_van)
    else:
        st.session_state[KHOA_GIAI_THICH] = tao_giai_thich_du_phong(
            ket_qua,
            truy_van,
            None,
        )


def _ve_the_xe(
    muc: XeDuocCham,
    ket_qua: KetQuaXepHang,
    giai_thich: KetQuaGiaiThich,
) -> None:
    xe = muc.xe
    hien_thi_ten = _ten_hien_thi_xe(xe)

    with st.container(border=True, key=f"vehicle_card_{muc.thu_hang}"):
        st.markdown(f"### #{muc.thu_hang:02d}. {hien_thi_ten}")
        st.caption(
            f"Nhiên liệu: {chu_hoac_thieu(xe.get('fuel_type'))} · "
            f"Kiểu xe: {chu_hoac_thieu(xe.get('vehicle_type'))} · "
            f"Tình trạng: {chu_hoac_thieu(xe.get('condition'))} · "
            f"Năm: {dinh_dang_nam(xe.get('year'))}"
        )

        cot_1, cot_2 = st.columns(2, gap="medium")
        cot_1.metric("Giá", dinh_dang_vnd(xe.get("price_vnd")))
        cot_2.metric("Công suất", dinh_dang_so(xe.get("max_power_kw"), hau_to=" kW"))
        cot_3, cot_4 = st.columns(2, gap="medium")
        cot_3.metric(
            "Dung tích cốp", dinh_dang_so(xe.get("boot_capacity_l"), hau_to=" lít")
        )
        cot_4.metric("Khoảng cách", dinh_dang_khoang_cach(muc.khoang_cach))

        ghi_chu = giai_thich.lay_giai_thich(str(xe.get("vehicle_id")))
        if ghi_chu is not None:
            st.markdown("**Vì sao phù hợp**")
            for ly_do in ghi_chu.reasons:
                st.markdown(f"- {ly_do}")
            if ghi_chu.tradeoffs:
                st.markdown("**Cần cân nhắc**")
                for can_nhac in ghi_chu.tradeoffs:
                    st.markdown(f"- {can_nhac}")
        else:
            st.caption("Chưa có nội dung giải thích cho xe này.")

        with st.expander("Chi tiết khoảng cách"):
            st.caption("Khoảng cách càng nhỏ thì xe càng gần tiêu chí ưu tiên.")
            st.table(
                [
                    {
                        "Tiêu chí": tieu_chi.nhan,
                        "Trọng số": f"{tieu_chi.trong_so_chuan_hoa:.1%}",
                        "Khoảng cách": dinh_dang_khoang_cach(
                            muc.khoang_cach_tieu_chi.get(tieu_chi.khoa)
                        ),
                    }
                    for tieu_chi in ket_qua.tieu_chi_dang_dung
                ],
                border="horizontal",
                hide_index=True,
                width="stretch",
            )


def _ve_ket_qua(
    ket_qua: KetQuaXepHang,
    giai_thich: KetQuaGiaiThich,
) -> None:
    st.subheader("Kết quả gợi ý")

    cot_1, cot_2, cot_3 = st.columns(3)
    cot_1.metric("Xe trong catalog", str(ket_qua.tong_danh_muc))
    cot_2.metric("Xe thỏa điều kiện", str(ket_qua.so_xe_sau_loc))
    cot_3.metric("Tiêu chí đang hoạt động", str(len(ket_qua.tieu_chi_dang_dung)))

    trong_so_chu = ", ".join(
        f"{tieu_chi.nhan} {tieu_chi.trong_so_chuan_hoa:.1%}"
        for tieu_chi in ket_qua.tieu_chi_dang_dung
    )
    st.caption(f"Trọng số chuẩn hóa: {trong_so_chu}.")

    if not ket_qua.cac_muc:
        st.warning(
            "Không có xe nào thỏa mãn các điều kiện bắt buộc đã chọn. "
            "Hãy nới ngân sách hoặc thay đổi nhiên liệu/tình trạng."
        )
        return

    if giai_thich.nguon == "gemini":
        st.caption(f"Giải thích bởi Gemini ({giai_thich.model}).")

    if giai_thich.thong_bao_loi:
        st.info(giai_thich.thong_bao_loi)
    if giai_thich.summary:
        st.markdown(giai_thich.summary)

    for muc in ket_qua.cac_muc:
        _ve_the_xe(muc, ket_qua, giai_thich)


def chay_ung_dung() -> None:
    st.set_page_config(
        page_title="Tư vấn chọn xe",
        page_icon=":material/two_wheeler:",
        layout="wide",
    )
    st.markdown(
        """
        <style>
        header[data-testid="stHeader"], [data-testid="stToolbar"] {
            display: none !important;
        }
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
            max-width: 1080px !important;
            width: 100% !important;
        }
        @media (max-width: 640px) {
            .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
        }
        h1, [data-testid="stHeading"] h1 {
            font-size: 26px !important;
            font-weight: 600 !important;
            line-height: 1.3 !important;
            margin-bottom: 0.25rem !important;
        }
        h2, [data-testid="stHeading"] h2 {
            font-size: 20px !important;
            font-weight: 600 !important;
        }
        h3, [data-testid="stHeading"] h3 {
            font-size: 18px !important;
            font-weight: 600 !important;
            margin-top: 1rem !important;
        }
        :root {
            --segmented-selected-bg: #1b6c80;
            --segmented-selected-fg: #ffffff;
            --segmented-focus-outline: #131416;
        }
        [role="radiogroup"] > button[role="radio"][aria-checked="true"] {
            background-color: var(--segmented-selected-bg) !important;
            border-color: var(--segmented-selected-bg) !important;
            color: var(--segmented-selected-fg) !important;
        }
        [role="radiogroup"] > button[role="radio"][aria-checked="true"] p {
            color: var(--segmented-selected-fg) !important;
        }
        [role="radiogroup"] > button[role="radio"][aria-checked="true"]:focus-visible {
            outline: 2px solid var(--segmented-focus-outline) !important;
            outline-offset: 2px !important;
        }
        div[data-testid="stMultiSelect"] [data-baseweb="select"] {
            outline: 2px solid var(--segmented-selected-bg);
            outline-offset: 2px;
            border-radius: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    danh_muc_duong_dan = lay_duong_dan_danh_muc()
    try:
        thoi_diem_ns = _thoi_diem_danh_muc(danh_muc_duong_dan)
        danh_muc = _nap_danh_muc_tam(str(danh_muc_duong_dan), thoi_diem_ns)
    except (LoiDuLieuCsv, LoiCauTrucCsv) as loi:
        st.title("Tư vấn chọn xe")
        st.error(f"Không thể nạp catalog: {loi}")
        st.stop()
    except FileNotFoundError:
        st.title("Tư vấn chọn xe")
        st.error(f"Không tìm thấy tệp CSV: {danh_muc_duong_dan}.")
        st.stop()
    except Exception as loi:
        st.title("Tư vấn chọn xe")
        st.error(f"Không đọc được catalog do lỗi không mong đợi: {loi}")
        st.stop()

    khoa_api = _lay_khoa_api()

    # Cache invalidation check
    da_luu_ket_qua = st.session_state.get(KHOA_KET_QUA)
    da_luu_duong_dan = st.session_state.get(KHOA_DUONG_DAN_DANH_MUC)
    thoi_diem_da_luu = st.session_state.get(KHOA_THOI_DIEM_DANH_MUC)
    if da_luu_ket_qua is not None and (
        da_luu_duong_dan != str(danh_muc_duong_dan) or thoi_diem_da_luu != thoi_diem_ns
    ):
        _xoa_ket_qua_phien()
        da_luu_ket_qua = None

    st.title("Tư vấn chọn xe")
    st.caption(
        f"Chọn ngân sách và tiêu chí để so sánh xe trong danh mục {len(danh_muc)} mẫu."
    )

    thong_bao_loi = st.session_state.get(KHOA_LOI)
    if thong_bao_loi:
        st.error(thong_bao_loi)

    # 1. Điều kiện bắt buộc
    st.subheader("Điều kiện bắt buộc")
    dung_ngan_sach = st.checkbox(
        "Giới hạn ngân sách tối đa", key=KHOA_DUNG_NGAN_SACH
    )
    if dung_ngan_sach:
        ngan_sach_hien_tai = int(
            st.session_state.get(KHOA_NGAN_SACH_TOI_DA, NGAN_SACH_MAC_DINH_VND)
        )
        ngan_sach_hien_tai = min(
            NGAN_SACH_TOI_DA_VND,
            max(NGAN_SACH_TOI_THIEU_VND, ngan_sach_hien_tai),
        )
        thanh_truot_toi_da = _muc_tran_thanh_truot(danh_muc, ngan_sach_hien_tai)
        st.session_state[KHOA_NGAN_SACH_TOI_DA] = ngan_sach_hien_tai
        st.session_state[KHOA_THANH_TRUOT_NGAN_SACH] = _gia_tri_thanh_truot(ngan_sach_hien_tai)
        st.session_state[KHOA_O_NHAP_NGAN_SACH] = ngan_sach_hien_tai

        with st.container(border=True):
            st.slider(
                "Ngân sách tối đa (VND)",
                min_value=NGAN_SACH_TOI_THIEU_VND,
                max_value=thanh_truot_toi_da,
                step=BUOC_NGAN_SACH_VND,
                format="localized",
                key=KHOA_THANH_TRUOT_NGAN_SACH,
                on_change=_dong_bo_ngan_sach_tu_thanh_truot,
            )
            st.caption(
                "Thanh trượt chọn theo nấc 100.000 ₫; "
                "dùng ô bên dưới để nhập số tiền chính xác."
            )
            ngan_sach_nhap, ngan_sach_hien_thi = st.columns(
                [1.25, 1], gap="medium", vertical_alignment="center"
            )
            ngan_sach_nhap.number_input(
                "Nhập chính xác (VND)",
                min_value=NGAN_SACH_TOI_THIEU_VND,
                max_value=NGAN_SACH_TOI_DA_VND,
                step=BUOC_NGAN_SACH_VND,
                help="Xe có giá cao hơn mức này sẽ bị loại khỏi kết quả.",
                key=KHOA_O_NHAP_NGAN_SACH,
                on_change=_dong_bo_ngan_sach_tu_o_nhap,
            )
            ngan_sach_hien_thi.metric(
                "Mức trần đang áp dụng",
                dinh_dang_vnd(st.session_state[KHOA_NGAN_SACH_TOI_DA]),
            )

    cot_nhien_lieu, cot_tinh_trang = st.columns(2)
    with cot_nhien_lieu:
        nhien_lieu_lua_chon = [KHONG_LOC] + danh_muc.gia_tri_danh_muc("fuel_type")
        st.selectbox("Nhiên liệu", options=nhien_lieu_lua_chon, key=KHOA_CHON_NHIEN_LIEU)
    with cot_tinh_trang:
        lua_chon_tinh_trang = [KHONG_LOC] + danh_muc.gia_tri_danh_muc("condition")
        st.selectbox("Tình trạng", options=lua_chon_tinh_trang, key=KHOA_CHON_TINH_TRANG)

    # 2. Tiêu chí ưu tiên
    st.subheader("Tiêu chí ưu tiên")
    ho_so = st.segmented_control(
        "Hồ sơ ưu tiên",
        options=[HO_SO_CAN_BANG, HO_SO_TUY_CHINH],
        format_func=lambda gia_tri: "Mặc định" if gia_tri == HO_SO_CAN_BANG else "Tùy chỉnh",
        default=HO_SO_CAN_BANG,
        key=KHOA_HO_SO_UU_TIEN,
    )

    kha_dung_cac_khoa = khoa_tieu_chi_kha_dung(danh_muc)
    if ho_so == HO_SO_TUY_CHINH:
        da_chon_cac_khoa = st.multiselect(
            "Chọn tiêu chí ưu tiên",
            options=kha_dung_cac_khoa,
            default=st.session_state.get(KHOA_TIEU_CHI_UU_TIEN, ["price"]),
            format_func=lambda k: DINH_NGHIA_TIEU_CHI[k].nhan,
            key=KHOA_TIEU_CHI_UU_TIEN,
        )

        if not da_chon_cac_khoa:
                st.caption(
                "Chưa chọn tiêu chí tùy chỉnh; hệ thống sẽ tự động áp dụng hồ sơ "
                "Mặc định khi gợi ý."
            )
        else:
            if "price" in da_chon_cac_khoa:
                st.segmented_control(
                    "Cách ưu tiên giá",
                    options=[GIA_THAP, GIA_MUC_TIEU],
                    format_func=lambda phan_tu: "Giá thấp"
                    if phan_tu == GIA_THAP
                    else "Gần giá mục tiêu",
                    default=st.session_state.get(KHOA_CHE_DO_GIA, GIA_THAP),
                    key=KHOA_CHE_DO_GIA,
                )
                che_do_hien_tai = st.session_state.get(KHOA_CHE_DO_GIA, GIA_THAP)
                if che_do_hien_tai == GIA_MUC_TIEU:
                    st.caption(
                        "Chế độ Gần giá mục tiêu sẽ xếp xe có giá gần mức mục tiêu nhất lên trước."
                    )
                    st.number_input(
                        "Giá mục tiêu (VND)",
                        min_value=1_000_000,
                        max_value=2_000_000_000,
                        value=st.session_state.get(TIEN_TO_KHOA_GIA_TRI + "price")
                        or 40_000_000,
                        step=1_000_000,
                        key=TIEN_TO_KHOA_GIA_TRI + "price",
                    )
                else:
                    st.caption("Chế độ Giá thấp ưu tiên các xe có giá thấp hơn.")
                    st.session_state.pop(TIEN_TO_KHOA_GIA_TRI + "price", None)

            # Details for non-price selected criteria
            khac_cac_khoa = [k for k in da_chon_cac_khoa if k != "price"]
            if khac_cac_khoa:
                with st.expander("Tùy chỉnh thông số chi tiết"):
                    for khoa in khac_cac_khoa:
                        dinh_nghia = DINH_NGHIA_TIEU_CHI[khoa]
                        st.markdown(f"**{dinh_nghia.nhan}**")
                        if dinh_nghia.loai == "categorical":
                            lua_chon = danh_muc.gia_tri_danh_muc(dinh_nghia.cot)
                            if lua_chon:
                                st.selectbox(
                                    f"Giá trị ưu tiên ({dinh_nghia.nhan})",
                                    options=lua_chon,
                                    key=TIEN_TO_KHOA_GIA_TRI + khoa,
                                )
                        elif dinh_nghia.loai in {"numeric", "numeric_min"}:
                            cac_gia_tri = [
                                float(gia_tri)
                                for gia_tri in danh_muc.bang[dinh_nghia.cot].dropna().tolist()
                                if math.isfinite(float(gia_tri))
                            ]
                            gia_tri_mac_dinh = float(cac_gia_tri[0]) if cac_gia_tri else 0.0
                            nhan = (
                                f"Mức tối thiểu ({dinh_nghia.nhan})"
                                if dinh_nghia.loai == "numeric_min"
                                else f"Mức mong muốn ({dinh_nghia.nhan})"
                            )
                            st.number_input(
                                nhan,
                                value=st.session_state.get(TIEN_TO_KHOA_GIA_TRI + khoa)
                                or gia_tri_mac_dinh,
                                key=TIEN_TO_KHOA_GIA_TRI + khoa,
                            )
    else:
        st.caption(
            "Hồ sơ Mặc định áp dụng trọng số bằng nhau cho tất cả tiêu chí "
            "có trong dữ liệu: giá, kiểu xe, nhiên liệu, công suất, cốp, tình trạng, năm, hãng."
        )

    # 3. K count & Action buttons
    st.number_input(
        "Số lượng xe gợi ý (K)",
        min_value=1,
        max_value=20,
        value=st.session_state.get(KHOA_SO_LUONG_KET_QUA, TOP_K_MAC_DINH),
        step=1,
        key=KHOA_SO_LUONG_KET_QUA,
    )

    cot_nut_1, cot_nut_2, cot_nut_3 = st.columns([1, 1, 1.2])
    with cot_nut_1:
        yeu_cau_gui = st.button(
            "Gợi ý xe",
            type="primary",
            key="submit_recommendation",
        )
    with cot_nut_2:
        st.button(
            "Đặt lại lựa chọn",
            key="reset_inputs",
            on_click=_dat_lai_trang_thai,
        )
    with cot_nut_3:
        if st.button("Giải thích bằng Gemini", key="request_gemini"):
            ket_qua_hien_tai = st.session_state.get(KHOA_KET_QUA)
            if not khoa_api:
                st.toast("Chưa tìm thấy GEMINI_API_KEY trong tệp .env.")
            elif ket_qua_hien_tai is None:
                st.toast("Chạy gợi ý trước để có kết quả cần giải thích.")
            else:
                bo_giai_thich = BoGiaiThichGemini(khoa_api=khoa_api)
                with st.spinner("Đang nhờ Gemini giải thích Top-K..."):
                    da_cap_nhat = bo_giai_thich.giai_thich(
                        ket_qua_hien_tai, ket_qua_hien_tai.truy_van
                    )
                st.session_state[KHOA_GIAI_THICH] = da_cap_nhat
                if da_cap_nhat.thong_bao_loi:
                    st.toast("Không gọi được Gemini; đã dùng giải thích cục bộ.")
                else:
                    st.toast("Đã cập nhật giải thích Gemini cho kết quả hiện tại.")
                st.rerun()

    if yeu_cau_gui:
        with st.spinner("Đang tìm xe phù hợp với lựa chọn của bạn...", show_time=True):
            _gui_tu_trang_thai(
                danh_muc, danh_muc_duong_dan, thoi_diem_ns, khoa_api=khoa_api
            )

    # 4. Inline Results directly below
    da_luu_ket_qua = st.session_state.get(KHOA_KET_QUA)
    giai_thich = st.session_state.get(KHOA_GIAI_THICH)
    if da_luu_ket_qua is not None and giai_thich is not None:
        st.divider()
        _ve_ket_qua(da_luu_ket_qua, giai_thich)
