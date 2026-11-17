from datetime import datetime
from decimal import Decimal, InvalidOperation

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


# Show the form on GET requests and process it when it is submitted with POST.
@app.route("/", methods=["GET", "POST"])
def home():
    """Display the income form and save valid submissions temporarily."""
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
            income_entries.append(
                {
                    "amount": amount,
                    "description": form_values["description"],
                    "date": income_date,
                }
            )
            confirmation = f"Income of ${amount:.2f} was added successfully."

    return render_template(
        "index.html",
        errors=errors,
        confirmation=confirmation,
        form_values=form_values,
        income_entries=income_entries,
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
        expense_entries.append(
            {
                "amount": amount,
                "description": form_values["description"],
                "date": expense_date,
                "category": form_values["category"],
            }
        )
        confirmation = f"Expense of ${amount:.2f} was added successfully."

    return render_template(
        "index.html",
        errors=[],
        confirmation=None,
        form_values={"amount": "", "description": "", "date": ""},
        income_entries=income_entries,
        expense_errors=errors,
        expense_confirmation=confirmation,
        expense_form_values=form_values,
        expense_entries=expense_entries,
        expense_categories=expense_categories,
    )


@app.route("/edit/<entry_type>/<int:index>", methods=["GET", "POST"])
def edit_entry(entry_type, index):
    """Show an edit form and save valid changes to an existing entry."""
    if entry_type == "income":
        entries = income_entries
    elif entry_type == "expense":
        entries = expense_entries
    else:
        abort(404)

    if index >= len(entries):
        abort(404)

    entry = entries[index]
    errors = []
    confirmation = None
    form_values = {
        "amount": str(entry["amount"]),
        "description": entry["description"],
        "date": str(entry["date"]),
        "category": entry.get("category", ""),
    }

    if request.method == "POST":
        form_values = {
            "amount": request.form.get("amount", "").strip(),
            "description": request.form.get("description", "").strip(),
            "date": request.form.get("date", "").strip(),
            "category": request.form.get("category", "").strip(),
        }

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
            entry["amount"] = amount
            entry["description"] = form_values["description"]
            entry["date"] = entry_date
            if entry_type == "expense":
                entry["category"] = form_values["category"]
            confirmation = f"{entry_type.title()} entry updated successfully."

    return render_template(
        "index.html",
        errors=[],
        confirmation=None,
        form_values={"amount": "", "description": "", "date": ""},
        income_entries=income_entries,
        expense_errors=[],
        expense_confirmation=None,
        expense_form_values={"amount": "", "description": "", "date": "", "category": ""},
        expense_entries=expense_entries,
        expense_categories=expense_categories,
        edit_entry=entry,
        edit_type=entry_type,
        edit_index=index,
        edit_errors=errors,
        edit_confirmation=confirmation,
        edit_form_values=form_values,
    )


@app.route("/delete/<entry_type>/<int:index>", methods=["POST"])
def delete_entry(entry_type, index):
    """Delete one income or expense entry and return to the home page."""
    if entry_type == "income":
        entries = income_entries
    elif entry_type == "expense":
        entries = expense_entries
    else:
        abort(404)

    if index < 0 or index >= len(entries):
        abort(404)

    entries.pop(index)
    flash(f"{entry_type.title()} entry deleted successfully.")
    return redirect(url_for("home"))