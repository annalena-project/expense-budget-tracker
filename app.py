from flask import Flask

# Create the Flask application.
app = Flask(__name__)


# Connect the home URL ("/") to this function.
@app.route("/")
def home():
    """Return the text shown on the home page."""
    return "Expense & Budget Tracker"