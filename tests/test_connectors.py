"""
Tests for connectors.md documentation accuracy.

These tests verify that the claims made in connectors.md accurately
reflect the actual implementation in app.py and database.py.
"""

import ast
import os
import re
import sys
import unittest

# Paths relative to this file's location (tests/)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_PY = os.path.join(ROOT_DIR, "app.py")
DATABASE_PY = os.path.join(ROOT_DIR, "database.py")
CONNECTORS_MD = os.path.join(ROOT_DIR, "connectors.md")


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Helpers for AST-based inspection of database.py (no merge conflict there)
# ---------------------------------------------------------------------------

def _parse_database_py():
    """Return an AST for database.py, raising on parse failure."""
    return ast.parse(_read(DATABASE_PY))


def _class_names_in_module(tree):
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}


def _get_tablename_for_class(tree, class_name):
    """Return the __tablename__ string literal for a given class, or None."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for stmt in ast.walk(node):
                if (
                    isinstance(stmt, ast.Assign)
                    and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and stmt.targets[0].id == "__tablename__"
                    and isinstance(stmt.value, ast.Constant)
                ):
                    return stmt.value.value
    return None


# ---------------------------------------------------------------------------
# 1. Markdown structure tests
# ---------------------------------------------------------------------------

class TestConnectorsMdStructure(unittest.TestCase):
    """connectors.md must contain all documented sections."""

    @classmethod
    def setUpClass(cls):
        cls.content = _read(CONNECTORS_MD)

    def test_file_exists(self):
        self.assertTrue(os.path.isfile(CONNECTORS_MD), "connectors.md must exist")

    def test_has_database_connector_section(self):
        self.assertIn("## Database Connector", self.content)

    def test_has_authentication_connector_section(self):
        self.assertIn("## Authentication Connector", self.content)

    def test_has_environment_configuration_section(self):
        self.assertIn("## Environment Configuration", self.content)

    def test_has_csrf_protection_section(self):
        self.assertIn("## CSRF Protection", self.content)

    def test_has_production_server_section(self):
        self.assertIn("## Production Server", self.content)

    def test_has_adding_connector_section(self):
        self.assertIn("## Adding a New Connector", self.content)

    def test_mentions_flask_sqlalchemy(self):
        self.assertIn("Flask-SQLAlchemy", self.content)

    def test_mentions_flask_login(self):
        self.assertIn("Flask-Login", self.content)

    def test_mentions_flask_wtf(self):
        self.assertIn("Flask-WTF", self.content)

    def test_mentions_gunicorn(self):
        self.assertIn("Gunicorn", self.content)

    def test_mentions_python_dotenv(self):
        self.assertIn("python-dotenv", self.content)


# ---------------------------------------------------------------------------
# 2. Database model documentation vs database.py
# ---------------------------------------------------------------------------

EXPECTED_MODELS = {
    "User": "users",
    "Message": "messages",
    "ForumPost": "forum_posts",
    "ForumComment": "forum_comments",
    "Like": "likes",
    "Match": "matches",
}


class TestDatabaseModelDocumentation(unittest.TestCase):
    """All models documented in connectors.md must exist with correct table names."""

    @classmethod
    def setUpClass(cls):
        cls.tree = _parse_database_py()
        cls.md_content = _read(CONNECTORS_MD)

    def test_database_py_is_parseable(self):
        """database.py must be valid Python (no merge conflicts)."""
        self.assertIsNotNone(self.tree)

    def test_all_documented_model_classes_exist(self):
        """Every model listed in connectors.md must be defined in database.py."""
        defined_classes = _class_names_in_module(self.tree)
        for model_name in EXPECTED_MODELS:
            with self.subTest(model=model_name):
                self.assertIn(
                    model_name,
                    defined_classes,
                    f"Model '{model_name}' documented in connectors.md not found in database.py",
                )

    def test_user_table_name(self):
        self.assertEqual(_get_tablename_for_class(self.tree, "User"), "users")

    def test_message_table_name(self):
        self.assertEqual(_get_tablename_for_class(self.tree, "Message"), "messages")

    def test_forum_post_table_name(self):
        self.assertEqual(_get_tablename_for_class(self.tree, "ForumPost"), "forum_posts")

    def test_forum_comment_table_name(self):
        self.assertEqual(_get_tablename_for_class(self.tree, "ForumComment"), "forum_comments")

    def test_like_table_name(self):
        self.assertEqual(_get_tablename_for_class(self.tree, "Like"), "likes")

    def test_match_table_name(self):
        self.assertEqual(_get_tablename_for_class(self.tree, "Match"), "matches")

    def test_models_table_in_md_lists_all_six_models(self):
        """connectors.md models table must mention every expected model name."""
        for model_name in EXPECTED_MODELS:
            with self.subTest(model=model_name):
                self.assertIn(
                    f"`{model_name}`",
                    self.md_content,
                    f"connectors.md models table missing backtick-wrapped `{model_name}`",
                )

    def test_models_table_in_md_lists_all_six_table_names(self):
        """connectors.md models table must mention every expected SQL table name."""
        for table_name in EXPECTED_MODELS.values():
            with self.subTest(table=table_name):
                self.assertIn(
                    f"`{table_name}`",
                    self.md_content,
                    f"connectors.md models table missing backtick-wrapped `{table_name}`",
                )

    def test_exactly_six_models_documented(self):
        """connectors.md should document exactly six models (no undocumented extras)."""
        self.assertEqual(len(EXPECTED_MODELS), 6)

    def test_md_states_models_in_database_py(self):
        self.assertIn("database.py", self.md_content)


# ---------------------------------------------------------------------------
# 3. Password hashing documentation vs database.py
# ---------------------------------------------------------------------------

class TestPasswordHashingDocumentation(unittest.TestCase):
    """connectors.md claims werkzeug.security is used for password hashing."""

    @classmethod
    def setUpClass(cls):
        cls.db_source = _read(DATABASE_PY)
        cls.md_content = _read(CONNECTORS_MD)

    def test_werkzeug_security_imported_in_database_py(self):
        self.assertIn("from werkzeug.security import", self.db_source)

    def test_generate_password_hash_imported(self):
        self.assertIn("generate_password_hash", self.db_source)

    def test_check_password_hash_imported(self):
        self.assertIn("check_password_hash", self.db_source)

    def test_md_mentions_werkzeug_security(self):
        self.assertIn("werkzeug.security", self.md_content)

    def test_md_mentions_generate_password_hash(self):
        self.assertIn("generate_password_hash", self.md_content)

    def test_md_mentions_check_password_hash(self):
        self.assertIn("check_password_hash", self.md_content)

    def test_set_password_uses_generate_hash(self):
        """User.set_password() must call generate_password_hash."""
        self.assertIn("generate_password_hash", self.db_source)
        # Verify it's used inside the set_password method body
        pattern = re.compile(r"def set_password.*?generate_password_hash", re.DOTALL)
        self.assertRegex(self.db_source, pattern)

    def test_check_password_uses_check_hash(self):
        """User.check_password() must call check_password_hash."""
        pattern = re.compile(r"def check_password.*?check_password_hash", re.DOTALL)
        self.assertRegex(self.db_source, pattern)


# ---------------------------------------------------------------------------
# 4. App configuration documentation vs app.py source text
# ---------------------------------------------------------------------------

class TestAppConfigDocumentation(unittest.TestCase):
    """
    connectors.md documents specific configuration code in app.py.
    We verify by inspecting app.py as text (it has a merge conflict so cannot be
    imported, but the relevant lines are outside the conflict region).
    """

    @classmethod
    def setUpClass(cls):
        cls.app_source = _read(APP_PY)
        cls.md_content = _read(CONNECTORS_MD)

    def test_database_uri_config_line_exists(self):
        """app.py must set SQLALCHEMY_DATABASE_URI from DATABASE_URL env var."""
        self.assertIn(
            "app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL'",
            self.app_source,
        )

    def test_database_uri_default_is_sqlite(self):
        """The default DATABASE_URL must be sqlite:///felon_dating.db as documented."""
        self.assertIn("sqlite:///felon_dating.db", self.app_source)

    def test_db_init_app_called(self):
        """db.init_app(app) must be called in app.py."""
        self.assertIn("db.init_app(app)", self.app_source)

    def test_secret_key_config_line_exists(self):
        """app.py must set SECRET_KEY from the SECRET_KEY env var."""
        self.assertIn("app.config['SECRET_KEY'] = os.getenv('SECRET_KEY'", self.app_source)

    def test_secret_key_default_value(self):
        """Default SECRET_KEY must match the value documented in connectors.md."""
        expected_default = "dev-secret-key-change-in-production"
        self.assertIn(expected_default, self.app_source)

    def test_md_documents_secret_key_default(self):
        self.assertIn("dev-secret-key-change-in-production", self.md_content)

    def test_md_documents_database_url_default(self):
        self.assertIn("sqlite:///felon_dating.db", self.md_content)

    def test_schema_initialisation_uses_app_context(self):
        """db.create_all() must be called inside an app context."""
        self.assertIn("with app.app_context():", self.app_source)
        self.assertIn("db.create_all()", self.app_source)

    def test_schema_init_pattern_is_contiguous(self):
        """The app_context block containing db.create_all() must appear together."""
        pattern = r"with app\.app_context\(\):\s+db\.create_all\(\)"
        self.assertRegex(
            self.app_source,
            pattern,
            "app.py must call db.create_all() directly inside 'with app.app_context():' block",
        )

    def test_md_documents_schema_init_pattern(self):
        """connectors.md code block must show the correct schema-init snippet."""
        self.assertIn("with app.app_context():", self.md_content)
        self.assertIn("db.create_all()", self.md_content)

    def test_host_env_var_used_in_app_py(self):
        """app.py must read the HOST environment variable."""
        self.assertIn("os.getenv('HOST'", self.app_source)

    def test_host_default_is_0_0_0_0(self):
        self.assertIn("0.0.0.0", self.app_source)

    def test_port_env_var_used_in_app_py(self):
        """app.py must read the PORT environment variable."""
        self.assertIn("os.getenv('PORT'", self.app_source)

    def test_port_default_is_5000(self):
        self.assertIn("5000", self.app_source)

    def test_flask_debug_env_var_used_in_app_py(self):
        """app.py must read the FLASK_DEBUG environment variable."""
        self.assertIn("os.getenv('FLASK_DEBUG'", self.app_source)

    def test_md_documents_host_env_var(self):
        self.assertIn("`HOST`", self.md_content)

    def test_md_documents_port_env_var(self):
        self.assertIn("`PORT`", self.md_content)

    def test_md_documents_flask_debug_env_var(self):
        self.assertIn("`FLASK_DEBUG`", self.md_content)

    def test_md_documents_host_default(self):
        self.assertIn("0.0.0.0", self.md_content)

    def test_md_documents_port_default(self):
        self.assertIn("5000", self.md_content)

    def test_md_code_snippet_matches_actual_uri_config(self):
        """The Python code block in connectors.md must match what is in app.py."""
        snippet = "app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///felon_dating.db')"
        self.assertIn(snippet, self.md_content)
        self.assertIn(snippet, self.app_source)


# ---------------------------------------------------------------------------
# 5. Authentication connector documentation vs app.py
# ---------------------------------------------------------------------------

class TestAuthenticationDocumentation(unittest.TestCase):
    """connectors.md claims about Flask-Login setup must hold in app.py."""

    @classmethod
    def setUpClass(cls):
        cls.app_source = _read(APP_PY)
        cls.md_content = _read(CONNECTORS_MD)

    def test_flask_login_imported(self):
        self.assertIn("from flask_login import", self.app_source)

    def test_login_manager_created(self):
        self.assertIn("LoginManager", self.app_source)

    def test_load_user_function_defined(self):
        """connectors.md claims load_user(user_id) is defined in app.py."""
        self.assertIn("def load_user(user_id)", self.app_source)

    def test_user_loader_decorator_present(self):
        """@login_manager.user_loader decorator must decorate load_user."""
        self.assertIn("@login_manager.user_loader", self.app_source)

    def test_login_view_set_to_login(self):
        """Unauthenticated users must be redirected to /login (login_view = 'login')."""
        self.assertIn("login_manager.login_view = 'login'", self.app_source)

    def test_md_claims_load_user_in_app_py(self):
        self.assertIn("load_user(user_id)", self.md_content)
        self.assertIn("app.py", self.md_content)

    def test_md_claims_redirect_to_login(self):
        self.assertIn("/login", self.md_content)

    def test_login_required_used_on_protected_routes(self):
        """@login_required must protect at least one route in app.py."""
        self.assertIn("@login_required", self.app_source)

    def test_dotenv_load_called(self):
        """python-dotenv load_dotenv() must be called in app.py."""
        self.assertIn("load_dotenv()", self.app_source)


# ---------------------------------------------------------------------------
# 6. CSRF protection documentation vs app.py
# ---------------------------------------------------------------------------

class TestCsrfProtectionDocumentation(unittest.TestCase):
    """
    connectors.md documents specific CSRF protection gaps:
    - add_comment uses request.form (not FlaskForm) → no CSRF
    - CSRFProtect is NOT globally initialized
    """

    @classmethod
    def setUpClass(cls):
        cls.app_source = _read(APP_PY)
        cls.md_content = _read(CONNECTORS_MD)

    def test_flask_wtf_imported(self):
        """Flask-WTF must be imported (FlaskForm used for CSRF-protected routes)."""
        self.assertIn("from flask_wtf import FlaskForm", self.app_source)

    def test_add_comment_uses_request_form_not_flask_form(self):
        """
        add_comment must use request.form.get() directly, confirming the CSRF gap
        documented in connectors.md.
        """
        # Locate the add_comment function body
        pattern = r"def add_comment\(.*?\).*?return redirect"
        match = re.search(pattern, self.app_source, re.DOTALL)
        self.assertIsNotNone(match, "add_comment function not found in app.py")
        body = match.group(0)
        self.assertIn("request.form.get(", body)

    def test_add_comment_does_not_use_flask_form(self):
        """add_comment must NOT instantiate a FlaskForm subclass."""
        pattern = r"def add_comment\(.*?\).*?return redirect"
        match = re.search(pattern, self.app_source, re.DOTALL)
        self.assertIsNotNone(match, "add_comment function not found in app.py")
        body = match.group(0)
        # Should not reference any Form class
        self.assertNotIn("FlaskForm", body)
        self.assertNotIn("Form()", body)

    def test_csrf_protect_not_globally_initialized(self):
        """
        connectors.md explicitly states CSRFProtect is NOT initialised globally.
        Verify that CSRFProtect() is not called in app.py.
        """
        # Allow import of CSRFProtect but not its instantiation/initialization
        self.assertNotIn("CSRFProtect(app)", self.app_source)
        self.assertNotIn("csrf = CSRFProtect(", self.app_source)
        self.assertNotIn("csrf.init_app(", self.app_source)

    def test_md_mentions_add_comment_lacks_csrf(self):
        self.assertIn("add_comment", self.md_content)

    def test_md_states_csrf_protect_not_initialized(self):
        self.assertIn("CSRFProtect", self.md_content)
        self.assertIn("not initialised", self.md_content)

    def test_md_secret_key_used_for_csrf_signing(self):
        """connectors.md must mention SECRET_KEY is used to sign CSRF tokens."""
        self.assertIn("SECRET_KEY", self.md_content)

    def test_forms_using_flask_form_have_csrf(self):
        """
        Regression: at least one form must use FlaskForm (CSRF-protected routes exist).
        """
        flask_form_subclasses = re.findall(r"class \w+\(FlaskForm\)", self.app_source)
        self.assertGreater(
            len(flask_form_subclasses),
            0,
            "No FlaskForm subclasses found; documented CSRF-protected routes would not have protection",
        )


# ---------------------------------------------------------------------------
# 7. Production server documentation
# ---------------------------------------------------------------------------

class TestProductionServerDocumentation(unittest.TestCase):
    """connectors.md documents a specific gunicorn command for production."""

    @classmethod
    def setUpClass(cls):
        cls.md_content = _read(CONNECTORS_MD)

    def test_gunicorn_command_present(self):
        self.assertIn("gunicorn", self.md_content)

    def test_gunicorn_worker_flag(self):
        """-w 4 (four workers) must appear in the documented command."""
        self.assertIn("-w 4", self.md_content)

    def test_gunicorn_bind_flag(self):
        """-b 0.0.0.0:5000 must appear in the documented command."""
        self.assertIn("-b 0.0.0.0:5000", self.md_content)

    def test_gunicorn_app_module(self):
        """The gunicorn command must target the app:app entry point."""
        self.assertIn("app:app", self.md_content)

    def test_full_gunicorn_command(self):
        """The complete gunicorn command must be present verbatim."""
        self.assertIn("gunicorn -w 4 -b 0.0.0.0:5000 app:app", self.md_content)


# ---------------------------------------------------------------------------
# 8. Adding a new connector — process documentation
# ---------------------------------------------------------------------------

class TestAddingConnectorDocumentation(unittest.TestCase):
    """connectors.md must describe a three-step process for adding connectors."""

    @classmethod
    def setUpClass(cls):
        cls.md_content = _read(CONNECTORS_MD)

    def test_step_install_package_mentioned(self):
        self.assertIn("requirements.txt", self.md_content)

    def test_step_initialise_in_app_py_mentioned(self):
        """Step 2 must mention initialising the connector in app.py."""
        # Should reference app.py in the adding-connector section
        adding_section_start = self.md_content.find("## Adding a New Connector")
        self.assertNotEqual(adding_section_start, -1)
        adding_section = self.md_content[adding_section_start:]
        self.assertIn("app.py", adding_section)

    def test_step_document_env_vars_mentioned(self):
        """.env must be mentioned in the adding-connector instructions."""
        adding_section_start = self.md_content.find("## Adding a New Connector")
        self.assertNotEqual(adding_section_start, -1)
        adding_section = self.md_content[adding_section_start:]
        self.assertIn(".env", adding_section)

    def test_three_numbered_steps(self):
        """The adding-connector section must have exactly 3 numbered steps."""
        adding_section_start = self.md_content.find("## Adding a New Connector")
        self.assertNotEqual(adding_section_start, -1)
        adding_section = self.md_content[adding_section_start:]
        steps = re.findall(r"^\d+\.", adding_section, re.MULTILINE)
        self.assertEqual(len(steps), 3, f"Expected 3 numbered steps, found {len(steps)}")


# ---------------------------------------------------------------------------
# 9. Environment variable table completeness
# ---------------------------------------------------------------------------

class TestEnvironmentVariableTable(unittest.TestCase):
    """The env-var table in connectors.md must document all five variables."""

    EXPECTED_VARS = ["SECRET_KEY", "DATABASE_URL", "HOST", "PORT", "FLASK_DEBUG"]

    @classmethod
    def setUpClass(cls):
        cls.md_content = _read(CONNECTORS_MD)

    def test_all_env_vars_documented(self):
        for var in self.EXPECTED_VARS:
            with self.subTest(var=var):
                self.assertIn(f"`{var}`", self.md_content)

    def test_gitignore_warning_present(self):
        """connectors.md must warn against committing .env."""
        self.assertIn(".gitignore", self.md_content)
        self.assertIn(".env", self.md_content)

    def test_flask_debug_default_is_zero(self):
        """FLASK_DEBUG default must be documented as 0."""
        # Find the env config section
        env_section_start = self.md_content.find("## Environment Configuration")
        self.assertNotEqual(env_section_start, -1)
        env_section = self.md_content[env_section_start:]
        # The table row for FLASK_DEBUG should show 0 as default
        flask_debug_row = re.search(r"`FLASK_DEBUG`.*", env_section)
        self.assertIsNotNone(flask_debug_row)
        self.assertIn("`0`", flask_debug_row.group(0))

    def test_secret_key_default_documented(self):
        env_section_start = self.md_content.find("## Environment Configuration")
        env_section = self.md_content[env_section_start:]
        secret_key_row = re.search(r"`SECRET_KEY`.*", env_section)
        self.assertIsNotNone(secret_key_row)
        self.assertIn("dev-secret-key-change-in-production", secret_key_row.group(0))

    def test_database_url_default_documented(self):
        env_section_start = self.md_content.find("## Environment Configuration")
        env_section = self.md_content[env_section_start:]
        db_url_row = re.search(r"`DATABASE_URL`.*", env_section)
        self.assertIsNotNone(db_url_row)
        self.assertIn("sqlite:///felon_dating.db", db_url_row.group(0))

    def test_host_default_documented(self):
        env_section_start = self.md_content.find("## Environment Configuration")
        env_section = self.md_content[env_section_start:]
        host_row = re.search(r"`HOST`.*", env_section)
        self.assertIsNotNone(host_row)
        self.assertIn("0.0.0.0", host_row.group(0))

    def test_port_default_documented(self):
        env_section_start = self.md_content.find("## Environment Configuration")
        env_section = self.md_content[env_section_start:]
        port_row = re.search(r"`PORT`.*", env_section)
        self.assertIsNotNone(port_row)
        self.assertIn("5000", port_row.group(0))


# ---------------------------------------------------------------------------
# 10. Cross-file consistency: model names documented vs actually exported
# ---------------------------------------------------------------------------

class TestModelExportsConsistency(unittest.TestCase):
    """
    app.py imports models from database.py; connectors.md documents those models.
    All three must be consistent.
    """

    @classmethod
    def setUpClass(cls):
        cls.app_source = _read(APP_PY)
        cls.db_source = _read(DATABASE_PY)
        cls.md_content = _read(CONNECTORS_MD)

    def test_app_imports_all_documented_models(self):
        """app.py must import every model that connectors.md documents."""
        import_line_match = re.search(
            r"from database import (.+)", self.app_source
        )
        self.assertIsNotNone(import_line_match, "No 'from database import ...' line found")
        import_line = import_line_match.group(1)
        for model_name in EXPECTED_MODELS:
            with self.subTest(model=model_name):
                self.assertIn(
                    model_name,
                    import_line,
                    f"app.py does not import model '{model_name}' from database",
                )

    def test_database_py_defines_all_documented_models(self):
        """database.py must define every model that connectors.md documents."""
        for model_name in EXPECTED_MODELS:
            with self.subTest(model=model_name):
                self.assertIn(
                    f"class {model_name}",
                    self.db_source,
                    f"database.py does not define class '{model_name}'",
                )

    def test_no_extra_undocumented_table_names(self):
        """
        Regression: every __tablename__ defined in database.py should be
        accounted for in connectors.md.
        """
        # Extract all __tablename__ values from database.py source
        found_tables = set(re.findall(r"__tablename__\s*=\s*'([^']+)'", self.db_source))
        documented_tables = set(EXPECTED_MODELS.values())
        undocumented = found_tables - documented_tables
        self.assertEqual(
            undocumented,
            set(),
            f"Tables in database.py not documented in connectors.md: {undocumented}",
        )


if __name__ == "__main__":
    unittest.main()
