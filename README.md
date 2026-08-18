# FastAPI Project: Music Memo

A minimal FastAPI backend with SQLAlchemy and PostgreSQL.

## Getting Started

### 1. Prerequisites
- Python 3.8+
- PostgreSQL database

### 2. Setup Environment
```bash
# Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Configuration
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Update the `POSTGRES_URL` in `.env` with your local PostgreSQL credentials.

### 4. Run the Application
```bash
uvicorn main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.
You can access the interactive documentation at `http://127.0.0.1:8000/docs`.

## Project Structure
- `main.py`: Entry point, initializes FastAPI and routers.
- `database.py`: SQLAlchemy engine, session, and base model class.
- `models.py`: Database models (SQLAlchemy).
- `routers/`: Directory for API route modules.
