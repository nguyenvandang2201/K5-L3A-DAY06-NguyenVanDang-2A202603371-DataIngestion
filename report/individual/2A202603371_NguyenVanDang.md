# Báo cáo cá nhân — Day 06

**Nguyễn Văn Đăng — 2A202603371 — L3A**

## 1. Dữ liệu và pipeline

Corpus là sáu chương 3–8 của [Python 3.12 Tutorial](https://docs.python.org/3.12/tutorial/), lấy bản HTML ngày 13/11/2026. Nguồn thuộc Python Software Foundation License Version 2; thông báo bản quyền, URL, thời điểm truy cập, SHA-256 HTML và số ký tự từng đơn vị được lưu trong [`data/manifest.json`](../../data/manifest.json). Bản quyền: Copyright © 2001-2023 Python Software Foundation; All Rights Reserved. Toàn văn giấy phép nằm ở [`data/PYTHON_LICENSE.txt`](../../data/PYTHON_LICENSE.txt).

Sau khi bỏ phần điều hướng HTML, văn bản được chuẩn hóa Unicode NFC và khoảng trắng, giữ ranh giới đoạn và ví dụ mã. Corpus có **59 đơn vị nguồn**, mỗi đơn vị dài ít nhất 1.500 ký tự: 7 đơn vị chương giới thiệu, 16 control flow, 9 data structures, 10 modules, 8 input/output, 9 errors. Đây là đơn vị văn bản tuần tự, **không phải trang PDF**. Corpus được lưu trong [`data/corpus.jsonl`](../../data/corpus.jsonl); vị trí truy vết là `(document_id, page)` với `page` là số thứ tự đơn vị trong chương. Không có đơn vị rỗng; không cần OCR.

Embedding: `sentence-transformers/all-MiniLM-L6-v2`, 384 chiều, Sentence Transformers 6.2.0 và PyTorch 2.13.0+cpu. Cùng một model và cùng cách mã hóa được dùng cho document/query trong A, B, C. Vector được chuẩn hóa, tìm exact cosine trên PostgreSQL 16 + pgvector 0.8.7. Metadata mỗi chunk gồm `document_id`, URL `source`, `page`, `chapter`, `title`, `python_version`; `chapter` lấy trực tiếp từ URL chương và dùng để lọc. API cost = **0 USD**; thời gian CPU và điện năng không quy đổi thành tiền.

Pipeline nạp lại theo chiến lược bằng cách thay toàn bộ bản ghi chiến lược trong một transaction, nên không nhân đôi hoặc để lại chunk cũ. Cấu hình truy vấn chỉ nhận filter `chapter` và tham số hóa giá trị SQL. Lệnh tái lập có trong [SOLUTION.md](../../SOLUTION.md).

## 2. Cấu hình và benchmark

| Cấu hình | Chunking | Truy xuất |
|---|---|---|
| A | Cửa sổ 600 ký tự, overlap 60, không vượt đơn vị nguồn | Không lọc |
| B | Gộp theo đoạn, tối đa 650 ký tự, không vượt đơn vị nguồn | Không lọc |
| C | Cùng chunk và vector với B | Lọc `chapter` khi câu hỏi cung cấp giá trị |

[`benchmark/questions.json`](../../benchmark/questions.json) có **24 câu** với đáp án, nguồn/đơn vị và đoạn bằng chứng đã kiểm tra tồn tại: **18 dev / 6 test**. Có 6 câu cung cấp filter theo chương, gồm 1 câu test. Bộ câu hỏi được tạo và kiểm chứng trước khi truy xuất. Câu hỏi bằng tiếng Việt, nguồn bằng tiếng Anh; đây là một thách thức liên ngôn ngữ đối với model đã chọn. Gold source và đáp án không được đưa vào vector query; C chỉ dùng filter có sẵn trong định nghĩa câu hỏi.

Thứ tự ưu tiên chọn cấu hình là Evidence Hit@3 trên dev, sau đó kiểm tra grounding và tài nguyên. Tiêu chí này được mô tả trong tài liệu lab nhưng **không được lưu thành một bản chốt có timestamp riêng trước lần chạy**, nên đây là giới hạn của kiểm soát test.

## 3. Kết quả chạy

Lần chạy ghi tại `results/summary.json` lúc 03:02 UTC, ngày 13/11/2026. Hit chỉ được tính khi **một** chunk đúng nguồn/đơn vị và chứa đủ chuỗi bằng chứng đã ghi; đây là phép kiểm tra nghiêm ngặt, có thể bỏ sót diễn đạt tương đương hoặc bằng chứng nằm ở nhiều chunk. Toàn bộ top-3, score, text, metadata và nhãn hit ở [`results/traces.jsonl`](../../results/traces.jsonl).

| Cấu hình | Split | Hit@1 | Evidence Hit@3 | Chunk | Ingest (giây) | API cost |
|---|---|---:|---:|---:|---:|---:|
| A | dev | 2/18 | 3/18 | 288 | 5,373 | 0 USD |
| A | test | 0/6 | 0/6 | 288 | 5,373 | 0 USD |
| B | dev | 3/18 | 5/18 | 274 | 4,807 | 0 USD |
| B | test | 0/6 | 0/6 | 274 | 4,807 | 0 USD |
| C | dev | 4/18 | 6/18 | 274 | 0,128* | 0 USD |
| C | test | 0/6 | 1/6 | 274 | 0,128* | 0 USD |

\* C dùng lại vector đã tính cho B; thời gian này chỉ gồm tạo chunk và ghi index, không phải thời gian embedding độc lập. Median độ dài chunk: A 600, B/C 527 ký tự. A có một số chunk đuôi rất ngắn (min 1 ký tự), là điểm yếu của cách chia cố định hiện tại.

## 4. Năm khía cạnh đánh giá

### Retrieval accuracy

B tăng Evidence Hit@3 dev từ 3/18 lên 5/18 so với A. C tăng tiếp lên 6/18 nhờ filter theo chương ở câu có điều kiện. Test chỉ C có một hit trong top-3, tại `q22`; không cấu hình nào đạt Hit@1 test. Không suy rộng từ sáu câu test.

### Chunk coherence

Chọn 10 đơn vị nguồn trải đều theo thứ tự corpus, lấy đoạn giữa mỗi đơn vị rồi đọc chunk chứa vị trí đó ở từng cấu hình. Theo thang 0–2 của GUIDE, điểm trung bình: **A 0,4/2; B 1,3/2; C 1,3/2**. ID, text và nhãn từng mẫu ở [`results/audit.json`](../../results/audit.json). C và B giống nhau vì cùng chunk. A thường cắt giữa câu hoặc ví dụ; B giữ được đoạn, dù vẫn có chunk thiếu heading hoặc lẫn ví dụ dài.

### Metadata usefulness

Đối chiếu 18 kết quả top-3 của 6 câu test cho mỗi cấu hình với corpus: **A 18/18, B 18/18, C 18/18** có nguồn, đơn vị và `chapter` đủ và đúng. Ở test, C áp dụng filter cho `q22` và **1/1 câu** có toàn bộ top-3 đúng chương. A/B không thiết kế lọc nên chỉ số tuân thủ filter là **N/A**. `source` và `page` giúp truy lại đoạn gốc; `chapter` giúp giới hạn tìm kiếm. Hạn chế: filter quá rộng vì một chương vẫn có nhiều chủ đề.

### Grounding quality

Đọc top-3 của cùng 6 câu test theo thang 0/1/2: 0 không đủ bằng chứng, 1 có liên quan nhưng thiếu ý chính hoặc điều kiện, 2 đủ để trả lời và truy nguồn. Nhãn một lượt, chưa có người chấm độc lập.

| Cấu hình | Số câu mức 0 / 1 / 2 | Trung bình |
|---|---:|---:|
| A | 5 / 1 / 0 | 0,17/2 |
| B | 5 / 1 / 0 | 0,17/2 |
| C | 4 / 1 / 1 | 0,50/2 |

`q22` là ví dụ C lấy được phát biểu về lớp ngoại lệ trong `except` ở top-2 nhờ filter `errors`; A/B không lấy được bằng chứng cần thiết. `q24` trả về ví dụ `ExceptionGroup` nhưng thiếu định nghĩa trọn vẹn trong một đoạn rõ ràng nên chỉ nhận mức 1. Các câu `q19`–`q21` và `q23` không có đủ bằng chứng ở top-3.

### Tác động của chiến lược dữ liệu

A → B giảm 14 chunk và tăng Hit@3 dev 2 câu; coherence tăng 0,9 điểm. B → C giữ nguyên chunk, chỉ thay filter khi có điều kiện; tăng Hit@3 dev 1 câu và test 1 câu. Hai ví dụ thất bại: `q19` (JSON) ở cả ba cấu hình lấy nhầm đoạn về dictionary/chuỗi, và `q23` (finally) trả về các đoạn không nói rõ điều kiện thực thi. Với mục tiêu của corpus này, **C là cấu hình được chọn**, nhưng hiệu quả tổng thể còn thấp.

## 5. Giới hạn và hướng cải tiến

Model tiếng Anh được áp dụng cho câu hỏi tiếng Việt, có khả năng làm giảm chất lượng semantic retrieval; kết quả đo chưa tách riêng ảnh hưởng của ngôn ngữ. Đơn vị nguồn được chia theo độ dài chứ không phải trang gốc, nên page ID chỉ có nghĩa trong snapshot này. Exact quote hit là proxy nghiêm ngặt, không đánh giá được bằng chứng tương đương. Mẫu test sáu câu nhỏ và audit chỉ một lượt. Một thử nghiệm tiếp theo nên chốt tập test mới trước khi đổi sang model đa ngữ và đánh giá lại; không dùng tập test hiện tại để báo như holdout mới sau khi tinh chỉnh.
