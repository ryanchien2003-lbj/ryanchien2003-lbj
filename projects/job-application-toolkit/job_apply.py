"""Draft a cover letter and submit a reviewed job application."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit

STATE = Path(__file__).resolve().parent / "private"
WORDS = re.compile(r"[a-z][a-z0-9+#]*(?:[.-][a-z0-9+#]+)*")


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def letter(profile, job):
    description = job["description"].lower()
    tokens = set(WORDS.findall(description))

    def score(item):
        return sum(
            keyword.lower() in tokens if " " not in keyword else
            re.search(r"\b" + re.escape(keyword.lower()) + r"\b", description) is not None
            for keyword in set(item["keywords"])
        )

    ranked = sorted(profile["evidence"], key=score, reverse=True)
    matched = [item for item in ranked if score(item)][:2]
    if not matched:
        raise ValueError("No evidence matched the job description. Add relevant, verified experience to the profile.")
    body = "\n\n".join(item["statement"] for item in matched)
    return (
        f"Dear {job['company']} Hiring Team,\n\n"
        f"I am applying for the {job['title']} position at {job['company']}. "
        f"{job['motivation'].strip()}\n\n"
        f"{body}\n\n"
        f"Thank you for considering my application. I would welcome the opportunity to discuss "
        f"how I could contribute to your team.\n\n"
        f"Sincerely,\n{profile['name']}\n"
    )


def origin(url):
    parsed = urlsplit(url)
    local = parsed.hostname in {"localhost", "127.0.0.1"}
    if (not parsed.hostname or parsed.username or parsed.password
            or (parsed.scheme != "https" and not (parsed.scheme == "http" and local))):
        raise ValueError("Use an HTTPS application URL, or HTTP on localhost for the demo.")
    return parsed.scheme, parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)


def open_log():
    STATE.mkdir(exist_ok=True)
    db = sqlite3.connect(STATE / "applications.sqlite")
    db.execute("""CREATE TABLE IF NOT EXISTS applications (
        job_id TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        status TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    return db


def begin_submission(db, job):
    try:
        with db:
            db.execute("INSERT INTO applications(job_id, url, status) VALUES (?, ?, 'pending')",
                       (job["job_id"], job["url"]))
    except sqlite3.IntegrityError as error:
        raise ValueError("This job already has a submission record. Check status before taking further action.") from error


def fill(page, form, profile, job, cover_letter, base):
    for field in job["form"]["fields"]:
        target = form.locator(field["selector"])
        target.wait_for(state="attached")
        if target.count() != 1:
            raise ValueError(f"Expected one field for {field['selector']}.")
        if origin(page.url) != origin(job["url"]):
            raise ValueError("The application navigated away from the configured site.")
        kind = field["type"]
        source = field.get("source")
        if source == "cover_letter":
            value = cover_letter
        elif source:
            value = profile["fields"][source]
        else:
            value = field["value"]
        if kind == "text":
            target.fill(str(value))
        elif kind == "select":
            target.select_option(label=str(value))
        elif kind == "file":
            path = (base / value).resolve(strict=True)
            if not path.is_file():
                raise ValueError("The configured attachment must be a file.")
            target.set_input_files(str(path))
        elif kind == "checkbox" and isinstance(value, bool):
            target.set_checked(value)
        else:
            raise ValueError(f"Unsupported field type or value: {kind}.")


def apply(profile_path, job_path, letter_path, fill_only, channel=None):
    from playwright.sync_api import Error as BrowserError, sync_playwright

    profile, job = load(profile_path), load(job_path)
    config = job["form"]
    expected = origin(job["url"])
    body = letter_path.read_text(encoding="utf-8-sig").strip()
    if not body:
        raise ValueError("Review and save a cover letter before opening an application.")
    with closing(open_log()) as db:
        if db.execute("SELECT 1 FROM applications WHERE job_id=?", (job["job_id"],)).fetchone():
            raise ValueError("This job already has a submission record. Run status to review it.")
        print(f"Opening {job['title']} at {job['company']}\n{job['url']}")
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=False, channel=channel)
            except BrowserError as error:
                raise ValueError("Could not launch the browser. Install Chromium or select an installed browser channel.") from error
            try:
                page = browser.new_page()
                page.set_default_timeout(10000)
                page.goto(job["url"], wait_until="domcontentloaded")
                if origin(page.url) != expected:
                    raise ValueError("The application redirected away from the configured site.")
                form = page.locator(config["selector"])
                form.wait_for(state="visible")
                if form.count() != 1:
                    raise ValueError("Configure a selector for exactly one application form.")
                fill(page, form, profile, job, body, profile_path.parent)
                if fill_only:
                    input("Review the filled form. Press Enter here to close the browser without clicking submit. ")
                    return
                print("Review the filled form in the browser, including all required questions and attachments.")
                if input("Type SUBMIT here to send this application: ").strip() != "SUBMIT":
                    print("Submission cancelled.")
                    return
                if origin(page.url) != expected:
                    raise ValueError("The application navigated away from the configured site.")
                submit = form.locator(config["submit"])
                confirmation = page.locator(config["confirmation"])
                if submit.count() != 1 or not submit.is_enabled() or confirmation.is_visible():
                    raise ValueError("The submit button or confirmation marker could not be validated.")
                if not form.evaluate("(element) => element.checkValidity()"):
                    raise ValueError("Complete all required fields before submitting.")
                begin_submission(db, job)
                try:
                    submit.click()
                    confirmation.wait_for(state="visible", timeout=15000)
                    if origin(page.url) != expected:
                        raise ValueError("Confirmation appeared on a different site.")
                except Exception as error:
                    raise ValueError("Submission outcome is unknown. Check the employer portal before retrying.") from error
                with db:
                    db.execute("UPDATE applications SET status='submitted', updated_at=CURRENT_TIMESTAMP "
                               "WHERE job_id=?", (job["job_id"],))
                print("Submitted and confirmed by the application page.")
            except BrowserError as error:
                raise ValueError("Could not open or fill the configured form. Check the selectors and browser installation.") from error
            finally:
                browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    draft = commands.add_parser("draft", help="Generate a cover letter from verified experience.")
    draft.add_argument("profile", type=Path)
    draft.add_argument("job", type=Path)
    draft.add_argument("output", type=Path)
    submit = commands.add_parser("apply", help="Fill a configured form and submit after review.")
    submit.add_argument("profile", type=Path)
    submit.add_argument("job", type=Path)
    submit.add_argument("letter", type=Path)
    submit.add_argument("--fill-only", action="store_true")
    submit.add_argument("--browser-channel", choices=["chrome", "msedge"])
    commands.add_parser("status", help="Show local submission records.")
    args = parser.parse_args()
    try:
        if args.command == "draft":
            output = letter(load(args.profile), load(args.job))
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as file:
                file.write(output)
            print(f"Draft written to {args.output}. Review it before applying.")
        elif args.command == "apply":
            apply(args.profile, args.job, args.letter, args.fill_only, args.browser_channel)
        else:
            with closing(open_log()) as db:
                for row in db.execute("SELECT job_id, status, updated_at FROM applications ORDER BY updated_at DESC"):
                    print(" | ".join(row))
    except (ValueError, OSError, KeyError, ImportError, sqlite3.Error) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
