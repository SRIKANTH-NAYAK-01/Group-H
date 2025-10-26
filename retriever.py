# app/chatbot/retriever.py
import sqlite3
from typing import List, Dict

import sqlite3
import json

class KBRetriever:
    def __init__(self, db_path: str = "app/db/kb.db"):
        self.db_path = db_path

    def get_disease_info(self, disease_name: str) -> str:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = """
        SELECT d.name, d.organ, d.description, d.red_flags, d.recommended_tests, d.suggested_measures
        FROM diseases d
        LEFT JOIN keywords k ON d.disease_id = k.disease_id
        WHERE LOWER(d.name) = LOWER(?) OR LOWER(k.keyword) = LOWER(?)
        """
        cursor.execute(query, (disease_name, disease_name))
        row = cursor.fetchone()
        conn.close()

        if row:
            name, organ, desc, red_flags, tests_json, measures_json = row
            # parse JSON fields
            tests = json.loads(tests_json) if tests_json else []
            measures = json.loads(measures_json) if measures_json else []

            return (
                f"Disease: {name}\n"
                f"Organ: {organ}\n"
                f"Description: {desc}\n"
                f"Red Flags: {red_flags}\n"
                f"Recommended Tests: {tests}\n"
                f"Measures: {measures}\n"
            )
        else:
            return f"No information found for disease: {disease_name}"