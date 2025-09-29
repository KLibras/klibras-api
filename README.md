# Mozukai Backend API

FastAPI-based backend for the Mozukai bonsai store with integrated user authentication, payment processing, and photogrammetry pipeline integration.

## Features

- **FastAPI Framework**: High-performance async API
- **PostgreSQL Database**: With SQLAlchemy ORM and async support
- **JWT Authentication**: Secure token-based authentication
- **Stripe Integration**: Payment processing
- **CORS Support**: Configurable cross-origin requests
- **Auto Documentation**: Built-in Swagger UI and ReDoc
- **Pipeline Integration**: Photogrammetry workflow endpoints

## Prerequisites

- **Python 3.8+**
- **PostgreSQL 12+**
- **Stripe Account** (for payment processing)

## Installation

### 1. Environment Setup
Create a `.env` file in the backend directory:

```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://admin:secret@localhost:5432/mydb

# Security
SECRET_KEY=your_super_secret_key_here_change_this_in_production
ALGORITHM=HS256

# Token Lifetimes (in minutes)
ACCESS_TOKEN_LIFETIME=15
SHORT_REFRESH_TOKEN_LIFETIME=60
LONG_REFRESH_TOKEN_LIFETIME=43200

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:5173

# Payment Processing
STRIPE_KEY=sk_test_your_stripe_secret_key_here
```

### 2. Database Setup
```bash
# Create PostgreSQL database
createdb mydb

# Or using psql
psql -c "CREATE DATABASE mydb;"
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Migration
```bash
# Run database migrations (if using Alembic)
alembic upgrade head

# Or initialize tables directly in your application
python -c "from app.database import create_tables; create_tables()"
```

## Running the Server

### Development
```bash
python main.py
```

### Production
```bash
# Using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000

# With auto-reload for development
uvicorn main:app --reload
```

The API will be available at:
- **API Base**: `http://localhost:8000`
- **API Documentation**: `http://localhost:8000/docs`
- **Alternative Docs**: `http://localhost:8000/redoc`

## API Structure

### Authentication Endpoints
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/refresh` - Token refresh
- `POST /auth/logout` - User logout

### User Management
- `GET /users/me` - Get current user profile
- `PUT /users/me` - Update user profile
- `DELETE /users/me` - Delete user account

### Product Management
- `GET /products` - List all products
- `GET /products/{id}` - Get specific product
- `POST /products` - Create new product (admin)
- `PUT /products/{id}` - Update product (admin)
- `DELETE /products/{id}` - Delete product (admin)

### Order Management
- `GET /orders` - Get user orders
- `POST /orders` - Create new order
- `GET /orders/{id}` - Get specific order
- `PUT /orders/{id}/status` - Update order status (admin)

### Payment Processing
- `POST /payments/create-intent` - Create Stripe payment intent
- `POST /payments/confirm` - Confirm payment
- `GET /payments/{id}` - Get payment details

### Photogrammetry Pipeline
- `POST /pipeline/upload` - Upload images for processing
- `GET /pipeline/status/{job_id}` - Check processing status
- `GET /pipeline/download/{job_id}` - Download processed 3D model

## Database Models

### User Model
```python
class User:
    id: int
    email: str
    username: str
    password_hash: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime
```

### Product Model
```python
class Product:
    id: int
    name: str
    description: str
    price: decimal
    category: str
    image_url: str
    stock_quantity: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### Order Model
```python
class Order:
    id: int
    user_id: int
    total_amount: decimal
    status: str  # pending, confirmed, shipped, delivered, cancelled
    stripe_payment_intent_id: str
    created_at: datetime
    updated_at: datetime
```

## Authentication

The API uses JWT (JSON Web Tokens) for authentication:

### Token Types
- **Access Token**: Short-lived (15 minutes) for API requests
- **Refresh Token**: Long-lived (30 days) for token renewal

### Usage
```bash
# Login to get tokens
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use access token for authenticated requests
curl -X GET "http://localhost:8000/users/me" \
  -H "Authorization: Bearer your_access_token_here"
```

## Environment Variables

### Required Variables
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT signing key (use a strong, random key in production)
- `STRIPE_KEY`: Stripe secret key

### Optional Variables
- `ALLOWED_ORIGINS`: CORS allowed origins (default: http://localhost:5173)
- `ACCESS_TOKEN_LIFETIME`: Access token lifetime in minutes (default: 15)
- `SHORT_REFRESH_TOKEN_LIFETIME`: Short refresh token lifetime in minutes (default: 60)
- `LONG_REFRESH_TOKEN_LIFETIME`: Long refresh token lifetime in minutes (default: 43200)

## Development

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest

# Run with coverage
pytest --cov=app tests/
```

### Code Formatting
```bash
# Install formatting tools
pip install black isort

# Format code
black .
isort .
```

### Database Operations
```bash
# Create new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Deployment

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Configuration
Ensure these environment variables are set in production:
- Use a strong, unique `SECRET_KEY`
- Set `DATABASE_URL` to your production database
- Configure production `STRIPE_KEY`
- Set `ALLOWED_ORIGINS` to your frontend domain
- Consider using environment-specific configuration files

### Health Checks
The API includes a health check endpoint:
```bash
curl http://localhost:8000/health
```

## Monitoring

### Logging
Logs are configured to output structured JSON for production monitoring:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Performance Monitoring
Consider integrating with monitoring services:
- Sentry for error tracking
- DataDog or New Relic for performance monitoring
- Prometheus for metrics collection

## Security Considerations

- **JWT Secret**: Use a strong, randomly generated secret key
- **Database Security**: Use connection pooling and prepared statements
- **CORS**: Configure allowed origins appropriately
- **Rate Limiting**: Consider implementing rate limiting for public endpoints
- **Input Validation**: All inputs are validated using Pydantic models
- **SQL Injection Protection**: SQLAlchemy ORM provides protection against SQL injection

## API Rate Limits

Default rate limits (implement as needed):
- Authentication endpoints: 5 requests per minute
- General API endpoints: 100 requests per minute
- File upload endpoints: 10 requests per minute

## Support

- **API Documentation**: Available at `/docs` when server is running
- **Database Issues**: Check PostgreSQL logs and connection string
- **Authentication Problems**: Verify JWT secret key and token expiration
- **Stripe Integration**: Check Stripe dashboard for payment issues

⚠️ **Production Notes:**
- Always use HTTPS in production
- Set secure, unique environment variables
- Regular security updates for dependencies
- Monitor API performance and error rates
- Backup database regularly