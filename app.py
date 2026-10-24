import sys
from pathlib import Path

DUONG_DAN_GOC = Path(__file__).resolve().parent
THU_MUC_NGUON = DUONG_DAN_GOC / "src"
if str(THU_MUC_NGUON) not in sys.path:
    sys.path.insert(0, str(THU_MUC_NGUON))

from goi_xe.giao_dien.ung_dung import chay_ung_dung  # noqa: E402, I001


if __name__ == "__main__":
    chay_ung_dung()
