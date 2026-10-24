from __future__ import annotations

import json
from pathlib import Path

from danh_gia.do_chinh_xac_k import chay_cli


def test_cli_ghi_chi_do_chinh_xac_tai_k_bao_cao(tmp_path: Path) -> None:
    danh_muc = tmp_path / "catalog.csv"
    danh_muc.write_text(
        "\n".join(
            [
                "Hãng,Model,Giá(VND),Công suất tối đa (Kw),Nhiên liệu,Kiểu xe",
                'Honda,Xe rẻ,10.000.000,"8,0",Xăng,Xe số',
                'Honda,Xe đắt,20.000.000,"8,0",Xăng,Xe số',
            ]
        ),
        encoding="utf-8",
    )
    cac_truy_van = tmp_path / "queries.json"
    cac_truy_van.write_text(
        json.dumps(
            {
                "queries": [
                    {
                        "id": "q1",
                        "k": 1,
                        "criteria": [{"key": "price", "weight": 1, "mode": "low"}],
                        "relevant_vehicle_ids": ["vehicle-0002"],
                        "label_basis": "Nhãn kiểm thử độc lập với thứ hạng.",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    dau_ra = tmp_path / "report.json"
    ma_thoat = chay_cli(
        [
            "--queries",
            str(cac_truy_van),
            "--catalog",
            str(danh_muc),
            "--output",
            str(dau_ra),
        ]
    )
    assert ma_thoat == 0
    bao_cao = json.loads(dau_ra.read_text(encoding="utf-8"))
    assert bao_cao["metric"] == "Precision@K"
    assert bao_cao["mean_precision_at_k"] == 1.0
    assert bao_cao["queries"][0]["recommended_ids"] == ["vehicle-0002"]
