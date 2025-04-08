# CS50 Finance

This project is a web application built using Flask, Python, and SQL, designed to simulate a stock trading platform. It's part of the CS50x Introduction to Computer Science.

## Features

* **User Registration and Login:** Secure user authentication with password hashing.
* **Stock Quotes:** Fetches real-time stock quotes using the IEX Cloud API.
* **Buy Stocks:** Allows users to purchase shares of stocks.
* **Sell Stocks:** Enables users to sell shares of stocks they own.
* **Transaction History:** Displays a history of all user transactions.
* **Portfolio:** Shows the user's current stock holdings and their total value.
* **Change Password:** Securely allows users to change their passwords.
* **Add Cash:** Allows users to add additional cash to their account.

## Technologies Used

* **Flask:** Python web framework.
* **SQL (SQLite):** Database for storing user data and transactions.
* **Jinja2:** Templating engine for HTML.
* **Werkzeug:** Password hashing and security.
* **IEX Cloud API:** For fetching stock quotes.
* **Bootstrap:** CSS framework for styling.

## Setup

1.  **Clone the Repository:**

    ```bash
    git clone [your_repository_url]
    cd finance
    ```

2.  **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up IEX Cloud API Key:**

    * Create an account on [IEX Cloud](https://iexcloud.io/).
    * Obtain your API key.
    * Set the `API_KEY` environment variable:

        ```bash
        export API_KEY=[your_api_key]
        ```

4.  **Run the Application:**

    ```bash
    flask run
    ```

5.  **Access the Application:**

    * Open your web browser and navigate to `http://127.0.0.1:5000/`.

## Database Setup

The application uses an SQLite database (`finance.db`). The database schema includes tables for:

* **users:** Stores user registration information (username, password hash, cash).
* **transactions:** Stores stock transaction records (user ID, symbol, shares, price, date).

The database is created and initialized automatically when the application runs for the first time.

## Adding Cash Feature (Additional Implementation)

I've also implemented a feature to allow users to add cash to their accounts. This involves:

* Creating a new route (`/add_cash`).
* A new HTML template (`add_cash.html`) with a form for cash input.
* Updating the `users` table in the database.
* Input validation to ensure the cash amount is a positive number.
* Flash messages to provide user feedback.

## Notes

* This project is for educational purposes and is not intended for real-world stock trading.
* Ensure you handle API keys securely and do not expose them in your code.
* The `helpers.py` file contains helper functions for looking up stock quotes, formatting currency, and other common tasks.
* The `layout.html` file provides the base layout for all HTML templates.
