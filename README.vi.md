# Fastie (Tiếng Việt)

Fastie là nền tảng backend dựa trên **FastAPI**, ưu tiên convention và tốc độ
dev. Project mới sinh ra dùng FastAPI thuần: `APIRouter`, `Depends(get_db)`,
SQLAlchemy, Pydantic và migration tường minh.

> Fastie hiện chưa được publish lên PyPI. Các lệnh dưới đây giả định bạn đang
> dùng source checkout và cài package ở chế độ editable.

Tiếng Anh: [English](README.md)

## Có sẵn

- Router FastAPI và SQLAlchemy session theo từng request.
- OAuth2 password flow, bearer token, kiểm tra claim bằng PyJWT và hash mật khẩu
  Argon2 qua `pwdlib`.
- Alembic migration có kiểm tra một head duy nhất và schema drift.
- `fastie make resource` tạo model, schema và CRUD router.
- Trường soft delete trong model base dùng chung.
- Rate limit dùng Redis khi cấu hình `REDIS_URL`.

## Bắt đầu nhanh

```bash
git clone https://github.com/nphuonha2101/fastie-py.git
cd fastie-py
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
fastie new my_project --database sqlite
cd my_project
pip install -r requirements.txt
fastie db migrate
fastie dev
```

API mặc định nằm dưới `/api/v1`. Endpoint OAuth2 chuẩn là
`POST /api/v1/auth/token`, nhận form `username` và `password`.
Endpoint trả về access token ngắn hạn và refresh token có rotation.

Để tạo nhanh stack Docker gồm PostgreSQL, Redis, application container chạy
non-root và một service migration chạy trước API, hãy trỏ Docker setup vào
source Fastie local vì package chưa được publish:

```bash
fastie setup docker --database postgres --local-source ..
cp .env.docker.example .env.docker
# Sửa secret, domain và CORS trong .env.docker.
docker compose --env-file .env.docker up --build
```

Dùng `--database mysql` nếu chọn MySQL. Hãy review các giá trị được sinh ra và
dùng secret manager cho credential production thật.
Tuỳ chọn `--local-source` sẽ build wheel local trong `.fastie-local/`.

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
- `fastie setup docker`: Tạo Dockerfile, Compose stack và template biến môi trường Docker; dùng `--local-source <path>` để test source chưa publish.
- `fastie dev`: Chạy Uvicorn có auto-reload trên localhost.
- `fastie serve`: Chạy Uvicorn không auto-reload mặc định.
- `fastie routes`: Liệt kê route.
- `fastie test`: Chạy test suite. Cài `requirements-test.txt` trước.
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

## Testing

Project generate sẵn SQLite test fixture, FastAPI `TestClient` và dependency
overrides. Cài dependency test rồi chạy từ root project:

```bash
pip install -r requirements-test.txt
fastie test
```

Dùng `fastie test --coverage` để xem coverage. Có thể truyền thêm argument của
pytest, ví dụ `fastie test tests/api/test_auth.py`.

Để dependency của Fastie ổn định trong development và CI, dùng
`uv sync --locked`; file `uv.lock` được commit cùng source.

## Cấu hình auth

```dotenv
JWT_SECRET=<secret ngẫu nhiên tối thiểu 32 ký tự>
JWT_ALGORITHM=HS256
JWT_ISSUER=fastie
JWT_AUDIENCE=fastie-api
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
CORS_ALLOWED_ORIGINS=https://api.example.com
ALLOWED_HOSTS=api.example.com
REDIS_URL=redis://localhost:6379/0
TRUSTED_PROXY_IPS=10.0.0.0/8
```

JWT chỉ được ký, không được mã hóa; không đưa password hoặc dữ liệu nhạy cảm
vào payload. Khi cần scale lớn hơn, có thể thay wrapper JWT bằng OIDC provider
và JWKS mà không phải đổi hình dạng dependency của route.

Ở production, chạy nhiều worker phía sau trusted reverse proxy, bật
`--proxy-headers` cùng `--forwarded-allow-ips` cụ thể, rồi chạy `fastie db check`
trước `fastie db migrate`. Không dùng SQLite hoặc CORS/host wildcard ở production.

## License

MIT License. Xem [LICENSE](LICENSE).
