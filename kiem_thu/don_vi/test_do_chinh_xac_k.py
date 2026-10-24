from __future__ import annotations

import json
from pathlib import Path

import pytest

from danh_gia.do_chinh_xac_k import (
    LoiDuLieuDanhGia,
    TruyVanDanhGia,
    do_chinh_xac_k,
    nap_danh_muc_danh_gia,
    nap_truy_van_danh_gia,
    tinh_danh_gia_truy_van,
)
from goi_xe.goi_y.tieu_chi import (
    LoiThieuTieuChi,
    TieuChiMem,
    TruyVanGoiY,
)
from kiem_thu.ho_tro import tao_danh_muc


def test_do_chinh_xac_tai_k_chinh_xac_dinh_nghia() -> None:
    duoc_goi_y = ["a", "b", "c", "d", "e"]
    phu_hop = {"a", "c", "x"}
    assert do_chinh_xac_k(duoc_goi_y, phu_hop, 3) == pytest.approx(2 / 3)
    assert do_chinh_xac_k(duoc_goi_y, phu_hop, 5) == pytest.approx(2 / 5)


def test_do_chinh_xac_tai_k_chia_cho_k_khi_it_hon_cac_ket_qua() -> None:
    assert do_chinh_xac_k(["a"], {"a"}, 3) == pytest.approx(1 / 3)
    assert do_chinh_xac_k([], {"a"}, 3) == 0.0
    with pytest.raises(ValueError):
        do_chinh_xac_k(["a"], {"a"}, 0)


def _truy_van(k: int = 2) -> TruyVanGoiY:
    return TruyVanGoiY(
        tieu_chi=(TieuChiMem("price", 0.3, che_do="low"),),
        k=k,
    )


def test_danh_gia_cac_truy_van_dung_doc_lap_cac_nhan_va_trung_binh() -> None:
    danh_muc = tao_danh_muc(
        [
            {"vehicle_id": "a", "model": "A", "price_vnd": 10.0},
            {"vehicle_id": "b", "model": "B", "price_vnd": 20.0},
            {"vehicle_id": "c", "model": "C", "price_vnd": 30.0},
        ]
    )
    cac_truy_van = (
        TruyVanDanhGia(
            ma_truy_van="q1",
            truy_van_goi_y=_truy_van(),
            ma_xe_phu_hop=frozenset({"a", "c"}),
            can_cu_gan_nhan="Người đánh giá chốt trước khi chạy.",
        ),
        TruyVanDanhGia(
            ma_truy_van="q2",
            truy_van_goi_y=_truy_van(),
            ma_xe_phu_hop=frozenset({"c"}),
            can_cu_gan_nhan="Nhãn từ khảo sát độc lập.",
        ),
    )
    bao_cao = tinh_danh_gia_truy_van(danh_muc, cac_truy_van)
    assert bao_cao.cac_dong[0].ma_xe_goi_y == ("a", "b")
    assert bao_cao.cac_dong[0].do_chinh_xac_k == 0.5
    assert bao_cao.cac_dong[1].do_chinh_xac_k == 0.0
    assert bao_cao.trung_binh_do_chinh_xac_k == pytest.approx(0.25)
    assert bao_cao.sang_tu_dien()["metric"] == "Precision@K"
    assert set(bao_cao.sang_tu_dien()) == {"metric", "mean_precision_at_k", "queries"}


def test_danh_gia_cac_truy_van_tu_choi_khong_biet_cac_nhan_va_trung_ma() -> None:
    danh_muc = tao_danh_muc([{"vehicle_id": "a", "model": "A"}])
    khong_biet = TruyVanDanhGia(
        ma_truy_van="q1",
        truy_van_goi_y=_truy_van(),
        ma_xe_phu_hop=frozenset({"missing"}),
        can_cu_gan_nhan="Nhãn kiểm thử.",
    )
    with pytest.raises(LoiDuLieuDanhGia):
        tinh_danh_gia_truy_van(danh_muc, [khong_biet])

    trung = TruyVanDanhGia(
        ma_truy_van="q1",
        truy_van_goi_y=_truy_van(),
        ma_xe_phu_hop=frozenset({"a"}),
        can_cu_gan_nhan="Nhãn kiểm thử.",
    )
    with pytest.raises(LoiDuLieuDanhGia):
        tinh_danh_gia_truy_van(danh_muc, [trung, trung])


def test_nap_danh_gia_cac_truy_van_kiem_tra_cau_truc(tmp_path: Path) -> None:
    duong_dan = tmp_path / "queries.json"
    duong_dan.write_text(
        json.dumps(
            {
                "queries": [
                    {
                        "id": "q1",
                        "k": 2,
                        "criteria": [
                            {"key": "price", "weight": 0.3, "mode": "low"}
                        ],
                        "hard_filters": {"max_price_vnd": 50_000_000},
                        "relevant_vehicle_ids": ["vehicle-test-0001"],
                        "label_basis": "Nhãn do người đánh giá chốt độc lập.",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    cac_truy_van = nap_truy_van_danh_gia(duong_dan)
    assert len(cac_truy_van) == 1
    assert cac_truy_van[0].ma_truy_van == "q1"
    assert cac_truy_van[0].truy_van_goi_y.k == 2
    assert cac_truy_van[0].ma_xe_phu_hop == frozenset({"vehicle-test-0001"})

    duong_dan.write_text("{not json", encoding="utf-8")
    with pytest.raises(LoiDuLieuDanhGia):
        nap_truy_van_danh_gia(duong_dan)

    duong_dan.write_text(
        json.dumps(
            {
                "queries": [
                    {
                        "id": "q1",
                        "k": 2,
                        "criteria": [{"key": "price", "weight": 1}],
                        "relevant_vehicle_ids": ["a"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(LoiDuLieuDanhGia):
        nap_truy_van_danh_gia(duong_dan)


def test_nap_danh_gia_cac_truy_van_tu_choi_khong_hop_le_cac_trong_so_va_cung_loc(
    tmp_path: Path,
) -> None:
    duong_dan = tmp_path / "queries.json"
    goc = {
        "id": "q1",
        "k": 2,
        "criteria": [{"key": "price", "weight": 1, "mode": "low"}],
        "hard_filters": {},
        "relevant_vehicle_ids": ["a"],
        "label_basis": "Nhãn kiểm thử độc lập.",
    }
    truong_hop_loi = [
        {**goc, "criteria": [{"key": "price", "weight": 0}]},
        {**goc, "criteria": [{"key": "price", "weight": float("inf")}]},
        {**goc, "criteria": [{"key": "brand", "weight": 1, "mode": "low"}]},
        {**goc, "hard_filters": {"max_price_vnd": "100"}},
        {**goc, "hard_filters": {"max_price_vnd": float("nan")}},
        {**goc, "hard_filters": {"required_fuel": "   "}},
        {**goc, "hard_filters": {"unknown_filter": 1}},
    ]
    for khong_hop_le in truong_hop_loi:
        duong_dan.write_text(json.dumps({"queries": [khong_hop_le]}), encoding="utf-8")
        with pytest.raises(LoiDuLieuDanhGia):
            nap_truy_van_danh_gia(duong_dan)


def test_danh_gia_bao_goi_xep_hang_va_danh_muc_loi(tmp_path: Path) -> None:
    danh_muc = tao_danh_muc([{"vehicle_id": "a", "model": "A"}])
    truy_van = TruyVanDanhGia(
        ma_truy_van="q1",
        truy_van_goi_y=TruyVanGoiY(
            tieu_chi=(TieuChiMem("price", 1.0, che_do="low"),),
            k=1,
        ),
        ma_xe_phu_hop=frozenset({"a"}),
        can_cu_gan_nhan="Nhãn kiểm thử độc lập.",
    )

    def bo_xep_hang_loi(*_tham_so, **_tu_khoa):
        raise LoiThieuTieuChi("Không có tiêu chí hoạt động.")

    with pytest.raises(LoiDuLieuDanhGia):
        tinh_danh_gia_truy_van(danh_muc, [truy_van], bo_xep_hang=bo_xep_hang_loi)

    khong_hop_le_danh_muc = tmp_path / "invalid.csv"
    khong_hop_le_danh_muc.write_text("Hãng,Model\nHonda,SH\n", encoding="utf-8")
    with pytest.raises(LoiDuLieuDanhGia):
        nap_danh_muc_danh_gia(khong_hop_le_danh_muc)
