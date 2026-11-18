import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date
from decimal import Decimal
from database import (
    get_financial_summary, add_transaction, get_transactions,
    update_transaction, delete_transaction, get_budget_summary, save_budget
)
import plotly.graph_objects as go
from database import get_spending_history
import math
import numpy as np
from matplotlib.patches import Wedge, Polygon, Circle
import os
from dotenv import load_dotenv
from openai import OpenAI
import ollama
from database import get_ai_financial_context
import json

load_dotenv()

st.set_page_config(page_title="Personal Finance Tracker", page_icon="💰", layout="wide")
st.title("💰 Personal Finance Tracker")
st.write("Manage your income, expenses, and savings.")

# Messages survive the rerun after a database write.
if message := st.session_state.pop("flash_message", None):
    st.success(message)

dashboard_tab, transactions_tab, budgets_tab, ai_tab = st.tabs(
    ["📊 Dashboard", "💳 Transactions", "💰 Budgets", "🤖 AI Assistant"]
)

CATEGORIES = [
    "Salary", "Food", "Groceries", "Transportation",
    "Shopping", "Entertainment", "Bills", "Other"
]
COLUMNS = ["ID", "Name", "Amount", "Category", "Type", "Date", "Description"]

# Load transaction data once for tables and graphs.
try:
    rows = get_transactions()
    all_df = pd.DataFrame(rows, columns=COLUMNS)
    if not all_df.empty:
        all_df["Amount"] = pd.to_numeric(all_df["Amount"])
        all_df["Date"] = pd.to_datetime(all_df["Date"])
except Exception as exc:
    st.error("Unable to load transactions from PostgreSQL.")
    st.exception(exc)
    st.stop()

with dashboard_tab:

    st.subheader("💰 Spending Health Meter")

    current_spending, previous_months = get_spending_history()

    if previous_months:
        typical_spending = sum(previous_months) / len(previous_months)

        if typical_spending > 0:
            spending_percent = (current_spending / typical_spending) * 100
            difference = current_spending - typical_spending
            difference_percent = (difference / typical_spending) * 100

            # Determine spending status
            if spending_percent < 80:
                status = "Low Spending 🟢"
            elif spending_percent <= 120:
                status = "Normal Spending 🟡"
            else:
                status = "High Spending 🔴"

            
           
            # Spending Health Meter - semicircular speedometer
            fig, ax = plt.subplots(figsize=(6, 3))
            # Match Streamlit's dark background
            fig.patch.set_facecolor("#0e1117")
            ax.set_facecolor("#0e1117")

            gauge_max = 200
            needle_value = min(max(spending_percent, 0), gauge_max)

            sections = [
                (0, 40, "#00c83a"),
                (40, 80, "#8bd000"),
                (80, 120, "#ffcc00"),
                (120, 160, "#ff7100"),
                (160, 200, "#f01616"),
            ]

            # Draw colored semicircle
            for start, end, color in sections:
                theta1 = 180 - (end / gauge_max) * 180
                theta2 = 180 - (start / gauge_max) * 180

                segment = Wedge(
                    center=(0, 0),
                    r=1,
                    theta1=theta1,
                    theta2=theta2,
                    width=0.30,
                    facecolor=color,
                    edgecolor="#0e1117",
                    linewidth=3
                )
                ax.add_patch(segment)

            # Calculate needle angle
            angle = np.pi - (needle_value / gauge_max) * np.pi

            # Needle tip
            tip_x = 0.83 * np.cos(angle)
            tip_y = 0.83 * np.sin(angle)

            # Needle base
            base_width = 0.045
            left_x = base_width * np.cos(angle + np.pi / 2)
            left_y = base_width * np.sin(angle + np.pi / 2)
            right_x = base_width * np.cos(angle - np.pi / 2)
            right_y = base_width * np.sin(angle - np.pi / 2)

            needle = Polygon(
                [
                    (left_x, left_y),
                    (tip_x, tip_y),
                    (right_x, right_y)
                ],
                closed=True,
                color="#f5f5f5"
            )
            ax.add_patch(needle)

            # Center pivot
            ax.add_patch(Circle(
                (0, 0),
                radius=0.075,
                color="#303030",
                ec="white",
                linewidth=3,
                zorder=5
            ))

            # Labels
            ax.text(
                -0.95, 0.55, "LOW",
                color="white", fontsize=14,
                ha="center", rotation=45
            )

            ax.text(
                0, 1.12, "NORMAL",
                color="white", fontsize=14,
                ha="center"
            )

            ax.text(
                0.95, 0.55, "HIGH",
                color="white", fontsize=14,
                ha="center", rotation=-45
            )

            ax.text(
                0, -0.22,
                f"{spending_percent:.1f}% of usual",
                color="white",
                fontsize=17,
                ha="center",
                fontweight="bold"
            )

            ax.set_xlim(-1.25, 1.25)
            ax.set_ylim(-0.35, 1.25)
            ax.set_aspect("equal")
            ax.axis("off")

            # Display the gauge in a narrower column
            left_space, gauge_col, right_space = st.columns([1, 2, 1])

            with gauge_col:
                st.pyplot(fig, use_container_width=True)

                plt.close(fig)

                col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Spent This Month", f"${current_spending:,.2f}")

            with col2:
                st.metric("Typical Spending", f"${typical_spending:,.2f}")

            with col3:
                st.metric(
                    "Compared to Usual",
                    f"{difference_percent:+.1f}%",
                    delta_color="inverse"
                )

            st.info(f"Your spending status: **{status}**")

        else:
            st.info(
                "There isn't enough previous spending data "
                "to calculate a typical spending level yet."
            )
    else:
        st.info(
            "Add expenses across previous months to unlock "
            "your personalized Spending Health Meter."
        )

    st.divider()

    st.subheader("Financial Overview")
    try:
        income, expenses, balance = get_financial_summary()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"${income:,.2f}")
        col2.metric("Total Expenses", f"${expenses:,.2f}")
        col3.metric("Remaining Balance", f"${balance:,.2f}")
    except Exception as exc:
        st.error("Unable to load financial totals.")
        st.exception(exc)

    chart_col1, chart_col2 = st.columns(2, gap="medium")
    expenses_df = all_df[all_df["Type"] == "Expense"].copy()

    with chart_col1:
        st.subheader("📊 Spending by Category")
        if expenses_df.empty:
            st.info("Add an expense to see the chart.")
        else:
            category_totals = (
                expenses_df.groupby("Category")["Amount"].sum()
                .sort_values(ascending=False)
            )
            fig, ax = plt.subplots(figsize=(9, 4))
            category_totals.plot(kind="bar", ax=ax)
            ax.set_xlabel("Category")
            ax.set_ylabel("Amount ($)")
            ax.set_title("Spending by Category")
            plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

    with chart_col2:
        st.subheader("📅 Monthly Spending Analysis")
        if expenses_df.empty:
            st.info("Add expenses to see monthly spending.")
        else:
            monthly = expenses_df.copy()
            monthly["Month"] = monthly["Date"].dt.to_period("M")
            monthly_totals = monthly.groupby("Month")["Amount"].sum().sort_index()
            # Include zero-spend months between first and last expense.
            months = pd.period_range(monthly_totals.index.min(), monthly_totals.index.max(), freq="M")
            monthly_totals = monthly_totals.reindex(months, fill_value=0)
            fig, ax = plt.subplots(figsize=(9, 4))
            ax.plot(monthly_totals.index.astype(str), monthly_totals.values, marker="o")
            ax.set_title("Monthly Expenses")
            ax.set_xlabel("Month")
            ax.set_ylabel("Total Expenses ($)")
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

with transactions_tab:
    st.subheader("➕ Add New Transaction")
    with st.form("transaction_form"):
        name = st.text_input("Transaction Name")
        amount = st.number_input("Amount ($)", min_value=0.01, value=0.01,
                                 step=0.01, format="%.2f")
        category = st.selectbox("Category", CATEGORIES, key="add_category")
        transaction_type = st.selectbox("Transaction Type", ["Expense", "Income"], key="add_type")
        transaction_date = st.date_input("Transaction Date", value=date.today(), key="add_date")
        description = st.text_area("Description (Optional)")
        submitted = st.form_submit_button("Add Transaction")

    if submitted:
        if not name.strip():
            st.warning("Please enter a transaction name.")
        else:
            try:
                add_transaction(name.strip(), Decimal(f"{amount:.2f}"), category,
                                transaction_type, transaction_date, description)
                st.session_state["flash_message"] = "Transaction added successfully!"
                st.rerun()
            except Exception as exc:
                st.error("Could not save the transaction.")
                st.exception(exc)

    st.divider()
    st.subheader("📋 Transaction History")
    if all_df.empty:
        st.info("No transactions found.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            type_filter = st.selectbox("Filter by Type", ["All", "Income", "Expense"],
                                       key="history_type_filter")
        with col2:
            categories = sorted(all_df["Category"].dropna().unique().tolist())
            category_filter = st.selectbox("Filter by Category", ["All"] + categories,
                                           key="history_category_filter")
        filtered_df = all_df.copy()
        if type_filter != "All":
            filtered_df = filtered_df[filtered_df["Type"] == type_filter]
        if category_filter != "All":
            filtered_df = filtered_df[filtered_df["Category"] == category_filter]
        st.write(f"Showing {len(filtered_df)} transactions")
        st.dataframe(filtered_df, use_container_width=True, hide_index=True,
                     column_config={
                         "Amount": st.column_config.NumberColumn("Amount ($)", format="$%.2f"),
                         "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                     })
    st.divider()
    st.subheader("✏️ Edit or Delete Transaction")
    if not rows:
        st.info("No transactions available to edit or delete.")
    else:
        options = {f"{r[0]} - {r[1]} (${r[2]:.2f})": r for r in rows}
        selected = st.selectbox("Select a Transaction", list(options), key="edit_transaction_selection")
        record = options[selected]
        transaction_id, old_name, old_amount, old_category, old_type, old_date, old_description = record
        edit_tab, delete_tab = st.tabs(["Edit Transaction", "Delete Transaction"])

        with edit_tab:
            with st.form("edit_transaction_form"):
                new_name = st.text_input("Transaction Name", value=old_name)
                new_amount = st.number_input("Amount ($)", min_value=0.01,
                                             value=float(old_amount), step=0.01, format="%.2f")
                edit_categories = CATEGORIES.copy()
                if old_category not in edit_categories:
                    edit_categories.append(old_category)
                new_category = st.selectbox("Category", edit_categories,
                                            index=edit_categories.index(old_category), key="edit_category")
                new_type = st.selectbox("Transaction Type", ["Income", "Expense"],
                                        index=["Income", "Expense"].index(old_type), key="edit_type")
                new_date = st.date_input("Transaction Date", value=old_date, key="edit_date")
                new_description = st.text_area("Description", value=old_description or "")
                update_clicked = st.form_submit_button("Save Changes")

            # Handle updates only when Save Changes is clicked.
            if update_clicked:
                if not new_name.strip():
                    st.warning("Please enter a transaction name.")
                else:
                    try:
                        updated = update_transaction(
                            transaction_id, new_name.strip(), Decimal(f"{new_amount:.2f}"),
                            new_category, new_type, new_date, new_description
                        )
                        if updated:
                            st.session_state["flash_message"] = "Transaction updated successfully!"
                            st.rerun()
                        else:
                            st.warning("Transaction not found.")
                    except Exception as exc:
                        st.error("Unable to update transaction.")
                        st.exception(exc)

        with delete_tab:
            st.warning("Deleting a transaction permanently removes it from PostgreSQL.")
            confirm_delete = st.checkbox("I confirm that I want to delete this transaction",
                                         key=f"confirm_delete_{transaction_id}")
            if st.button("Delete Transaction", disabled=not confirm_delete,
                         key="delete_transaction_button"):
                try:
                    deleted = delete_transaction(transaction_id)
                    if deleted:
                        st.session_state["flash_message"] = "Transaction deleted successfully!"
                        st.rerun()
                    else:
                        st.warning("Transaction not found.")
                except Exception as exc:
                    st.error("Unable to delete transaction.")
                    st.exception(exc)

with budgets_tab:
    st.subheader("💰 Monthly Budget Tracking")
    selected_month = st.date_input("Select Budget Month", value=date.today().replace(day=1),
                                   key="budget_month").replace(day=1)
    try:
        budgets = get_budget_summary(selected_month)
        if not budgets:
            st.info("No budgets found for this month.")
        else:
            for category, monthly_limit, spent in budgets:
                remaining = monthly_limit - spent
                percentage = float(spent / monthly_limit)
                st.write(f"### {category}")
                st.write(f"Spent: ${spent:,.2f} / Budget: ${monthly_limit:,.2f}")
                st.progress(min(max(percentage, 0.0), 1.0))
                if remaining >= 0:
                    st.success(f"${remaining:,.2f} remaining")
                else:
                    st.error(f"Over budget by ${abs(remaining):,.2f}!")
    except Exception as exc:
        st.error("Unable to load budget information.")
        st.exception(exc)

    st.divider()
    st.subheader("📝 Set Monthly Budget")
    with st.form("budget_form"):
        budget_category = st.selectbox("Budget Category",
                                       ["Food", "Groceries", "Shopping", "Transportation",
                                        "Entertainment", "Bills", "Other"], key="new_budget_category")
        budget_amount = st.number_input("Monthly Budget ($)", min_value=0.01,
                                        value=100.0, step=10.0, format="%.2f")
        budget_date = st.date_input("Budget Month", value=date.today().replace(day=1),
                                    key="new_budget_month")
        save_clicked = st.form_submit_button("Save Budget")

    if save_clicked:
        try:
            save_budget(budget_category, Decimal(f"{budget_amount:.2f}"),
                        budget_date.replace(day=1))
            st.session_state["flash_message"] = "Budget saved successfully!"
            st.rerun()
        except Exception as exc:
            st.error("Unable to save budget.")
            st.exception(exc)

# AI Assistant Tab
with ai_tab:
    st.header("🤖 AI Finance Assistant")

    st.write(
        "Ask questions about your spending, budgets, "
        "and financial habits!"
    )

    # Store chat messages during the Streamlit session
    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = []

    # Display previous messages
    for message in st.session_state.ai_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    user_question = st.chat_input(
        "Ask me something about your finances..."
    )

    if user_question:
        st.session_state.ai_messages.append({
            "role": "user",
            "content": user_question
        })

        with st.chat_message("user"):
            st.markdown(user_question)

        
        
        with st.chat_message("assistant"):
            try:
                with st.spinner("🤖 AI is thinking..."):
                    
                    # Get spending summaries from PostgreSQL
                    financial_data = get_ai_financial_context()

                    # Prepare the information for the AI
                    financial_context = json.dumps(
                        financial_data,
                        indent=2
                    )

                    # Ask the local AI model
                    response = ollama.chat(
                        model="llama3.2:3b",
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "You are a friendly personal finance assistant "
                                    "for a Streamlit Finance Tracker. "
                                    "Use ONLY the financial data provided below "
                                    "when answering questions about the user's spending. "
                                    "The data contains monthly expense totals grouped "
                                    "by category. Each month is formatted YYYY-MM-01. "
                                    "Add category totals together when calculating "
                                    "the total spent in a month. "
                                    "Do not invent transactions, amounts, or budgets. "
                                    "If the requested information is not available, "
                                    "say so clearly. "
                                    "Keep answers concise and easy to understand. "
                                    "Financial data:\n"
                                    + financial_context
                                )
                            },
                            {
                                "role": "user",
                                "content": user_question
                            }
                        ]
                    )


                    ai_reply = response["message"]["content"]

                st.markdown(ai_reply)

                st.session_state.ai_messages.append({
                    "role": "assistant",
                    "content": ai_reply
                })

            except Exception as error:
                st.error("Could not connect to Ollama.")
                st.write("Error type:", type(error).__name__)
                st.info(
                    "Make sure Ollama is installed and running "
                    "on your computer."
                )


        
