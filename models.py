from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Borrower(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    rate = db.Column(db.Float, default=12.0)  # annual % rate
    notes = db.Column(db.Text)
    preferred_mode = db.Column(db.String(20), default="simple")
    transactions = db.relationship("Transaction", backref="borrower", lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    borrower_id = db.Column(db.Integer, db.ForeignKey("borrower.id"), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # "loan" or "payment"
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
