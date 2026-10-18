import os
import sys
from dotenv import load_dotenv
from flask import Flask, render_template
from pymongo import MongoClient

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

db_uri = os.getenv("DB_URI")
db_name = os.getenv("DB_NAME")

if db_uri is None:
    print("DB_URI not set in .env")
    sys.exit(1)

if db_name is None:
    print("DB_NAME not set in .env")
    sys.exit(1)

client = MongoClient(db_uri)

db = client[db_name]


@app.route("/", methods=["GET"])
def home():
    """Home page"""
    testEntries = [
            {"name": "person1", "description": "hello"},
            {"name": "person2", "description": "bye"},
            {"name": "person3", "description": "wow"},
            {"name": "person3", "description": "wow"},
            {"name": "person3", "description": "wow"},
            {"name": "person3", "description": "wow"},
            {"name": "person3", "description": "wow"}
        ]
    return render_template("index.html", entries=testEntries)


@app.route("/items", methods=["GET"])
def items():
    """Items page, shows a list of all the items"""
    items = [
        {"name": "bananas", "price": 3},
        {"name": "apples", "price": 5},
        {"name": "oranges", "price": 6},
        {"name": "oranges", "price": 6},
        {"name": "oranges", "price": 6},
        {"name": "oranges", "price": 6},
        {"name": "oranges", "price": 6},
        {"name": "oranges", "price": 6},
        {"name": "oranges", "price": 6},
        {"name": "oranges", "price": 6},
        {"name": "oranges", "price": 6},
        {"name": "oranges", "price": 6},
        {"name": "oranges", "price": 6}
    ]
    return render_template("lists.html", items=items)

@app.route("/profile", methods=["GET"])
def profile():
    """Profile page, shows user profile"""
    user = {
        "username": "Jack",
        "room": "Dorm 1",
        "biography": "cool guy"
    }
    return render_template("profile.html", user=user)

@app.route("/item_entry", methods=["GET"])
def item_entry():
    return render_template("item_entry.html");

@app.route("/create", methods=["POST"])
def item_create():
    #Put create item code here
    #Follow fields from item_entry.html to get values
    return

if __name__ == "__main__":
    host = os.getenv("HOST") if os.getenv("HOST") is not None else "localhost"
    port_str = os.getenv("PORT")
    port = int(port_str) if port_str is not None else 8081

    app.run(host=host, port=port, debug=True)
