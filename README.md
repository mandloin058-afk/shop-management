# Shop Management System

A simple Django + MySQL web app for a shopkeeper: products, purchases, sales, stock,
expenses, customers/udhaar and profit/loss reports.

## Profit rules
- **Gross profit** = sales revenue − cost of the products sold
  (cost is the product's purchase price *at the time of the sale*)
- **Net profit** = gross profit − expenses

## Setup on Windows (Command Prompt)

Install first: **Python 3.10+** (tick "Add Python to PATH") and **MySQL Server 8**.

```bat
:: 1. Go to the project folder
cd shop_management

:: 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

:: 3. Install dependencies
pip install -r requirements.txt

:: 4. Create your settings file, then open .env in Notepad and fill in the MySQL password
copy .env.example .env
notepad .env

:: 5. Create the MySQL database (enter your MySQL root password when asked)
mysql -u root -p -e "CREATE DATABASE shop_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

:: 6. Create the tables
python manage.py migrate

:: 7. Create the shopkeeper/admin login
python manage.py createsuperuser

:: 8. (Optional) Add sample data
python manage.py seed_data

:: 9. Start the server
python manage.py runserver
```

Open http://127.0.0.1:8000/ and log in. The Django admin is at http://127.0.0.1:8000/admin/.

Next time, just run `venv\Scripts\activate` and `python manage.py runserver`.

If `mysql` is not recognised, add `C:\Program Files\MySQL\MySQL Server 8.0\bin` to PATH,
or run the CREATE DATABASE line in **MySQL Command Line Client** / **MySQL Workbench**.

Generate a strong secret key for `.env`:
```bat
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## If `pip install mysqlclient` fails
Use the pure-Python driver instead:
```bat
pip install pymysql cryptography
```
Then add these two lines at the top of `config/__init__.py`:
```python
import pymysql
pymysql.install_as_MySQLdb()
```

## Project structure
```
shop_management/
├── manage.py
├── requirements.txt
├── .env.example
├── config/      settings, urls, wsgi
├── shop/        models, forms, views, urls, migrations, seed command
├── templates/   base, login, form pages and templates/shop/*
└── static/      css/style.css, js/app.js
```

## How stock works
- Saving a **purchase** adds to product stock; deleting it takes the stock back.
- Saving a **sale** reduces stock (you cannot sell more than you have); deleting it returns the stock.
- A **sale with Udhaar** needs a customer; record what the customer pays later on the customer page.
