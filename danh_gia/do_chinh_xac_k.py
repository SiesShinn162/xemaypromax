"""Harness và CLI đánh giá ranking xe máy bằng duy nhất Precision@K."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from goi_xe.cau_hinh import lay_duong_dan_danh_muc
from goi_xe.du_lieu.cau_truc import LoiCauTrucCsv
from goi_xe.du_lieu.nap_du_lieu import DanhMucXe, LoiDuLieuCsv, nap_danh_muc
from goi_xe.goi_y.tieu_chi import (
    GIA_MUC_TIEU,
    GIA_THAP,
    LoiTruyVanKhongHopLe,
    TieuChiMem,
    TruyVanGoiY,
)
from goi_xe.goi_y.xep_hang import KetQuaXepHang, xep_hang_xe

BoXepHang = Callable[[DanhMucXe, TruyVanGoiY], KetQuaXepHang]


class LoiDuLieuDanhGia(ValueError):
    """Dữ liệu đánh giá không hợp lệ."""


@dataclass(frozen=True)
class TruyVanDanhGia:
    ma_truy_van: str
    truy_van_goi_y: TruyVanGoiY
    ma_xe_phu_hop: frozenset[str]
    can_cu_gan_nhan: str


@dataclass(frozen=True)
class DongDanhGia:
    ma_truy_van: str
    k: int
    ma_xe_goi_y: tuple[str, ...]
    ma_xe_phu_hop_trong_top_k: tuple[str, ...]
    do_chinh_xac_k: float
    so_xe_sau_loc: int


@dataclass(frozen=True)
class BaoCaoDanhGia:
    cac_dong: tuple[DongDanhGia, ...]
    trung_binh_do_chinh_xac_k: float

    def sang_tu_dien(self) -> dict[str, Any]:
        return {
            "metric": "Precision@K",
            "mean_precision_at_k": self.trung_binh_do_chinh_xac_k,
            "queries": [
                {
                    "query_id": dong.ma_truy_van,
                    "k": dong.k,
                    "recommended_ids": list(dong.ma_xe_goi_y),
                    "relevant_ids_in_top_k": list(dong.ma_xe_phu_hop_trong_top_k),
                    "precision_at_k": dong.do_chinh_xac_k,
                    "candidates_after_filters": dong.so_xe_sau_loc,
                }
                for dong in self.cac_dong
            ],
        }


def do_chinh_xac_k(
    ma_xe_goi_y: Sequence[str],
    phu_hop_ma: Iterable[str],
    k: int,
) -> float:
    """Số xe phù hợp trong K vị trí đầu chia cho K, kể cả khi thiếu kết quả."""

    if k < 1:
        raise ValueError("K phải lớn hơn hoặc bằng 1.")
    phu_hop = set(phu_hop_ma)
    top_k = list(ma_xe_goi_y)[:k]
    trung = sum(1 for vehicle_id in top_k if vehicle_id in phu_hop)
    return trung / k


def tinh_danh_gia_truy_van(
    danh_muc: DanhMucXe,
    cac_truy_van: Sequence[TruyVanDanhGia],
    *,
    bo_xep_hang: BoXepHang = xep_hang_xe,
) -> BaoCaoDanhGia:
    if not cac_truy_van:
        raise LoiDuLieuDanhGia("Danh sách truy vấn đánh giá đang trống.")
    truy_van_ma = [truy_van.ma_truy_van for truy_van in cac_truy_van]
    if len(truy_van_ma) != len(set(truy_van_ma)):
        raise LoiDuLieuDanhGia("Các truy vấn đánh giá có id bị trùng.")

    danh_muc_ma = set(danh_muc.bang["vehicle_id"].astype(str))
    cac_dong: list[DongDanhGia] = []
    for truy_van in cac_truy_van:
        if not truy_van.can_cu_gan_nhan.strip():
            raise LoiDuLieuDanhGia(
                f"Truy vấn '{truy_van.ma_truy_van}' thiếu căn cứ gán nhãn (label_basis)."
            )
        khong_biet = set(truy_van.ma_xe_phu_hop) - danh_muc_ma
        if khong_biet:
            raise LoiDuLieuDanhGia(
                f"Truy vấn '{truy_van.ma_truy_van}' có vehicle_id không tồn tại trong catalog: "
                + ", ".join(sorted(khong_biet))
            )
        try:
            xep_hang = bo_xep_hang(danh_muc, truy_van.truy_van_goi_y)
        except LoiTruyVanKhongHopLe as loi:
            raise LoiDuLieuDanhGia(
                f"Truy vấn '{truy_van.ma_truy_van}' không thể xếp hạng: {loi}"
            ) from loi
        duoc_goi_y = list(xep_hang.ma_xe_top_k)
        ma_phu_hop_trong_top = tuple(
            vehicle_id for vehicle_id in duoc_goi_y if vehicle_id in truy_van.ma_xe_phu_hop
        )
        cac_dong.append(
            DongDanhGia(
                ma_truy_van=truy_van.ma_truy_van,
                k=truy_van.truy_van_goi_y.k,
                ma_xe_goi_y=tuple(duoc_goi_y),
                ma_xe_phu_hop_trong_top_k=ma_phu_hop_trong_top,
                do_chinh_xac_k=do_chinh_xac_k(
                    duoc_goi_y,
                    truy_van.ma_xe_phu_hop,
                    truy_van.truy_van_goi_y.k,
                ),
                so_xe_sau_loc=xep_hang.so_xe_sau_loc,
            )
        )

    trung_binh = sum(dong.do_chinh_xac_k for dong in cac_dong) / len(cac_dong)
    return BaoCaoDanhGia(cac_dong=tuple(cac_dong), trung_binh_do_chinh_xac_k=trung_binh)


def _doc_tieu_chi_mem(tho: Any, ma_truy_van: str) -> tuple[TieuChiMem, ...]:
    if not isinstance(tho, list) or not tho:
        raise LoiDuLieuDanhGia(
            f"Truy vấn '{ma_truy_van}' phải có danh sách 'criteria' không rỗng."
        )
    tieu_chi: list[TieuChiMem] = []
    for phan_tu in tho:
        if not isinstance(phan_tu, dict):
            raise LoiDuLieuDanhGia(
                f"Truy vấn '{ma_truy_van}' có phần tử 'criteria' không hợp lệ."
            )
        khoa = phan_tu.get("key")
        trong_so = phan_tu.get("weight")
        che_do = phan_tu.get("mode")
        if not isinstance(khoa, str) or not khoa.strip():
            raise LoiDuLieuDanhGia(
                f"Truy vấn '{ma_truy_van}' có tiêu chí thiếu khóa 'key'."
            )
        khoa = khoa.strip()
        if not isinstance(trong_so, (int, float)) or isinstance(trong_so, bool):
            raise LoiDuLieuDanhGia(
                f"Truy vấn '{ma_truy_van}' có trọng số không phải số cho '{khoa}'."
            )
        try:
            trong_so_gia_tri = float(trong_so)
        except (OverflowError, TypeError, ValueError) as loi:
            raise LoiDuLieuDanhGia(
                f"Truy vấn '{ma_truy_van}' có trọng số không hợp lệ cho '{khoa}'."
            ) from loi
        if not math.isfinite(trong_so_gia_tri) or trong_so_gia_tri <= 0:
            raise LoiDuLieuDanhGia(
                f"Truy vấn '{ma_truy_van}' có trọng số phải là số hữu hạn dương cho '{khoa}'."
            )
        if che_do is not None and che_do not in {GIA_THAP, GIA_MUC_TIEU}:
            raise LoiDuLieuDanhGia(
                f"Truy vấn '{ma_truy_van}' có mode giá không hợp lệ: '{che_do}'."
            )
        if che_do is not None and khoa != "price":
            raise LoiDuLieuDanhGia(
                f"Truy vấn '{ma_truy_van}' chỉ được dùng 'mode' cho tiêu chí price."
            )
        tieu_chi.append(
            TieuChiMem(
                khoa=khoa,
                trong_so=trong_so_gia_tri,
                gia_tri=phan_tu.get("value"),
                che_do=che_do,
            )
        )
    return tuple(tieu_chi)


def nap_truy_van_danh_gia(duong_dan: str | Path) -> tuple[TruyVanDanhGia, ...]:
    nguon = Path(duong_dan)
    if not nguon.exists():
        raise LoiDuLieuDanhGia(f"Không tìm thấy tệp truy vấn: {nguon}.")
    try:
        chu = nguon.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as loi:
        raise LoiDuLieuDanhGia(f"Không đọc được tệp truy vấn: {nguon}.") from loi
    try:
        goi_du_lieu = json.loads(chu)
    except json.JSONDecodeError as loi:
        raise LoiDuLieuDanhGia("Tệp truy vấn không phải JSON hợp lệ.") from loi
    if not isinstance(goi_du_lieu, dict) or not isinstance(goi_du_lieu.get("queries"), list):
        raise LoiDuLieuDanhGia("Tệp truy vấn phải là JSON có khóa 'queries' là danh sách.")

    cac_truy_van: list[TruyVanDanhGia] = []
    for phan_tu in goi_du_lieu["queries"]:
        if not isinstance(phan_tu, dict):
            raise LoiDuLieuDanhGia("Mỗi truy vấn phải là một đối tượng JSON.")
        ma_truy_van = phan_tu.get("id")
        if not isinstance(ma_truy_van, str) or not ma_truy_van.strip():
            raise LoiDuLieuDanhGia("Mỗi truy vấn cần có 'id' không rỗng.")
        ma_truy_van = ma_truy_van.strip()
        k = phan_tu.get("k")
        if not isinstance(k, int) or isinstance(k, bool) or k < 1:
            raise LoiDuLieuDanhGia(
                f"Truy vấn '{ma_truy_van}' cần 'k' là số nguyên dương."
            )
        cung_loc = phan_tu.get("hard_filters", {})
        if not isinstance(cung_loc, dict):
            raise LoiDuLieuDanhGia(
                f"Truy vấn '{ma_truy_van}' có 'hard_filters' không hợp lệ."
            )
        khong_biet_loc = set(cung_loc) - {
            "max_price_vnd",
            "required_fuel",
            "required_condition",
        }
        if khong_biet_loc:
            raise LoiDuLieuDanhGia(
                f"Truy vấn '{ma_truy_van}' có điều kiện bắt buộc không hỗ trợ: "
                + ", ".join(sorted(khong_biet_loc))
                + "."
            )
        toi_da_gia = cung_loc.get("max_price_vnd")
        if toi_da_gia is not None:
            if isinstance(toi_da_gia, bool) or not isinstance(toi_da_gia, (int, float)):
                raise LoiDuLieuDanhGia(
                    f"Truy vấn '{ma_truy_van}' có 'max_price_vnd' phải là số."
                )
            try:
                toi_da_gia_gia_tri = float(toi_da_gia)
            except (OverflowError, TypeError, ValueError) as loi:
                raise LoiDuLieuDanhGia(
                    f"Truy vấn '{ma_truy_van}' có 'max_price_vnd' không hợp lệ."
                ) from loi
            if not math.isfinite(toi_da_gia_gia_tri) or toi_da_gia_gia_tri < 0:
                raise LoiDuLieuDanhGia(
                    f"Truy vấn '{ma_truy_van}' có 'max_price_vnd' phải là số hữu hạn không âm."
                )
        for truong_ten in ("required_fuel", "required_condition"):
            gia_tri = cung_loc.get(truong_ten)
            if gia_tri is not None and (
                not isinstance(gia_tri, str) or not gia_tri.strip()
            ):
                raise LoiDuLieuDanhGia(
                    f"Truy vấn '{ma_truy_van}' có '{truong_ten}' phải là chuỗi không rỗng."
                )
        phu_hop = phan_tu.get("relevant_vehicle_ids")
        if not isinstance(phu_hop, list) or not all(
            isinstance(muc, str) and muc.strip() for muc in phu_hop
        ):
            raise LoiDuLieuDanhGia(
                f"Truy vấn '{ma_truy_van}' cần danh sách 'relevant_vehicle_ids'."
            )
        can_cu_gan_nhan = phan_tu.get("label_basis")
        if not isinstance(can_cu_gan_nhan, str) or not can_cu_gan_nhan.strip():
            raise LoiDuLieuDanhGia(
                f"Truy vấn '{ma_truy_van}' cần 'label_basis' mô tả cách gán nhãn độc lập."
            )
        try:
            truy_van_goi_y = TruyVanGoiY(
                tieu_chi=_doc_tieu_chi_mem(phan_tu.get("criteria"), ma_truy_van),
                gia_toi_da_vnd=cung_loc.get("max_price_vnd"),
                dieu_kien_nhien_lieu=cung_loc.get("required_fuel"),
                dieu_kien_tinh_trang=cung_loc.get("required_condition"),
                k=k,
            )
        except LoiTruyVanKhongHopLe as loi:
            raise LoiDuLieuDanhGia(
                f"Truy vấn '{ma_truy_van}' không hợp lệ: {loi}"
            ) from loi

        cac_truy_van.append(
            TruyVanDanhGia(
                ma_truy_van=ma_truy_van,
                truy_van_goi_y=truy_van_goi_y,
                ma_xe_phu_hop=frozenset(muc.strip() for muc in phu_hop),
                can_cu_gan_nhan=can_cu_gan_nhan.strip(),
            )
        )

    return tuple(cac_truy_van)


def nap_danh_muc_danh_gia(duong_dan: str | Path) -> DanhMucXe:
    try:
        return nap_danh_muc(duong_dan)
    except (LoiDuLieuCsv, LoiCauTrucCsv) as loi:
        raise LoiDuLieuDanhGia(str(loi)) from loi


def _tao_bo_phan_tich_tham_so() -> argparse.ArgumentParser:
    bo_phan_tich = argparse.ArgumentParser(
        description="Đánh giá ranking xe máy bằng Precision@K."
    )
    bo_phan_tich.add_argument(
        "--queries",
        required=True,
        help="Tệp JSON chứa truy vấn và nhãn phù hợp đã chốt độc lập.",
    )
    bo_phan_tich.add_argument(
        "--catalog",
        default=str(lay_duong_dan_danh_muc()),
        help="CSV catalog (mặc định: data/dataset-done.csv).",
    )
    bo_phan_tich.add_argument(
        "--output",
        help="Tệp JSON để ghi báo cáo Precision@K (tùy chọn).",
    )
    return bo_phan_tich


def chay_cli(tham_so_cli: list[str] | None = None) -> int:
    bo_phan_tich = _tao_bo_phan_tich_tham_so()
    tham_so = bo_phan_tich.parse_args(tham_so_cli)
    try:
        cac_truy_van = nap_truy_van_danh_gia(tham_so.queries)
        danh_muc = nap_danh_muc_danh_gia(tham_so.catalog)
        bao_cao = tinh_danh_gia_truy_van(danh_muc, cac_truy_van)
    except LoiDuLieuDanhGia as loi:
        print(f"Lỗi dữ liệu đánh giá: {loi}", file=sys.stderr)
        return 2

    print("Precision@K theo từng truy vấn")
    for dong in bao_cao.cac_dong:
        print(
            f"- {dong.ma_truy_van}: K={dong.k}, phù hợp trong Top-K="
            f"{len(dong.ma_xe_phu_hop_trong_top_k)}, Precision@{dong.k}="
            f"{dong.do_chinh_xac_k:.4f}"
        )
    print(f"Precision@K trung bình: {bao_cao.trung_binh_do_chinh_xac_k:.4f}")

    if tham_so.output:
        dau_ra_duong_dan = Path(tham_so.output)
        dau_ra_duong_dan.parent.mkdir(parents=True, exist_ok=True)
        dau_ra_duong_dan.write_text(
            json.dumps(bao_cao.sang_tu_dien(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Đã ghi báo cáo: {dau_ra_duong_dan}")
    return 0


if __name__ == "__main__":
    raise SystemExit(chay_cli())
