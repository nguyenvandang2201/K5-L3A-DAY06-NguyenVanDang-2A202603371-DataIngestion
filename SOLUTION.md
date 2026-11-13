# Bài lab Data Ingestion — Nguyễn Văn Đăng

MSSV **2A202603371**, lớp **L3A**. Bài làm dùng 59 đơn vị văn bản từ sáu chương Python 3.12 Tutorial, 24 câu hỏi benchmark, local embedding và PostgreSQL + pgvector. [Báo cáo đầy đủ](report/individual/2A202603371_NguyenVanDang.md) chứa kết quả thật và giới hạn.

## Tái lập

Cần Python 3.12, Docker Engine/Compose và mạng cho lần tải dependencies/model đầu tiên. Tại thư mục repo:

```powershell
cd starter
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
docker compose -p day6_student_starter up -d --wait
python scripts/check_setup.py
python -m src.run
python -m scripts.audit_results
```

`src.run` tự dùng URL database local mặc định nếu không có `.env`. Docker chỉ mở PostgreSQL tại `127.0.0.1:55433`. Dừng dịch vụ mà giữ dữ liệu bằng `docker compose -p day6_student_starter stop`.

Snapshot đã được commit trong `data/corpus.jsonl` và `data/manifest.json`. Để lấy snapshot mới từ nguồn công khai rồi xây lại benchmark **trước khi thí nghiệm mới**, chạy từ `starter/`:

```powershell
python -m scripts.fetch_corpus
python -m scripts.build_benchmark
```

Nguồn HTML có thể cập nhật; nếu câu trích dẫn thay đổi, script benchmark sẽ báo lỗi để sửa gold và tạo tập đánh giá mới. Corpus tuân Python Software Foundation License Version 2; xem `data/PYTHON_LICENSE.txt`.

## Đầu vào và đầu ra

| File | Ý nghĩa |
|---|---|
| `data/manifest.json`, `data/corpus.jsonl` | Quyền, URL, hash nguồn và 59 đơn vị văn bản |
| `benchmark/questions.json` | 18 dev, 6 test, gold và 6 câu filter |
| `artifacts/experiment_log.csv` | Cấu hình A/B/C và giả thuyết |
| `results/summary.json` | Số chunk, thời gian, Hit@1 và Evidence Hit@3 |
| `results/traces.jsonl` | Toàn bộ top-3, score, text, metadata cho 72 lượt hỏi |
| `results/audit.json` | Mẫu coherence, kiểm tra metadata và nhãn grounding |
| `report/individual/2A202603371_NguyenVanDang.md` | Phân tích đủ năm tiêu chí |

Ba chiến lược dùng cùng corpus, model `sentence-transformers/all-MiniLM-L6-v2` và exact cosine search. C chia chunk giống B và chỉ bật filter `chapter` khi câu hỏi yêu cầu. `src.run` thay thế dữ liệu của từng chiến lược trong một transaction khi nạp lại, tránh duplicate và chunk cũ. Kết quả gốc được chạy ngày 13/11/2026. Lần chạy mới sẽ ghi đè `results/summary.json` và `results/traces.jsonl`.
