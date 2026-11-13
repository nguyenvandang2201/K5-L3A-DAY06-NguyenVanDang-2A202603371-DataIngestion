# Starter đã hoàn thiện — PostgreSQL + pgvector

Thư mục này chứa pipeline Python đã hiện thực cho bài lab. Xem [SOLUTION.md](../SOLUTION.md) để cài đặt và chạy, [báo cáo](../report/individual/2A202603371_NguyenVanDang.md) để xem kết quả và giới hạn. Từ thư mục `starter/`, chạy `python -m src.run` sau khi cài `requirements.txt` và khởi động `docker compose -p day6_student_starter up -d --wait`.

Các module `src/` lần lượt xử lý chuẩn hóa/đọc PDF, chia chunk, embedding thật, lưu pgvector, đánh giá evidence và điều phối. `scripts/fetch_corpus.py` tạo snapshot HTML có giấy phép; `scripts/build_benchmark.py` đối chiếu quote với nguồn trước khi truy xuất; `scripts/audit_results.py` lưu mẫu đánh giá. Database chỉ mở cổng local `127.0.0.1:55433`; cấu hình mẫu ở `.env.example`.
