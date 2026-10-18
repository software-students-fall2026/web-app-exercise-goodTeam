import os
import re
import sys

from bson.objectid import ObjectId
from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from pymongo import MongoClient
from werkzeug.security import check_password_hash, generate_password_hash

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

CATEGORIES = ["Food", "Snacks", "Drinks", "Cleaning", "Toiletries", "Other"]

# login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(UserMixin):
    def __init__(self, user_doc):
        self.id = str(user_doc["_id"])
        self.username = user_doc["username"]
        self.room = user_doc.get("room", "")
        self.biography = user_doc.get("biography", "")


@login_manager.user_loader
def load_user(user_id):
    user_doc = db.users.find_one({"_id": ObjectId(user_id)})
    if user_doc is None:
        return None
    return User(user_doc)


def get_item(item_id):
    if not ObjectId.is_valid(item_id):
        abort(404)
    item = db.items.find_one({"_id": ObjectId(item_id)})
    if item is None:
        abort(404)
    return item


def check_owner(item):
    if item["owner_id"] != current_user.id:
        abort(403)


# ---------- accounts ----------


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == "" or password == "":
            flash("Username and password are required")
            return redirect(url_for("register"))

        if db.users.find_one({"username": username}):
            flash("That username is taken")
            return redirect(url_for("register"))

        db.users.insert_one(
            {
                "username": username,
                "password": generate_password_hash(password),
                "room": request.form.get("room", ""),
                "biography": "",
            }
        )
        flash("Account created, please log in")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user_doc = db.users.find_one({"username": username})
        if user_doc and check_password_hash(user_doc["password"], password):
            login_user(User(user_doc))
            return redirect(url_for("home"))

        flash("Wrong username or password")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------- viewing items ----------


@app.route("/", methods=["GET"])
@login_required
def home():
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "")

    query = {}
    if search:
        query["name"] = {"$regex": re.escape(search), "$options": "i"}
    if category:
        query["category"] = category

    items = list(db.items.find(query).sort("name", 1))
    return render_template(
        "index.html",
        entries=items,
        categories=CATEGORIES,
        search=search,
        category=category,
        title="All Items",
    )


@app.route("/shared", methods=["GET"])
@login_required
def shared():
    items = list(db.items.find({"shared": True}).sort("name", 1))
    return render_template(
        "index.html",
        entries=items,
        categories=CATEGORIES,
        search="",
        category="",
        title="Shared Items",
    )


@app.route("/items", methods=["GET"])
@login_required
def items():
    my_items = list(db.items.find({"owner_id": current_user.id}).sort("name", 1))
    return render_template("lists.html", items=my_items)


@app.route("/item/<item_id>", methods=["GET"])
@login_required
def item_detail(item_id):
    item = get_item(item_id)
    return render_template("item_detail.html", item=item)


@app.route("/profile", methods=["GET"])
@login_required
def profile():
    return render_template("profile.html", user=current_user)


# ---------- adding / changing items ----------


@app.route("/item_entry", methods=["GET"])
@login_required
def item_entry():
    return render_template("item_entry.html", item=None, categories=CATEGORIES)


@app.route("/create", methods=["POST"])
@login_required
def item_create():
    name = request.form.get("item_name", "").strip()
    if name == "":
        flash("Item name is required")
        return redirect(url_for("item_entry"))

    new_item = {
        "name": name,
        "category": request.form.get("item_category", "Other"),
        "quantity": request.form.get("item_quantity", "1"),
        "description": request.form.get("item_description", ""),
        "shared": request.form.get("tag") == "everyone",
        "owner_id": current_user.id,
        "owner_name": current_user.username,
    }
    db.items.insert_one(new_item)
    return redirect(url_for("home"))


@app.route("/item/<item_id>/edit", methods=["GET", "POST"])
@login_required
def item_edit(item_id):
    item = get_item(item_id)
    check_owner(item)

    if request.method == "POST":
        db.items.update_one(
            {"_id": item["_id"]},
            {
                "$set": {
                    "name": request.form.get("item_name", item["name"]).strip(),
                    "category": request.form.get("item_category", item["category"]),
                    "quantity": request.form.get("item_quantity", item["quantity"]),
                    "description": request.form.get("item_description", ""),
                    "shared": request.form.get("tag") == "everyone",
                }
            },
        )
        return redirect(url_for("item_detail", item_id=item_id))

    return render_template("item_entry.html", item=item, categories=CATEGORIES)


@app.route("/item/<item_id>/share", methods=["POST"])
@login_required
def item_toggle_share(item_id):
    item = get_item(item_id)
    check_owner(item)
    db.items.update_one({"_id": item["_id"]}, {"$set": {"shared": not item["shared"]}})
    return redirect(url_for("item_detail", item_id=item_id))


@app.route("/item/<item_id>/delete", methods=["POST"])
@login_required
def item_delete(item_id):
    item = get_item(item_id)
    check_owner(item)
    db.items.delete_one({"_id": item["_id"]})
    return redirect(url_for("items"))


if __name__ == "__main__":
    host = os.getenv("HOST") if os.getenv("HOST") is not None else "localhost"
    port_str = os.getenv("PORT")
    port = int(port_str) if port_str is not None else 8081

    app.run(host=host, port=port, debug=True)
