"""Entry point tương thích cho CLI đánh giá Precision@K."""

import sys
from pathlib import Path

DUONG_DAN_GOC = Path(__file__).resolve().parent
if str(DUONG_DAN_GOC) not in sys.path:
    sys.path.insert(0, str(DUONG_DAN_GOC))
if str(DUONG_DAN_GOC / "src") not in sys.path:
    sys.path.insert(0, str(DUONG_DAN_GOC / "src"))

from danh_gia.do_chinh_xac_k import chay_cli  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(chay_cli())
