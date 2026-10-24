"""Chuẩn hóa văn bản, số liệu theo định dạng Việt Nam và danh mục xe."""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Any

TU_THIEU = {
    "",
    "-",
    "--",
    "—",
    "nan",
    "none",
    "null",
    "n/a",
    "n a",
    "na",
    "khong co",
    "chua co",
    "khong ro",
    "khong ap dung",
}

_MAU_TIEN_TE = re.compile(r"(vnđ|vnd|₫|đồng|dong|usd|\$)", re.IGNORECASE)
_MAU_DON_VI = re.compile(r"(?<![a-z])(kw|lít|lit|l)(?![a-z])", re.IGNORECASE)
_MAU_DON_VI_CONG_SUAT = re.compile(r"(?<![a-z])(kw|w)(?![a-z])", re.IGNORECASE)


def chuan_hoa_khoa(gia_tri: Any) -> str:
    """Bỏ dấu, hạ chữ thường và gom khoảng trắng để so khớp khóa."""

    chu = "" if gia_tri is None else str(gia_tri)
    chu = chu.replace("đ", "d").replace("Đ", "D")
    chu = unicodedata.normalize("NFKD", chu)
    chu = "".join(ky_tu for ky_tu in chu if not unicodedata.combining(ky_tu))
    chu = chu.casefold().replace("đ", "d")
    chu = re.sub(r"[^a-z0-9]+", " ", chu)
    return " ".join(chu.split())


def chuan_hoa_tieu_de(gia_tri: Any) -> str:
    return chuan_hoa_khoa(gia_tri)


def la_gia_tri_thieu(gia_tri: Any) -> bool:
    if gia_tri is None:
        return True
    if isinstance(gia_tri, float) and math.isnan(gia_tri):
        return True
    if isinstance(gia_tri, str):
        return chuan_hoa_khoa(gia_tri) in TU_THIEU
    return False


def lam_sach_chu(gia_tri: Any) -> str | None:
    if la_gia_tri_thieu(gia_tri):
        return None
    chu = unicodedata.normalize("NFC", str(gia_tri))
    chu = chu.replace("\u00a0", " ")
    return " ".join(chu.split())


def _chuan_hoa_dau_phan_tach(chu: str, *, uu_tien_thap_phan_mot_dau_cham: bool) -> str:
    if "," in chu and "." in chu:
        if chu.rfind(",") > chu.rfind("."):
            return chu.replace(".", "").replace(",", ".")
        return chu.replace(",", "")

    if "," in chu:
        cac_phan = chu.split(",")
        if len(cac_phan) == 2 and 1 <= len(cac_phan[1]) <= 2:
            return chu.replace(",", ".")
        return chu.replace(",", "")

    if "." in chu:
        cac_phan = chu.split(".")
        if len(cac_phan) > 2:
            if all(len(phan) == 3 for phan in cac_phan[1:]):
                return chu.replace(".", "")
            return "".join(cac_phan[:-1]) + "." + cac_phan[-1]
        if len(cac_phan) == 2 and len(cac_phan[1]) == 3 and not uu_tien_thap_phan_mot_dau_cham:
            return chu.replace(".", "")

    return chu


def doc_so_dinh_dang_dia_phuong(
    gia_tri: Any,
    *,
    uu_tien_thap_phan_mot_dau_cham: bool = True,
) -> float | None:
    """Đọc số có dấu chấm nghìn, dấu phẩy thập phân hoặc ngược lại."""

    chu = lam_sach_chu(gia_tri)
    if chu is None:
        return None

    chu = chu.casefold()
    chu = _MAU_TIEN_TE.sub(" ", chu)
    chu = _MAU_DON_VI.sub(" ", chu)
    chu = chu.replace("\u00a0", " ").replace(" ", "")
    chu = re.sub(r"[^0-9,.\-+]", "", chu)
    if not chu or not re.search(r"\d", chu):
        return None

    dau = ""
    if chu[0] in "+-":
        dau, chu = chu[0], chu[1:]
    if not chu:
        return None

    chu = _chuan_hoa_dau_phan_tach(
        chu,
        uu_tien_thap_phan_mot_dau_cham=uu_tien_thap_phan_mot_dau_cham,
    )
    try:
        so = float(f"{dau}{chu}")
    except ValueError:
        return None
    if not math.isfinite(so):
        return None
    return so


def doc_gia_vnd(gia_tri: Any) -> int | None:
    so = doc_so_dinh_dang_dia_phuong(gia_tri, uu_tien_thap_phan_mot_dau_cham=False)
    if so is None or so <= 0:
        return None
    return int(round(so))


def doc_cong_suat_kw(gia_tri: Any, *, nguon_don_vi: str = "kW") -> float | None:
    chu = lam_sach_chu(gia_tri)
    if chu is None:
        return None

    nhan_dien_don_vi = nguon_don_vi
    ket_qua_tim_kiem = _MAU_DON_VI_CONG_SUAT.search(chuan_hoa_khoa(chu))
    if ket_qua_tim_kiem:
        nhan_dien_don_vi = "kW" if ket_qua_tim_kiem.group(1).casefold() == "kw" else "W"

    so = doc_so_dinh_dang_dia_phuong(
        chu,
        uu_tien_thap_phan_mot_dau_cham=nhan_dien_don_vi != "W",
    )
    if so is None or so <= 0:
        return None
    if nhan_dien_don_vi == "W":
        so /= 1000.0
    return so


def doc_dung_tich_cop_l(gia_tri: Any) -> float | None:
    so = doc_so_dinh_dang_dia_phuong(gia_tri, uu_tien_thap_phan_mot_dau_cham=True)
    if so is None or so < 0:
        return None
    return so


def doc_nam_sx(gia_tri: Any) -> int | None:
    so = doc_so_dinh_dang_dia_phuong(gia_tri, uu_tien_thap_phan_mot_dau_cham=False)
    if so is None:
        return None
    year = int(round(so))
    if 1900 <= year <= 2100:
        return year
    return None


def chuan_hoa_nhien_lieu(gia_tri: Any) -> str | None:
    chu = lam_sach_chu(gia_tri)
    if chu is None:
        return None
    khoa = chuan_hoa_khoa(chu)
    da_biet = {
        "xang": "Xăng",
        "xang dien": "Hybrid",
        "hybrid": "Hybrid",
        "dien": "Điện",
        "dau": "Dầu",
        "dau diesel": "Dầu diesel",
        "diesel": "Dầu diesel",
    }
    return da_biet.get(khoa, chu)


def chuan_hoa_loai_xe(gia_tri: Any) -> str | None:
    chu = lam_sach_chu(gia_tri)
    if chu is None:
        return None
    khoa = chuan_hoa_khoa(chu)
    if khoa.startswith("xe "):
        khoa = khoa[3:]
    da_biet = {
        "tay ga": "Xe tay ga",
        "tay ga 50cc": "Xe tay ga (50cc)",
        "so": "Xe số",
        "so 50cc": "Xe số (50cc)",
        "con tay": "Xe côn tay",
        "dien": "Xe điện",
        "phan khoi lon": "Xe phân khối lớn",
    }
    return da_biet.get(khoa, chu)


def chuan_hoa_tinh_trang(gia_tri: Any) -> str | None:
    chu = lam_sach_chu(gia_tri)
    if chu is None:
        return None
    da_biet = {
        "moi": "Mới",
        "xe moi": "Mới",
        "new": "Mới",
        "cu": "Cũ",
        "xe cu": "Cũ",
        "da qua su dung": "Cũ",
        "used": "Cũ",
    }
    return da_biet.get(chuan_hoa_khoa(chu), chu)
