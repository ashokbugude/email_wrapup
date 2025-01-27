Here’s the updated README with proper formatting for better readability:

---

# Email Warmup Service

A **FastAPI-based service** for warming up email accounts by gradually increasing sending limits and managing email quotas. Supports Gmail and Outlook integration through OAuth2.

---

## Features

- Gradual email account warmup with quota management
- OAuth2 integration for Gmail and Outlook
- Asynchronous email processing using Redis queues
- Email validation and MX record checking
- Rate limiting and retry mechanisms with exponential backoff
- Real-time status tracking

---

## Architecture

### Components

1. **API Layer** (`src/api/routes.py`)
   - Provides REST endpoints for email sending and account management
   - Handles OAuth callbacks and request validation
   - Implements user authentication

2. **Queue System** (`src/queue/redis_queue.py`)
   - Asynchronous message queue using Redis
   - Supports event publishing, subscription, and message persistence

3. **Email Processing** (`src/services/email_service.py`)
   - Implements email sending logic for Gmail and Outlook
   - Manages quotas, errors, and retries

4. **Workers** (`src/workers/email_worker.py`)
   - Processes background tasks
   - Enforces rate limits and retries
   - Tracks and logs status updates

---

### Database Schema

The application uses **MySQL** with the following tables:

1. **credentials**
   - Stores OAuth tokens, user and tenant mappings, and provider details

2. **email_quotas**
   - Tracks daily quotas, warmup progress, and usage statistics

3. **email_logs**
   - Tracks events, statuses, and errors

---

## Configuration

### Email Warmup Settings

- **Initial Quota**: 5 emails/day  
- **Maximum Quota**: 50 emails/day  
- **Quota Increase Rate**:
  - After 7 days: +10/day
  - After 14 days: +20/day
  - After 30 days: +50/day

---

## API Endpoints

### Authentication
- `POST /api/auth/validate` - Validate user credentials  
- `POST /api/auth/gmail` - Authenticate Gmail account  
- `GET /api/oauth/callback/{provider}` - OAuth callback handler  
- `POST /api/auth/link-account` - Link email provider account  

### Email Operations
- `POST /api/send-email` - Queue an email for sending  

---

## Frontend Interface

The service includes a **web interface** (`src/static/index.html`) that offers:

1. **Account Management**  
   - Link Gmail/Outlook accounts via OAuth  
   - Display account status  

2. **Email Sending**  
   - Select email provider  
   - Input recipient, subject, and body  
   - View send status feedback  

---

## Worker Process

The **email worker** (`src/workers/email_worker.py`) handles:

1. **Queue Processing**
   - Processes events asynchronously  
   - Enforces rate limits and quotas  

2. **Retry Logic**
   - Maximum of 3 retry attempts  
   - Implements exponential backoff  
   - Tracks and logs errors  

---

## Development

### Local Development Setup

1. **Start MySQL and Redis servers**  
2. **Set up OAuth credentials** in Google/Microsoft developer consoles  
3. **Configure environment variables**  
4. Run the application with hot reload:  
   ```bash
   uvicorn main:app --host 127.0.0.1 --port 5000 --reload
   ```



## Requirements

- **Python** 3.8+  
- **MySQL** 5.7+  
- **Redis** 6+  
- Gmail/Outlook Developer Account  

---

## Setup Instructions

1. **Clone the repository**:  
   ```bash
   git clone https://github.com/yourusername/email_wrapup.git
   cd email_wrapup
   ```

2. **Create and activate a virtual environment**:  
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:  
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables (.env)**:  
   ```bash
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


   # API
   API_HOST=0.0.0.0
   API_PORT=5000
   DEBUG=True
   ```

5. **Initialize the database**:  
   create db named 'email_warmup' and start the server , tables are expected to be created

6. **Run the application**:  
   ```bash
   uvicorn main:app --host 127.0.0.1 --port 5000 --reload
   ```

---

## Error Handling

The service implements **comprehensive error handling** for:

1. **Email Validation**  
   - Verifies format, MX records, and filters throwaway domains  

2. **Queue Management**  
   - Recovers from connection errors  
   - Ensures message persistence  
   - Logs failed events  

3. **OAuth Flow**  
   - Refreshes tokens and manages errors  

---

## License

This project is licensed under the **MIT License**.

---

## Contributing

1. Fork the repository  
2. Create your feature branch  
3. Commit your changes  
4. Push to the branch  
5. Create a Pull Request  

--- 

This formatting makes the document clear, professional, and easy to read. Let me know if you need further modifications!
