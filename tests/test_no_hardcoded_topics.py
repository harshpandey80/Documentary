import unittest
from pathlib import Path

class TestNoHardcodedTopics(unittest.TestCase):
    """
    Rule 5 Compliance Check:
    'Topic-specific content lives only in project.yaml and input files, never in code.'
    Assures no topic-specific strings remain inside non-legacy docstudio/ source files.
    """

    BANNED_TOPIC_SUBSTRINGS = [
        "challenger deep",
        "10,994m",
        "10,994 meters",
        "36,070 ft",
        "1,086 atmospheres",
        "flight 19",
        "bathyscaphe trieste",
        "dsv limiting factor",
        "bayeux tapestry",
        "domesday book",
        "magna carta",
        "tudor warships",
        "london blitz",
    ]

    def test_docstudio_source_clean_of_topic_facts(self):
        project_root = Path(__file__).resolve().parent.parent
        docstudio_dir = project_root / "docstudio"
        self.assertTrue(docstudio_dir.exists(), "docstudio package dir must exist")

        # Scan all active docstudio python modules
        py_files = [
            f for f in docstudio_dir.rglob("*.py")
            if "legacy" not in f.parts and "__pycache__" not in f.parts
        ]

        # Also scan every active root script (including any render_*.py outside legacy)
        for root_py in project_root.glob("*.py"):
            if "legacy" not in root_py.parts and "__pycache__" not in root_py.parts:
                py_files.append(root_py)

        # Also scan any render_*.py anywhere outside legacy/ and tests/
        for render_script in project_root.rglob("render_*.py"):
            if "legacy" not in render_script.parts and "tests" not in render_script.parts:
                if render_script not in py_files:
                    py_files.append(render_script)

        self.assertGreater(len(py_files), 5, "Must find active python modules to scan")

        violations = []
        for py_file in py_files:
            content = py_file.read_text(encoding="utf-8").lower()
            for banned in self.BANNED_TOPIC_SUBSTRINGS:
                if banned in content:
                    violations.append(f"{py_file.relative_to(project_root)}: contains banned topic string '{banned}'")

        if violations:
            self.fail(
                "Hardcoded topic facts found in active source code (Rule 5 violation):\n"
                + "\n".join(violations)
            )

if __name__ == "__main__":
    unittest.main()
