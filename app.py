import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd
import datetime

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

def get_user_data():
    # Retrieves the username and cash for the current user.
    user_data = db.execute("SELECT username, cash FROM users WHERE id=?", session["user_id"])
    if user_data:
        return user_data[0] #Returns the first (and only) dictionary
    else:
        return None #Returns None if user not found.

@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # if request.method == "GET":
    # Query database for user's transactions
    user_transactions = db.execute(
        "SELECT symbol, SUM(shares) AS total_shares FROM transactions WHERE user_id = ? GROUP BY symbol HAVING total_shares > 0",
        session["user_id"],
    )
    # to check what user_transactions get:
    # return jsonify(user_transactions)

    user_data = get_user_data()
    user_cash = round(user_data["cash"], 2)
    
    stock_data_list = []  # Create a list to store stock data

    # Loop through each transaction and get stock data
    for transaction in user_transactions:
        stock_data = lookup(transaction["symbol"])
        if stock_data:  # Check if lookup() returned a valid result
            stock_data["shares"] = transaction["total_shares"] # add the shares to the stock data dictionary.
            stock_data_list.append(stock_data)
        else:
            return apology("Symbol not found", 400) # Handle lookup errors.
    
    # Calculate total value of stocks
    total_value = round(sum(stock["shares"] * stock["price"] for stock in stock_data_list), 2)
    grand_total = round(total_value + user_cash, 2)
    
    # Render the index.html template with the user's portfolio data
    return render_template("index.html", stocks=stock_data_list, cash=user_cash, total_value=total_value, grand_total=grand_total, username=user_data["username"])


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    user_data = get_user_data()

    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        # Apology if the input is blank or the symbol does not exist.
        if not symbol or not shares:
            return apology(f"Missing {'symbol' if not symbol else 'shares'}")
        
        #Lookup symbol data
        stock_data = lookup(symbol) #lookup function deals with uppercase symbols
        if not stock_data:
            return apology("Symbol not found", 400)
        
        # Ensure shares is a positive integer
        try:
            shares = int(shares)
            if shares <=0:
                return apology("Shares must be positive", 400)
        except ValueError:
            return apology("Invalid number of shares", 400)
        
        """CREATE TABLE "transactions" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                symbol TEXT,
                shares INTEGER,
                price REAL,
                date timestamp,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        
        name = stock_data["name"]
        price = stock_data["price"]
        user_id = session["user_id"]
        total_cost = shares * price
        
        # user_cash_rows = db.execute("SELECT cash FROM users WHERE id=?", user_id)
        #to check what user_cash_rows get:
        # return jsonify(user_cash_rows)
        # output list of dictionaries containing a single dictionary:
        # [{"cash":10000}]
        """if not user_cash_rows:
            return apology("User not found", 500)  # Internal server error if user not found"""
        
        user_cash = user_data["cash"]

        #Render an apology, without completing a purchase, if the user cannot afford the number of shares at the current price.
        if total_cost > user_cash:
            return apology("Insufficient funds", 400)
        
        # Update user's cash
        new_cash = user_cash - total_cost
        # UPDATE table_name SET column_name = new_value WHERE condition
        db.execute("UPDATE users SET cash = ? WHERE id=?", new_cash, user_id)
        
        #Insert transaction in transactions table

        date_now = datetime.datetime.now()
        try:
            db.execute("INSERT INTO transactions (user_id, symbol, shares, price, date) VALUES (?, ?, ?, ?, ?)",user_id, symbol, shares, price, date_now)
        except:
            return apology("Database insertion Error!")
        
        flash(f"Bought {shares} shares of {name} ({symbol}) for {usd(total_cost)}")
        return redirect("/")
    # if request.method == "GET":
    return render_template("buy.html", username=user_data["username"], cash=user_data["cash"])


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    # For each row, make clear whether a stock was bought or sold and include the stock’s symbol, the (purchase or sale) price, the number of shares bought or sold, and the date and time at which the transaction occurred.
    transactions_db = db.execute(
        "SELECT * FROM transactions WHERE user_id =?", session["user_id"]
    )
    user_data = get_user_data()
    return render_template("history.html", transactions=transactions_db, username=user_data["username"], cash=user_data["cash"])


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    user_data = get_user_data()
    if request.method == "POST":
        symbol = request.form.get("quote")
        if not symbol:
            return apology("Must provide a Symbol")
        try:
            #get symbol data
            stock_data = lookup(symbol)
            if stock_data is None:
                return apology("Symbol not found")
        except:
            return apology("Symbol not found!")
        name = stock_data["name"]
        price = stock_data["price"]
        return render_template("quoted.html", name=name, price=price, symbol=stock_data["symbol"], username=user_data["username"], cash=user_data["cash"]) #embedding values from lookup
    
    # if request.method == "GET":
    return render_template("quote.html", username=user_data["username"], cash=user_data["cash"])


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        # Get form data
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Validate form data
        if not username:
            return apology("must provide username", 400)
        elif not password:
            return apology("must provide password", 400)
        elif password != confirmation:
            return apology("passwords do not match", 400)

        #Hash the password
        hash = generate_password_hash(password)

        try:
            # Insert user into database
            db.execute(
                "INSERT INTO users (username, hash) VALUES (?, ?)",
                username, hash
            )
        except ValueError:
            return apology("username already exists", 400)
        
        # Retrieve the new user's ID using SELECT
        row = db.execute("SELECT id FROM users WHERE username = ?", username)
        if not row:
            return apology("registration failed", 500)  # Server error if ID is not found

        # Remember which user has logged in (Store user ID in session)
        user_id = row[0]["id"]
        session["user_id"] = user_id

        # Redirect user to home page
        return redirect("/")
    # if request.method == "GET":
    return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # Get the unique stock symbols and total shares the user owns
    user_stocks = db.execute(
        "SELECT symbol, SUM(shares) AS total_shares FROM transactions WHERE user_id = ? GROUP BY symbol HAVING total_shares > 0",
        session["user_id"],
    )

    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
    
        # Find the correct total_shares from the user_stocks list
        total_shares = None
        for stock in user_stocks:
            if stock["symbol"] == symbol:
                total_shares = stock["total_shares"]
                break

        # Handles both not symbol and symbol not in user_stocks
        if total_shares is None:
            return apology("Symbol not found!")

        try:
            shares = int(shares)
        except ValueError:
            return apology("Invalid shares input!")

        if shares <= 0 or total_shares < shares:
            return apology(f"Allowed Shares between 1 - {total_shares}")
        
        price = lookup(symbol)
        if price is None:
            return apology("Could not look up price")
        sale = shares * price["price"]

        user_id = session["user_id"]
        cash = db.execute("SELECT cash FROM users WHERE id=?", user_id)[0]["cash"]

        updated_cash = cash + sale

        # Update user cash in the database
        db.execute("UPDATE users SET cash = ? WHERE id = ?", updated_cash, user_id)

        # Update Transactions Table
        db.execute(
            "INSERT INTO transactions (user_id, symbol, shares, price, date) VALUES (?, ?, ?, ?, ?)",
            user_id,
            symbol,
            -shares, # Make shares negative for selling
            price["price"],
            datetime.datetime.now(),
        )

        flash(f"{shares} Shares of ({symbol}) sold for {price['price'] * shares} !")
        return redirect("/")

    # GET request handling
    return render_template("sell.html", stocks=user_stocks)

@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    """Change user password"""
    if request.method == "POST":
        # Data entered by the user.
        password = request.form.get("password")
        new_pass = request.form.get("new_pass")
        confirm = request.form.get("confirmation")

        #Check if all fields are filled.
        if not password:
            return apology("Please provide your old password.")
        elif not new_pass:
            return apology("Please provide your new password.")
        elif not confirm:
            return apology("Please confirm your new password.")

        user_id= session["user_id"]
        # Verify Old Password:
        # Queries the database to retrieve the stored password hash for the current user.
        stored_hash = db.execute("SELECT hash FROM users WHERE id=?", user_id)

        """if not stored_hash:
            return apology("User not found", 400) #handles if the user does not exist.
        """
        stored_hash = stored_hash[0]["hash"]

        # Use check_password_hash() to verify that the entered old password matches the stored hash.
        if not check_password_hash(stored_hash, password):
            return apology("Incorrect old password.", 403) #403 is forbidden.
        
        # Check if the Old password and New Password are diffrent.
        if check_password_hash(stored_hash, new_pass):
            return apology("Old Password & New Password are the same!")
        
        # Check if the new password and confirmation match.
        if new_pass!= confirm:
            return apology("New password isn't as confirmed password")
        
        # use generate_password_hash() to hash the new password.
        new_hash = generate_password_hash(new_pass)
        
        # Update the user's password hash in the database.
        db.execute("UPDATE users SET hash =? WHERE id=?", new_hash, user_id)

        # Display a flash message to inform the user that their password has been changed successfully.
        flash("Password changed successfully!")
        return redirect("/")


    # if request.method == "GET":
    user_data = get_user_data()
    return render_template("changepassword.html", username=user_data["username"])