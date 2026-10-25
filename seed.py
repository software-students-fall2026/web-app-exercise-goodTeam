import os
import sys

from dotenv import load_dotenv
from pymongo import MongoClient
from werkzeug.security import generate_password_hash

load_dotenv()

db_uri = os.getenv("DB_URI")
db_name = os.getenv("DB_NAME")

if db_uri is None or db_name is None:
    print("DB_URI and DB_NAME must be set in .env")
    sys.exit(1)

db = MongoClient(db_uri)[db_name]

PASSWORD = "password"
USERNAMES = ["alice", "bob"]

db.users.delete_many({"$or": [{"seed": True}, {"username": {"$in": USERNAMES}}]})
db.groups.delete_many({"seed": True})
db.items.delete_many({"seed": True})

apartment_id = db.groups.insert_one({"name": "Apartment 4B", "seed": True}).inserted_id
beach_id = db.groups.insert_one({"name": "Beach House", "seed": True}).inserted_id

alice_id = db.users.insert_one(
    {
        "username": "coolAlice",
        "first_name": "Alice",
        "last_name": "Test",
        "password": generate_password_hash(PASSWORD),
        "biography": "Loves cooking, hates dishes.",
        "group_ids": [apartment_id, beach_id],
        "seed": True,
    }
).inserted_id
bob_id = db.users.insert_one(
    {
        "username": "coolBob",
        "first_name": "Bob",
        "last_name": "Test",
        "password": generate_password_hash(PASSWORD),
        "biography": "Will trade snacks for sleep.",
        "group_ids": [apartment_id],
        "seed": True,
    }
).inserted_id

owners = {
    "alice": (str(alice_id), "alice"),
    "bob": (str(bob_id), "bob"),
}

items = [
    ("alice", apartment_id, "Oat Milk", "Drinks", "2", "Unopened cartons", True),
    ("alice", apartment_id, "Pasta", "Food", "3", "Penne and spaghetti", True),
    ("alice", apartment_id, "Dish Soap", "Cleaning", "1", "", True),
    ("bob", apartment_id, "Protein Bars", "Snacks", "6", "Please ask first", False),
    ("bob", apartment_id, "Paper Towels", "Cleaning", "4", "", True),
    ("bob", apartment_id, "Hot Sauce", "Food", "1", "Very spicy", False),
    ("alice", beach_id, "Sunscreen", "Toiletries", "2", "SPF 50", True),
    ("alice", beach_id, "Chips", "Snacks", "5", "For the beach trip", False),
]

for owner, group_id, name, category, quantity, description, shared in items:
    owner_id, owner_name = owners[owner]
    db.items.insert_one(
        {
            "name": name,
            "category": category,
            "quantity": quantity,
            "description": description,
            "shared": shared,
            "owner_id": owner_id,
            "owner_name": owner_name,
            "parent_group_id": group_id,
            "seed": True,
        }
    )

print("Seeded 2 users, 2 groups and", len(items), "items.")
print("Log in as alice or bob, password:", PASSWORD)
