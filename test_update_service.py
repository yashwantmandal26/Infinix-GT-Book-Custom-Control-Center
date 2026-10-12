import unittest
from unittest.mock import patch

from update_service import GitHubUpdateService


class UpdateServiceTests(unittest.TestCase):
    def test_current_release_does_not_offer_update(self):
        service = GitHubUpdateService("owner/repo", "4.4.0")
        with patch.object(service, "_request_json", return_value={"tag_name": "v4.4.0", "assets": []}):
            self.assertIsNone(service.check())

    def test_new_release_requires_verified_assets(self):
        service = GitHubUpdateService("owner/repo", "4.4.0")
        release = {"tag_name": "v4.4.1", "assets": []}
        with patch.object(service, "_request_json", return_value=release), \
             self.assertRaisesRegex(RuntimeError, "verified installer assets"):
            service.check()

    def test_new_release_returns_verified_update_information(self):
        service = GitHubUpdateService("owner/repo", "4.4.0")
        release = {
            "tag_name": "v4.5.0",
            "html_url": "https://github.com/owner/repo/releases/tag/v4.5.0",
            "body": "New release",
            "assets": [
                {"name": "InfinixGTToolkit.exe", "browser_download_url": "https://example/exe"},
                {"name": "update-manifest.json", "browser_download_url": "https://example/manifest"},
            ],
        }
        with patch.object(service, "_request_json", side_effect=[release, {"sha256": "A" * 64}]):
            update = service.check()
        self.assertEqual(update.version, "4.5.0")
        self.assertEqual(update.executable_url, "https://example/exe")
        self.assertEqual(update.sha256, "A" * 64)


if __name__ == "__main__":
    unittest.main()
