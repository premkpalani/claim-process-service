# Claim Process Service

A production-ready dockerized FastAPI service for processing healthcare claims with transaction-based billing.

## Features

- ✅ **Claim Processing**: Process claims with multiple line items
- ✅ **Net Fee Calculation**: Automatic calculation using formula: `net_fee = provider_fees + member_coinsurance + member_copay - allowed_fees`
- ✅ **Data Validation**: Flexible validation for procedure codes (must start with 'D') and Provider NPI (must be 10 digits)
- ✅ **Top Providers Analytics**: Optimized endpoint to get top N providers by net fees with O(n log n) performance
- ✅ **Rate Limiting**: 10 requests/minute to prevent abuse
- ✅ **PostgreSQL + SQLModel**: Full ORM support with database migrations
- ✅ **Docker Compose**: One-command deployment of app + database
- ✅ **Comprehensive Tests**: Unit and integration tests with >90% coverage
- ✅ **Payment Service Integration**: Detailed architecture for distributed transaction handling

## Architecture

```
┌─────────────────┐
│   FastAPI App   │
│  (claim_process)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│   PostgreSQL    │◄────►│  Message Queue   │
│    Database     │      │ (RabbitMQ/Kafka) │
└─────────────────┘      └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Payments Service │
                         └──────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd claim_process
```

### 2. Start the Services

```bash
docker-compose up --build
```

This single command will:
- Build the FastAPI application image
- Start PostgreSQL database
- Run database migrations
- Start the API server on port 8000

### 3. Verify Deployment

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### 4. View API Documentation

Open your browser to:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### POST /claims

Create a new claim with multiple lines.

**Request:**
```json
{
  "claim_reference": "claim_1234",
  "lines": [
    {
      "service_date": "2018-03-28",
      "submitted_procedure": "D0180",
      "quadrant": null,
      "plan_group": "GRP-1000",
      "subscriber_number": "3730189502",
      "provider_npi": "1497775530",
      "provider_fees": 100.00,
      "allowed_fees": 100.00,
      "member_coinsurance": 0.00,
      "member_copay": 0.00
    }
  ]
}
```

**Response:**
```json
{
  "id": 1,
  "claim_reference": "claim_1234",
  "status": "processed",
  "total_net_fee": "0.00",
  "created_at": "2024-01-08T12:00:00Z",
  "lines": [...]
}
```

### GET /claims/{claim_id}

Retrieve a claim by ID.

**Response:**
```json
{
  "id": 1,
  "claim_reference": "claim_1234",
  "status": "processed",
  "total_net_fee": "0.00",
  "created_at": "2024-01-08T12:00:00Z",
  "lines": [...]
}
```

### GET /providers/top?limit=10

Get top N providers by net fees generated.

**Performance Optimization:**
- Database-level aggregation (SQL GROUP BY + SUM)
- Indexed provider_npi column
- Single query (no N+1 problem)
- Algorithm: O(n log n) where n = unique providers
- Space: O(k) where k = limit

**Response:**
```json
[
  {
    "provider_npi": "1497775530",
    "total_net_fees": "1234.56",
    "claim_count": 42,
    "rank": 1
  }
]
```

### GET /health

Health check endpoint for container orchestration.

## Data Validation

### Submitted Procedure
- **Rule**: Must start with letter 'D'
- **Case**: Insensitive (normalized to uppercase)
- **Example**: `D0180`, `d0210` ✅ | `X0180` ❌

### Provider NPI
- **Rule**: Must be exactly 10 digits
- **Format**: Numeric only
- **Example**: `1497775530` ✅ | `12345` ❌, `149A775530` ❌

### Quadrant
- **Rule**: Optional field
- **Example**: `"UR"`, `"UL"`, `null` ✅

### Other Fields
- All fields except `quadrant` are **required**

## Net Fee Calculation

Formula:
```
net_fee = provider_fees + member_coinsurance + member_copay - allowed_fees
```

Example:
```
provider_fees:       $130.00
member_coinsurance:  $ 16.25
member_copay:        $  0.00
allowed_fees:        $ 65.00
─────────────────────────────
net_fee:             $ 81.25
```

## Payment Service Communication

The service implements a robust distributed architecture for communicating with the downstream payments service.

### Key Design Decisions

1. **Asynchronous Messaging** (RabbitMQ/Kafka)
   - Decoupled services
   - Built-in retry and DLQ
   - Handles high volumes

2. **Transaction Outbox Pattern**
   - Ensures atomicity
   - Messages published reliably
   - No lost payments

3. **Idempotency**
   - Duplicate detection
   - Safe retries
   - Uses idempotency keys

4. **Saga Pattern**
   - Distributed transactions
   - Compensating transactions
   - Rollback handling

### Failure Scenarios

**1. claim_process fails after sending message:**
- Message persists in queue
- payments service processes it
- Uses transaction outbox for atomicity

**2. payments service fails:**
- Message moves to retry queue
- Exponential backoff (2^n seconds)
- After max retries → Dead Letter Queue (DLQ)
- Alerts sent to operations team

**3. Network partition:**
- Messages persist in durable queue
- Consumers reconnect automatically
- Idempotency prevents duplicates

### Concurrent Instances

Multiple instances of both services can run concurrently:
- Queue ensures exactly-once processing
- Database locks prevent race conditions
- Idempotency keys for safety
- Distributed locks (Redis) for critical sections

**Full implementation details in:** `app/payment_service.py`

## Rate Limiting

All endpoints are rate-limited to **10 requests per minute** per client IP.

When limit exceeded:
```json
{
  "error": "Rate limit exceeded: 10 per 1 minute"
}
```

Response code: `429 Too Many Requests`

## Running Tests

### Run All Tests

```bash
# Inside Docker container
docker-compose run app pytest

# Or locally (requires Python 3.11+)
pip install -r requirements.txt
pytest
```

### Run with Coverage

```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Test Structure

```
tests/
├── conftest.py          # Test fixtures
├── test_models.py       # Data validation tests
├── test_services.py     # Business logic tests
└── test_api.py          # API endpoint tests
```

## Development

### Local Development (without Docker)

1. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set environment variables:**
```bash
export USE_POSTGRES=false
export DEBUG=true
```

4. **Run the server:**
```bash
python -m app.main
# or
uvicorn app.main:app --reload
```

### Database Migrations

The application uses SQLModel which automatically creates tables on startup.

To manually manage database:

```bash
# Connect to PostgreSQL
docker-compose exec db psql -U claimuser -d claimdb

# View tables
\dt

# View schema
\d claims
\d claim_lines
```

## Configuration

Environment variables (set in `docker-compose.yml` or `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |
| `USE_POSTGRES` | `true` | Use PostgreSQL (false = SQLite) |
| `DEBUG` | `false` | Enable debug mode |
| `RATE_LIMIT_PER_MINUTE` | `10` | Rate limit per minute |
| `ENVIRONMENT` | `production` | Environment name |

## Project Structure

```
claim_process/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── models.py            # SQLModel database models
│   ├── database.py          # Database connection
│   ├── services.py          # Business logic
│   └── payment_service.py   # Payment service integration
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_services.py
│   └── test_api.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .gitignore
├── .dockerignore
└── README.md
```

## Technology Stack

- **Framework**: FastAPI 0.109.0
- **ORM**: SQLModel 0.0.14
- **Database**: PostgreSQL 15 / SQLite (development)
- **Rate Limiting**: SlowAPI 0.1.9
- **Testing**: Pytest 7.4.4
- **Containerization**: Docker & Docker Compose

## Performance Considerations

### Top Providers Endpoint

**Optimization Strategy:**
1. Database-level aggregation (not in-memory)
2. Indexed columns (provider_npi)
3. Single SQL query
4. LIMIT applied at database level

**Scalability:**
- For millions of claims: Use materialized view
- For real-time: Add Redis cache with TTL
- For distributed: Use read replicas

### Database Indexes

```sql
-- Automatically created
CREATE INDEX idx_claim_lines_provider_npi ON claim_lines(provider_npi);
CREATE INDEX idx_claim_lines_claim_id ON claim_lines(claim_id);
CREATE UNIQUE INDEX idx_claims_claim_reference ON claims(claim_reference);
```

## Monitoring & Observability

The service is instrumented for:
- Health checks (`/health`)
- Structured logging
- Request/response tracking
- Error tracking

**Production recommendations:**
- Add Prometheus metrics
- Set up Grafana dashboards
- Configure alerting (PagerDuty/Opsgenie)
- Implement distributed tracing (Jaeger)

## Security

- ✅ Non-root Docker user
- ✅ Environment variable secrets
- ✅ Input validation
- ✅ SQL injection prevention (ORM)
- ✅ Rate limiting
- ✅ Pre-commit security hooks

### Pre-commit Security Hooks

The project includes automated security scanning and build validation via pre-commit hooks:

```bash
# Install dependencies (one-time setup)
pip install -r requirements.txt

# Install pre-commit hooks (one-time setup)
pre-commit install

# Initialize secrets baseline (one-time setup)
detect-secrets scan > .secrets.baseline

# Run all security checks manually
pre-commit run --all-files
```

**Build & Test Validation:**

| Check | Purpose |
|-------|---------|
| **check-ast** | Validates Python syntax - no code with syntax errors can be committed |
| **pytest** | Runs all tests - commits blocked if any test fails |

**Security tools included:**

| Tool | Purpose |
|------|---------|
| **Bandit** | Scans Python code for common security vulnerabilities (SQL injection, hardcoded passwords, etc.) |
| **Safety** | Checks dependencies against known vulnerability databases |
| **detect-secrets** | Prevents committing passwords, API keys, and other secrets |
| **Ruff** | Fast linter with security rules (flake8-bandit) |
| **Checkov** | IaC security scanner for Dockerfile and docker-compose.yml |

**What gets checked on every commit:**
- ✅ Python code compiles with no syntax errors
- ✅ All tests pass (pytest)
- ✅ No hardcoded secrets or API keys
- ✅ No known vulnerable dependencies
- ✅ No common Python security issues (eval, exec, shell injection, etc.)
- ✅ No debug statements left in code
- ✅ YAML/JSON/TOML files are valid
- ✅ Dockerfile follows security best practices (non-root user, healthcheck, etc.)
- ✅ docker-compose.yml has no security misconfigurations

**Production recommendations:**
- Enable HTTPS/TLS
- Add authentication (JWT)
- Implement RBAC
- Use secrets management (Vault)
- Enable audit logging

## Deployment

### Production Checklist

- [ ] Update `POSTGRES_PASSWORD` in docker-compose.yml
- [ ] Set `DEBUG=false`
- [ ] Configure proper `CORS_ORIGINS`
- [ ] Set up database backups
- [ ] Configure log aggregation (ELK/DataDog)
- [ ] Set up monitoring and alerts
- [ ] Enable HTTPS
- [ ] Add authentication
- [ ] Review rate limits
- [ ] Load testing

### Kubernetes Deployment

```yaml
# Example Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: claim-process
spec:
  replicas: 3
  selector:
    matchLabels:
      app: claim-process
  template:
    metadata:
      labels:
        app: claim-process
    spec:
      containers:
      - name: claim-process
        image: claim-process:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secrets
              key: connection-string
```

## Troubleshooting

### Database connection errors

```bash
# Check if PostgreSQL is running
docker-compose ps

# View database logs
docker-compose logs db

# Restart services
docker-compose restart
```

### Application errors

```bash
# View application logs
docker-compose logs app

# Check health
curl http://localhost:8000/health

# Interactive debugging
docker-compose exec app python
```

## License

MIT License

## Contact

For questions or issues, please contact:
- Email: hiring@32health.care
- GitHub: [Create an issue](<repo-url>/issues)

## Assumptions Made

1. **Field Naming**: Inconsistent capitalization in CSV is handled by flexible parsing
2. **Unique Identifiers**: `claim_reference` must be unique across all claims
3. **Currency**: All monetary values use 2 decimal places (Decimal type)
4. **Timezone**: All timestamps stored in UTC
5. **Payment Service**: Detailed pseudo-code provided for async communication
6. **Scalability**: Designed for horizontal scaling with multiple instances

## Future Enhancements

- [ ] Add webhook notifications for claim status updates
- [ ] Implement claim status tracking workflow
- [ ] Add batch import from CSV files
- [ ] Create admin dashboard
- [ ] Add claim reversal/void functionality
- [ ] Implement claim search and filtering
- [ ] Add audit logging for all changes
- [ ] Create billing reports and analytics
