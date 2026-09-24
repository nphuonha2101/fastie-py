# Fastie (Tiếng Việt)

Fastie là nền tảng backend dựa trên **FastAPI**, ưu tiên convention và tốc độ
dev. Project mới sinh ra dùng FastAPI thuần: `APIRouter`, `Depends(get_db)`,
SQLAlchemy, Pydantic và migration tường minh.

Tiếng Anh: [English](README.md)

## Có sẵn

- Router FastAPI và SQLAlchemy session theo từng request.
- OAuth2 password flow, bearer token, kiểm tra claim bằng PyJWT và hash mật khẩu
  Argon2 qua `pwdlib` (vẫn verify bcrypt cũ và tự nâng hash sau login thành công).
- Alembic migration có kiểm tra một head duy nhất và schema drift.
- `fastie make resource` tạo model, schema và CRUD router.
- Trường soft delete trong model base dùng chung.
- Rate limit dùng Redis khi cấu hình `REDIS_URL`.

## Bắt đầu nhanh

```bash
pip install fastie-py
fastie new my_project --database sqlite
cd my_project
pip install -r requirements.txt
fastie db migrate
fastie dev
```

API mặc định nằm dưới `/api/v1`. Endpoint OAuth2 chuẩn là
`POST /api/v1/auth/token`, nhận form `username` và `password`.
`/api/v1/auth/login` vẫn có để client JSON dùng tiện hơn.

## Tạo resource

```bash
fastie make resource Product --fields "name:str,price:decimal,is_active:bool"
fastie make migration add_products_table --auto
fastie db check
fastie db migrate
```

Lệnh này tạo model SQLAlchemy, schema create/update/response, CRUD router
FastAPI và tự đăng ký router vào project mới. Vẫn nên review code và migration
trước khi chạy production.

## CLI chính

- `fastie new <name>`: Tạo project.
- `fastie dev`: Chạy Uvicorn có auto-reload trên localhost.
- `fastie serve`: Chạy Uvicorn không auto-reload mặc định.
- `fastie routes`: Liệt kê route.
- `fastie make resource <Name>`: Tạo luồng CRUD mặc định.
- `fastie make model <Name>`: Chỉ tạo model.
- `fastie make migration <Name>`: Tạo migration để review.
- `fastie db migrate`: Apply migration.
- `fastie db check`: Kiểm tra migration graph và schema drift.
- `fastie db status`: Xem trạng thái migration.
- `fastie db rollback`: Rollback ở development; production cần `--force`.
- `fastie db reset`: Reset database ngoài production.

Production nên chạy `fastie db check` và `fastie db migrate` như các bước riêng
trong deploy trước khi rollout app. App không tự chạy migration lúc startup.

## Cấu hình auth

```dotenv
JWT_SECRET=<secret ngẫu nhiên tối thiểu 32 ký tự>
JWT_ALGORITHM=HS256
JWT_ISSUER=fastie
JWT_AUDIENCE=fastie-api
ACCESS_TOKEN_EXPIRE_MINUTES=30
CORS_ALLOWED_ORIGINS=https://api.example.com
REDIS_URL=redis://localhost:6379/0
```

JWT chỉ được ký, không được mã hóa; không đưa password hoặc dữ liệu nhạy cảm
vào payload. Khi cần scale lớn hơn, có thể thay wrapper JWT bằng OIDC provider
và JWKS mà không phải đổi hình dạng dependency của route.

## License

MIT License. Xem [LICENSE](LICENSE).
