# Auth Service API - Backend

A robust FastAPI backend architecture featuring user authentication, plan-based access control, and an AI chat interface powered by LangGraph and Groq.

## 🚀 Features

- **User Authentication**: Secure registration and login using JWT (JSON Web Tokens) and Argon2 password hashing.
- **Subscription Plans**: Foundation for tiered access with `Plans` and `Users` relationship.
- **AI Chat Integration**: Advanced LLM reasoning using LangGraph and the Groq Llama3 model.
- **Token Usage Metering**: Daily token limit enforcement and usage tracking per user.
- **Database Management**: SQLAlchemy ORM with SQLite (extensible to PostgreSQL/MySQL).
- **Environment Configuration**: Secure settings management using Pydantic Settings and `.env` files.

## 🛠️ Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **AI Orchestration**: [LangGraph](https://python.langchain.com/docs/langgraph) / [LangChain](https://python.langchain.com/)
- **LLM Provider**: [Groq](https://groq.com/)
- **Database**: SQLAlchemy + SQLite
- **Security**: JWT + Argon2
- **Validation**: Pydantic v2

## 📁 Project Structure

```text
backend_day_wise/
├── app/
│   ├── ai/               # AI reasoning logic (LangGraph, LLM config)
│   │   ├── graph/        # StateGraph definitions
│   │   └── llm.py        # LLM provider configuration
│   ├── api/              # API routes/endpoints
│   │   └── routes/       # Auth and Chat routers
│   ├── core/             # Core logic (Security, Config)
│   ├── db/               # Database models, session, and CRUD
│   ├── schemas/          # Pydantic models for request/response
│   ├── services/         # Business logic layer
│   └── main.py           # Application entry point
├── .env                  # Environment variables
├── requirements.txt      # Python dependencies
└── test.db               # SQLite database (auto-generated)
```

## ⚙️ Setup Instructions

### 1. Prerequisites
- Python 3.10+
- A Groq API Key (Get one at [console.groq.com](https://console.groq.com/))

### 2. Environment Setup
Create a `.env` file in the root directory:

```env
APP_NAME="Auth Service API"
DEBUG=True
DATABASE_URL="sqlite:///./test.db"
SECRET_KEY="your-super-secret-key"
GROQ_API_KEY="your_groq_api_key_here"
```

### 3. Installation
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Running the Application
```powershell
uvicorn app.main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

## 📖 API Documentation

Once the server is running, you can access the interactive Swagger documentation at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### Key Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Health Check |
| `POST` | `/auth/register` | Register a new user |
| `POST` | `/auth/login` | Login and receive JWT access token |
| `GET` | `/auth/me` | Get current user details (Requires Token) |
| `POST` | `/chat` | Chat with AI (Requires Token + Token Balance) |

## 🛡️ Token Policy & Metering

The system enforces a daily token limit for AI interactions:
1. **Initial Credit**: New users are granted 5,000 tokens upon their first chat.
2. **Daily Tracking**: Usage is tracked per user per calendar day.
3. **Enforcement**: Responses are blocked if the user's daily limit is exhausted.
4. **Accuracy**: The system attempts to read metadata from the LLM response for precise billing, falling back to word counts if metadata is unavailable.

## 🤝 Contributing

1. Fork the project.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.
