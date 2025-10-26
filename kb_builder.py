import sqlite3
import json
from datetime import datetime

# --- Create a fresh DB ---
conn = sqlite3.connect("app/db/kb_full.db")  # new DB file
c = conn.cursor()

# ------------------
# Create tables
# ------------------
c.execute("""
CREATE TABLE IF NOT EXISTS diseases (
    disease_id TEXT PRIMARY KEY,
    name TEXT,
    organ TEXT,
    description TEXT,
    red_flags TEXT,
    recommended_tests TEXT,
    suggested_measures TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS symptoms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    disease_id TEXT,
    symptom TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    disease_id TEXT,
    test_name TEXT,
    details TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS drugs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    disease_id TEXT,
    name TEXT,
    rxnorm_json TEXT,
    openfda_json TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    disease_id TEXT,
    keyword TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS disease_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    disease_id TEXT,
    source TEXT,
    url TEXT
)
""")

# ------------------
# Full KB Data
# ------------------
diseases = [
    {
        "disease_id": "D001",
        "name": "Drusen",
        "organ": "Eye (Retina)",
        "description": (
            "Drusen are yellow deposits under the retina, often found in people over 50. "
            "They are composed of lipids, proteins, and cellular debris, and are early indicators "
            "of age-related macular degeneration (AMD)."
        ),
        "red_flags": "Sudden vision loss, distortion in central vision, new floaters",
        "recommended_tests": ["Fundus Photography", "Optical Coherence Tomography (OCT)"],
        "suggested_measures": ["Regular eye check-ups", "Monitor vision changes"],
        "keywords": ["Drusen","Retina"],
        "symptoms": ["Yellow deposits under retina", "Mild vision distortion"],
        "tests": [
            {"name": "OCT", "details": "Detect drusen deposits in retina"},
            {"name": "Fundus Photography", "details": "Visualize retina and detect early changes"}
        ],
        "drugs": [],
        "references": [{"source": "NEI", "url": "https://www.nei.nih.gov/learn-about-eye-health/eye-conditions-and-diseases/drusen"}]
    },
    {
        "disease_id": "D002",
        "name": "Diabetic Macular Edema (DME)",
        "organ": "Eye (Retina)",
        "description": (
            "DME is a complication of diabetic retinopathy where fluid accumulates in the macula. "
            "It can lead to blurred or distorted central vision and is a major cause of vision loss in diabetic patients."
        ),
        "red_flags": "Rapid vision loss, central scotoma, distorted vision",
        "recommended_tests": ["OCT", "Fluorescein Angiography"],
        "suggested_measures": ["Strict blood sugar control", "Regular ophthalmic exams"],
        "keywords": ["DME","Diabetes"],
        "symptoms": ["Blurred central vision", "Vision distortion in macula"],
        "tests": [
            {"name": "OCT", "details": "Assess macular thickness"},
            {"name": "Fluorescein Angiography", "details": "Identify retinal leakage"}
        ],
        "drugs": [{"name": "Anti-VEGF Injection", "rxnorm": {"rxnorm_id":"12345"}, "openfda": {"openfda_id":"A123"}}],
        "references": [{"source": "AAO", "url": "https://www.aao.org/eye-health/diseases/diabetic-macular-edema"}]
    },
    {
        "disease_id": "D003",
        "name": "Age-related Macular Degeneration (AMD)",
        "organ": "Eye (Retina)",
        "description": (
            "AMD is a degenerative disease of the macula causing central vision loss. "
            "It has dry and wet forms, with drusen accumulation in the dry type and neovascularization in the wet type."
        ),
        "red_flags": "Loss of central vision, metamorphopsia, difficulty reading",
        "recommended_tests": ["Fundus Exam", "OCT", "Fluorescein Angiography"],
        "suggested_measures": ["Anti-VEGF therapy for wet AMD", "Lifestyle modifications for dry AMD"],
        "keywords": ["AMD","Macula"],
        "symptoms": ["Central vision loss", "Difficulty recognizing faces"],
        "tests": [
            {"name": "Fundus Exam", "details": "Check for drusen and pigment changes"},
            {"name": "OCT", "details": "Assess macular structure"}
        ],
        "drugs": [{"name": "Anti-VEGF Injection", "rxnorm": {"rxnorm_id":"12345"}, "openfda": {"openfda_id":"A123"}}],
        "references": [{"source": "Mayo Clinic", "url": "https://www.mayoclinic.org/diseases-conditions/macular-degeneration"}]
    }
]

# ------------------
# Insert full data
# ------------------
for d in diseases:
    c.execute("""
    INSERT INTO diseases (disease_id, name, organ, description, red_flags,
                          recommended_tests, suggested_measures, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        d["disease_id"], d["name"], d["organ"], d["description"], d["red_flags"],
        json.dumps(d["recommended_tests"]), json.dumps(d["suggested_measures"]),
        datetime.now(), datetime.now()
    ))

    # Symptoms
    for s in d["symptoms"]:
        c.execute("INSERT INTO symptoms (disease_id, symptom) VALUES (?, ?)", (d["disease_id"], s))

    # Tests
    for t in d["tests"]:
        c.execute("INSERT INTO tests (disease_id, test_name, details) VALUES (?, ?, ?)", (d["disease_id"], t["name"], t["details"]))

    # Drugs
    for dr in d["drugs"]:
        c.execute("""
        INSERT INTO drugs (disease_id, name, rxnorm_json, openfda_json)
        VALUES (?, ?, ?, ?)
        """, (d["disease_id"], dr["name"], json.dumps(dr.get("rxnorm", {})), json.dumps(dr.get("openfda", {}))))

    # Keywords
    for k in d["keywords"]:
        c.execute("INSERT INTO keywords (disease_id, keyword) VALUES (?, ?)", (d["disease_id"], k))

    # References
    for r in d["references"]:
        c.execute("INSERT INTO disease_references (disease_id, source, url) VALUES (?, ?, ?)",
                  (d["disease_id"], r["source"], r["url"]))

conn.commit()
conn.close()
print("✅ Permanent full KB created: app/db/kb_full.db")
