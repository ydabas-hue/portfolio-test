import unittest
import csv
import json
from pathlib import Path
import sys

# Add scraper dir to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import semantic_db

class TestSemanticDatabase(unittest.TestCase):
    def test_classify_dpl_accredited(self):
        res = semantic_db.classify_text(
            "Episode 6 : Story Behind the Post ft - @anujrawat_1755 #puranidilli #dpl2026",
            "abhishekpandey_26",
            "2026-08-15"
        )
        self.assertIn("DPL", res["tournament"])
        self.assertIn("Accredited", res["accreditation"])
        self.assertIn("Story Behind the Post", res["format"])
        self.assertIn("Anuj Rawat", res["entities"])

    def test_classify_ipl(self):
        res = semantic_db.classify_text(
            "Gt fan vs Mi fan (Matchday Banter)",
            "spinandswing26",
            "2026-05-31"
        )
        self.assertIn("IPL", res["tournament"])
        self.assertIn("Gujarat Titans", res["entities"])

    def test_classify_wpl(self):
        res = semantic_db.classify_text(
            "Harmanpreet Fan is cuteee (WPL)",
            "abhishekpandey_26",
            "2026-02-10"
        )
        self.assertIn("WPL", res["tournament"])
        self.assertIn("Harmanpreet", res["entities"])

    def test_generation_and_exports(self):
        records = semantic_db.generate_semantic_database()
        self.assertGreater(len(records), 20)

        # Check CSV files exist
        self.assertTrue(semantic_db.SRC_CSV.exists())
        self.assertTrue(semantic_db.PUB_CSV.exists())
        self.assertTrue(semantic_db.SRC_JSON.exists())
        self.assertTrue(semantic_db.PUB_JSON.exists())

        # Verify CSV readability
        with open(semantic_db.SRC_CSV, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), len(records))
            self.assertIn("Platform", rows[0])
            self.assertIn("URL", rows[0])
            self.assertIn("Tournament", rows[0])
            self.assertIn("Accreditation_Status", rows[0])
            self.assertIn("Views", rows[0])
            self.assertIn("Likes", rows[0])

if __name__ == "__main__":
    unittest.main()
