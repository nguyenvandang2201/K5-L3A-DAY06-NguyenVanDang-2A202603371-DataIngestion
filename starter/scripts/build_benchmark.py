"""Freeze human-written questions against verified corpus excerpts before retrieval."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = [json.loads(line) for line in (ROOT / "data/corpus.jsonl").read_text(encoding="utf-8").splitlines()]

# id, chapter, question, answer, exact supporting excerpt, question type, filter?
SPECS = [
    ("q01", "introduction", "Trong ví dụ Python, chú thích bắt đầu bằng ký tự nào?", "Dấu #.", "Comments in Python start with the hash character", "direct", False),
    ("q02", "introduction", "Trong phần giới thiệu, toán tử nào dùng cho phép chia lấy phần nguyên theo floor?", "//.", "17 // 3 # floor division discards the fractional part", "paraphrase", True),
    ("q03", "introduction", "Làm sao để dấu gạch chéo ngược trong chuỗi không bị hiểu là ký tự đặc biệt?", "Thêm tiền tố r để tạo raw string.", "you can use raw strings by adding an r before the first quote", "direct", False),
    ("q04", "introduction", "Theo tài liệu, list có thay đổi nội dung được không?", "Có, list là kiểu mutable.", "lists are a mutable type", "direct", False),
    ("q05", "controlflow", "Giá trị điểm cuối của range() có nằm trong dãy sinh ra không?", "Không.", "The given end point is never part of the generated sequence", "condition", True),
    ("q06", "controlflow", "Khi nào else gắn với vòng lặp được thực thi?", "Khi vòng lặp kết thúc mà không gặp break.", "If the loop finishes without executing the break , the else clause executes", "condition", False),
    ("q07", "controlflow", "Lệnh pass thực hiện thao tác gì?", "Không làm gì.", "The pass statement does nothing", "direct", False),
    ("q08", "controlflow", "Từ khóa nào bắt đầu định nghĩa hàm?", "def.", "The keyword def introduces a function definition", "direct", False),
    ("q09", "datastructures", "Các phương thức list chỉ sửa đổi tại chỗ thường trả về gì?", "None.", "only modify the list have no return value printed", "paraphrase", True),
    ("q10", "datastructures", "List có thể làm stack theo nguyên tắc nào?", "LIFO, vào sau ra trước.", "last-in, first-out", "direct", False),
    ("q11", "datastructures", "Set có cho phép phần tử trùng nhau không?", "Không.", "A set is an unordered collection with no duplicate elements", "condition", False),
    ("q12", "datastructures", "Các khóa trong dictionary có được trùng nhau không?", "Không, khóa phải duy nhất.", "the keys are unique (within one dictionary)", "condition", False),
    ("q13", "modules", "Một module Python là loại file nào?", "File chứa định nghĩa và câu lệnh Python, có đuôi .py.", "A module is a file containing Python definitions and statements", "direct", True),
    ("q14", "modules", "Các câu lệnh khởi tạo trong module chạy bao nhiêu lần khi import?", "Chỉ lần đầu tên module được gặp trong câu lệnh import.", "They are executed only the first time the module name is encountered in an import statement", "condition", False),
    ("q15", "modules", "Đọc từ file .pyc có làm chương trình chạy nhanh hơn không?", "Không, chỉ tốc độ nạp nhanh hơn.", "A program doesn’t run any faster when it is read from a .pyc file", "condition", False),
    ("q16", "modules", "Package tổ chức namespace của module bằng dạng tên gì?", "Tên module có dấu chấm.", "dotted module names", "paraphrase", False),
    ("q17", "inputoutput", "F-string chèn giá trị biểu thức bằng cú pháp nào?", "Tiền tố f/F và biểu thức trong dấu ngoặc nhọn.", "prefixing the string with f or F and writing expressions as {expression}", "direct", False),
    ("q18", "inputoutput", "Tại sao nên dùng with khi làm việc với file?", "File được đóng kể cả khi phát sinh exception.", "properly closed after its suite finishes, even if an exception is raised", "condition", True),
    ("q19", "inputoutput", "Định dạng nào được Python dùng phổ biến để trao đổi dữ liệu có cấu trúc?", "JSON.", "popular data interchange format called JSON", "paraphrase", False),
    ("q20", "inputoutput", "str.zfill() thêm ký tự gì ở bên trái chuỗi số?", "Số 0.", "pads a numeric string on the left with zeros", "direct", False),
    ("q21", "errors", "Tài liệu phân biệt hai loại lỗi cơ bản nào?", "Syntax errors và exceptions.", "two distinguishable kinds of errors: syntax errors and exceptions", "direct", False),
    ("q22", "errors", "except bắt được ngoại lệ thuộc lớp con của lớp ghi trong except không?", "Có.", "instances of the class itself or one of its derived classes", "condition", True),
    ("q23", "errors", "Khối finally có chạy khi phát sinh lỗi không?", "Có, finally vẫn chạy.", "the finally clause is executed in any event", "condition", False),
    ("q24", "errors", "ExceptionGroup dùng để làm gì?", "Gom nhiều instance ngoại lệ để raise cùng nhau.", "wraps a list of exception instances so that they can be raised together", "paraphrase", False),
]


def main() -> None:
    benchmark = []
    for i, (qid, chapter, question, answer, quote, kind, use_filter) in enumerate(SPECS):
        matches = [page for page in PAGES if page["document_id"] == chapter and
                   " ".join(quote.split()) in " ".join(page["text"].split())]
        if len(matches) != 1:
            raise ValueError(f"{qid}: evidence found on {len(matches)} pages, expected one")
        page = matches[0]
        benchmark.append({"id": qid, "split": "dev" if i < 18 else "test",
                          "type": kind, "question": question, "expected_answer": answer,
                          "gold_source_id": chapter, "gold_page": page["page"],
                          "evidence_quote": quote,
                          "filter": {"chapter": chapter} if use_filter else None})
    folder = ROOT / "benchmark"
    folder.mkdir(exist_ok=True)
    (folder / "questions.json").write_text(json.dumps(benchmark, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(benchmark)} verified questions: 18 dev, 6 test")


if __name__ == "__main__":
    main()
