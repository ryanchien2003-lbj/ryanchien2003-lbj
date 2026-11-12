from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import MagicMock, patch

import job_apply

ROOT = Path(__file__).resolve().parent


class JobToolkitTests(TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        state = patch.object(job_apply, "STATE", root / "state")
        state.start()
        self.addCleanup(state.stop)
        self.profile = ROOT / "profile.example.json"
        self.job = ROOT / "job.example.json"
        self.letter = root / "letter.txt"
        self.letter.write_text(job_apply.letter(job_apply.load(self.profile),
                                               job_apply.load(self.job)), encoding="utf-8")
        browser_api = patch("playwright.sync_api.sync_playwright")
        launch = browser_api.start()
        self.addCleanup(browser_api.stop)
        browser = launch.return_value.__enter__.return_value.chromium.launch.return_value
        page = browser.new_page.return_value
        page.url = job_apply.load(self.job)["url"]
        form = MagicMock()
        form.count.return_value = 1
        form.evaluate.return_value = True
        self.confirmation = MagicMock()
        self.confirmation.is_visible.return_value = False
        page.locator.side_effect = {"#application": form,
                                   "#application-received": self.confirmation}.__getitem__
        self.fields = {s: MagicMock() for s in ["#name", "#email", "#resume", "#letter",
                                                 "#availability", "button[type=submit]"]}
        for field in self.fields.values():
            field.count.return_value = 1
        form.locator.side_effect = self.fields.__getitem__

    def run_form(self, answer, fill_only=False):
        with patch("builtins.input", return_value=answer):
            job_apply.apply(self.profile, self.job, self.letter, fill_only)

    def statuses(self):
        with closing(job_apply.open_log()) as db:
            return db.execute("SELECT status FROM applications").fetchall()

    def test_draft_and_fill_only(self):
        self.run_form("", fill_only=True)
        body = self.letter.read_text(encoding="utf-8")
        self.assertIn("I used SQL", body)
        self.fields["#letter"].fill.assert_called_once_with(body.strip())
        self.fields["#resume"].set_input_files.assert_called_once_with(str(ROOT / "resume.txt"))
        self.fields["#availability"].select_option.assert_called_once_with(label="Summer")
        self.fields["button[type=submit]"].click.assert_not_called()
        self.assertEqual([], self.statuses())

    def test_cancel_then_submit_and_block_duplicate(self):
        button = self.fields["button[type=submit]"]
        self.run_form("CANCEL")
        button.click.assert_not_called()
        self.run_form("SUBMIT")
        self.assertEqual([("submitted",)], self.statuses())
        with self.assertRaisesRegex(ValueError, "already"):
            self.run_form("SUBMIT")
        button.click.assert_called_once()

    def test_uncertain_confirmation_blocks_retry(self):
        self.confirmation.wait_for.side_effect = TimeoutError
        with self.assertRaisesRegex(ValueError, "outcome is unknown"):
            self.run_form("SUBMIT")
        self.assertEqual([("pending",)], self.statuses())
        with self.assertRaisesRegex(ValueError, "already"):
            self.run_form("SUBMIT")
        self.fields["button[type=submit]"].click.assert_called_once()


if __name__ == "__main__":
    main()
