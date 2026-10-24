from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from goi_xe.giai_thich import (
    HUONG_DAN_HE_THONG,
    THONG_BAO_LOI_API,
    THONG_BAO_QUA_THOI_GIAN,
    BoGiaiThichGemini,
    LoiGiaiThichKhongHopLe,
    doc_json_giai_thich,
    lay_khoa_api,
    tao_goi_giai_thich,
    tao_loi_nhac_giai_thich,
)
from goi_xe.goi_y.tieu_chi import (
    TieuChiMem,
    TruyVanGoiY,
)
from goi_xe.goi_y.xep_hang import xep_hang_xe
from kiem_thu.ho_tro import tao_danh_muc


def _xep_hang(k: int = 2):
    danh_muc = tao_danh_muc(
        [
            {"vehicle_id": "a", "model": "Alpha", "price_vnd": 10.0},
            {"vehicle_id": "b", "model": "Beta", "price_vnd": 20.0},
            {"vehicle_id": "c", "model": "Gamma", "price_vnd": 30.0},
        ]
    )
    truy_van = TruyVanGoiY(
        tieu_chi=(TieuChiMem("price", 1.0, che_do="low"),),
        k=k,
    )
    return xep_hang_xe(danh_muc, truy_van), truy_van


def _goi_du_lieu_hop_le(ket_qua, thu_tu: list[str] | None = None) -> dict[str, Any]:
    cac_muc = {muc.xe["vehicle_id"]: muc for muc in ket_qua.cac_muc}
    ma = thu_tu or list(cac_muc)
    return {
        "summary": "Tóm tắt từ dữ liệu Top-K.",
        "recommendations": [
            {
                "vehicle_id": vehicle_id,
                "model_name": cac_muc[vehicle_id].xe["model"],
                "reasons": ["Giá và thông số phù hợp với dữ liệu."],
                "tradeoffs": ["Cần kiểm tra thực tế."],
            }
            for vehicle_id in ma
        ],
        "missing_data": ["Năm sản xuất"],
    }


class _GiaLapTuongTac:
    def __init__(self, phan_hoi: str | None = None, loi: Exception | None = None):
        self.phan_hoi = phan_hoi
        self.loi = loi
        self.tu_khoa: dict[str, Any] = {}

    def create(self, **tu_khoa: Any) -> SimpleNamespace:
        self.tu_khoa = tu_khoa
        if self.loi is not None:
            raise self.loi
        return SimpleNamespace(output_text=self.phan_hoi)


class _GiaLapClient:
    def __init__(self, phan_hoi: str | None = None, loi: Exception | None = None):
        self.interactions = _GiaLapTuongTac(phan_hoi=phan_hoi, loi=loi)


def test_goi_du_lieu_chua_chi_top_k_va_khong_bi_mat() -> None:
    ket_qua, truy_van = _xep_hang(k=2)
    goi_du_lieu = tao_goi_giai_thich(ket_qua, truy_van)
    assert len(goi_du_lieu["top_k"]) == 2
    assert {muc["vehicle_id"] for muc in goi_du_lieu["top_k"]} == {"a", "b"}
    loi_nhac = tao_loi_nhac_giai_thich(goi_du_lieu)
    assert "Gamma" not in loi_nhac
    assert "a" in loi_nhac and "b" in loi_nhac


def test_doc_hop_le_json_anh_xa_cho_xe_ma_khong_thu_tu() -> None:
    ket_qua, _ = _xep_hang(k=2)
    chu = "```json\n" + json.dumps(
        _goi_du_lieu_hop_le(ket_qua, thu_tu=["b", "a"]), ensure_ascii=False
    ) + "\n```"
    da_doc = doc_json_giai_thich(chu, {"a": "Alpha", "b": "Beta"})
    assert da_doc.nguon == "gemini"
    assert set(da_doc.cac_muc) == {"a", "b"}
    assert da_doc.cac_muc["b"].model_name == "Beta"
    assert da_doc.du_lieu_thieu == ("Năm sản xuất",)


@pytest.mark.parametrize(
    "ham_thay_doi",
    [
        lambda goi_du_lieu: goi_du_lieu.update({"summary": ""}),
        lambda goi_du_lieu: goi_du_lieu.update({"recommendations": []}),
        lambda goi_du_lieu: goi_du_lieu["recommendations"].append(
            {
                "vehicle_id": "unknown",
                "model_name": "Không có",
                "reasons": ["x"],
                "tradeoffs": [],
            }
        ),
        lambda goi_du_lieu: goi_du_lieu["recommendations"][0].update(
            {"vehicle_id": "a", "model_name": "Sai tên"}
        ),
        lambda goi_du_lieu: goi_du_lieu["recommendations"][0].update({"reasons": []}),
    ],
)
def test_khong_hop_le_json_cau_truc_la_bi_tu_choi(ham_thay_doi) -> None:
    ket_qua, _ = _xep_hang(k=2)
    goi_du_lieu = _goi_du_lieu_hop_le(ket_qua)
    ham_thay_doi(goi_du_lieu)
    with pytest.raises(LoiGiaiThichKhongHopLe):
        doc_json_giai_thich(
            json.dumps(goi_du_lieu, ensure_ascii=False),
            {"a": "Alpha", "b": "Beta"},
        )


def test_thieu_khoa_tra_ve_tieng_viet_du_phong() -> None:
    ket_qua, truy_van = _xep_hang(k=2)
    bo_giai_thich = BoGiaiThichGemini(khoa_api="", khach=None)
    giai_thich = bo_giai_thich.giai_thich(ket_qua, truy_van)
    assert giai_thich.nguon == "fallback"
    assert giai_thich.summary == ""
    assert "GEMINI_API_KEY" in (giai_thich.thong_bao_loi or "")
    assert set(giai_thich.cac_muc) == {"a", "b"}
    assert giai_thich.cac_muc["a"].reasons


def test_gemini_thanh_cong_giu_xep_hang_va_gui_chi_top_k() -> None:
    ket_qua, truy_van = _xep_hang(k=2)
    truoc = ket_qua.ma_xe_top_k
    gia_lap = _GiaLapClient(
        phan_hoi=json.dumps(
            _goi_du_lieu_hop_le(ket_qua, thu_tu=["b", "a"]), ensure_ascii=False
        )
    )
    bo_giai_thich = BoGiaiThichGemini(
        khoa_api="super-secret-key",
        model="gemini-test-model",
        thoi_gian_cho_giay=7.5,
        khach=gia_lap,
    )
    giai_thich = bo_giai_thich.giai_thich(ket_qua, truy_van)
    assert giai_thich.nguon == "gemini"
    assert giai_thich.model == "gemini-test-model"
    assert set(giai_thich.cac_muc) == {"a", "b"}
    assert ket_qua.ma_xe_top_k == truoc

    yeu_cau = gia_lap.interactions.tu_khoa
    assert yeu_cau["model"] == "gemini-test-model"
    assert yeu_cau["system_instruction"] == HUONG_DAN_HE_THONG
    assert yeu_cau["timeout"] == 7.5
    assert yeu_cau["store"] is False
    assert yeu_cau["response_format"]["schema"]
    loi_nhac = yeu_cau["input"]
    assert "super-secret-key" not in loi_nhac
    assert "Gamma" not in loi_nhac
    assert "a" in loi_nhac and "b" in loi_nhac


@pytest.mark.parametrize(
    ("loi", "mong_doi_thong_bao"),
    [
        (TimeoutError(), THONG_BAO_QUA_THOI_GIAN),
        (RuntimeError("api down"), THONG_BAO_LOI_API),
    ],
)
def test_api_va_qua_thoi_gian_loi_roi_du_phong(loi: Exception, mong_doi_thong_bao: str) -> None:
    ket_qua, truy_van = _xep_hang(k=2)
    bo_giai_thich = BoGiaiThichGemini(
        khoa_api="secret",
        khach=_GiaLapClient(loi=loi),
    )
    giai_thich = bo_giai_thich.giai_thich(ket_qua, truy_van)
    assert giai_thich.nguon == "fallback"
    assert giai_thich.thong_bao_loi == mong_doi_thong_bao
    assert set(giai_thich.cac_muc) == {"a", "b"}
    assert ket_qua.ma_xe_top_k == ("a", "b")


def test_khong_hop_le_json_phan_hoi_roi_du_phong() -> None:
    ket_qua, truy_van = _xep_hang(k=2)
    bo_giai_thich = BoGiaiThichGemini(
        khoa_api="secret",
        khach=_GiaLapClient(phan_hoi="{not valid json"),
    )
    giai_thich = bo_giai_thich.giai_thich(ket_qua, truy_van)
    assert giai_thich.nguon == "fallback"
    assert "JSON" in (giai_thich.thong_bao_loi or "")


def test_giai_api_khoa_nap_dotenv_va_uu_tien_moi_truong(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    (tmp_path / ".env").write_text("GEMINI_API_KEY=from-dotenv\n", encoding="utf-8")
    monkeypatch.setattr("goi_xe.giai_thich.DUONG_DAN_GOC", tmp_path)

    assert lay_khoa_api() == "from-dotenv"
    monkeypatch.setenv("GEMINI_API_KEY", "from-env")
    assert lay_khoa_api() == "from-env"
