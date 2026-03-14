import os
import sys
import unittest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.append(BACKEND_DIR)

from ingest.linkedin import parse_linkedin_profile


class LinkedInIngestTests(unittest.TestCase):
    def test_normalises_skills_and_maps_headline(self):
        payload = {
            "name": "Sam Test",
            "email": "SAM@EXAMPLE.COM",
            "headline": "Senior Developer",
            "skills": ["ReactJS", "ML", "python"],
        }
        parsed = parse_linkedin_profile(payload)
        self.assertEqual(parsed["email"], "sam@example.com")
        self.assertEqual(parsed["current_role"], "Senior Developer")
        self.assertEqual(parsed["skills"], ["react", "machine learning", "python"])
        self.assertEqual(parsed["source"], "linkedin")

    def test_requires_email(self):
        with self.assertRaises(ValueError):
            parse_linkedin_profile({"name": "Missing Email"})


if __name__ == "__main__":
    unittest.main()

