from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Flask
from flask import render_template, request

# Create the Flask application and a temporary in-memory list for income entries.
app = Flask(__name__)
income_entries = []


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
    )