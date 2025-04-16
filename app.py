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
        
        if symbol:  # Check if symbol is not None
            symbol = symbol.upper()
            
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
        """Another way to find total shares:
        user_shares = db.excute("SELECT shares FROM transactions WHERE user_id=? AND symbol=? GROUP BY symbol", session["user_id"], symbol)
        total_shares = user_shares[0]["shares"]
        """

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
        
        try:
            # Update the user's password hash in the database.
            db.execute("UPDATE users SET hash =? WHERE id=?", new_hash, user_id)
        except:
            return apology("Database Error!")

        # Display a flash message to inform the user that their password has been changed successfully.
        flash("Password changed successfully!")
        return redirect("/")


    # if request.method == "GET":
    user_data = get_user_data()
    return render_template("changepassword.html", username=user_data["username"])

@app.route("/add_cash", methods=["GET", "POST"])
@login_required
def add_cash():
    user_data = get_user_data()
    if request.method == "POST":
        # Input Validation
        cash_amount = request.form.get("add_cash")
        if not cash_amount:
            return apology("Provide amount of Cash if you want to Add some!")
        
        try:
            cash_amount = float(cash_amount)
            # Check cash amount is a positive number.
            if cash_amount <=0:
                return apology("Amout of Cash to add Must be Positive!")
        except ValueError:
            return apology("Cash ammount must be Numeric!")

        try:
            # Update Database
            total_cash = cash_amount + user_data["cash"]
            db.execute("UPDATE users SET cash = ? WHERE id=?", total_cash, session["user_id"])
        except:
            return apology("Database error", 500)

        flash(f"{cash_amount} Added successfully!")
        return redirect("/")
    
    # if request.method == "GET":
    return render_template("add_cash.html", username=user_data["username"], cash=user_data["cash"])

@app.route("/watchlist", methods=["GET", "POST"])
@login_required
def watchlist(): 
    user_id = session["user_id"]
    edit_id = request.args.get("edit_id", type=int)

    if request.method == "POST":
        # Get form inputs
        symbol = request.form.get("symbol")
        target_price_input = request.form.get("target_price")
        direction = request.form.get("direction")

        # Validate presence
        if not symbol or not target_price_input:
            return apology("Must enter both symbol & target price!")

        # Validate stock symbol
        stock = lookup(symbol)
        if not stock:
            return apology("Symbol not found!")

        # Validate and convert target price
        try:
            target_price = float(target_price_input)
            if target_price < 0:
                return apology("Target price can't be negative!")
        except ValueError:
            return apology("Enter a valid number for price!")

        symbol = symbol.upper()
        # Insert new watchlist entry into the database
        db.execute(
            "INSERT INTO watchlist (user_id, symbol, target_price, direction) VALUES (?, ?, ?, ?)",
            user_id, symbol, target_price, direction
        )
        
        flash(f"{symbol} Added to watchlist")

    # GET request (or after POST insert)
    try:
        entries = db.execute("SELECT * FROM watchlist WHERE user_id = ?", user_id)
    except:
        return apology("Database Error, try again!")

    # Prepare list of entries with current price and condition status
    watchlist_with_status = []

    for entry in entries:
        # Get real-time data
        quote = lookup(entry["symbol"])
        if quote:
            current_price = float(quote["price"])
            target_price = float(entry["target_price"])
            direction = entry["direction"].lower()

            # Determine status
            if (direction == "above" and current_price > target_price) or \
            (direction == "below" and current_price < target_price):
                status = "✅"
            else:
                status = "-"

            # Add current price and status to entry
            watchlist_with_status.append({
                "id": entry["id"],  # Include this so HTML gets stock.id
                "symbol": entry["symbol"],
                "current_price": current_price,
                "target_price": target_price,
                "direction": direction,
                "status": status
            })
        else:
            # optionally message (or you may skip silently)
            print(f"Warning: No quote found for {entry['symbol']}")

    # Pass the structured list to the template
    return render_template("watchlist.html", watchlist=watchlist_with_status, edit_id=edit_id)
# That way, when you click "Edit", the route /watchlist/edit/3 can redirect to /watchlist?edit_id=3 to show the inline form.

@app.route("/watchlist/delete/<int:entry_id>", methods=["POST"])
@login_required
def delete_watchlist_entry(entry_id):
    # Get the current user's ID from the session
    user_id = session["user_id"]

    # Check if the watchlist entry with the given ID exists and belongs to this user
    entry = db.execute("SELECT * FROM watchlist WHERE id = ? AND user_id = ?", entry_id, user_id)

    # If not found or does not belong to the user, return an apology or error
    if not entry:
        return apology("No entry to be deleted!")

    # If valid, delete the entry from the watchlist table (confirm user_id)
    db.execute("DELETE FROM watchlist WHERE id = ? AND user_id = ?", entry_id, user_id)

    symbol = entry[0]["symbol"]  # Extract symbol for message
    flash(f"{symbol} successfully deleted from watchlist!")

    # Redirect the user back to the watchlist page
    return redirect("/watchlist")

@app.route("/watchlist/edit/<int:entry_id>", methods=["GET", "POST"]) 
@login_required
def edit_watchlist_entry(entry_id):
    # Get current user's ID from session
    user_id = session["user_id"]

    # Fetch the watchlist entry from DB by ID and make sure it belongs to this user
    entry = db.execute("SELECT * FROM watchlist WHERE id = ? AND user_id = ?", entry_id, user_id)

    # If entry not found or does not belong to the user, return an apology
    if not entry:
        return apology("No entry to edit!")

    # print(entry) # Outputs like:
    # [{'id': 8, 'user_id': 4, 'symbol': 'IBM', 'target_price': 220.0, 'direction': 'above', 'timestamp': '2025-04-14 15:07:22'}]
    # entry is returned as a list, so it’s best to extract the first dictionary
    entry = entry[0]

    # If method is POST:
    if request.method == "POST":
        # Get new values (e.g. target_price, direction) from form
        new_target_price = request.form.get("target_price")
        new_direction = request.form.get("direction")

        # Validate input: Use existing values if inputs are left blank
        if not new_target_price:
            new_target_price = entry["target_price"]
        if not new_direction:
            new_direction = entry["direction"]

        # Compare with existing values
        # This avoids false negatives like "220.0" != 220.0.
        new_target_price = float(new_target_price)
        changed_target = new_target_price != entry["target_price"]
        changed_direction = new_direction.lower() != entry["direction"].lower()

        if changed_target or changed_direction:
            # Update the entry in the database
            db.execute("UPDATE watchlist SET target_price = ?, direction = ? WHERE id = ?", new_target_price, new_direction, entry["id"])

            # flash a success message
            flash(f"{entry['symbol']} Successfully edited!")
        else:
            flash("No changes made.")

        # Redirect back to the watchlist
        return redirect("/watchlist")

    # If method is GET:
    # Render an edit form template, pre-filled with current values of the entry
    # return render_template("edit_watchlist.html", entry=entry) #if we have seperate edit html page
    return redirect(f"/watchlist?edit_id={entry_id}")