# Job Application Toolkit

Draft a cover letter from your verified experience, fill a job application in Chromium, and submit it after you review the form. The toolkit works locally with Python and Playwright and needs no AI API key.

## Try it on a practice form

From this directory, install Python 3.10 or newer and run:

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python job_apply.py draft profile.example.json job.example.json private/letter.txt
python demo_server.py
```

If Chrome or Edge is already installed, you can skip the Chromium download and pass `--browser-channel chrome` or `--browser-channel msedge` to the apply command.

Leave the practice server running and open a second terminal in the same directory.

```bash
python job_apply.py apply profile.example.json job.example.json private/letter.txt --fill-only
python job_apply.py apply profile.example.json job.example.json private/letter.txt
python job_apply.py status
```

The second command opens the form and fills it. Review it in Chromium, then type `SUBMIT` in the terminal to click the configured button. The local practice server discards the submission. The confirmation page and `status` show the result. Run the draft command with a fresh output filename when generating another draft.

## Set up a real application

1. Copy the example JSON files into `private/` and place your résumé in that directory. Use a different `job_id` for each job and use the same ID if you return to it.
2. Add your actual experience to `evidence`. Each entry has a complete sentence and keywords. Paste the job description into `description` and write one sentence about why you want the role in `motivation`. The draft ranks evidence by keyword overlap and uses up to two relevant statements.
3. Set `url` to the employer’s direct HTTPS application form. Configure a CSS selector for the form, submit button, visible confirmation message, and each field to fill. Supported field types are `text`, `select` (option label), `file`, and `checkbox` (JSON boolean). A field can use a profile `source`, the special `cover_letter` source for a text box, or a literal `value`. Attachment paths are relative to the profile file.
4. Generate a draft and review it. Run the `apply` command with the paths to your private profile, job configuration and edited letter. Use `--fill-only` to try the mapping before submitting.

The current adapter supports forms in the main browser document with a single submit step and an on-site confirmation marker. Handle login, CAPTCHAs, multi-step portals and required answers outside the mapping in the browser. The tool uses values you supply for application questions.

## Submission status

The local SQLite log records `pending` before the click and `submitted` after the confirmation appears. A job with a pending or submitted record is blocked from automatic retry. If the outcome is uncertain, check the employer portal before taking further action. Personal inputs, generated drafts and the local log belong in `private/`, which Git ignores.

Run the regression checks with `python -m unittest -v`. They cover fill-only mode, cancellation, confirmation, and blocking retries after an uncertain result.
