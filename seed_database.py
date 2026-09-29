# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0

from google.cloud import firestore

# Hardcoded Project ID string (DO NOT use GOOGLE_CLOUD_PROJECT or google.auth.default())
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-01-dc80020db869"

def seed():
    print(f"Connecting to Firestore for project: {FIRESTORE_PROJECT_ID}...")
    db = firestore.Client(project=FIRESTORE_PROJECT_ID)
    collection_ref = db.collection("pantry_items")

    items = [
        {
            "name": "Organic Olive Oil",
            "category": "Pantry Staples",
            "quantity": 1,
            "unit": "bottle",
            "expiration_days": 180,
        },
        {
            "name": "Jasmine Rice",
            "category": "Grains & Rice",
            "quantity": 5,
            "unit": "kg",
            "expiration_days": 365,
        },
        {
            "name": "Canned Black Beans",
            "category": "Canned Goods",
            "quantity": 6,
            "unit": "cans",
            "expiration_days": 730,
        },
        {
            "name": "Whole Wheat Pasta",
            "category": "Pasta & Grains",
            "quantity": 3,
            "unit": "boxes",
            "expiration_days": 300,
        },
        {
            "name": "Garlic Cloves",
            "category": "Produce",
            "quantity": 8,
            "unit": "cloves",
            "expiration_days": 14,
        },
    ]

    for item in items:
        # Use name slug as document ID
        doc_id = item["name"].lower().replace(" ", "_")
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(item)
        print(f"  - Seeded: {item['name']} ({doc_id})")

    print("✅ Firestore database successfully seeded!")

if __name__ == "__main__":
    seed()
