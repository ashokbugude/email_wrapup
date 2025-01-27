# Email Warmup Service

A FastAPI-based service for warming up email accounts by gradually increasing sending limits and managing email quotas. Supports Gmail and Outlook integration through OAuth2.

## Features

- Email account warmup with gradual quota increase
- OAuth2 integration for Gmail and Outlook
- Asynchronous email processing with Redis queue
- Email validation and MX record checking
- Quota management and rate limiting
- Retry mechanism with exponential backoff
- Real-time status tracking

## Architecture

### Components

1. **API Layer** (`src/api/routes.py`)
   - REST endpoints for email sending and account management
   - OAuth callback handling
   - Request validation and authentication

2. **Queue System** (`src/queue/redis_queue.py`)
   - Asynchronous message queue using Redis
   - Event publishing and subscription
   - Message persistence

3. **Email Processing** (`src/services/email_service.py`)
   - Email sending logic for different providers
   - Quota management
   - Error handling and retries

4. **Workers** (`src/workers/email_worker.py`)
   - Background task processing
   - Retry mechanism with exponential backoff
   - Status tracking and logging

### Database Schema

The application uses MySQL with the following tables:

1. **credentials**
   - Stores OAuth tokens and provider information
   - User and tenant mapping
   - Email provider details

2. **email_quotas**
   - Daily quota tracking
   - Warmup progress
   - Usage statistics

3. **email_logs**
   - Event tracking
   - Status monitoring
   - Error logging

## Configuration

The service configuration is managed through `src/config.py`:

### Email Warmup Settings
- Initial quota: 5 emails/day
- Maximum quota: 50 emails/day
- Quota increase rate:
  - After 7 days: 10/day
  - After 14 days: 20/day
  - After 30 days: 50/day

## API Endpoints

### Authentication
- POST `/api/auth/validate` - Validate user credentials
- POST `/api/auth/gmail` - Authenticate Gmail account
- GET `/api/oauth/callback/{provider}` - OAuth callback handler
- POST `/api/auth/link-account` - Link email provider account

### Email Operations
- POST `/api/send-email` - Queue email for sending

## Frontend Interface

The service includes a web interface (`src/static/index.html`) that provides:

1. Account Management
   - Gmail/Outlook account linking
   - OAuth authentication flow
   - Account status display

2. Email Sending
   - Provider selection
   - Recipient input
   - Subject and body composition
   - Send status feedback

## Worker Process

The email worker (`src/workers/email_worker.py`) handles:

1. Queue Processing
   - Asynchronous event handling
   - Rate limiting
   - Quota enforcement

2. Retry Logic
   - Maximum 3 retry attempts
   - Exponential backoff
   - Error tracking

## Development

For local development:

1. Start MySQL and Redis servers
2. Set up OAuth credentials in Google/Microsoft developer consoles
3. Configure environment variables
4. Run with hot reload: `uvicorn main:app --host 127.0.0.1 --port 5000 --reload`

## Testing

Run tests using pytest:

## Requirements

- Python 3.8+
- MySQL 5.7+
- Redis 6+
- Gmail/Outlook Developer Account

## Setup

1. Clone the repository:

bash
git clone https://github.com/yourusername/email_wrapup.git
cd email_wrapup

2. Create and activate virtual environment:

bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install dependencies:

bash
pip install -r requirements.txt

4. Set up environment variables (.env):

bash
# Database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=email_warmup
DB_USER=root
DB_PASSWORD=your_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_QUEUE_NAME=email_queue

# OAuth Credentials
GMAIL_CLIENT_ID=your_gmail_client_id
GMAIL_CLIENT_SECRET=your_gmail_client_secret
OUTLOOK_CLIENT_ID=your_outlook_client_id
OUTLOOK_CLIENT_SECRET=your_outlook_client_secret

# JWT
SECRET_KEY=your_secret_key

# API
API_HOST=0.0.0.0
API_PORT=5000
DEBUG=True

5. Initialize database:

bash
mysql -u root -p < src/db/schema.sql

6. Run the application:

bash
uvicorn main:app --host 127.0.0.1 --port 5000 --reload

## Error Handling

The service implements comprehensive error handling:

1. Email Validation
   - Format checking
   - MX record verification
   - Throwaway domain filtering

2. Queue Management
   - Connection error recovery
   - Message persistence
   - Failed event logging

3. OAuth Flow
   - Token refresh
   - Error recovery
   - Session management

## License

MIT License

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

