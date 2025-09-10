from flask import Flask, render_template, request, redirect, url_for, Response
from models import db, Borrower, Transaction
from utils import (
    calculate_running_simple_balance,
    calculate_running_compound_balance,
    borrower_ledger_df,
)
from datetime import datetime
import pandas as pd
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lending.db"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
db.init_app(app)

@app.route("/")
def dashboard():
    borrowers = Borrower.query.all()
    data = []
    total_simple, total_compound = 0, 0

    for b in borrowers:
        sb, _ = calculate_running_simple_balance(b)
        cb, _ = calculate_running_compound_balance(b)
        total_simple += sb
        total_compound += cb
        data.append({"borrower": b, "simple": sb, "compound": cb})

    return render_template(
        "dashboard.html", borrowers=data,
        total_simple=total_simple, total_compound=total_compound
    )

@app.route("/borrower/<int:id>")
def borrower_detail(id):
    borrower = Borrower.query.get_or_404(id)

    # If mode is in query string → update borrower preference
    mode = request.args.get("mode")
    if mode in ["simple", "compound"]:
        borrower.preferred_mode = mode
        db.session.commit()
    else:
        # fallback: use saved preference
        mode = borrower.preferred_mode or "simple"

    # Calculate ledger
    if mode == "compound":
        balance, ledger = calculate_running_compound_balance(borrower)
    else:
        balance, ledger = calculate_running_simple_balance(borrower)

    # Pagination
    per_page = 20
    page = int(request.args.get("page", 1))
    total = len(ledger)
    total_pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    ledger_display = ledger[start:end]

    return render_template(
        "borrower.html",
        borrower=borrower,
        mode=mode,
        balance=balance,
        ledger=ledger_display,
        page=page,
        total_pages=total_pages,
        total=total
    )


@app.route("/add_borrower", methods=["POST"])
def add_borrower():
    name = request.form["name"]
    rate = float(request.form["rate"])
    notes = request.form.get("notes")
    b = Borrower(name=name, rate=rate, notes=notes)
    db.session.add(b)
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/edit_borrower/<int:id>", methods=["POST"])
def edit_borrower(id):
    borrower = Borrower.query.get_or_404(id)
    borrower.name = request.form["name"]
    borrower.rate = float(request.form["rate"])
    borrower.notes = request.form.get("notes")
    db.session.commit()
    return redirect(url_for("borrower_detail", id=id))

@app.route("/transaction/<int:id>", methods=["POST"])
def add_transaction(id):
    borrower = Borrower.query.get_or_404(id)
    txn_type = request.form["type"]
    amount = float(request.form["amount"])
    txn_date = request.form.get("date")

    if txn_date:
        txn_date = datetime.strptime(txn_date, "%Y-%m-%d")
    else:
        txn_date = datetime.utcnow()

    txn = Transaction(
        borrower_id=id, type=txn_type, amount=amount, date=txn_date
    )
    db.session.add(txn)
    db.session.commit()
    return redirect(url_for("borrower_detail", id=id))

@app.route("/transaction/edit/<int:txn_id>/<int:borrower_id>", methods=["POST"])
def edit_transaction(txn_id, borrower_id):
    txn = Transaction.query.get_or_404(txn_id)
    txn.type = request.form["type"]
    txn.amount = float(request.form["amount"])
    txn_date = request.form.get("date")
    if txn_date:
        txn.date = datetime.strptime(txn_date, "%Y-%m-%d")
    db.session.commit()
    return redirect(url_for("borrower_detail", id=borrower_id))

@app.route("/transaction/delete/<int:txn_id>/<int:borrower_id>", methods=["POST"])
def delete_transaction(txn_id, borrower_id):
    txn = Transaction.query.get_or_404(txn_id)
    db.session.delete(txn)
    db.session.commit()
    return redirect(url_for("borrower_detail", id=borrower_id))

@app.route("/upload", methods=["GET", "POST"])
def upload_excel():
    if request.method == "POST":
        file = request.files["file"]
        if file and file.filename.endswith((".xls", ".xlsx")):
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(file.filename))
            file.save(filepath)

            df = pd.read_excel(filepath)

            # Expected columns: borrower, date, type, amount, rate (optional)
            for _, row in df.iterrows():
                borrower_name = str(row.get("borrower", "Unknown")).strip()
                rate = float(row.get("rate", 12.0))

                # Get or create borrower
                borrower = Borrower.query.filter_by(name=borrower_name).first()
                if not borrower:
                    borrower = Borrower(name=borrower_name, rate=rate)
                    db.session.add(borrower)
                    db.session.commit()

                # Append transaction (no overwrite)
                # print(row)
                txn = Transaction(
                    borrower_id=borrower.id,
                    type=row["type"].strip().lower(),  # "loan" / "payment"
                    amount=float(row["amount"]),
                    date=pd.to_datetime(row["date"])
                )
                db.session.add(txn)

            db.session.commit()
            return redirect(url_for("dashboard"))

    return render_template("upload.html")

@app.route("/export/<int:id>/<string:mode>")
def export_csv(id, mode):
    borrower = Borrower.query.get_or_404(id)
    df = borrower_ledger_df(borrower, mode=mode)
    return Response(
        df.to_csv(index=False),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={borrower.name}_{mode}_ledger.csv"}
    )

def format_inr(value):
    try:
        value = float(value)
    except (ValueError, TypeError):
        return value

    # Split integer & decimal
    s = str(int(value))
    last3 = s[-3:]
    rest = s[:-3]
    if rest != '':
        rest = ",".join([rest[i - 2:i] for i in range(len(rest) % 2, len(rest), 2)])
        s = rest + "," + last3
    else:
        s = last3

    # Add decimals if any
    decimals = f"{value:.2f}".split(".")[1]
    return f"₹{s}.{decimals}"

# Register as Jinja filter
app.jinja_env.filters["inr"] = format_inr


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
