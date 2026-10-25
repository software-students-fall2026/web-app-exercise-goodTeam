import os
import re
import sys
import uuid
from pathlib import Path

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

ALLOWED_IMAGE_EXTS = [".png", ".jpg", ".jpeg", ".webp"]

load_dotenv()

app_secret = os.getenv("FLASK_SECRET_KEY")
db_uri = os.getenv("DB_URI")
db_name = os.getenv("DB_NAME")

if app_secret is None:
    print("FLASK_SECRET_KEY not set in .env")
    sys.exit(1)

if db_uri is None:
    print("DB_URI not set in .env")
    sys.exit(1)

if db_name is None:
    print("DB_NAME not set in .env")
    sys.exit(1)

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.secret_key = app_secret
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

UPLOAD_DIR = Path(app.static_folder) / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
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
        self.first_name = user_doc["first_name"]
        self.last_name = user_doc["last_name"]
        self.biography = user_doc.get("biography", "")
        self.group_ids = user_doc.get("group_ids", [])


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


def get_group(group_id):
    if not ObjectId.is_valid(group_id):
        abort(404)
    group = db.groups.find_one({"_id": ObjectId(group_id)})
    if group is None:
        abort(404)
    return group


def add_user_to_group(group_id):
    cur_user_groups = current_user.group_ids
    cur_user_groups.append(group_id)
    db.users.update_one(
        {"_id": ObjectId(current_user.id)},
        {
            "$push": {
                "group_ids": ObjectId(group_id),
            }
        },
    )


# def get_users_in_group(group_id):
#     if not ObjectId.is_valid(group_id):
#         abort(404)
#     group = get_group(group_id)
#     return []


def remove_image(image_filename):
    if image_filename:
        (UPLOAD_DIR / image_filename).unlink(missing_ok=True)


def assert_owner(item):
    if item["owner_id"] != current_user.id:
        abort(403)


def assert_group_member(group):
    if not db.users.find_one(
        {"_id": ObjectId(current_user.id), "group_ids": group["_id"]},
        {"_id": 1},
    ):
        abort(403)


def assert_item_in_group(group, item):
    if item["parent_group_id"] != group["_id"]:
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
                "biography": "",
                "group_ids": [],
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


@app.route("/profile", methods=["GET"])
@login_required
def profile():
    return render_template("profile.html", user=current_user)


# ---------- main routes -----------


@app.route("/", methods=["GET"])
def home():
    if current_user.is_authenticated:
        return redirect(url_for("groups"))
    return render_template("no_acct.html")


@app.route("/groups", methods=["GET"])
@login_required
def groups():
    cur_user_groups = list(db.groups.find({"_id": {"$in": current_user.group_ids}}))
    return render_template("groups.html", groups=cur_user_groups)


@app.route("/group/<group_id>/members", methods=["GET"])
@login_required
def group_members(group_id):
    cur_group = get_group(group_id)
    assert_group_member(cur_group)
    members = list(db.users.find({"group_ids": cur_group["_id"]}))
    return render_template("members.html", group=cur_group, members=members)


@app.route("/group/<group_id>/items", methods=["GET"])
@login_required
def items(group_id):
    cur_group = get_group(group_id)
    assert_group_member(cur_group)
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "")
    view = request.args.get("view", "all")

    query = {"parent_group_id": cur_group["_id"]}
    if search:
        query["name"] = {"$regex": re.escape(search), "$options": "i"}
    if category in CATEGORIES:
        query["category"] = category
    if view == "shared":
        query["shared"] = True
    elif view == "mine":
        query["owner_id"] = current_user.id
    else:
        view = "all"

    my_items = list(db.items.find(query).sort("name", 1))
    return render_template(
        "lists.html",
        group=cur_group,
        items=my_items,
        categories=CATEGORIES,
        search=search,
        category=category,
        view=view,
    )


@app.route("/group/<group_id>/item/<item_id>", methods=["GET"])
@login_required
def item_detail(group_id, item_id):
    cur_group = get_group(group_id)
    assert_group_member(cur_group)
    item = get_item(item_id)

    assert_item_in_group(cur_group, item)

    return render_template("item_detail.html", item=item)


@app.route("/group/<group_id>/item/add", methods=["GET", "POST"])
@login_required
def item_create(group_id):
    cur_group = get_group(group_id)
    assert_group_member(cur_group)

    if request.method == "POST":
        req_img = request.files.get("item_image")
        image_filename = ""
        if req_img is not None and req_img.filename != "":
            img_ext = Path(req_img.filename).suffix.lower()
            if img_ext not in ALLOWED_IMAGE_EXTS:
                flash("Image must be a .png, .jpg, .jpeg or .webp file")
                return redirect(url_for("item_create", group_id=group_id))

            image_filename = f"{uuid.uuid4().hex}{img_ext}"
            req_img.save(UPLOAD_DIR / image_filename)

        new_item = {
            "name": request.form.get("item_name", "").strip(),
            "category": request.form.get("item_category", "Other"),
            "quantity": request.form.get("item_quantity", "1"),
            "description": request.form.get("item_description", ""),
            "image": image_filename,
            "shared": request.form.get("shared") == "true",
            "owner_id": current_user.id,
            "owner_name": current_user.username,
            "parent_group_id": cur_group["_id"],
        }
        db.items.insert_one(new_item)
        return redirect(url_for("items", group_id=group_id))

    return render_template(
        "item_entry.html", group=cur_group, item=None, categories=CATEGORIES
    )


@app.route("/group/<group_id>/item/<item_id>/edit", methods=["GET", "POST"])
@login_required
def item_edit(group_id, item_id):
    cur_group = get_group(group_id)
    assert_group_member(cur_group)

    item = get_item(item_id)
    assert_owner(item)

    assert_item_in_group(cur_group, item)

    if request.method == "POST":
        req_img = request.files.get("item_image")
        image_filename = item.get("image", "")
        if req_img is not None and req_img.filename != "":
            img_ext = Path(req_img.filename).suffix.lower()
            if img_ext not in ALLOWED_IMAGE_EXTS:
                flash("Image must be a .png, .jpg, .jpeg or .webp file")
                return redirect(
                    url_for("item_edit", group_id=group_id, item_id=item_id)
                )

            remove_image(image_filename)
            image_filename = f"{uuid.uuid4().hex}{img_ext}"
            req_img.save(UPLOAD_DIR / image_filename)

        db.items.update_one(
            {"_id": item["_id"]},
            {
                "$set": {
                    "name": request.form.get("item_name", item["name"]).strip(),
                    "category": request.form.get("item_category", item["category"]),
                    "quantity": request.form.get("item_quantity", item["quantity"]),
                    "description": request.form.get("item_description", ""),
                    "image": image_filename,
                    "shared": request.form.get("shared") == "true",
                }
            },
        )
        return redirect(url_for("item_detail", group_id=group_id, item_id=item_id))

    return render_template(
        "item_entry.html", group=cur_group, item=item, categories=CATEGORIES
    )


@app.route("/group/create", methods=["GET", "POST"])
@login_required
def group_create():
    if request.method == "POST":
        name = request.form.get("group_name")
        result = db.groups.insert_one({"name": name})

        add_user_to_group(result.inserted_id)
        cur_user_groups = list(db.groups.find({"_id": {"$in": current_user.group_ids}}))
        return redirect(url_for("groups", groups=cur_user_groups))

    return render_template("create_group.html")


@app.route("/group/<group_id>/item/<item_id>/delete", methods=["POST"])
@login_required
def item_delete(group_id, item_id):
    cur_group = get_group(group_id)
    assert_group_member(cur_group)

    item = get_item(item_id)
    assert_owner(item)

    assert_item_in_group(cur_group, item)

    remove_image(item.get("image", ""))
    db.items.delete_one({"_id": item["_id"]})
    return redirect(url_for("items", group_id=group_id))


if __name__ == "__main__":
    host = os.getenv("HOST") if os.getenv("HOST") is not None else "localhost"
    port_str = os.getenv("PORT")
    port = int(port_str) if port_str is not None else 8081

    app.run(host=host, port=port, debug=True)
