from datetime import datetime
from decimal import Decimal, InvalidOperation

import psycopg

from db import get_db_connection
from flask import Flask
from flask import abort, flash, redirect, render_template, request, url_for

# Create the Flask application and a temporary in-memory list for income entries.
app = Flask(__name__)
app.secret_key = "dev-only-change-me"
income_entries = []
expense_entries = []
expense_categories = [
    "Food",
    "Housing",
    "Transportation",
    "Shopping",
    "Entertainment",
    "Other",
]


def load_entries():
    """Load income and expense records for the page tables."""
    income_entries = []
    expense_entries = []
    income_load_error = None
    expense_load_error = None
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                "SELECT id, amount, description, date FROM income "
                "ORDER BY date DESC, id DESC"
            )
            income_entries = [
                {
                    "id": row[0],
                    "amount": row[1],
                    "description": row[2],
                    "date": row[3],
                }
                for row in cursor.fetchall()
            ]
        except psycopg.Error:
            app.logger.exception("Database error while loading income.")
            income_load_error = "Could not load income records. Please try again."
            try:
                connection.rollback()
            except psycopg.Error:
                app.logger.exception("Database error while resetting income query.")

        try:
            cursor.execute(
                "SELECT id, amount, description, date, category FROM expense "
                "ORDER BY date DESC, id DESC"
            )
            expense_entries = [
                {
                    "id": row[0],
                    "amount": row[1],
                    "description": row[2],
                    "date": row[3],
                    "category": row[4],
                }
                for row in cursor.fetchall()
            ]
        except psycopg.Error:
            app.logger.exception("Database error while loading expenses.")
            expense_load_error = "Could not load expenses. Please try again."
            try:
                connection.rollback()
            except psycopg.Error:
                app.logger.exception("Database error while resetting expense query.")
    except psycopg.Error:
        app.logger.exception("Database error while connecting to load records.")
        income_load_error = "Could not load income records. Please try again."
        expense_load_error = "Could not load expenses. Please try again."
    finally:
        try:
            if cursor is not None:
                cursor.close()
        except psycopg.Error:
            app.logger.exception("Database error while closing records cursor.")
        finally:
            if connection is not None:
                try:
                    connection.close()
                except psycopg.Error:
                    app.logger.exception("Database error while closing records connection.")

    totals = None
    if not income_load_error and not expense_load_error:
        total_income = sum(
            (Decimal(str(entry["amount"])) for entry in income_entries),
            Decimal("0.00"),
        )
        total_expenses = sum(
            (Decimal(str(entry["amount"])) for entry in expense_entries),
            Decimal("0.00"),
        )
        balance = total_income - total_expenses
        totals = {
            "income": f"${total_income:,.2f}",
            "expenses": f"${total_expenses:,.2f}",
            "balance": f"${balance:,.2f}",
        }

    return income_entries, income_load_error, expense_entries, expense_load_error, totals


# Show the form on GET requests and process it when it is submitted with POST.
@app.route("/", methods=["GET", "POST"])
def home():
    """Display PostgreSQL records and process income form submissions."""
    errors = []
    confirmation = None
    form_values = {"amount": "", "description": "", "date": ""}

    if request.method == "POST":
        form_values = {
            "amount": request.form.get("amount", "").strip(),
            "description": request.form.get("description", "").strip(),
            "date": request.form.get("date", "").strip(),
        }

        try:
            amount = Decimal(form_values["amount"])
            if not amount.is_finite() or amount <= 0:
                errors.append("Enter an income amount greater than zero.")
        except InvalidOperation:
            errors.append("Enter a valid income amount.")

        if not form_values["description"]:
            errors.append("Enter a description.")

        try:
            income_date = datetime.strptime(form_values["date"], "%Y-%m-%d").date()
        except ValueError:
            errors.append("Enter a valid date.")

        if not errors:
            connection = None
            cursor = None
            try:
                connection = get_db_connection()
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO income (amount, description, date) VALUES (%s, %s, %s)",
                    (amount, form_values["description"], income_date),
                )
                connection.commit()
                confirmation = f"Income of ${amount:.2f} was added successfully."
            except psycopg.Error:
                app.logger.exception("Database error while saving income.")
                errors.append("Could not save income. Please try again.")
                if connection is not None:
                    try:
                        connection.rollback()
                    except psycopg.Error:
                        app.logger.exception("Database error while rolling back income insert.")
            finally:
                try:
                    if cursor is not None:
                        cursor.close()
                except psycopg.Error:
                    app.logger.exception("Database error while closing income cursor.")
                finally:
                    if connection is not None:
                        try:
                            connection.close()
                        except psycopg.Error:
                            app.logger.exception("Database error while closing income connection.")

    income_entries, income_load_error, expense_entries, expense_load_error, totals = load_entries()

    return render_template(
        "index.html",
        errors=errors,
        confirmation=confirmation,
        form_values=form_values,
        income_entries=income_entries,
        income_load_error=income_load_error,
        expense_load_error=expense_load_error,
        totals=totals,
        expense_errors=[],
        expense_confirmation=None,
        expense_form_values={"amount": "", "description": "", "date": "", "category": ""},
        expense_entries=expense_entries,
        expense_categories=expense_categories,
    )


@app.route("/add-expense", methods=["POST"])
def add_expense():
    """Validate an expense form submission and save it temporarily."""
    errors = []
    confirmation = None
    form_values = {
        "amount": request.form.get("amount", "").strip(),
        "description": request.form.get("description", "").strip(),
        "date": request.form.get("date", "").strip(),
        "category": request.form.get("category", "").strip(),
    }

    try:
        amount = Decimal(form_values["amount"])
        if not amount.is_finite() or amount <= 0:
            errors.append("Enter an expense amount greater than zero.")
    except InvalidOperation:
        errors.append("Enter a valid expense amount.")

    if not form_values["description"]:
        errors.append("Enter a description.")

    try:
        expense_date = datetime.strptime(form_values["date"], "%Y-%m-%d").date()
    except ValueError:
        errors.append("Enter a valid date.")

    if form_values["category"] not in expense_categories:
        errors.append("Choose a valid expense category.")

    if not errors:
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO expense (amount, description, date, category) "
                "VALUES (%s, %s, %s, %s)",
                (
                    amount,
                    form_values["description"],
                    expense_date,
                    form_values["category"],
                ),
            )
            connection.commit()
            confirmation = f"Expense of ${amount:.2f} was added successfully."
        except psycopg.Error:
            app.logger.exception("Database error while saving expense.")
            errors.append("Could not save expense. Please try again.")
            if connection is not None:
                try:
                    connection.rollback()
                except psycopg.Error:
                    app.logger.exception("Database error while rolling back expense insert.")
        finally:
            try:
                if cursor is not None:
                    cursor.close()
            except psycopg.Error:
                app.logger.exception("Database error while closing expense cursor.")
            finally:
                if connection is not None:
                    try:
                        connection.close()
                    except psycopg.Error:
                        app.logger.exception("Database error while closing expense connection.")

    income_entries, income_load_error, expense_entries, expense_load_error, totals = load_entries()

    return render_template(
        "index.html",
        errors=[],
        confirmation=None,
        form_values={"amount": "", "description": "", "date": ""},
        income_entries=income_entries,
        income_load_error=income_load_error,
        expense_errors=errors,
        expense_confirmation=confirmation,
        expense_form_values=form_values,
        expense_entries=expense_entries,
        expense_load_error=expense_load_error,
        totals=totals,
        expense_categories=expense_categories,
    )


@app.route("/edit/<entry_type>/<int:entry_id>", methods=["GET", "POST"])
def edit_entry(entry_type, entry_id):
    """Load an income or expense record and save valid edits."""
    if entry_type == "income":
        select_sql = "SELECT id, amount, description, date FROM income WHERE id = %s"
        update_sql = (
            "UPDATE income SET amount = %s, description = %s, date = %s WHERE id = %s"
        )
    elif entry_type == "expense":
        select_sql = (
            "SELECT id, amount, description, date, category FROM expense WHERE id = %s"
        )
        update_sql = (
            "UPDATE expense SET amount = %s, description = %s, date = %s, "
            "category = %s WHERE id = %s"
        )
    else:
        abort(404)

    entry = None
    errors = []
    load_error = None
    confirmation = None
    form_values = {"amount": "", "description": "", "date": "", "category": ""}
    loading_entry = True
    connection = None
    cursor = None

    if request.method == "POST":
        form_values = {
            "amount": request.form.get("amount", "").strip(),
            "description": request.form.get("description", "").strip(),
            "date": request.form.get("date", "").strip(),
            "category": request.form.get("category", "").strip(),
        }

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(select_sql, (entry_id,))
        row = cursor.fetchone()
        if row is None:
            abort(404)

        entry = {
            "id": row[0],
            "amount": row[1],
            "description": row[2],
            "date": row[3],
        }
        if entry_type == "expense":
            entry["category"] = row[4]

        loading_entry = False
        if request.method == "GET":
            form_values = {
                "amount": str(entry["amount"]),
                "description": entry["description"],
                "date": str(entry["date"]),
                "category": entry.get("category", ""),
            }
        else:
            try:
                amount = Decimal(form_values["amount"])
                if not amount.is_finite() or amount <= 0:
                    errors.append(f"Enter an {entry_type} amount greater than zero.")
            except InvalidOperation:
                errors.append(f"Enter a valid {entry_type} amount.")

            if not form_values["description"]:
                errors.append("Enter a description.")

            try:
                entry_date = datetime.strptime(form_values["date"], "%Y-%m-%d").date()
            except ValueError:
                errors.append("Enter a valid date.")

            if entry_type == "expense" and form_values["category"] not in expense_categories:
                errors.append("Choose a valid expense category.")

            if not errors:
                if entry_type == "income":
                    cursor.execute(
                        update_sql,
                        (
                            amount,
                            form_values["description"],
                            entry_date,
                            entry_id,
                        ),
                    )
                else:
                    cursor.execute(
                        update_sql,
                        (
                            amount,
                            form_values["description"],
                            entry_date,
                            form_values["category"],
                            entry_id,
                        ),
                    )

                if cursor.rowcount == 0:
                    abort(404)

                connection.commit()
                entry["amount"] = amount
                entry["description"] = form_values["description"]
                entry["date"] = entry_date
                if entry_type == "expense":
                    entry["category"] = form_values["category"]
                confirmation = f"{entry_type.title()} entry updated successfully."
    except psycopg.Error:
        app.logger.exception("Database error while editing %s entry %s.", entry_type, entry_id)
        if connection is not None:
            try:
                connection.rollback()
            except psycopg.Error:
                app.logger.exception("Database error while rolling back edit.")
        if loading_entry:
            load_error = "Could not load this entry for editing. Please try again."
        else:
            errors.append("Could not save changes. Please try again.")
    finally:
        try:
            if cursor is not None:
                cursor.close()
        except psycopg.Error:
            app.logger.exception("Database error while closing edit cursor.")
        finally:
            if connection is not None:
                try:
                    connection.close()
                except psycopg.Error:
                    app.logger.exception("Database error while closing edit connection.")

    income_entries, income_load_error, expense_entries, expense_load_error, totals = load_entries()

    return render_template(
        "index.html",
        errors=[],
        confirmation=None,
        form_values={"amount": "", "description": "", "date": ""},
        income_entries=income_entries,
        income_load_error=income_load_error,
        expense_errors=[],
        expense_confirmation=None,
        expense_form_values={"amount": "", "description": "", "date": "", "category": ""},
        expense_entries=expense_entries,
        expense_load_error=expense_load_error,
        totals=totals,
        expense_categories=expense_categories,
        edit_entry=entry,
        edit_type=entry_type,
        edit_entry_id=entry_id,
        edit_errors=errors,
        edit_load_error=load_error,
        edit_confirmation=confirmation,
        edit_form_values=form_values,
    )


@app.route("/delete/<entry_type>/<int:entry_id>", methods=["POST"])
def delete_entry(entry_type, entry_id):
    """Delete one income or expense record from PostgreSQL."""
    if entry_type == "income":
        delete_sql = "DELETE FROM income WHERE id = %s"
    elif entry_type == "expense":
        delete_sql = "DELETE FROM expense WHERE id = %s"
    else:
        abort(404)

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(delete_sql, (entry_id,))
        if cursor.rowcount == 0:
            abort(404)

        connection.commit()
        flash(f"{entry_type.title()} entry deleted successfully.")
    except psycopg.Error:
        app.logger.exception("Database error while deleting %s entry %s.", entry_type, entry_id)
        if connection is not None:
            try:
                connection.rollback()
            except psycopg.Error:
                app.logger.exception("Database error while rolling back delete.")
        flash(f"Could not delete {entry_type}. Please try again.")
    finally:
        try:
            if cursor is not None:
                cursor.close()
        except psycopg.Error:
            app.logger.exception("Database error while closing delete cursor.")
        finally:
            if connection is not None:
                try:
                    connection.close()
                except psycopg.Error:
                    app.logger.exception("Database error while closing delete connection.")

    return redirect(url_for("home"))