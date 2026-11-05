# Gmail draft delivery — setup (FS-42)

When an agent ticks **"Also create a Gmail draft of the welcome email"** on the Register
Applicant form, the platform places the composed email (text **and** HTML, with the
brochure buttons) in the shared sending mailbox as a **draft**. The agent opens Gmail,
reviews, edits and sends it by hand. **The platform never sends.**

Until the steps below are done the app keeps working: `DRAFT_TRANSPORT` defaults to
`fake`, which records the draft in memory only (the page says "Test mode … no Gmail
draft exists").

> **Secrets rule.** The client secret and refresh token are passwords for a mailbox.
> They go into Render's Environment tab and nowhere else — not chat, tickets, commits,
> screenshots or this repo. `.env` stays git-ignored.

## What you need first

1. **A FutureSynch mailbox for test drafts** (decision pending — e.g. a dedicated
   address, not a personal one). Drafts land here.
2. **Someone who can create a Google Cloud project inside the FutureSynch Google
   Workspace organisation** (a Workspace admin, or a user the admin has allowed). The
   project must belong to the organisation, or Google will not offer the **Internal**
   audience used below.
3. A computer with Python 3.11+ for the one-off token step.

## Part A — Google Cloud (once, about 10 minutes)

Menu names below are Google's current "Google Auth Platform" layout; Google renames
things now and then, so if a label differs, look for the one that means the same.

1. Open <https://console.cloud.google.com> signed in with the FutureSynch Workspace
   account. In the project picker choose **New project**. Name: `MyTeamAI Dev`.
   **Organisation: the FutureSynch organisation.** Create.
2. **APIs & Services → Library →** search **Gmail API → Enable**.
3. **Google Auth Platform** (or **APIs & Services → OAuth consent screen**) **→ Get
   started / Configure**:
   - **App name:** `MyTeamAI`, **User support email:** yours.
   - **Audience / User type: Internal.** *(This is what makes the sign-in last. An
     External app left in "Testing" has its refresh tokens expire after 7 days — see
     Google's note on Trusted apps and the Testing limit.)*
   - **Contact email:** yours. Agree and create.
4. **Data Access → Add or remove scopes →** add exactly
   `https://www.googleapis.com/auth/gmail.compose` → Update → Save.
   *Do not add any Drive scope or any other Gmail scope.*
5. **Clients** (or **APIs & Services → Credentials**) **→ Create client / Create
   credentials → OAuth client ID.** **Application type: Desktop app.** Name:
   `MyTeamAI dev desktop`. Create, then **Download JSON**. Keep that file private.

If **Internal** is not offered, the project is not inside the organisation. Stop and
create it under the organisation; do not fall back to External.

## Part B — get the refresh token (your computer, about 2 minutes)

```bash
pip install google-auth-oauthlib google-api-python-client
python scripts/gmail_get_refresh_token.py --client-secrets ~/Downloads/client_secret_XXXX.json
```

A browser opens. **Sign in as the test mailbox** (not as yourself) and click **Allow**.
The terminal then prints the mailbox address and the refresh token. Nothing is saved to
disk. Clear the terminal afterwards.

## Part C — Render environment (Environment tab)

Add these (names are exact; values come from Part A's JSON and Part B's output):

| Key | Value |
|---|---|
| `DRAFT_TRANSPORT` | `gmail` |
| `GMAIL_CREDENTIAL_MODE` | `futuresynch_dev` |
| `GMAIL_DEV_CLIENT_ID` | `client_id` from the downloaded JSON |
| `GMAIL_DEV_CLIENT_SECRET` | `client_secret` from the downloaded JSON |
| `GMAIL_DEV_REFRESH_TOKEN` | printed by the script |
| `GMAIL_DEV_MAILBOX` | the mailbox address the script printed |

Saving environment variables **redeploys the service**. Check the service is tracking a
branch that contains FS-42 *before* you save, or it will rebuild an old commit.

No `GMAIL_PROD_*` values are set or read while the mode is `futuresynch_dev`.

## Part D — check it

1. Sign in, open **Register Applicant**, fill a new applicant (new email each time),
   tick **Also create a Gmail draft…**, register.
2. Expect: the green *"Gmail draft created in the shared mailbox (…)"* message.
3. Open Gmail as the test mailbox → **Drafts**. The draft is addressed to the applicant
   and shows the *View brochure* button for any matched listing that has a public
   brochure in HubSpot.

Optional, on your own computer only (exports the same variables first, ideally with
`read -s` so secrets stay out of shell history):
`python -m app.services.transports.gmail` creates one draft addressed to the mailbox
itself and prints `OK` or `FAILED: <reason>`.

## When it does not work

| What the page / probe says | Meaning | Fix |
|---|---|---|
| `GMAIL_CREDENTIAL_MODE is not set` / `Missing required setting(s): GMAIL_DEV_…` | A variable is missing or blank. The message names it, never its value. | Add it in Render. |
| `Mailbox guard: the connected Google account is not the mailbox expected…` | The token belongs to a different account than `GMAIL_DEV_MAILBOX`. No draft was created. | Re-run Part B signed in as the right mailbox and update the token and mailbox together. |
| `Gmail reconnect required` | Google reports the sign-in revoked, expired or blocked (`invalid_grant`, `admin_policy_enforced`). Retrying will not help; the composed email is kept on the page. | Repeat Part B and update `GMAIL_DEV_REFRESH_TOKEN`. If it was blocked by an administrator, check Admin console → Security → Access and data control → API controls. |
| `Gmail API error (HTTP 4xx/5xx)` | A Gmail-side error. Not sticky; the next attempt tries again. | Check the Gmail API is enabled (Part A step 2). |
| Browser says *Access blocked* / `org_internal` during Part B | You signed in with an account outside the organisation. | Sign in as the Workspace mailbox. |
| Page says *Test mode … "fake" transport* | `DRAFT_TRANSPORT` is not `gmail` on the running deploy. | Part C. |

## Production later (M5)

Production uses the same code with a different mode: `GMAIL_CREDENTIAL_MODE=curtis_sloane_prod`
and the `GMAIL_PROD_*` variables, set only in the production service. Do not create or use
production credentials before M5. Nothing else changes.

## What the code guarantees

- Draft only: it calls `drafts.create`, never `messages.send`. (`gmail.compose` can
  technically send, so this is enforced in code and tested.)
- Before the first draft it checks the connected account equals `GMAIL_*_MAILBOX`.
- A revoked sign-in is an explicit *reconnect required* state; nothing is lost.
- A delivery failure never undoes the HubSpot registration or the composed text.
- The test suite is forced onto the in-memory transport, so running tests can never
  create a real draft.
