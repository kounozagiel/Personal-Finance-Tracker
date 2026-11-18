import os
import psycopg
from dotenv import load_dotenv
from datetime import date, timedelta
import calendar

# Load database credentials from .env
load_dotenv()

# Connect Python to PostgreSQL
def get_connection():
    connection = psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    return connection

# Get income, expenses, and balance
def get_financial_summary():

    # Open database connection
    with get_connection() as connection:
        with connection.cursor() as cursor:

            # Run SQL query
            cursor.execute("""
                SELECT
                    COALESCE(SUM(CASE
                        WHEN transaction_type = 'Income'
                        THEN amount ELSE 0 END), 0),
                    COALESCE(SUM(CASE
                        WHEN transaction_type = 'Expense'
                        THEN amount ELSE 0 END), 0)
                FROM transactions;
            """)

            # Retrieve results
            income, expenses = cursor.fetchone()

    # Calculate remaining balance
    balance = income - expenses

    return income, expenses, balance


# Add a new transaction to PostgreSQL
def add_transaction(name, amount, category, transaction_type, date, description):

    # Open database connection
    with get_connection() as connection:
        with connection.cursor() as cursor:

            # Insert the transaction into the database
            cursor.execute("""
                INSERT INTO transactions
                (transaction_name, amount, category,
                 transaction_type, transaction_date, description)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (name, amount, category, transaction_type, date, description))

    # Transaction is committed when connection closes successfully


# Retrieve all transactions from PostgreSQL
def get_transactions():

    # Open database connection
    with get_connection() as connection:
        with connection.cursor() as cursor:

            # Retrieve transactions, newest first
            cursor.execute("""
                SELECT
                    transaction_id,
                    transaction_name,
                    amount,
                    category,
                    transaction_type,
                    transaction_date,
                    description
                FROM transactions
                ORDER BY transaction_date DESC, transaction_id DESC;
            """)

            # Fetch all rows from the database
            transactions = cursor.fetchall()

    return transactions

# Update an existing transaction
def update_transaction(transaction_id, name, amount, category,
                       transaction_type, date, description):

    with get_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute("""
                UPDATE transactions
                SET transaction_name = %s,
                    amount = %s,
                    category = %s,
                    transaction_type = %s,
                    transaction_date = %s,
                    description = %s
                WHERE transaction_id = %s;
            """, (name, amount, category, transaction_type,
                  date, description, transaction_id))

            return cursor.rowcount > 0


# Delete a transaction
def delete_transaction(transaction_id):

    with get_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute("""
                DELETE FROM transactions
                WHERE transaction_id = %s;
            """, (transaction_id,))

            return cursor.rowcount > 0


# Get monthly budgets and spending from PostgreSQL
def get_budget_summary(month):

    with get_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT
                    b.category,
                    b.monthly_limit,
                    COALESCE(SUM(t.amount), 0) AS spent
                FROM budgets b
                LEFT JOIN transactions t
                    ON b.category = t.category
                    AND t.transaction_type = 'Expense'
                    AND t.transaction_date >= b.budget_month
                    AND t.transaction_date <
                        (b.budget_month + INTERVAL '1 month')
                WHERE b.budget_month = %s
                GROUP BY b.budget_id, b.category, b.monthly_limit
                ORDER BY b.category;
            """, (month,))

            budgets = cursor.fetchall()

    return budgets

# Create or update a monthly budget
def save_budget(category, monthly_limit, month):

    # Connect to PostgreSQL
    with get_connection() as connection:
        with connection.cursor() as cursor:

            # Insert a new budget or update an existing one
            cursor.execute("""
                INSERT INTO budgets
                    (category, monthly_limit, budget_month)
                VALUES (%s, %s, %s)

                ON CONFLICT (category, budget_month)
                DO UPDATE SET
                    monthly_limit = EXCLUDED.monthly_limit;
            """, (category, monthly_limit, month))

def get_spending_history():
    """Get this month's spending and comparable previous-month totals."""
    today = date.today()
    current_start = today.replace(day=1)

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            # Total expenses so far this month
            cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM transactions
                WHERE transaction_type = 'Expense'
                  AND transaction_date >= %s
                  AND transaction_date <= %s
                """,
                (current_start, today)
            )
            current_spending = float(cursor.fetchone()[0])

            # Find the first month with recorded expenses
            cursor.execute(
                """
                SELECT MIN(transaction_date)
                FROM transactions
                WHERE transaction_type = 'Expense'
                """
            )
            first_expense_date = cursor.fetchone()[0]

            previous_months = []

            for months_back in range(1, 4):
                year = today.year
                month = today.month - months_back

                while month <= 0:
                    month += 12
                    year -= 1

                month_start = date(year, month, 1)

                # Do not count months before tracking began
                if first_expense_date is None or month_start < first_expense_date.replace(day=1):
                    continue

                last_day = calendar.monthrange(year, month)[1]
                comparison_day = min(today.day, last_day)
                comparison_end = date(year, month, comparison_day)

                cursor.execute(
                    """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM transactions
                    WHERE transaction_type = 'Expense'
                      AND transaction_date >= %s
                      AND transaction_date <= %s
                    """,
                    (month_start, comparison_end)
                )

                monthly_spending = float(cursor.fetchone()[0])

                # Only include months with recorded expenses
                if monthly_spending > 0:
                    previous_months.append(monthly_spending)
                    
                return current_spending, previous_months

    finally:
        connection.close()


def get_ai_financial_context():
    """Return read-only financial data for the AI chatbot."""
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    DATE_TRUNC('month', transaction_date)::date AS month,
                    category,
                    SUM(amount) AS total_spent
                FROM transactions
                WHERE transaction_type = 'Expense'
                GROUP BY
                    DATE_TRUNC('month', transaction_date)::date,
                    category
                ORDER BY month DESC, category
            """)

            rows = cur.fetchall()

            return [
                {
                    "month": str(row[0]),
                    "category": row[1],
                    "total_spent": float(row[2])
                }
                for row in rows
            ]

    finally:
        conn.close()
