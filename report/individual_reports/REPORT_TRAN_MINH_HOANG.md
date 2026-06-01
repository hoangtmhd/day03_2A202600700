# Báo Cáo Cá Nhân: Lab 3 - Chatbot vs ReAct Agent

- **Họ và tên học viên**: Trần Minh Hoàng
- **Mã số học viên**: 2A202600700
- **Ngày hoàn thành**: 2026-06-01

---

## I. Đóng Góp Kỹ Thuật Cá Nhân (Technical Contribution - 15 Điểm)

Trong bài tập Lab 3 này, đóng góp chính của tôi tập trung vào việc thiết kế bộ công cụ thực tế, tối ưu hóa bộ phân tích đối số động (Dynamic Argument Parser) và nâng cao khả năng xử lý ngoại lệ trong vòng lặp lập luận.

### 1. Hiện thực hóa các Công cụ Thương mại Điện tử
Tôi đã trực tiếp thiết kế cấu trúc dữ liệu và logic cho 3 công cụ mô phỏng thực tế tại tập tin `src/tools/ecommerce_tools.py`:
- [ecommerce_tools.py](file:///d:/Work/Study/ai-in-action/Lab3/Day-3-Lab-Chatbot-vs-react-agent/src/tools/ecommerce_tools.py#L22-L68)
  - `check_stock`: Thực hiện chuẩn hóa tên sản phẩm (loại bỏ khoảng trắng, đưa về chữ thường), xử lý dấu ngoặc đơn/kép do LLM sinh ra, và đưa ra danh sách các sản phẩm sẵn có nếu người dùng nhập sai tên.
  - `get_discount`: Xác thực mã coupon bằng cách đưa về dạng chữ in hoa và tra cứu chiết khấu tương ứng.
  - `calc_shipping`: Tích hợp bộ xử lý chuỗi thông minh để trích xuất số thực (float) từ các tham số văn bản (ví dụ: chuyển đổi chuỗi `"1.5kg"` thành số thực `1.5`) và tính chi phí giao hàng theo từng tỉnh thành.

### 2. Bộ Phân Phối Công Cụ Động (Dynamic Tool Dispatcher)
Tôi đã xây dựng cơ chế phân tích đối số và thực thi hàm động bên trong vòng lặp ReAct trong tập tin `src/agent/agent.py`:
- [agent.py](file:///d:/Work/Study/ai-in-action/Lab3/Day-3-Lab-Chatbot-vs-react-agent/src/agent/agent.py#L111-L157)
  - Trích xuất tham số từ định dạng chuỗi `tool_name(args)` thông qua biểu thức chính quy (Regex).
  - Hỗ trợ phân tích cả tham số vị trí (positional args), tham số từ khóa (keyword args) và định dạng JSON phức tạp được sinh ra bởi các LLM cao cấp.
  - Tích hợp cơ chế tự động ép kiểu dữ liệu chuỗi số sang định dạng số thực/số nguyên nhằm tránh lỗi không khớp kiểu dữ liệu (`TypeError`) khi gọi hàm Python.

---

## II. Nghiên Cứu Tình Huống Debug Lỗi Thực Tế (Debugging Case Study - 10 Điểm)

### 1. Mô tả bài toán và Lỗi phát sinh
Trong quá trình kiểm thử kịch bản thanh toán đa bước phức tạp (Scenario 3) với phiên bản Agent v1, hệ thống đã bị treo hoặc sinh lỗi do LLM truyền tham số công cụ kèm theo đơn vị đo lường văn bản.
- **Dòng vết lỗi thu được**:
  ```text
  Action: calc_shipping(weight="1.0kg", destination="Hanoi")
  ```
  Hành vi này dẫn đến lỗi ngoại lệ `TypeError: weight must be a float, got str` khi thực thi hàm tính toán phí giao hàng, làm sập toàn bộ chu trình lập luận của Agent.

### 2. Chẩn đoán nguyên nhân (Diagnosis)
1. **Lỗi từ Prompt**: System Prompt ở phiên bản v1 chưa quy định chặt chẽ việc LLM bắt buộc phải truyền giá trị số thô (ví dụ: `1.0`) mà không được kèm theo đơn vị đo lường (như `"kg"`).
2. **Lỗi từ Code xử lý**: Hàm thực thi công cụ trong Agent v1 nhận chuỗi tham số thô trực tiếp từ LLM và truyền thẳng vào hàm Python mà không qua bất kỳ bước làm sạch hay chuẩn hóa kiểu dữ liệu nào.

### 3. Giải pháp khắc phục (Triển khai trên Agent v2)
Tôi đã giải quyết triệt để lỗi này bằng hai giải pháp đồng bộ:
- **Lọc sạch tham số đầu vào (Regex Arguments Sanitizer)**: Bổ sung bộ xử lý chuỗi trong hàm `_execute_tool` để tự động tách bỏ mọi ký tự đơn vị đo lường dư thừa (như `"kg"`, `"VND"`, `"$"`), loại bỏ dấu nháy và tự động ép kiểu dữ liệu về dạng số thực trước khi gọi hàm:
  ```python
  if isinstance(weight, str):
      weight_str = re.sub(r"[^\d\.]", "", weight)
      weight = float(weight_str)
  ```
- **Cơ chế Tự sửa lỗi (Self-Correction feedback loop)**: Bao bọc lời gọi hàm trong khối lệnh `try-except`. Nếu xảy ra bất kỳ lỗi thực thi nào, lỗi đó sẽ được bắt lại và trả về cho LLM dưới dạng một `Observation: <Thông tin lỗi>`. Nhờ vậy, LLM sẽ nhận biết được lỗi sai cấu trúc của mình ở bước trước để tự động điều chỉnh và gọi lại công cụ một cách chính xác trong lượt lập luận tiếp theo mà không làm crash chương trình.

---

## III. Trải Nghiệm & Nhận Thức Cá Nhân: Chatbot vs ReAct (10 Điểm)

Trải qua quá trình trực tiếp xây dựng và chạy thử nghiệm đối chứng, tôi đã rút ra được những nhận thức sâu sắc về khả năng lập luận của LLM:

1.  **Lập luận (Reasoning) so với Sinh văn bản trực tiếp**:
    Khối suy nghĩ `Thought` hoạt động giống như một "bảng nháp tư duy" (scratchpad) bắt LLM phải lên kế hoạch và giải quyết bài toán từng bước một trước khi hành động. Chatbot truyền thống sinh câu trả lời ngay lập tức dựa trên liên kết ngữ nghĩa từ vựng, dẫn đến việc "ảo tưởng" (hallucination) nghiêm trọng khi gặp các bài toán đòi hỏi tính toán logic và đối chiếu dữ liệu.
2.  **Khả năng neo giữ thông tin thực tế (Grounding)**:
    ReAct Agent duy trì tính chính xác cao nhờ các phản hồi thực tế (`Observation`) từ môi trường bên ngoài. Phản hồi thực tế này định hướng cho các bước tiếp theo của mô hình, giúp kiểm chứng kết quả và tự động sửa sai nếu các bước trước đó có lỗi.
3.  **Sự đánh đổi về chi phí và tài nguyên (Latency vs Token)**:
    Đối với các tác vụ đơn giản (như hỏi đáp thông tin tĩnh), ReAct Agent hoạt động kém hiệu quả hơn hẳn so với Chatbot thông thường. Agent tiêu tốn lượng Token nhiều gấp ~4 lần và độ trễ cao gấp ~2.3 lần do phải chạy qua nhiều vòng lặp `Thought-Action` không cần thiết. Vì vậy, việc thiết kế bộ định tuyến câu hỏi (Query Router) để phân tách tác vụ đơn giản và phức tạp là cực kỳ quan trọng trong thực tế.

---

## IV. Đề Xuất Cải Tiến Trong Tương Lai (Future Improvements - 5 Điểm)

Để đưa hệ thống Agent thử nghiệm này lên mức độ sẵn sàng vận hành trong môi trường doanh nghiệp thực tế, tôi đề xuất:

1.  **Thực thi công cụ bất đồng bộ (Asynchronous Tool Execution)**: Áp dụng thư viện `asyncio` để cho phép Agent gọi song song nhiều công cụ độc lập (ví dụ: kiểm tra số lượng tồn kho của nhiều mặt hàng cùng lúc), giúp giảm đáng kể tổng độ trễ phản hồi của hệ thống.
2.  **Hệ thống giám sát an toàn (Guardrails & Input Sanitization)**: Tích hợp thư viện bảo mật như NeMo Guardrails để kiểm soát chặt chẽ cả dữ liệu đầu vào của người dùng (ngăn chặn tấn công Prompt Injection) và mã lệnh đầu ra của LLM trước khi chuyển tới bộ điều phối công cụ, đảm bảo hệ thống không thực thi các tác vụ độc hại.
3.  **Lấy công cụ theo ngữ nghĩa (Semantic Tool Retrieval)**: Khi số lượng công cụ trong doanh nghiệp tăng lên hàng trăm hoặc hàng nghìn API, chúng ta không thể đưa toàn bộ mô tả vào ngữ cảnh hệ thống. Việc áp dụng **Vector Database** (như Chroma hay Qdrant) để chỉ tìm kiếm và nhúng từ 3-5 công cụ phù hợp nhất theo ngữ nghĩa câu hỏi sẽ giúp tiết kiệm tối đa chi phí Token và tối ưu hóa hiệu năng của Agent.
