## FastAPI NoSQL Starter

A RESTful API, asynchronous FastAPI template with MongoDB, Redis, and OAuth 2.0.

## Features

- **Async MongoDB & Redis**: Direct async driver ([pymongo](https://pymongo.readthedocs.io/en/stable/)), connection pooling, and Redis for session / cache storage.
- **Security**: Assymetric RS256 JWT tokens, Argon2 password hashing, and Google OAuth2 via [AuthLib](https://docs.authlib.org/en/stable/oauth2/client/web/fastapi.html#fastapi-integration)
- **Rate limiting**: Built-in Redis rate limiting powered by [SlowAPI](https://github.com/laurents/slowapi)

### Tech Stack

| Component | Tech |
| :--- | :--- |
| Framework | FastAPI + Pydantic v2 |
| Databases | MongoDB & Redis |
| Auth & Crypto | PyJWT (RS256), Argon2, Authlib |
| Infra | Docker Compose, Nginx, Prometheus |
| Tooling | UV, Ruff, Pytest |

### Requirements

List dependencies only:

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Docker & Docker Compose
- MongoDB 7+
- Redis 7+

### Installation

```bash
git clone https://github.com/th0truth/fastapi-nosql-starter && cd fastapi-nosql-starter

# environment and RSA keys
cp .env.example .env
openssl genrsa -out private_key.pem 2048
openssl rsa -in private_key.pem -pubout -out public_key.pem

# run with Docker

docker compose up -d --build

# or

bash scripts/run.sh
```

#### Local Setup

```bash
# install dependencies
uv sync

# run server
uv run uvicorn src.app.main:create_app --reload
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for complete details.

