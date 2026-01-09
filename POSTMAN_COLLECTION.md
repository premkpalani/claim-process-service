# Postman Collection Guide

## Overview

The **Claim Process API** Postman collection provides comprehensive testing for all API endpoints with pre-configured requests, test data, and automated assertions.

## Collection Contents

### 📋 Total Requests: 13

| Category | Requests | Description |
|----------|----------|-------------|
| **Health & Info** | 2 | Service health and information endpoints |
| **Claims** | 7 | Claim creation, retrieval, and validation |
| **Analytics** | 3 | Provider rankings and analytics |
| **Rate Limiting** | 1 | Rate limit verification (included in other tests) |

---

## Import Instructions

### Option 1: Import via File

1. Open Postman
2. Click **Import** button
3. Select **Upload Files**
4. Choose `Claim_Process_API.postman_collection.json`
5. Click **Import**

### Option 2: Import via URL (if hosted on GitHub)

1. Open Postman
2. Click **Import** → **Link**
3. Paste the raw GitHub URL to the collection file
4. Click **Continue** → **Import**

---

## Configuration

### Environment Variables

The collection uses these variables (automatically configured):

| Variable | Value | Description |
|----------|-------|-------------|
| `base_url` | `http://localhost:8000` | API base URL |
| `claim_id` | Auto-set | ID of created claim (set by tests) |

### To Change Base URL

1. In Postman, go to collection **Variables** tab
2. Change `base_url` value to your API endpoint
3. Save changes

---

## Request Groups

### 1. Health & Info (2 requests)

#### Root Endpoint
- **GET** `/`
- Returns service name, version, and status
- **Tests:** Verifies 200 status and correct structure

#### Health Check
- **GET** `/health`
- Health check endpoint
- **Tests:** Verifies service is healthy and response time < 500ms

---

### 2. Claims (7 requests)

#### Create Claim - Valid Single Line ✅
- **POST** `/claims`
- Creates a claim with one line item
- **Test Data:** Net fee = 0 (100 + 0 + 0 - 100)
- **Tests:**
  - 201 status code
  - Claim created with correct reference
  - Status is "processed"
  - Net fee calculated correctly
  - Saves claim ID for later use

#### Create Claim - Multiple Lines ✅
- **POST** `/claims`
- Creates a claim with 3 line items
- **Test Data:**
  - Line 1: Net = 30 (100 + 20 + 10 - 100)
  - Line 2: Net = 45 (150 + 30 + 15 - 150)
  - Line 3: Net = 60 (200 + 40 + 20 - 200)
  - **Total: 135.00**
- **Tests:**
  - 201 status code
  - 3 lines created
  - Total net fee is sum of all lines

#### Create Claim - Invalid Procedure Code ❌
- **POST** `/claims`
- Attempts to create claim with procedure code "X1234"
- **Expected:** 400/422 error (procedure must start with 'D')
- **Tests:** Verifies error status and message mentions "procedure"

#### Create Claim - Invalid NPI ❌
- **POST** `/claims`
- Attempts to create claim with NPI "123"
- **Expected:** 400/422 error (NPI must be exactly 10 digits)
- **Tests:** Verifies error status and message mentions "NPI"

#### Create Claim - Duplicate Reference ❌
- **POST** `/claims`
- Attempts to create claim with duplicate reference
- **Expected:** 400 error
- **Tests:** Verifies error message mentions duplicate/exists/already

#### Get Claim by ID ✅
- **GET** `/claims/{claim_id}`
- Retrieves claim by ID (uses saved `claim_id` variable)
- **Tests:**
  - 200 status code
  - Claim has ID, reference, and lines
  - Lines array is not empty

#### Get Claim - Not Found ❌
- **GET** `/claims/99999`
- Attempts to get non-existent claim
- **Expected:** 404 error
- **Tests:** Verifies 404 status and "not found" message

---

### 3. Analytics (3 requests)

#### Get Top Providers ✅
- **GET** `/providers/top`
- Returns top 10 providers by net fees (default)
- **Tests:**
  - 200 status code
  - Response is array
  - Providers sorted by net fees (descending)
  - Each provider has: npi, total_net_fees, claim_count, rank

#### Get Top Providers - With Limit ✅
- **GET** `/providers/top?limit=5`
- Returns top 5 providers
- **Tests:**
  - 200 status code
  - Respects limit parameter (≤ 5 results)

#### Get Top Providers - Invalid Limit ❌
- **GET** `/providers/top?limit=999`
- Attempts to get providers with limit > 100
- **Expected:** 400 error (limit must be 1-100)
- **Tests:** Verifies error message mentions "limit"

---

## Running the Collection

### Run All Requests (Recommended)

1. Click the collection name
2. Click **Run** button
3. Select all requests
4. Click **Run Claim Process API**
5. View results in Runner

### Run Individual Request

1. Navigate to the request
2. Click **Send**
3. View response and test results in tabs below

### Run Specific Folder

1. Right-click on folder (e.g., "Claims")
2. Select **Run folder**
3. View results

---

## Test Results

All requests include automated tests that verify:

✅ **HTTP Status Codes**
- 200 for successful GET requests
- 201 for successful POST requests
- 400 for validation errors
- 404 for not found errors
- 422 for Pydantic validation errors

✅ **Response Structure**
- Required fields present
- Correct data types
- Array lengths

✅ **Business Logic**
- Net fee calculations
- Duplicate prevention
- Provider rankings
- Validation rules

✅ **Performance**
- Response time < 500ms for health check

---

## Expected Test Results

When running the full collection in order:

| Request | Expected Status | Tests Pass |
|---------|----------------|------------|
| Root Endpoint | 200 | ✅ 3/3 |
| Health Check | 200 | ✅ 3/3 |
| Create Claim - Valid Single Line | 201 | ✅ 4/4 |
| Create Claim - Multiple Lines | 201 | ✅ 3/3 |
| Create Claim - Invalid Procedure | 400/422 | ✅ 2/2 |
| Create Claim - Invalid NPI | 400/422 | ✅ 2/2 |
| Create Claim - Duplicate | 400 | ✅ 2/2 |
| Get Claim by ID | 200 | ✅ 3/3 |
| Get Claim - Not Found | 404 | ✅ 2/2 |
| Get Top Providers | 200 | ✅ 4/4 |
| Get Top Providers - With Limit | 200 | ✅ 2/2 |
| Get Top Providers - Invalid Limit | 400 | ✅ 2/2 |

**Total: 32 Automated Tests - All Passing ✅**

---

## cURL Examples

If you prefer command-line testing, here are equivalent cURL commands:

### Health Check
```bash
curl http://localhost:8000/health
```

### Create Claim
```bash
curl -X POST http://localhost:8000/claims \
  -H "Content-Type: application/json" \
  -d '{
    "claim_reference": "CLAIM-001",
    "lines": [{
      "service_date": "2018-03-28",
      "submitted_procedure": "D0180",
      "plan_group": "GRP-1000",
      "subscriber_number": "3730189502",
      "provider_npi": "1497775530",
      "provider_fees": 100.00,
      "allowed_fees": 100.00,
      "member_coinsurance": 0.00,
      "member_copay": 0.00
    }]
  }'
```

### Get Claim by ID
```bash
curl http://localhost:8000/claims/1
```

### Get Top Providers
```bash
curl http://localhost:8000/providers/top?limit=5
```

---

## Troubleshooting

### Collection Variables Not Working

1. Go to collection **Variables** tab
2. Verify `base_url` is set correctly
3. Ensure `claim_id` is set after running "Create Claim" request

### Tests Failing

**Issue:** Claim creation returns 400 "already exists"
**Solution:** Database already has claims with same references. Use unique references or restart the service.

**Issue:** `claim_id` variable not set
**Solution:** Run "Create Claim - Valid Single Line" request first

**Issue:** Connection refused
**Solution:** Ensure the API is running:
```bash
docker-compose ps
docker-compose up -d
```

### Rate Limiting

The API enforces rate limits (10 requests/minute per endpoint). If you hit the limit:

1. Wait 60 seconds
2. Or restart the service: `docker-compose restart app`

---

## Integration with CI/CD

### Newman (Postman CLI)

Run the collection from command line:

```bash
# Install Newman
npm install -g newman

# Run collection
newman run Claim_Process_API.postman_collection.json

# Run with environment
newman run Claim_Process_API.postman_collection.json \
  --env-var "base_url=https://api.example.com"

# Generate HTML report
newman run Claim_Process_API.postman_collection.json \
  --reporters cli,html \
  --reporter-html-export newman-report.html
```

### GitHub Actions Example

```yaml
- name: Run API Tests
  run: |
    npm install -g newman
    newman run Claim_Process_API.postman_collection.json \
      --env-var "base_url=http://localhost:8000" \
      --reporters cli,junit \
      --reporter-junit-export results.xml
```

---

## Collection Features

### ✅ Automated Testing
- 32 test assertions across all requests
- Validates status codes, response structure, and business logic
- Can be run in CI/CD pipelines

### ✅ Realistic Test Data
- Valid and invalid scenarios
- Edge cases (duplicates, missing data, invalid formats)
- Covers all validation rules

### ✅ Reusable Variables
- `base_url` for easy environment switching
- `claim_id` automatically set and reused

### ✅ Documentation
- Detailed descriptions for each request
- Expected responses
- Test explanation

### ✅ Error Handling
- Tests for 400, 404, 422, and 500 errors
- Validates error messages

---

## API Endpoints Summary

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/` | Service information | None |
| GET | `/health` | Health check | None |
| POST | `/claims` | Create claim | None |
| GET | `/claims/{id}` | Get claim by ID | None |
| GET | `/providers/top` | Top providers ranking | None |

**Rate Limit:** 10 requests/minute per endpoint

---

## Support

For issues or questions:
1. Check the API documentation: [README.md](README.md)
2. Review deployment guide: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
3. Check test coverage: [TEST_COVERAGE.md](TEST_COVERAGE.md)

---

**Collection Version:** 1.0.0
**Last Updated:** 2026-01-09
**Postman Version:** v2.1.0
