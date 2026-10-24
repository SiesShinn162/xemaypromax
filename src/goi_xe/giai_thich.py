"""Hợp nhất mô hình, prompt, fallback cục bộ và tích hợp Gemini để giải thích Top-K."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from dotenv import load_dotenv

from .cau_hinh import DUONG_DAN_GOC, lay_mo_hinh_gemini, lay_thoi_gian_cho_gemini
from .dinh_dang import (
    chu_hoac_thieu,
    dinh_dang_khoang_cach,
    dinh_dang_nam,
    dinh_dang_so,
    dinh_dang_vnd,
)
from .du_lieu.cau_truc import NHAN_COT
from .goi_y.tieu_chi import TruyVanGoiY
from .goi_y.xep_hang import KetQuaXepHang, XeDuocCham

try:
    from google import genai
except ImportError:  # pragma: no cover - chỉ xảy ra khi thiếu dependency
    genai = None  # type: ignore[assignment]

NguonGiaiThich = Literal["gemini", "fallback"]

HUONG_DAN_HE_THONG = """Bạn là trợ lý tư vấn xe máy. Chỉ giải thích dựa trên nhu cầu người dùng và
thông tin các xe được cung cấp trong yêu cầu này.

Quy tắc:
- Không bịa giá, công suất, tính năng, mức tiêu hao, độ bền hoặc bảo hành.
- Không thay đổi thứ hạng Top-K do hệ thống cung cấp.
- Với mỗi xe, nêu lý do phù hợp và điểm cần cân nhắc dựa trên dữ liệu.
- Nếu thiếu dữ liệu, nói rõ là chưa có thông tin; không tự suy diễn.
- Không khẳng định xe phù hợp với mục đích/quãng đường nếu dữ liệu không hỗ trợ.
- Trả lời ngắn gọn, trung lập, bằng tiếng Việt có dấu.
- Giữ nguyên vehicle_id và model_name đúng như dữ liệu được cung cấp.
- Trả về JSON đúng schema, không thêm chữ ngoài JSON."""

CAU_TRUC_PHAN_HOI: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "vehicle_id": {"type": "string"},
                    "model_name": {"type": "string"},
                    "reasons": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "tradeoffs": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "vehicle_id",
                    "model_name",
                    "reasons",
                    "tradeoffs",
                ],
            },
        },
        "missing_data": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["summary", "recommendations", "missing_data"],
}

THONG_BAO_THIEU_KHOA_API = "Chưa tìm thấy GEMINI_API_KEY trong tệp .env."
THONG_BAO_PHAN_HOI_LOI = (
    "Gemini trả về JSON không đúng cấu trúc hoặc không khớp Top-K. "
    "Kết quả KNN vẫn được giữ nguyên."
)
THONG_BAO_LOI_API = (
    "Không thể nhận giải thích từ Gemini do lỗi API hoặc kết nối. "
    "Kết quả KNN vẫn được giữ nguyên."
)
THONG_BAO_QUA_THOI_GIAN = (
    "Gemini phản hồi quá thời gian chờ. Kết quả KNN vẫn được giữ nguyên."
)


class LoiGiaiThichKhongHopLe(ValueError):
    """Phản hồi Gemini không đúng cấu trúc hoặc không khớp Top-K."""


@dataclass(frozen=True)
class MucGiaiThich:
    vehicle_id: str
    model_name: str
    reasons: tuple[str, ...]
    tradeoffs: tuple[str, ...]


@dataclass(frozen=True)
class KetQuaGiaiThich:
    summary: str
    cac_muc: dict[str, MucGiaiThich]
    du_lieu_thieu: tuple[str, ...]
    nguon: NguonGiaiThich
    thong_bao_loi: str | None = None
    model: str | None = None

    def lay_giai_thich(self, vehicle_id: str) -> MucGiaiThich | None:
        return self.cac_muc.get(vehicle_id)


def lay_khoa_api() -> str | None:
    load_dotenv(DUONG_DAN_GOC / ".env", override=False)
    khoa = os.environ.get("GEMINI_API_KEY", "").strip()
    return khoa or None


def _la_loi_het_thoi_gian(loi: BaseException) -> bool:
    return isinstance(loi, TimeoutError) or "timeout" in type(loi).__name__.casefold()


def _du_kien_cho_xe(muc: Any) -> dict[str, Any]:
    xe = muc.xe
    return {
        "vehicle_id": xe.get("vehicle_id"),
        "rank": muc.thu_hang,
        "model_name": xe.get("model"),
        "brand": xe.get("brand"),
        "price_vnd": xe.get("price_vnd"),
        "max_power_kw": xe.get("max_power_kw"),
        "fuel_type": xe.get("fuel_type"),
        "vehicle_type": xe.get("vehicle_type"),
        "boot_capacity_l": xe.get("boot_capacity_l"),
        "condition": xe.get("condition"),
        "year": xe.get("year"),
        "distance": round(muc.khoang_cach, 6),
        "missing_fields": list(muc.truong_thieu),
    }


def tao_goi_giai_thich(
    ket_qua: KetQuaXepHang,
    truy_van: TruyVanGoiY,
) -> dict[str, Any]:
    """Chỉ đóng gói dữ liệu thật của Top-K, không gửi toàn bộ catalog."""

    return {
        "user_needs": {
            "max_price_vnd": truy_van.gia_toi_da_vnd,
            "required_fuel": truy_van.dieu_kien_nhien_lieu,
            "required_condition": truy_van.dieu_kien_tinh_trang,
            "k": truy_van.k,
            "priorities": [
                {
                    "key": tieu_chi.khoa,
                    "label": tieu_chi.nhan,
                    "value": tieu_chi.gia_tri,
                    "mode": tieu_chi.che_do,
                    "normalized_weight": round(tieu_chi.trong_so_chuan_hoa, 6),
                }
                for tieu_chi in ket_qua.tieu_chi_dang_dung
            ],
        },
        "top_k": [_du_kien_cho_xe(muc) for muc in ket_qua.cac_muc],
    }


def tao_loi_nhac_giai_thich(goi_du_lieu: Mapping[str, Any]) -> str:
    return (
        "Giải thích kết quả gợi ý dưới đây. Chỉ dùng đúng dữ liệu trong JSON này; "
        "không thêm thông số ngoài dữ liệu. Không đổi thứ hạng.\n\n"
        + json.dumps(goi_du_lieu, ensure_ascii=False, indent=2, allow_nan=False)
    )


def _bo_hang_rao_ma(chu: str) -> str:
    da_cat = chu.strip()
    if not da_cat.startswith("```"):
        return da_cat
    da_cat = re.sub(r"^```(?:json)?\s*", "", da_cat, flags=re.IGNORECASE)
    da_cat = re.sub(r"\s*```$", "", da_cat)
    return da_cat.strip()


def _yeu_cau_chuoi(gia_tri: Any, truong_ten: str) -> str:
    if not isinstance(gia_tri, str) or not gia_tri.strip():
        raise LoiGiaiThichKhongHopLe(
            f"Trường '{truong_ten}' phải là chuỗi không rỗng."
        )
    return gia_tri.strip()


def _yeu_cau_danh_sach_chuoi(gia_tri: Any, truong_ten: str) -> tuple[str, ...]:
    if not isinstance(gia_tri, list):
        raise LoiGiaiThichKhongHopLe(f"Trường '{truong_ten}' phải là danh sách.")
    ket_qua: list[str] = []
    for phan_tu in gia_tri:
        if not isinstance(phan_tu, str) or not phan_tu.strip():
            raise LoiGiaiThichKhongHopLe(
                f"Trường '{truong_ten}' chỉ được chứa chuỗi không rỗng."
            )
        ket_qua.append(phan_tu.strip())
    return tuple(ket_qua)


def doc_json_giai_thich(
    chu: str,
    mong_doi_cac_muc: Mapping[str, str],
) -> KetQuaGiaiThich:
    """Kiểm tra JSON và ánh xạ giải thích theo vehicle_id của Top-K."""

    if not isinstance(chu, str) or not chu.strip():
        raise LoiGiaiThichKhongHopLe("Gemini không trả về nội dung JSON.")
    try:
        goi_du_lieu = json.loads(_bo_hang_rao_ma(chu))
    except json.JSONDecodeError as loi:
        raise LoiGiaiThichKhongHopLe("Gemini trả về JSON không hợp lệ.") from loi

    if not isinstance(goi_du_lieu, dict):
        raise LoiGiaiThichKhongHopLe("Phản hồi Gemini phải là một đối tượng JSON.")

    summary = _yeu_cau_chuoi(goi_du_lieu.get("summary"), "summary")
    cac_goi_y = goi_du_lieu.get("recommendations")
    if not isinstance(cac_goi_y, list):
        raise LoiGiaiThichKhongHopLe("Trường 'recommendations' phải là danh sách.")
    du_lieu_thieu = _yeu_cau_danh_sach_chuoi(goi_du_lieu.get("missing_data"), "missing_data")

    mong_doi_ma = set(mong_doi_cac_muc)
    da_nhan: dict[str, MucGiaiThich] = {}
    for phan_tu in cac_goi_y:
        if not isinstance(phan_tu, dict):
            raise LoiGiaiThichKhongHopLe(
                "Mỗi phần tử 'recommendations' phải là một đối tượng."
            )
        vehicle_id = _yeu_cau_chuoi(phan_tu.get("vehicle_id"), "vehicle_id")
        model_name = _yeu_cau_chuoi(phan_tu.get("model_name"), "model_name")
        if vehicle_id not in mong_doi_ma:
            raise LoiGiaiThichKhongHopLe(
                f"Gemini trả về vehicle_id không có trong Top-K: '{vehicle_id}'."
            )
        if vehicle_id in da_nhan:
            raise LoiGiaiThichKhongHopLe(
                f"Gemini trả về vehicle_id bị lặp: '{vehicle_id}'."
            )
        mo_hinh_mong_doi = mong_doi_cac_muc[vehicle_id]
        if model_name != mo_hinh_mong_doi:
            raise LoiGiaiThichKhongHopLe(
                f"model_name không khớp dữ liệu cho '{vehicle_id}'."
            )
        reasons = _yeu_cau_danh_sach_chuoi(phan_tu.get("reasons"), "reasons")
        tradeoffs = _yeu_cau_danh_sach_chuoi(phan_tu.get("tradeoffs"), "tradeoffs")
        if not reasons:
            raise LoiGiaiThichKhongHopLe(
                f"Xe '{vehicle_id}' cần có ít nhất một lý do phù hợp."
            )
        da_nhan[vehicle_id] = MucGiaiThich(
            vehicle_id=vehicle_id,
            model_name=model_name,
            reasons=reasons,
            tradeoffs=tradeoffs,
        )

    thieu_ma = mong_doi_ma - set(da_nhan)
    if thieu_ma:
        raise LoiGiaiThichKhongHopLe(
            "Gemini bỏ sót xe trong Top-K: " + ", ".join(sorted(thieu_ma)) + "."
        )

    return KetQuaGiaiThich(
        summary=summary,
        cac_muc=da_nhan,
        du_lieu_thieu=du_lieu_thieu,
        nguon="gemini",
    )


def _ly_do_cho_xe(
    muc: XeDuocCham,
    ket_qua: KetQuaXepHang,
    truy_van: TruyVanGoiY,
) -> list[str]:
    xe = muc.xe
    reasons = [
        f"Xếp hạng #{muc.thu_hang} theo khoảng cách Euclid có trọng số "
        f"{dinh_dang_khoang_cach(muc.khoang_cach)} (nhỏ hơn là gần hơn)."
    ]

    if truy_van.gia_toi_da_vnd is not None and xe.get("price_vnd") is not None:
        reasons.append(
            f"Giá {dinh_dang_vnd(xe['price_vnd'])} không vượt ngân sách "
            f"{dinh_dang_vnd(truy_van.gia_toi_da_vnd)}."
        )
    if truy_van.dieu_kien_nhien_lieu and xe.get("fuel_type") is not None:
        reasons.append(
            f"Nhiên liệu {chu_hoac_thieu(xe['fuel_type'])} đúng điều kiện bắt buộc."
        )
    if truy_van.dieu_kien_tinh_trang and xe.get("condition") is not None:
        reasons.append(
            f"Tình trạng {chu_hoac_thieu(xe['condition'])} đúng điều kiện bắt buộc."
        )

    for tieu_chi in ket_qua.tieu_chi_dang_dung:
        gia_tri = xe.get(
            {
                "price": "price_vnd",
                "vehicle_type": "vehicle_type",
                "fuel_type": "fuel_type",
                "max_power_kw": "max_power_kw",
                "boot_capacity_l": "boot_capacity_l",
                "condition": "condition",
                "year": "year",
                "brand": "brand",
            }.get(tieu_chi.khoa, tieu_chi.khoa)
        )
        if gia_tri is None:
            continue
        if tieu_chi.khoa == "price":
            if tieu_chi.che_do == "target":
                reasons.append(
                    f"Giá {dinh_dang_vnd(gia_tri)} được đối chiếu với giá mục tiêu "
                    f"{dinh_dang_vnd(tieu_chi.gia_tri)}."
                )
            else:
                reasons.append(
                    f"Giá {dinh_dang_vnd(gia_tri)} thuộc tiêu chí ưu tiên giá thấp."
                )
        elif tieu_chi.khoa == "max_power_kw":
            reasons.append(
                f"Công suất {dinh_dang_so(gia_tri, chu_so=1, hau_to=' kW')} được đối chiếu "
                f"với mức mong muốn {dinh_dang_so(tieu_chi.gia_tri, chu_so=1, hau_to=' kW')}."
            )
        elif tieu_chi.khoa == "boot_capacity_l":
            toi_thieu = float(tieu_chi.gia_tri)
            if float(gia_tri) >= toi_thieu:
                reasons.append(
                    f"Cốp {dinh_dang_so(gia_tri, chu_so=1, hau_to=' lít')} đạt mức tối thiểu "
                    f"{dinh_dang_so(toi_thieu, chu_so=1, hau_to=' lít')}."
                )
            else:
                reasons.append(
                    f"Cốp {dinh_dang_so(gia_tri, chu_so=1, hau_to=' lít')} thấp hơn mức tối thiểu "
                    f"{dinh_dang_so(toi_thieu, chu_so=1, hau_to=' lít')}; khoảng cách đã bị phạt."
                )
        elif tieu_chi.khoa == "year":
            toi_thieu = int(float(tieu_chi.gia_tri))
            if int(float(gia_tri)) >= toi_thieu:
                reasons.append(
                    f"Năm sản xuất {dinh_dang_nam(gia_tri)} đạt mức tối thiểu {toi_thieu}."
                )
            else:
                reasons.append(
                    f"Năm sản xuất {dinh_dang_nam(gia_tri)} thấp hơn mức tối thiểu {toi_thieu}; "
                    "khoảng cách đã bị phạt."
                )
        else:
            reasons.append(
                f"Giá trị {chu_hoac_thieu(gia_tri)} thuộc tiêu chí {tieu_chi.nhan}."
            )

    return reasons


def _diem_can_nhac_cho_xe(muc: XeDuocCham) -> list[str]:
    tradeoffs: list[str] = []
    if muc.truong_thieu:
        cac_nhan = [NHAN_COT.get(field, field) for field in muc.truong_thieu]
        tradeoffs.append("Chưa có dữ liệu: " + ", ".join(cac_nhan) + ".")
    if "price_vnd" in muc.truong_thieu:
        tradeoffs.append("Chưa thể đối chiếu ngân sách vì CSV thiếu giá của xe này.")
    if "max_power_kw" in muc.truong_thieu:
        tradeoffs.append("Chưa thể đối chiếu công suất vì CSV thiếu thông số của xe này.")
    return tradeoffs


def tao_giai_thich_du_phong(
    ket_qua: KetQuaXepHang,
    truy_van: TruyVanGoiY,
    thong_bao_loi: str | None,
) -> KetQuaGiaiThich:
    cac_muc: dict[str, MucGiaiThich] = {}
    thieu_cac_nhan: set[str] = set()
    for muc in ket_qua.cac_muc:
        xe = muc.xe
        thieu_cac_nhan.update(
            NHAN_COT.get(field, field) for field in muc.truong_thieu
        )
        cac_muc[xe["vehicle_id"]] = MucGiaiThich(
            vehicle_id=xe["vehicle_id"],
            model_name=xe["model"],
            reasons=tuple(_ly_do_cho_xe(muc, ket_qua, truy_van)),
            tradeoffs=tuple(_diem_can_nhac_cho_xe(muc)),
        )

    return KetQuaGiaiThich(
        summary="",
        cac_muc=cac_muc,
        du_lieu_thieu=tuple(sorted(thieu_cac_nhan)),
        nguon="fallback",
        thong_bao_loi=thong_bao_loi,
    )


class BoGiaiThichGemini:
    def __init__(
        self,
        *,
        khoa_api: str | None = None,
        model: str | None = None,
        thoi_gian_cho_giay: float | None = None,
        khach: Any | None = None,
    ) -> None:
        self.khoa_api = khoa_api if khoa_api is not None else lay_khoa_api()
        self.model = model or lay_mo_hinh_gemini()
        self.thoi_gian_cho_giay = (
            thoi_gian_cho_giay
            if thoi_gian_cho_giay is not None
            else lay_thoi_gian_cho_gemini()
        )
        self._khach = khach

    def giai_thich(
        self,
        ket_qua: KetQuaXepHang,
        truy_van: TruyVanGoiY,
    ) -> KetQuaGiaiThich:
        if not ket_qua.cac_muc:
            return tao_giai_thich_du_phong(
                ket_qua,
                truy_van,
                "Không có kết quả Top-K để giải thích.",
            )
        if self._khach is None and not self.khoa_api:
            return tao_giai_thich_du_phong(ket_qua, truy_van, THONG_BAO_THIEU_KHOA_API)
        if self._khach is None and genai is None:
            return tao_giai_thich_du_phong(
                ket_qua,
                truy_van,
                "Chưa cài đặt google-genai. Kết quả KNN vẫn được giữ nguyên.",
            )

        goi_du_lieu = tao_goi_giai_thich(ket_qua, truy_van)
        loi_nhac = tao_loi_nhac_giai_thich(goi_du_lieu)
        mong_doi = {
            muc.xe["vehicle_id"]: muc.xe["model"]
            for muc in ket_qua.cac_muc
        }

        try:
            khach = self._khach
            if khach is None:
                khach = genai.Client(api_key=self.khoa_api)
            tuong_tac = khach.interactions.create(
                model=self.model,
                system_instruction=HUONG_DAN_HE_THONG,
                input=loi_nhac,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": CAU_TRUC_PHAN_HOI,
                },
                store=False,
                timeout=self.thoi_gian_cho_giay,
            )
            chu = getattr(tuong_tac, "output_text", None)
            if not chu:
                raise LoiGiaiThichKhongHopLe(
                    "Gemini không trả về nội dung văn bản JSON."
                )
            da_doc = doc_json_giai_thich(chu, mong_doi)
            return KetQuaGiaiThich(
                summary=da_doc.summary,
                cac_muc=da_doc.cac_muc,
                du_lieu_thieu=da_doc.du_lieu_thieu,
                nguon="gemini",
                thong_bao_loi=None,
                model=self.model,
            )
        except LoiGiaiThichKhongHopLe:
            return tao_giai_thich_du_phong(ket_qua, truy_van, THONG_BAO_PHAN_HOI_LOI)
        except Exception as loi:
            if _la_loi_het_thoi_gian(loi):
                return tao_giai_thich_du_phong(ket_qua, truy_van, THONG_BAO_QUA_THOI_GIAN)
            return tao_giai_thich_du_phong(ket_qua, truy_van, THONG_BAO_LOI_API)
