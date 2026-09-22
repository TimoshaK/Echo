# Phase 7: Security Hardening - Technical Research

**Researched:** 2026-09-22
**Phase requirement IDs:** SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, SEC-06
**Baseline verified against:** working tree at `9f22b5d` (Python 3.14.3, Windows / `os.name == "nt"`)

## Summary

The audit findings in ROADMAP Phase 7 map onto exactly **six code sites in five files**. All six
are reproduced below against the live tree, with the current behaviour quoted rather than
paraphrased. The two findings that are outright credential-leak bugs are:

1. **`urllib.request.HTTPRedirectHandler.redirect_request` copies the `Authorization` header to
   the redirect target, including a different host** (SEC-03). Verified by reading the CPython
   stdlib source on this machine (quoted in §4).
2. **`load_config()` swallows `json.JSONDecodeError` and returns defaults with an empty API key**,
   so a corrupted `app_config.json` silently disables summarization with no user-visible signal
   (SEC-04).

Everything else is hardening of an existing mechanism: file permissions + write atomicity
(SEC-01), `base_url` scheme validation (SEC-02), error-text redaction (SEC-05), and dependency
pinning (SEC-06).

Two constraints shaped the design and must not be lost during planning:

- **The operator's live `app_config.json` is already `https`** (`https://api.dslab.tech/v1`,
  `summary_preset: "daily"`, `enabled: true`). Validation must accept it unchanged. A validator
  that only accepts `openrouter.ai` would break the working app.
- **Phase 6 decision T-260921-04 keeps `echo/llm_client.py` free of `import re`.** The new
  redaction helper therefore lives in `echo/errors.py`, and `llm_client.py` stays regex-free.

## 1. Verified baseline (what the code does today)

### SEC-01 — config at rest (`echo/config.py`, 41 lines)

```python
def save_config(cfg: dict) -> None:
    normalized = json.loads(json.dumps(DEFAULT_CONFIG))
    normalized["llm"].update(cfg.get("llm", {}))
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)
```

Three defects, all reproducible:

| Defect | Evidence |
|--------|----------|
| Not atomic | `open(..., "w")` truncates the live file, then `json.dump` streams into it. A crash or a full disk between the two leaves a truncated / partial JSON file. |
| No permissions applied | No `os.chmod` / `os.open` anywhere; the file inherits the process umask (typically `0644`) and on Windows inherits the parent directory ACL. |
| No durability | No `flush()` + `os.fsync()` before close. |

### SEC-02 — `base_url` is never validated

`echo/summarization_engine.py:43-52` stores whatever the dialog produced:

```python
"base_url": base_url.strip().rstrip("/"),
```

`echo/ui/settings_dialog.py:55-64` renders a free-text `tk.Entry` with no validation; `save_settings()`
(line 99) calls `update_config(...)` unconditionally. `echo/llm_client.py:25` then formats
`f"{llm['base_url']}/chat/completions"` and attaches `Authorization: Bearer <api_key>`.

So `http://`, `ftp://`, `file://`, and `https://user:pass@host` all reach the wire. `http://`
sends the bearer token in cleartext; `file://` is rejected by urllib but only after the request
object is built; userinfo in the URL is echoed back in error text.

### SEC-03 — redirect credential leak (confirmed in stdlib source)

`echo/llm_client.py:37` calls `urllib.request.urlopen(req, timeout=60)`, which installs the default
`HTTPRedirectHandler`. Read from this machine's stdlib:

```python
# urllib/request.py — HTTPRedirectHandler.redirect_request
CONTENT_HEADERS = ("content-length", "content-type")
newheaders = {k: v for k, v in req.headers.items()
              if k.lower() not in CONTENT_HEADERS}
return Request(newurl,
               method="HEAD" if m == "HEAD" else "GET",
               headers=newheaders,
               origin_req_host=req.origin_req_host,
               unverifiable=True)
```

Only `content-length` and `content-type` are dropped. **`Authorization` is forwarded to `newurl`
whatever host it names.** The default handler accepts 301/302/303/307/308 for GET/HEAD and
301/302/303 for POST (a POST is downgraded to GET, but the headers survive). This is the leak.

### SEC-04 — silent fallback on corrupt config

```python
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    return json.loads(json.dumps(DEFAULT_CONFIG))
```

Failure modes that are currently silent: truncated JSON, a JSON array or string at the root
(`cfg.setdefault` would then raise `AttributeError` — an unhandled crash, not a fallback),
`"llm"` present but not an object (`cfg["llm"].setdefault` raises `AttributeError` — also a crash),
and a `UnicodeDecodeError` from a corrupted byte sequence (uncaught today).

A second, subtler defect: `cfg.setdefault("llm", DEFAULT_CONFIG["llm"])` inserts the
**same dict object** as `DEFAULT_CONFIG["llm"]`, so `cfg["llm"]` and `DEFAULT_CONFIG["llm"]`
can alias. The current code happens to be harmless (every key already exists), but a mutation
through one would be visible from the other. The rewrite must deep-copy.

### SEC-05 — API error text is shown raw

```python
except urllib.error.HTTPError as e:
    detail = e.read().decode("utf-8", errors="replace")[:500]
    raise SummaryApiError(f"Ошибка API ({e.code}): {detail}", code=e.code)
except urllib.error.URLError as e:
    raise SummaryApiError(f"Сетевая ошибка: {e.reason}", code=0)
```

That string travels `_run_summary` → `progress_queue["error"]` → `_handle_summary_error` →
`messagebox.showerror("Ошибка конспекта", f"Не удалось сгенерировать конспект.\n\n{error}")`
(`echo/ui/app.py:244-258`). Nothing redacts, nothing bounds the length beyond the 500-char
body slice, and control characters / newlines from the body land verbatim in the dialog.

If a misconfigured or hostile endpoint echoes the request (a debug endpoint, a proxy, an
OpenAI-compatible shim), the **API key comes back in the error body and is displayed**. That is
the concrete leak this requirement closes.

### SEC-06 — unpinned dependencies, one unused

`requirements.txt` (5 lines, every one with `>=`):

```
openai-whisper>=20250625
torch>=2.14.0
numpy>=2.5.0
tqdm>=4.70.0
srt>=3.5.3
```

Verified installed versions on this machine (the versions the app actually runs on):

| Package | Installed | Note |
|---------|-----------|------|
| openai-whisper | `20250625` | matches the declared floor |
| torch | `2.14.0+cu130` | the `+cu130` local tag comes from the PyTorch CUDA index, not PyPI |
| numpy | `2.4.4` | **the declared floor `>=2.5.0` is already wrong** — 2.4.4 is what is installed and working |
| tqdm | `4.70.0` | matches |
| srt | `3.5.3` | **unused** |

`srt` is imported nowhere: `grep -i "import srt\|srt\."` over `echo/*.py`, `echo/ui/*.py`
and `main.py` returns nothing. The only `srt` identifier in the project is the **local module
`echo/srt.py`**, which is `echo.srt`, not top-level `srt`, and formats subtitles by hand.
The installed `srt` package resolves to `A:\python\Lib\site-packages\srt.py` and is dead weight.

**Doc coupling (easy to miss):** `README.md` (~line 197 and ~line 204) and `SETUP_GUIDE.txt`
(~line 282-284) both *document* that `srt` is declared-but-unused. Removing the dependency
without updating those two files leaves the docs describing a state that no longer exists.

## 2. Environment facts verified on this machine

| Probe | Result | Consequence for the plan |
|-------|--------|--------------------------|
| `os.name` | `nt` | POSIX mode bits are not enforced here |
| `hasattr(os, "fchmod")` | `True` | `os.fchmod` exists but only accepts the Windows-supported bits |
| `os.chmod(p, 0o600)` then `stat` | `st_mode & 0o777 == 0o666` | **`0600` is silently a no-op on Windows** — the requirement cannot be met by `chmod` alone on the operator's platform |
| `shutil.which("icacls")` | `C:\WINDOWS\system32\icacls.EXE` | ACL restriction is achievable via `icacls /inheritance:r /grant:r <user>:F` |
| `tempfile.mkstemp` + `os.replace` | available | atomic same-directory replace is portable |
| `import pytest` | `ModuleNotFoundError` | **no test framework installed**; see §6 |
| `import srt` | resolves to site-packages | confirms the dead dependency is really installable but untouched |
| Python | 3.14.3 | `dict \| None` unions, `str.partition`, `Path.read_text` all available |

**Cross-platform conclusion for SEC-01:** the honest implementation is
`os.chmod(tmp, 0o600)` (real on POSIX, no-op on Windows) **plus** a best-effort Windows ACL step
via `icacls`. The Windows step must be non-fatal (tolerate a missing `icacls`, a non-NTFS
volume, or a locked-down policy) and must not flash a console window from a GUI process
(`subprocess.CREATE_NO_WINDOW`).

## 3. Architecture Patterns

### Pattern 1: Write-temp-fsync-rename for a secret file

```python
fd, tmp = tempfile.mkstemp(dir=CONFIG_PATH.parent, prefix=".app_config.", suffix=".tmp")
try:
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(tmp, 0o600)          # real on POSIX, tolerated no-op on Windows
    os.replace(tmp, CONFIG_PATH)  # atomic on the same volume
finally:
    if os.path.exists(tmp):
        os.unlink(tmp)
```

Key properties: the destination is replaced by a **rename**, so it never exists in a partially
written state; the temp file is created in the **same directory** (a cross-volume `os.replace`
is not atomic); `mkstemp` already creates the temp file `0600` on POSIX, so the window in which
the data sits in a world-readable file does not exist.

### Pattern 2: Subclass the redirect handler instead of disabling it

```python
class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is not None and _is_cross_origin(req.full_url, newurl):
            new_req.headers.pop("Authorization", None)
        return new_req
```

`urlopen` uses the global opener; a dedicated `urllib.request.build_opener(...)` used **only** in
`echo/llm_client.py` avoids mutating process-global state (important: mutating the global opener
would be a side effect on any other library sharing the process). Compare `netloc` **including
port** (lowercased) — a redirect from `host:443` to `maintenance.host` is cross-origin even
though the hostname suffix matches.

### Pattern 3: Redact, then bound, then flatten

Sanitization order matters: redact secrets **before** truncating (otherwise a truncated token
leaks its prefix), then collapse control characters/whitespace, then truncate. Truncating the raw
input *first* (a hard cap of a few KB) is what makes the regex step DoS-safe.

### Anti-patterns to avoid

- **`chmod`-only on Windows.** It silently does nothing here (verified: `0o666` after `chmod 0o600`).
- **Disabling redirects entirely.** A 307 from a load balancer would then surface as an opaque
  failure. Stripping the credential is the required behaviour, not refusing to follow.
- **Sanitizing only at the display site.** The queue payload is also observable by tests and by
  future consumers; sanitize at the request layer *and* at the display layer.
- **Blocking private/loopback hosts.** SEC-02 mandates https-only, not egress restriction. The
  whole point of the pluggable provider is a self-hosted endpoint; a private-IP block would be a
  functional regression. Recorded as accepted residual risk instead.
- **`re` in `echo/llm_client.py`.** Violates the Phase 6 T-260921-04 decision.

## 4. Don't Hand-Roll

| Need | Use | Why not hand-rolled |
|------|-----|---------------------|
| Atomic replace | `os.replace` | POSIX `rename(2)` / Windows `MoveFileEx(MOVEFILE_REPLACE_EXISTING)`; the stdlib version is the portable form |
| Temp file in the target dir | `tempfile.mkstemp(dir=...)` | unique name + `0600` + no race, versus a hand-built `.tmp` suffix that collides |
| URL parsing | `urllib.parse.urlsplit` | handles userinfo, IPv6 literals, default ports; a `.startswith("https://")` check accepts `https://` and `https://evil` with empty host |
| Redirect interception | subclass `HTTPRedirectHandler` | reimplementing redirect-following means reimplementing 301/303/307/308 method semantics |
| Secret redaction patterns | `re` in `echo/errors.py` | string slicing cannot express `Bearer <token>` |
| Test framework | stdlib `unittest` | `pytest` is not installed and adding an unpinned dev dependency in a *pinning* phase is self-contradictory |

## 5. Common Pitfalls

### Pitfall 1: Truncating before redacting

`detail[:500]` then redacting produces `sk-live_AbC…` — a partial key is still a key prefix leak,
and it is also what makes the current code's 500-char slice insufficient. Redact first; bound last.

### Pitfall 2: Comparing the wrong thing on redirect

`newurl.startswith(req.full_url.split("/api")[0])` style checks break on port changes and
scheme downgrades. Use `urlsplit(...).netloc.lower()` (host **and** port) plus a scheme check;
strip the header if either differs, or if the scheme is no longer `https`.

### Pitfall 3: `os.chmod` raising on odd platforms

On some volumes/filesystems `chmod` raises `OSError`. The permission step must be wrapped so a
failure cannot lose a just-saved API key. Same for `icacls`: any non-zero exit is tolerated.

### Pitfall 4: Testing against the operator's live config

`app_config.json` holds a real key and is gitignored. Every test must point
`echo.config.CONFIG_PATH` at a `tempfile.TemporaryDirectory()` (monkeypatch the module attribute)
or call the writer with an explicit path. A test that saves through the real `CONFIG_PATH`
would overwrite the operator's working configuration.

### Pitfall 5: `ConfigCorruptError` escaping into the GUI thread

`SummarizationEngine.__init__` runs on the Tk main thread during `TranscriberApp.__init__`. If it
lets the exception propagate, the app dies at startup. It must be caught in `__init__`, stored as
`self.config_error`, and surfaced by the UI as a `messagebox` — with defaults in place so
transcription still works.

### Pitfall 6: `is_layer_failure` swallowing the new validation error

`is_layer_failure` returns `True` for `code is None`. If `post_chat` raised a *subclass of*
`SummaryApiError` for a bad `base_url`, the ladder would retry three times and then show a
generic message. The validation error must be a **separate** exception type so it propagates
immediately.

### Pitfall 7: `import re` creeping into `llm_client.py`

Verified Phase 6 decision: `parse_json_content` is linear-only and `import re` is asserted absent
from `echo/llm_client.py`. Keep the redaction regex in `echo/errors.py`.

## 6. Validation Architecture

### Framework decision (reverses the Phase 6 no-`tests/` call, deliberately)

Phase 6 chose a transient `%TEMP%` smoke harness (D-05) because a `tests/` package was declared
out of scope for a *behaviour-preserving* refactor. Phase 7 is the opposite situation: it
introduces **security invariants** (atomicity, permission bits, redirect header stripping, key
redaction) that are (a) pure functions with crisp I/O, (b) impossible to eyeball, and (c) exactly
the kind of thing that silently regresses. Nyquist validation also requires an automated command
per task. So Phase 7 introduces a durable `tests/` package.

- **Framework:** stdlib `unittest` — zero new dependencies, which matters in a phase whose last
  requirement is "pin the dependencies".
- **Discovery:** `py -3 -m unittest discover -s tests -v` from the repo root (`python -m` puts the
  repo root on `sys.path`, so `import echo.config` resolves; the `tests/` directory needs **no**
  `__init__.py`, which keeps file ownership disjoint across parallel plans).
- **Config file:** none — no `pytest.ini`/`conftest.py`. Tests are plain modules named
  `tests/test_<subject>.py`.
- **Estimated runtime:** a few seconds. No `torch`/`whisper` import is allowed in the test suite
  (that is a ~20 s import); tests target `echo.config`, `echo.errors`, `echo.llm_client` and
  `echo.summarization_engine` only, none of which import `whisper`.
- **GUI:** `echo/ui/*` has exactly one testable seam — that `validate_base_url` is *called* before
  `update_config`. Assert it by importing `echo.ui.settings_dialog`, monkeypatching
  `messagebox.showerror`, and driving `save_settings` through a stub app. Full widget construction
  is covered by the human checkpoint, not by tests.

### Verification dimensions

| # | Dimension | Coverage in this phase |
|---|-----------|------------------------|
| 1 | Happy path | `validate_base_url` accepts the operator's live `https://api.dslab.tech/v1`; `load_config` reads the real shape; `save_config` round-trips |
| 2 | Boundary | trailing slash, `http://`, `ftp://`, empty string, whitespace-only, `https://` with no host, `https://user:pass@host`, port variants |
| 3 | Error handling | corrupt JSON, JSON array root, `"llm"` as a list, unreadable file (`OSError`), `os.replace` failure mid-save |
| 4 | Idempotency | two consecutive `save_config` calls leave one file and no `.tmp` residue in the directory |
| 5 | Integration | `settings_dialog.save_settings` refuses and does not call `update_config`; `SummarizationEngine` stores `config_error` instead of raising |
| 6 | Security assertions | no `Authorization` header on a cross-origin redirect target (positive case: preserved on same-origin); `[REDACTED]` replaces the key, `Bearer …`, `sk-…`, URL userinfo; `import re` absent from `echo/llm_client.py` |
| 7 | Performance / DoS | a 100 000-character error body is truncated and sanitized without measurable delay |
| 8 | Validation requirements | every task in Phase 7 carries an `<automated>` command (or an explicit Wave 0 dependency); see `07-VALIDATION.md` |

### Wave 0 assessment

`tests/` does not exist → **Wave 0 work is genuinely required** and is carried by plan `07-01`
Task 1 (it creates the first test module) and plan `07-02` Task 1 (first config test module).
No framework install is needed because the framework is `unittest`.

| MISSING reference | Owner | Resolution |
|-------------------|-------|------------|
| `tests/` directory + first test module | 07-01 | created inline by the TDD task, no separate Wave 0 plan |
| config test module | 07-02 | created inline by the TDD task |
| engine/config-error + dialog validation test modules | 07-03 | created inline by the TDD tasks |

The Nyquist rule "no task may reference a test file that does not exist" is satisfied because each
test file is created by the same task whose `<verify>` runs it.

### Manual-only verification

| Behavior | Requirement | Why manual | How |
|----------|-------------|------------|-----|
| A corrupted `app_config.json` shows an explicit message at application start | SEC-04 | Requires launching the real Tk window; `messagebox` needs a display | 07-04 checkpoint: corrupt the file, start the app, observe the dialog, restore from backup |
| The settings dialog visibly refuses a non-`https` URL and the stored config is unchanged | SEC-02 | Requires the real dialog widget and a real click | 07-04 checkpoint: type `http://example.com/v1`, click SAVE, observe the error, confirm `app_config.json` is byte-identical |
| Real API error text contains no credential | SEC-05 | Needs a live provider round-trip to be worth anything | 07-04 checkpoint: temporarily point the key at `https://openrouter.ai/api/v1` with a bogus key, click GENERATE SUMMARY, read the dialog |
| File permissions are owner-only on the operator's actual filesystem | SEC-01 | Platform-dependent ACL semantics; cannot be asserted portably | 07-04 checkpoint: `icacls app_config.json` on Windows (or `ls -l` on POSIX) |

## Sources

### Primary (HIGH confidence)

- CPython 3.14.3 stdlib, read on this machine: `urllib/request.py` → `HTTPRedirectHandler.redirect_request` (the header-copy bug), `os.chmod` behaviour on `nt`, `tempfile.mkstemp`, `os.replace`.
- Live project source (read in full): `echo/config.py`, `echo/llm_client.py`, `echo/summarization_engine.py`, `echo/errors.py`, `echo/ui/app.py`, `echo/ui/settings_dialog.py`, `requirements.txt`.
- Live probes on this machine: `os.name`, `hasattr(os, "fchmod")`, `os.chmod(0o600)` → `0o666`, `shutil.which("icacls")`, `import pytest` → `ModuleNotFoundError`, `pip freeze` for the pinned versions.
- `.planning/REQUIREMENTS.md` §Безопасность (SEC-01…SEC-06) and `.planning/ROADMAP.md` Phase 7 success criteria.

### Secondary (MEDIUM confidence)

- OWASP ASVS L1 (the configured `security_asvs_level`): V2.10 (secrets not stored in cleartext where avoidable / access-restricted), V5.1 (input validation), V12.1/V12.2 (file upload/at-rest handling). The per-plan threat registers map to these.
- Microsoft `icacls` documentation for `/inheritance:r` and `/grant:r <user>:F` semantics.

### Tertiary (LOW confidence — needs validation)

- Exact upstream `numpy` upper bound compatible with the installed `torch==2.14.0+cu130`; the plan pins to the **verified installed** `2.4.4` rather than guessing at `2.5.x`.

## Metadata

- **Confidence:** HIGH for the six findings and the environment facts (all verified in-place).
- **Open question (non-blocking):** whether the operator wants the Windows ACL step at all, given
  it is best-effort and adds a subprocess call per save. The plan implements it as non-fatal and
  cached; if the operator objects, dropping the `icacls` call does not affect any other requirement.
- **Open question (non-blocking):** whether `torchvision` (installed, unused by this project)
  should also be pinned. It is not in `requirements.txt`, so it is out of scope for SEC-06.

## Validation Architecture

> Nyquist gate: see §6 above for the full strategy; `07-VALIDATION.md` is the per-task contract.

- **Framework:** stdlib `unittest`, no new dependency, discovery via `py -3 -m unittest discover -s tests -v`.
- **Wave 0:** required (`tests/` does not exist) and satisfied inline by the first TDD task of each
  of plans 07-01, 07-02 and 07-03 — no separate Wave 0 plan.
- **Automated commands:** every task in the phase carries an `<automated>` command.
- **Security dimension:** each task's `<verify>` also asserts its threat-register mitigation
  (header stripped, `[REDACTED]` present, `0600` attempted, `import re` absent from `llm_client.py`).
- **Manual-only:** the four GUI/permission behaviours listed in §6, all covered by the single
  human-verify checkpoint in plan 07-04.
