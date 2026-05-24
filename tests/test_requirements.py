"""
Tests for requirements.txt – Pillow version constraint.

Verifies that the Pillow dependency was correctly bumped to >=12.2.0,<13
to address CVE fixes, and that the constraint properly excludes the
previously vulnerable range (>=10.4.0,<11).
"""

import os
import re
import unittest

from packaging.requirements import Requirement
from packaging.version import Version

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIREMENTS_TXT = os.path.join(ROOT_DIR, "requirements.txt")


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _parse_requirements(text):
    """Return a dict mapping package name (lower-case) -> Requirement."""
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            req = Requirement(line)
            result[req.name.lower()] = req
        except Exception:
            pass
    return result


# ---------------------------------------------------------------------------
# 1. requirements.txt file-level checks
# ---------------------------------------------------------------------------


class TestRequirementsFile(unittest.TestCase):
    """Basic sanity checks for the requirements.txt file itself."""

    def test_requirements_file_exists(self):
        self.assertTrue(
            os.path.isfile(REQUIREMENTS_TXT),
            "requirements.txt must exist at the project root",
        )

    def test_requirements_file_is_not_empty(self):
        content = _read(REQUIREMENTS_TXT)
        self.assertTrue(content.strip(), "requirements.txt must not be empty")

    def test_pillow_entry_is_present(self):
        content = _read(REQUIREMENTS_TXT)
        # Case-insensitive search – pip is case-insensitive for package names
        self.assertRegex(
            content,
            re.compile(r"(?i)^pillow", re.MULTILINE),
            "requirements.txt must contain a Pillow entry",
        )


# ---------------------------------------------------------------------------
# 2. Pillow version constraint correctness
# ---------------------------------------------------------------------------


class TestPillowVersionConstraint(unittest.TestCase):
    """The Pillow constraint must reflect the security bump to >=12.2.0,<13."""

    @classmethod
    def setUpClass(cls):
        content = _read(REQUIREMENTS_TXT)
        reqs = _parse_requirements(content)
        cls.pillow_req = reqs.get("pillow")

    def test_pillow_requirement_parseable(self):
        self.assertIsNotNone(
            self.pillow_req,
            "Pillow entry in requirements.txt must be parseable by packaging",
        )

    def test_pillow_minimum_version_is_12_2_0(self):
        """Minimum must be 12.2.0 (the CVE-fix release), not the old 10.4.0."""
        specifier = self.pillow_req.specifier
        # Version 12.2.0 must be allowed
        self.assertTrue(
            specifier.contains("12.2.0", prereleases=False),
            "Pillow specifier must allow version 12.2.0",
        )

    def test_pillow_lower_bound_excludes_10_4_0(self):
        """Old minimum 10.4.0 must be rejected by the new constraint."""
        specifier = self.pillow_req.specifier
        self.assertFalse(
            specifier.contains("10.4.0", prereleases=False),
            "Pillow specifier must NOT allow vulnerable version 10.4.0",
        )

    def test_pillow_upper_bound_excludes_version_13(self):
        """Major version 13 must be excluded to avoid untested breaking changes."""
        specifier = self.pillow_req.specifier
        self.assertFalse(
            specifier.contains("13.0.0", prereleases=False),
            "Pillow specifier must NOT allow version 13.0.0 (upper bound is <13)",
        )

    def test_pillow_upper_bound_allows_12_x(self):
        """A representative 12.x release beyond 12.2.0 must be allowed."""
        specifier = self.pillow_req.specifier
        self.assertTrue(
            specifier.contains("12.9.0", prereleases=False),
            "Pillow specifier must allow 12.9.0 (within the 12.x range)",
        )

    def test_pillow_constraint_string_contains_new_minimum(self):
        """The raw line in requirements.txt must reference 12.2.0, not 10.4.0."""
        content = _read(REQUIREMENTS_TXT)
        # Find the Pillow line (case-insensitive)
        pillow_line = next(
            (ln for ln in content.splitlines() if re.match(r"(?i)pillow", ln.strip())),
            None,
        )
        self.assertIsNotNone(pillow_line, "Pillow line must exist in requirements.txt")
        self.assertIn(
            "12.2.0",
            pillow_line,
            "Pillow line must contain '12.2.0' as the lower bound",
        )
        self.assertNotIn(
            "10.4.0",
            pillow_line,
            "Pillow line must NOT still reference the old lower bound '10.4.0'",
        )

    def test_pillow_upper_bound_is_less_than_13(self):
        """Explicit check that the upper bound specifier is <13, not <11."""
        content = _read(REQUIREMENTS_TXT)
        pillow_line = next(
            (ln for ln in content.splitlines() if re.match(r"(?i)pillow", ln.strip())),
            None,
        )
        self.assertIsNotNone(pillow_line)
        self.assertIn(
            "<13",
            pillow_line,
            "Pillow upper bound must be '<13', not '<11' (the old value)",
        )
        self.assertNotIn(
            "<11",
            pillow_line,
            "Pillow line must NOT contain the old upper bound '<11'",
        )


# ---------------------------------------------------------------------------
# 3. Boundary / regression tests for the specifier
# ---------------------------------------------------------------------------


class TestPillowVersionBoundaries(unittest.TestCase):
    """Edge-case and regression tests for the Pillow version specifier."""

    @classmethod
    def setUpClass(cls):
        content = _read(REQUIREMENTS_TXT)
        reqs = _parse_requirements(content)
        cls.specifier = reqs["pillow"].specifier

    def test_version_just_below_minimum_is_rejected(self):
        """12.1.9 is below 12.2.0 and must be rejected."""
        self.assertFalse(
            self.specifier.contains("12.1.9", prereleases=False),
            "Version 12.1.9 is below the minimum and must be rejected",
        )

    def test_exact_minimum_version_is_accepted(self):
        """12.2.0 is the exact minimum and must be accepted."""
        self.assertTrue(
            self.specifier.contains("12.2.0", prereleases=False),
            "Exact minimum version 12.2.0 must be accepted",
        )

    def test_version_just_above_minimum_is_accepted(self):
        """12.2.1 is just above the minimum and must be accepted."""
        self.assertTrue(
            self.specifier.contains("12.2.1", prereleases=False),
            "Version 12.2.1 must be accepted",
        )

    def test_last_valid_12_x_patch_is_accepted(self):
        """12.99.99 is still within the 12.x range and must be accepted."""
        self.assertTrue(
            self.specifier.contains("12.99.99", prereleases=False),
            "Version 12.99.99 must be accepted (still <13)",
        )

    def test_version_13_0_0_is_rejected(self):
        """13.0.0 must be rejected by the <13 upper bound."""
        self.assertFalse(
            self.specifier.contains("13.0.0", prereleases=False),
            "Version 13.0.0 must be rejected by the <13 upper bound",
        )

    def test_old_vulnerable_11_x_versions_are_rejected(self):
        """Versions in the previously-allowed 10.4.0–11 range must now be rejected."""
        for ver in ("10.4.0", "10.4.1", "10.5.0", "11.0.0", "11.9.9"):
            with self.subTest(version=ver):
                self.assertFalse(
                    self.specifier.contains(ver, prereleases=False),
                    f"Previously vulnerable version {ver} must be rejected",
                )

    def test_cve_fix_release_series_accepted(self):
        """Several 12.2.x and higher patch releases must all be accepted."""
        for ver in ("12.2.0", "12.2.1", "12.3.0", "12.4.0", "12.5.0"):
            with self.subTest(version=ver):
                self.assertTrue(
                    self.specifier.contains(ver, prereleases=False),
                    f"Version {ver} must be accepted by the updated constraint",
                )


# ---------------------------------------------------------------------------
# 4. Installed Pillow version check (skipped when Pillow is not installed)
# ---------------------------------------------------------------------------


class TestInstalledPillowVersion(unittest.TestCase):
    """Verify the *installed* Pillow version satisfies the constraint."""

    @classmethod
    def setUpClass(cls):
        try:
            import importlib.metadata as meta
            cls.installed_version = Version(meta.version("Pillow"))
            cls.pillow_available = True
        except Exception:
            cls.installed_version = None
            cls.pillow_available = False

        content = _read(REQUIREMENTS_TXT)
        reqs = _parse_requirements(content)
        cls.specifier = reqs["pillow"].specifier

    def _skip_if_not_installed(self):
        if not self.pillow_available:
            self.skipTest("Pillow is not installed in this environment")

    def test_installed_version_meets_minimum(self):
        self._skip_if_not_installed()
        self.assertGreaterEqual(
            self.installed_version,
            Version("12.2.0"),
            f"Installed Pillow {self.installed_version} must be >= 12.2.0",
        )

    def test_installed_version_meets_upper_bound(self):
        self._skip_if_not_installed()
        self.assertLess(
            self.installed_version,
            Version("13.0.0"),
            f"Installed Pillow {self.installed_version} must be < 13.0.0",
        )

    def test_installed_version_satisfies_full_specifier(self):
        self._skip_if_not_installed()
        self.assertTrue(
            self.specifier.contains(str(self.installed_version), prereleases=False),
            f"Installed Pillow {self.installed_version} must satisfy {self.specifier}",
        )

    def test_installed_version_is_not_from_old_vulnerable_range(self):
        self._skip_if_not_installed()
        self.assertGreaterEqual(
            self.installed_version,
            Version("12.2.0"),
            f"Installed Pillow {self.installed_version} must not be from the "
            "old vulnerable >=10.4.0,<11 range",
        )


if __name__ == "__main__":
    unittest.main()
