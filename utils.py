# app/chatbot/utils.py
import datetime
import sqlite3

def format_assistant_card(prediction, confidence, heatmap_url, rag_response):
    return {
        "prediction": prediction,
        "confidence": confidence,
        "heatmap": heatmap_url,
        "description": rag_response["response"],
        "sources": rag_response["sources"],
        "timestamp": str(datetime.datetime.now())
    }

def log_doctor_action(case_id, action, note="", db_path="app/db/cases.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO doctor_feedback (case_id, action, note, timestamp)
        VALUES (?, ?, ?, ?)
    """, (case_id, action, note, datetime.datetime.now()))
    conn.commit()
    conn.close()
