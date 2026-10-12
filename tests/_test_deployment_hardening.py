"""Public-deployment password guard and credential file permissions."""
import argparse
import os
import stat
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import wb_accounts
import wb_proxy
import wb_settings


class DeploymentPasswordTests(unittest.TestCase):
    def args(self, password=None):
        return argparse.Namespace(panel_password=password)

    def validate(self, directory, password=None):
        with mock.patch.object(wb_proxy, "ACCOUNTS_DIR", directory), \
             mock.patch.dict(os.environ, {"WB_REQUIRE_PANEL_PASSWORD": "1"}, clear=False):
            return wb_proxy._validate_deployment_panel_password(self.args(password))

    def test_fresh_public_deployment_requires_password(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SystemExit) as caught:
                self.validate(directory)
            self.assertIn("PANEL_PASSWORD is required", str(caught.exception))

    def test_default_and_short_passwords_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for password in ("admin", "too-short"):
                with self.subTest(password=password), self.assertRaises(SystemExit):
                    self.validate(directory, password)

    def test_strong_environment_password_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            self.validate(directory, "correct-horse-battery-staple")

    def test_persisted_strong_password_allows_secretless_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            wb_settings.set_panel_password(directory, "already-persisted-strong")
            self.validate(directory)

    def test_guard_is_opt_in_for_local_backwards_compatibility(self):
        with tempfile.TemporaryDirectory() as directory, \
             mock.patch.object(wb_proxy, "ACCOUNTS_DIR", directory), \
             mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("WB_REQUIRE_PANEL_PASSWORD", None)
            wb_proxy._validate_deployment_panel_password(self.args())


@unittest.skipIf(os.name == "nt", "POSIX mode bits are not enforced on Windows")
class CredentialPermissionTests(unittest.TestCase):
    def mode(self, path):
        return stat.S_IMODE(os.stat(path).st_mode)

    def test_settings_and_account_credentials_are_private(self):
        with tempfile.TemporaryDirectory() as parent:
            directory = os.path.join(parent, "accounts")
            old_umask = os.umask(0)
            try:
                wb_settings.save(directory, {"api_key": "secret"})
                account = wb_accounts.Account({
                    "uid": "permission-test",
                    "realm": "intl",
                    "domain": "www.workbuddy.ai",
                    "accessToken": "token",
                })
                account_path = account.save(directory)
            finally:
                os.umask(old_umask)
            self.assertEqual(self.mode(directory), 0o700)
            self.assertEqual(self.mode(wb_settings.settings_path(directory)), 0o600)
            self.assertEqual(self.mode(account_path), 0o600)

    def test_upgrade_hardens_existing_json_files(self):
        with tempfile.TemporaryDirectory() as parent:
            directory = os.path.join(parent, "accounts")
            os.mkdir(directory, 0o777)
            path = os.path.join(directory, "legacy.json")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("{}")
            os.chmod(directory, 0o777)
            os.chmod(path, 0o666)
            wb_settings.harden_accounts_storage(directory)
            self.assertEqual(self.mode(directory), 0o700)
            self.assertEqual(self.mode(path), 0o600)


if __name__ == "__main__":
    unittest.main()
