from datetime import date
import pandas as pd

# ---------- PYTHON LOOP VERSIONS ----------
def calculate_running_simple_balance(borrower):
    transactions = sorted(borrower.transactions, key=lambda t: t.date)
    if not transactions:
        return 0.0, []

    balance = 0.0
    last_date = transactions[0].date
    ledger = []
    daily_rate = borrower.rate / 100 / 365

    for txn in transactions:
        days = (txn.date.date() - last_date.date()).days
        interest = balance * daily_rate * days if balance > 0 else 0
        balance += interest

        if txn.type == "loan":
            balance += txn.amount
        elif txn.type == "payment":
            balance -= txn.amount

        ledger.append({
            "id": txn.id,
            "date": txn.date.date(),
            "type": txn.type,
            "amount": txn.amount,
            "days": days,
            "interest": round(interest, 2),
            "balance": round(balance, 2)
        })
        last_date = txn.date

    # Final accrual
    days = (date.today() - last_date.date()).days
    interest = balance * daily_rate * days if balance > 0 else 0
    balance += interest
    ledger.append({
        "date": date.today(),
        "type": "accrual",
        "amount": 0,
        "days": days,
        "interest": round(interest, 2),
        "balance": round(balance, 2)
    })

    return round(balance, 2), ledger


def calculate_running_compound_balance(borrower):
    transactions = sorted(borrower.transactions, key=lambda t: t.date)
    if not transactions:
        return 0.0, []

    balance = 0.0
    last_date = transactions[0].date
    ledger = []
    daily_rate = borrower.rate / 100 / 365

    for txn in transactions:
        days = (txn.date.date() - last_date.date()).days
        interest = 0
        if days > 0 and balance > 0:
            interest = balance * ((1 + daily_rate) ** days - 1)
            balance += interest

        if txn.type == "loan":
            balance += txn.amount
        elif txn.type == "payment":
            balance -= txn.amount

        ledger.append({
            "id": txn.id,
            "date": txn.date.date(),
            "type": txn.type,
            "amount": txn.amount,
            "days": days,
            "interest": round(interest, 2),
            "balance": round(balance, 2)
        })
        last_date = txn.date

    # Final accrual
    days = (date.today() - last_date.date()).days
    if days > 0 and balance > 0:
        interest = balance * ((1 + daily_rate) ** days - 1)
        balance += interest
        ledger.append({
            "date": date.today(),
            "type": "accrual",
            "amount": 0,
            "days": days,
            "interest": round(interest, 2),
            "balance": round(balance, 2)
        })

    return round(balance, 2), ledger


# ---------- PANDAS VERSIONS ----------
def borrower_ledger_df(borrower, mode="compound"):
    txns = [{"date": t.date.date(), "type": t.type, "amount": t.amount} for t in borrower.transactions]
    if not txns:
        return pd.DataFrame()

    df = pd.DataFrame(txns).sort_values("date").reset_index(drop=True)
    df["days"] = df["date"].diff().dt.days.fillna(0).astype(int)

    balance = 0
    balances, interests = [], []
    daily_rate = borrower.rate / 100 / 365

    for i, row in df.iterrows():
        days = row["days"]
        interest = 0
        if days > 0 and balance > 0:
            if mode == "compound":
                interest = balance * ((1 + daily_rate) ** days - 1)
            else:
                interest = balance * daily_rate * days
            balance += interest

        if row["type"] == "loan":
            balance += row["amount"]
        elif row["type"] == "payment":
            balance -= row["amount"]

        interests.append(round(interest, 2))
        balances.append(round(balance, 2))

    df["interest"] = interests
    df["balance"] = balances

    # Final accrual
    last_date = df.iloc[-1]["date"]
    days = (date.today() - last_date).days
    if days > 0 and balance > 0:
        if mode == "compound":
            interest = balance * ((1 + daily_rate) ** days - 1)
        else:
            interest = balance * daily_rate * days
        balance += interest
        df = pd.concat([df, pd.DataFrame([{
            "date": date.today(),
            "type": "accrual",
            "amount": 0,
            "days": days,
            "interest": round(interest, 2),
            "balance": round(balance, 2)
        }])], ignore_index=True)

    return df
