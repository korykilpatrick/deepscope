#!/usr/bin/env python3
import os
import sys

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.dependencies import get_firebase_db

# Get the database instance from dependencies
db = get_firebase_db()

def delete_collection(coll_ref, batch_size=10):
    docs = list(coll_ref.limit(batch_size).stream())
    if not docs:
        return
    for doc in docs:
        # Delete any nested subcollections
        for subcoll in doc.reference.collections():
            delete_collection(subcoll, batch_size)
        doc.reference.delete()
    delete_collection(coll_ref, batch_size)

def reset_fact_check_results():
    # Assuming 'fact_checks' is the parent collection
    for fact_check in db.collection('fact_checks').stream():
        subcoll = fact_check.reference.collection('fact_check_results')
        delete_collection(subcoll)

if __name__ == '__main__':
    reset_fact_check_results()
    print("All fact_check_results subcollections have been deleted.")