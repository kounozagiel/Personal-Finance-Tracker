# 💰 Personal Finance Tracker

An interactive, AI-powered personal finance management application built with **Python, Streamlit, PostgreSQL, and Ollama**.

The application helps users track income and expenses, manage monthly budgets, visualize spending patterns, and receive personalized financial insights through a locally running AI assistant.

## ✨ Features

### 📊 Financial Dashboard
- View total income, total expenses, and account balance.
- Visualize spending by category.
- Analyze monthly spending trends using charts.
- Monitor spending habits with a color-coded Spending Health Meter.

### 💳 Transaction Management
- Add income and expense transactions.
- View and filter transaction records.
- Edit existing transactions.
- Delete transactions.

### 🎯 Monthly Budget Tracking
- Set monthly spending limits for different categories.
- Compare actual spending against budgets.
- Monitor budget usage through progress bars.

### 🤖 AI Finance Assistant
- Chat with a local AI assistant powered by **Ollama and Llama 3.2**.
- Ask questions about monthly expenses.
- Identify highest-spending categories.
- Receive general budgeting and financial guidance.
- Analyze spending summaries retrieved from PostgreSQL.

**Note:** The AI assistant runs locally and does not require a paid AI API. Its financial calculations should be verified against the underlying data.

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python | Application logic |
| Streamlit | Interactive web interface |
| PostgreSQL | Relational database |
| pgAdmin | Database administration |
| pandas | Data processing |
| Matplotlib | Data visualization |
| psycopg | PostgreSQL connectivity |
| Ollama | Local AI model runtime |
| Llama 3.2 | AI chatbot model |
| python-dotenv | Environment variable management |

## 🚀 Getting Started

### Prerequisites

Install the following:

- Python
- PostgreSQL
- Ollama
- Git

### 1. Clone the repository

```bash
git clone https://github.com/kounozagiel/Personal-Finance-Tracker.git
cd Personal-Finance-Tracker
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install streamlit pandas matplotlib psycopg python-dotenv ollama
```

### 4. Configure PostgreSQL

Create a PostgreSQL database named `finance_tracker`.

Create the required `transactions` and `budgets` tables using the database schema configured for the application.

### 5. Configure environment variables

Create a `.env` file in the project root.

Add the PostgreSQL connection settings expected by `database.py`.

**Never commit your `.env` file or database passwords to GitHub.**

### 6. Download the local AI model

```bash
ollama pull llama3.2:3b
```

Make sure Ollama is running before using the AI Assistant.

### 7. Launch the application

```bash
streamlit run app.py
```

Open the local URL shown in your terminal.

## 📸 Screenshots

Screenshots of the following features will be added:

- Financial Dashboard
- Transaction Management
- Monthly Budget Tracking
- Spending Health Meter
- AI Finance Assistant

## 🔮 Future Improvements

- Conversation memory for the AI assistant
- More detailed AI analysis of transactions and budgets
- CSV import and export
- Automated spending alerts
- Improved financial forecasting

## 🔐 Security and Privacy

- Database credentials are stored in environment variables.
- The `.env` file is excluded from Git.
- The AI assistant runs locally through Ollama.
- Financial summaries are retrieved from PostgreSQL for analysis.
- The application is intended as a personal finance
