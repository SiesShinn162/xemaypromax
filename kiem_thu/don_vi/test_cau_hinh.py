from goi_xe.cau_hinh import MO_HINH_GEMINI_MAC_DINH, lay_mo_hinh_gemini


def test_gemini_mo_hinh_mac_dinh_den_flash_lite(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    assert MO_HINH_GEMINI_MAC_DINH == "gemini-3.5-flash-lite"
    assert lay_mo_hinh_gemini() == MO_HINH_GEMINI_MAC_DINH


def test_gemini_mo_hinh_moi_truong_ghi_de_la_duoc_giu(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_MODEL", "custom-gemini-model")

    assert lay_mo_hinh_gemini() == "custom-gemini-model"
