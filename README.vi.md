# Fastie (Tiếng Việt)

**Fastie** là một web framework hiện đại dựa trên **FastAPI**, được thiết kế với triết lý của **Laravel Artisan**. Fastie cung cấp cấu trúc dự án chuẩn mực, hệ thống Dependency Injection mạnh mẽ và bộ công cụ CLI chuyên nghiệp để tăng tốc quá trình phát hành ứng dụng.

Tiếng Anh: [English](README.md)

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Tính năng chính

- **Clean Architecture**: Tách biệt logic nghiệp vụ thông qua Repository & Service layer.
- **Dependency Injection**: Quản lý phụ thuộc tự động với Decorators (`@inject`, `@controller`).
- **Fastie CLI**: Bộ công cụ dòng lệnh giúp tạo boilerplate code và quản lý database.
- **Soft Delete**: Hỗ trợ xóa mềm tích hợp sẵn trong lớp Repository cơ bản.
- **Modern UI**: Giao diện dòng lệnh trực quan và chuyên nghiệp.

## Cài đặt

Cài đặt thông qua pip:

```bash
pip install fastie-py
```

Khởi tạo dự án mới:

```bash
fastie new my_project
cd my_project
```

## CLI Reference

### Dự án & Server
- `fastie new <name>`: Khởi tạo dự án mới.
- `fastie serve`: Chạy server phát triển (auto-reload).
- `fastie routes`: Liệt kê tất cả route hiện có.

### Code Generation (make)
- `fastie make controller <Name>`: Tạo Controller mới.
- `fastie make service <Name>`: Tạo Service mới.
- `fastie make repository <Name>`: Tạo Repository mới.
- `fastie make model <Name>`: Tạo SQLAlchemy Model.
- `fastie make migration <Name>`: Tạo file migration.

### Database (db)
- `fastie db migrate`: Thực thi migration.
- `fastie db rollback`: Quay lại migration trước ở môi trường development; production cần `--force`.
- `fastie db reset`: Xóa và dựng lại database, chỉ cho development.
- `fastie db status`: Xem trạng thái database.
- `fastie db check`: Kiểm tra migration graph chỉ có một head và schema không lệch model.

### Quy trình migration

Mỗi migration cần được tạo, review và kiểm tra trước khi áp dụng:

```bash
fastie make migration add_profile_fields --auto
fastie db check
fastie db migrate
```

Fastie yêu cầu migration có một head duy nhất. Nếu các branch song song tạo nhiều head,
cần merge rõ ràng trước khi migrate hoặc tạo migration tiếp theo:

```bash
alembic merge -m "merge migration heads" <head-one> <head-two>
fastie db check
```

Production nên chạy `fastie db migrate` như một bước riêng trong deploy trước khi rollout ứng dụng.
Ứng dụng không tự chạy migration khi startup; rollback/reset destructive không nằm trong workflow production.

Trong production, cần cấu hình `JWT_SECRET` là chuỗi ngẫu nhiên tối thiểu 32 ký tự, khai báo rõ
`CORS_ALLOWED_ORIGINS`, và cung cấp `REDIS_URL` để rate limit được chia sẻ giữa các worker.

## Ví dụ sử dụng

### Dependency Injection

```python
@controller
@inject
class UserController(BaseController):
    def __init__(self, user_service: IUserService):
        self.user_service = user_service
        
    def define_routes(self):
        self.router.get("/")(self.index)

    async def index(self):
        return self.success(content=self.user_service.get_all())
```

### Soft Delete

```python
# Xóa mềm
self.repository.delete(id)

# Khôi phục
self.repository.restore(id)

# Lấy dữ liệu bao gồm cả mục đã xóa
items = self.repository.get_all(with_trash=True)
```

## Đóng góp

Mọi đóng góp nhằm cải thiện Fastie đều được trân trọng! Vui lòng fork repository và tạo pull request.

## License

Phát hành dưới giấy phép **MIT License**. Xem chi tiết tại [LICENSE](LICENSE).

---
Sản phẩm được phát triển bởi **Phuong Nha Nguyen** với sự cộng tác của **Antigravity (Google DeepMind)**.
