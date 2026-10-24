# Gợi ý xe máy bằng KNN và Gemini

Ứng dụng Streamlit nhận nhu cầu mua xe, lọc các điều kiện bắt buộc, xếp hạng xe
bằng khoảng cách Euclid có trọng số trên dữ liệu CSV hiện có và dùng Gemini để
giải thích Top-K. Đây là hệ thống gợi ý theo nội dung, không huấn luyện mô hình
và không dùng ảnh.

## Tính năng

- Đọc CSV ở chế độ chỉ đọc, hỗ trợ tiêu đề tiếng Việt có dấu/không dấu, chữ hoa
  thường, dấu phân cách `,`/`;`/tab và số theo định dạng Việt Nam như
  `166.190.000`, `21,5`, `5 L`.
- Tách điều kiện bắt buộc (ngân sách, nhiên liệu, tình trạng) khỏi tiêu chí ưu
  tiên (giá, kiểu xe, nhiên liệu, công suất, cốp, tình trạng, năm, hãng).
- Tiêu chí của hồ sơ đang áp dụng (hồ sơ Cân bằng mặc định hoặc Tùy chỉnh được chọn) tham gia tính khoảng cách; trọng số được chuẩn hóa lại trên các tiêu chí đang hoạt động.
- Giao diện một trang đơn giản, đáp ứng: điều kiện bắt buộc và hồ sơ ưu tiên ở trên, kết quả hiển thị liền kề ngay bên dưới sau khi gợi ý.
- Hỗ trợ hồ sơ “Cân bằng (mặc định)” (áp dụng trọng số bằng nhau cho toàn bộ tiêu chí có trong dữ liệu, median cho giá trị số, mode cho danh mục, giá mục tiêu tại median) hoặc “Tùy chỉnh”; nếu để trống tùy chỉnh, tự động áp dụng hồ sơ Cân bằng.
- Giá là một tiêu chí duy nhất với hai chế độ `Giá thấp` và `Gần giá mục tiêu`;
  ô giá mục tiêu chỉ hiện trong chế độ target.
- Min-Max số về `[0, 1]` theo catalog, clip truy vấn, xử lý trường hợp
  `max = min`, khoảng cách bất đối xứng cho cốp/năm tối thiểu và mismatch `0/1`
  cho danh mục.
- Kết quả Top-K kèm thẻ thông số, lý do phù hợp, điểm cần cân nhắc và chi tiết
  khoảng cách. Điểm gần chỉ là thứ tự tương đối, không phải xác suất.
- Gemini chỉ nhận dữ liệu thật của Top-K để diễn giải. Thiếu khóa, lỗi JSON,
  timeout hoặc lỗi API đều có thông báo tiếng Việt và fallback cục bộ; KNN vẫn
  hoạt động.
- Harness Precision@K cho tập truy vấn và nhãn do người đánh giá chốt độc lập.

## Yêu cầu

- Python 3.11 trở lên.
- Windows PowerShell hoặc shell tương đương.
- Các gói trong `requirements.txt`; gói kiểm thử/lint trong
  `requirements-dev.txt`.

## Cài đặt

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

Trên macOS/Linux, dùng `python3 -m venv .venv` và
`source .venv/bin/activate`.

## Chạy ứng dụng

Từ thư mục gốc dự án:

```powershell
python -m streamlit run app.py
```

Sau đó mở địa chỉ Streamlit in ra (mặc định `http://localhost:8501`). Giao diện
đơn trang hiển thị trực quan các mục nhập điều kiện bắt buộc, hồ sơ ưu tiên
và các nút hành động; kết quả gợi ý Top-K và giải thích hiển thị trực tiếp
ngay bên dưới sau khi bấm “Gợi ý xe”.

## Cấu hình Gemini

Ứng dụng không bắt buộc Gemini để xếp hạng. Nếu chưa cấu hình, phần giải thích
dùng dữ liệu CSV cục bộ.

Tạo `.env` từ mẫu rồi thêm khóa của bạn:

```powershell
Copy-Item .env.example .env
notepad .env
```

Đặt `GEMINI_API_KEY=khóa-của-bạn` trong `.env`, lưu tệp rồi khởi động lại ứng
dụng. `.env` đã nằm trong `.gitignore`; không đưa khóa vào mã nguồn, tài liệu,
log hoặc báo cáo. Biến môi trường hệ điều hành cùng tên, nếu có, được ưu tiên hơn
giá trị trong `.env`.

Tùy chọn:

- `GEMINI_MODEL`: mặc định `gemini-3.5-flash-lite` để ưu tiên chi phí thấp; có
  thể ghi đè bằng biến môi trường.
- `GEMINI_TIMEOUT_SECONDS`: mặc định `30`.
- `MOTORCYCLE_CSV_PATH`: đường dẫn CSV thay thế nếu cần; ứng dụng vẫn chỉ đọc
  tệp và không ghi đè.

Tích hợp dùng Gemini Interactions API qua gói `google-genai`, gửi
`store=False`, yêu cầu JSON theo schema và chỉ gửi dữ liệu Top-K cùng nhu cầu
người dùng. Model/API được đối chiếu với tài liệu Google chính thức hiện hành.

## Kiểm thử và lint

```powershell
python -m pytest
python -m ruff check src danh_gia kiem_thu app.py evaluate_precision.py
```

Bộ test hiện có 77 test, bao phủ:

- parse giá/công suất/cốp/năm và schema thiếu cột;
- Min-Max, clip, `max = min`, khoảng cách thiếu `0,5`;
- bỏ tiêu chí không hoạt động và chuẩn hóa lại trọng số;
- lọc ngân sách/nhiên liệu/tình trạng, cốp bất đối xứng, categorical, Top-K;
- Precision@K và CLI xuất báo cáo chỉ có metric `Precision@K`;
- fallback Gemini khi thiếu khóa, JSON sai, timeout hoặc lỗi API;
- AppTest kiểm tra cấu trúc đơn trang (không sidebar, không tab, không rail, không input mục đích/quãng đường), chế độ Cân bằng mặc định, rơi về Cân bằng khi để trống tùy chỉnh, chế độ giá low/target, submit hợp lệ, đặt lại lựa chọn và trạng thái thiếu khóa Gemini;
- CSV thật không bị thay đổi sau khi nạp.

## Đánh giá Precision@K

Định nghĩa:

```text
Precision@K = số xe phù hợp trong K kết quả đầu / K
```

Nếu không đủ K xe vì bộ lọc, vẫn chia cho K. Chạy harness:

```powershell
python evaluate_precision.py --queries danh_gia/queries_synthetic.json --output danh_gia/ket_qua.json
```

Tệp truy vấn phải có `id`, `k`, `criteria`, `hard_filters`,
`relevant_vehicle_ids` và `label_basis`. Nhãn phải được chốt trước khi xem kết
quả của cấu hình đang đánh giá và không được gán chỉ vì xe xuất hiện trong
Top-K. Tệp `queries_synthetic.json` là tập R ảo sinh theo quy tắc, không phải
nhãn thực nghiệm.

Repo chưa kèm tập nhãn thật hay kết quả Precision@K thực nghiệm.

## Dữ liệu và giới hạn

Tệp mặc định: `data/dataset-done.csv` (chỉ đọc). Trạng thái kiểm tra ngày
2026-10-24:

- 225 dòng nguồn, đều là xe hợp lệ; không có dòng trống, tiêu đề khối hãng,
  thiếu Model hoặc trùng hoàn toàn.
- 216 dòng được điền hãng theo khối tiêu đề gần nhất.
- Không thiếu hoặc lỗi dữ liệu ở các trường trong schema.
- Danh mục có 163 xe Xăng và 62 xe Điện; 9 hãng; 6 kiểu xe.
- Cả 225 xe đều được ghi tình trạng `Mới`; năm sản xuất từ 2022 đến 2024
  (21 xe năm 2022, 52 xe năm 2023, 152 xe năm 2024).
- CSV không có cột hệ thống phanh, không có mục đích sử dụng/quãng đường và
  không có ảnh. Vì vậy phanh không phải tiêu chí xếp hạng; ứng dụng không thu thập
  hay dùng mục đích/quãng đường làm đầu vào.
- Giá từ 12.900.000 đến 1.231.000.000 VND; công suất 0,5–140 kW; cốp 0–50 lít.

Hệ quả:

- Bật ngân sách sẽ loại xe thiếu giá; chọn nhiên liệu/tình trạng bắt buộc sẽ loại
  xe thiếu trường tương ứng.
- Xe thiếu dữ liệu ở tiêu chí mềm đang hoạt động nhận khoảng cách `0,5` và được
  nêu trong phần giải thích; ứng dụng không tự điền thông số.
- Kết quả chỉ phản ánh CSV, không thay thế kiểm tra thực tế trước khi mua.

## Cấu trúc project

```text
app.py                                  # entrypoint Streamlit
evaluate_precision.py                   # entrypoint CLI Precision@K
README.md                               # hướng dẫn cài đặt, chạy, dữ liệu
pyproject.toml                          # metadata, dependency, pytest/ruff config
requirements.txt / requirements-dev.txt # phụ thuộc chạy và dev
.streamlit/config.toml                  # theme và cấu hình Streamlit
.env.example                            # mẫu biến môi trường Gemini, không chứa khóa thật
data/dataset-done.csv                   # CSV người dùng, chỉ đọc
danh_gia/do_chinh_xac_k.py              # harness và CLI Precision@K
danh_gia/queries_synthetic.json         # tập R ảo để kiểm tra harness
kiem_thu/                               # kiểm thử đơn vị và tích hợp
src/goi_xe/
├── cau_hinh.py
├── dinh_dang.py
├── giai_thich.py                       # prompt, Gemini và giải thích dự phòng
├── du_lieu/                            # nạp, schema, phân tích và làm sạch CSV
├── goi_y/                              # tiêu chí, chuẩn hóa và xếp hạng KNN
└── giao_dien/                          # giao diện Streamlit đơn trang liền kề
```

## Ghi chú thiết kế

- Một cột công suất tối đa chung `max_power_kw` cho cả xe xăng và xe điện.
  Không dùng CC hoặc W như feature tách biệt; nếu nguồn ghi W, đổi sang kW bằng
  cách chia 1.000.
- Công thức:

  ```text
  D(x, u) = sqrt( sum[j in A(u)] w_j * d_j(x, u)^2
                  / sum[j in A(u)] w_j )
  ```

  Trong đó `A(u)` chỉ gồm các tiêu chí mềm đang hoạt động. Khoảng cách nhỏ hơn
  được xếp trước; hòa điểm được phân định ổn định theo dòng nguồn.
- Trọng số baseline nằm trong `src/goi_xe/goi_y/tieu_chi.py`
  và được chuẩn hóa lại khi chỉ một phần tiêu chí được chọn.
- Không dùng metric ranking nào khác ngoài `Precision@K`.
