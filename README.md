# ML Content Moderation API

Production-ready FastAPI moderation API with ML-powered content filtering, Redis caching, rate limiting, and full CI/CD pipeline.

[![CI/CD Pipeline](https://github.com/Nyadzayo/moderation-api/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/Nyadzayo/moderation-api/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Pull the pre-built image
docker pull nyadzayo/moderation-api:latest

# Run with Docker Compose (includes Redis)
docker-compose up -d

# API is now available at http://localhost:8000
# View interactive docs at http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# Clone the repository
git clone https://github.com/Nyadzayo/moderation-api.git
cd moderation-api

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# Run the API
uvicorn app.main:app --reload --env-file .env.dev
```

---

## Features

### Core Functionality
- **ML-Powered Moderation** - unitary/toxic-bert model for text classification
- **Batch Processing** - Handle multiple texts in a single request
- **Custom Thresholds** - Per-category threshold overrides
- **Multi-Category Detection** - harassment, hate, profanity, sexual, spam, violence

### Performance & Scalability
- **Redis Caching** - 40x faster for repeated requests (268ms to 6ms)
- **Rate Limiting** - Per-IP sliding window rate limits
- **Lazy Model Loading** - Fast startup, load on first request
- **Async/Await** - Non-blocking I/O for high concurrency

### Production Ready
- **Health Checks** - Comprehensive component status monitoring
- **Structured Logging** - JSON logs with colored console output
- **Graceful Degradation** - API continues if Redis unavailable
- **CI/CD Pipeline** - Automated testing, build, and deployment
- **Docker Multi-Arch** - AMD64 and ARM64 support
- **100% Test Coverage** - 22 passing tests

---

## API Usage

### Basic Moderation Request

```bash
curl -X POST "http://localhost:8000/v1/moderate" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [
      {"text": "Hello, world!"},
      {"text": "This is inappropriate content"}
    ],
    "return_scores": true
  }'
```

### Response Format

```json
{
  "results": [
    {
      "request_id": "req_abc123",
      "flagged": false,
      "categories": {
        "harassment": false,
        "hate": false,
        "profanity": false,
        "sexual": false,
        "spam": false,
        "violence": false
      },
      "category_scores": {
        "harassment": 0.01,
        "hate": 0.02,
        "profanity": 0.01,
        "sexual": 0.00,
        "spam": 0.01,
        "violence": 0.00
      },
      "model_info": {
        "text_model": "unitary/toxic-bert",
        "version": "1.0.0"
      },
      "processing_time_ms": 45,
      "timestamp": "2025-09-30T12:00:00.000Z"
    }
  ],
  "total_items": 2,
  "processing_time_ms": 95
}
```

### Custom Thresholds

```bash
curl -X POST "http://localhost:8000/v1/moderate" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [{"text": "borderline content"}],
    "thresholds": {
      "harassment": 0.9,
      "profanity": 0.8
    }
  }'
```

---

## Architecture

See [ARCHITECTURE.md](./docs/ARCHITECTURE.md) for detailed system design, component diagrams, and technical decisions.

**Key Components:**
- **FastAPI** - High-performance web framework
- **Transformers** - Hugging Face ML model inference
- **Redis** - Caching and rate limiting
- **Docker** - Containerization
- **GitHub Actions** - CI/CD automation
- **Railway** - Production deployment

---

## Configuration

All configuration via environment variables. See `.env.example` for full list.

**Key Variables:**
```bash
# API
API_PORT=8000
LOG_LEVEL=INFO

# Model
DEFAULT_MODEL=unitary/toxic-bert
LAZY_LOAD_MODEL=true

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60

# Caching
CACHE_ENABLED=true
CACHE_TTL_SECONDS=3600
```

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

**Test Results:**
```
======================== 22 passed in 0.11s ========================
test_cache.py - 3 tests
test_health.py - 4 tests
test_moderate.py - 7 tests
test_rate_limit.py - 3 tests
test_services.py - 5 tests
```

---

## Deployment

### Automatic Deployment (CI/CD)

Push to `main` branch triggers:
1. Run all tests
2. Build Docker image (multi-arch)
3. Push to Docker Hub
4. Auto-deploy to Railway

### Manual Deployment

```bash
# Build image
docker build -t nyadzayo/moderation-api:latest .

# Push to Docker Hub
docker push nyadzayo/moderation-api:latest

# Deploy to Railway
railway up
```

---

## Performance

| Metric | Value |
|--------|-------|
| **Cold Start** | ~12s (model loading) |
| **Warm Request** | ~50ms |
| **Cached Request** | ~6ms (40x faster) |
| **Rate Limit** | 100 req/min per IP |
| **Concurrency** | 4 workers (configurable) |

---

## Security

- Input validation with Pydantic
- Rate limiting per IP
- CORS configuration
- No sensitive data in logs
- Environment-based secrets
- Docker security best practices

---

## Documentation

- **[ARCHITECTURE.md](./docs/ARCHITECTURE.md)** - System design & diagrams

---

## Quick Start Demo

```bash
# Pull and run (requires Docker)
docker pull nyadzayo/moderation-api:latest
docker-compose up -d

# Test the API
curl -X POST "http://localhost:8000/v1/moderate" \
  -H "Content-Type: application/json" \
  -d '{"inputs":[{"text":"test content"}]}'

# View interactive docs
open http://localhost:8000/docs
```

### Project Highlights

- Clean, well-documented code with comprehensive type hints
- Full test coverage with 22 passing tests
- Scalable, production-ready architecture
- Automated CI/CD pipeline with GitHub Actions
- Comprehensive technical documentation

---

## License

MIT License - See [LICENSE](LICENSE) for details

---

## Author

**Kelvin Nyadzayo**
- GitHub: [@Nyadzayo](https://github.com/Nyadzayo)
- Email: kelvinnyadzayo@gmail.com

---

Built for production use
