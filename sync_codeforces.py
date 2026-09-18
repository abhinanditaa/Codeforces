import json
import os
import re
import time
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

HANDLE = os.environ["CODEFORCES_HANDLE"]

API_URL = (
    "https://codeforces.com/api/user.status?"
    + urllib.parse.urlencode({
        "handle": HANDLE,
        "from": 1,
        "count": 1000
    })
)

SOLUTIONS_DIR = Path("solutions")


def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', '_', name)
    name = name.strip("._")
    return name[:100] or "Problem"


def get_extension(language):
    language = language.lower()

    if "java" in language:
        return ".java"
    if "python" in language:
        return ".py"
    if "gnu c++" in language or "g++" in language or "c++" in language:
        return ".cpp"
    if "gnu c" in language or language == "c":
        return ".c"
    if "kotlin" in language:
        return ".kt"
    if "rust" in language:
        return ".rs"
    if "c#" in language:
        return ".cs"
    if "go" in language:
        return ".go"
    if "javascript" in language:
        return ".js"
    if "typescript" in language:
        return ".ts"

    return ".txt"


def get_language_folder(language):
    language = language.lower()

    if "java" in language:
        return "Java"
    if "python" in language:
        return "Python"
    if "gnu c++" in language or "g++" in language or "c++" in language:
        return "C++"
    if "gnu c" in language or language == "c":
        return "C"
    if "kotlin" in language:
        return "Kotlin"
    if "rust" in language:
        return "Rust"
    if "c#" in language:
        return "CSharp"
    if "go" in language:
        return "Go"
    if "javascript" in language:
        return "JavaScript"
    if "typescript" in language:
        return "TypeScript"

    return "Other"


def fetch_source_code(contest_id, submission_id):
    """
    Fetch source code from the Codeforces submission page.
    """

    url = (
        f"https://codeforces.com/contest/"
        f"{contest_id}/submission/{submission_id}"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 "
                          "(compatible; Codeforces-GitHub-Sync/1.0)"
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            html = response.read().decode("utf-8", errors="replace")

        # Codeforces stores source code inside:
        # <pre id="program-source-text">...</pre>

        match = re.search(
            r'<pre[^>]*id=["\']program-source-text["\'][^>]*>'
            r'(.*?)'
            r'</pre>',
            html,
            re.DOTALL | re.IGNORECASE
        )

        if not match:
            print(
                f"Could not find source code for submission "
                f"{submission_id}"
            )
            return None

        source = match.group(1)

        # Convert HTML entities back to normal source code.
        source = unescape(source)

        return source

    except Exception as e:
        print(
            f"Failed to fetch submission {submission_id}: {e}"
        )
        return None


print(f"Fetching Codeforces submissions for: {HANDLE}")

request = urllib.request.Request(
    API_URL,
    headers={
        "User-Agent": "Codeforces-GitHub-Sync/1.0"
    }
)

with urllib.request.urlopen(request, timeout=30) as response:
    data = json.loads(response.read().decode("utf-8"))

if data.get("status") != "OK":
    raise RuntimeError(
        "Codeforces API error: "
        + data.get("comment", "Unknown error")
    )

submissions = data["result"]

print(f"Fetched {len(submissions)} submissions.")

created = 0
skipped = 0

for submission in submissions:

    # Only sync accepted submissions.
    if submission.get("verdict") != "OK":
        continue

    problem = submission.get("problem", {})

    contest_id = problem.get("contestId")
    index = problem.get("index", "Unknown")

    if not contest_id:
        skipped += 1
        continue

    problem_name = problem.get(
        "name",
        f"Problem_{contest_id}_{index}"
    )

    language = submission.get(
        "programmingLanguage",
        "Unknown"
    )

    extension = get_extension(language)
    language_folder = get_language_folder(language)

    safe_name = sanitize_filename(problem_name)

    output_dir = SOLUTIONS_DIR / language_folder
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = (
        f"{contest_id}_{index}_{safe_name}{extension}"
    )

    output_file = output_dir / filename

    # Already synced.
    if output_file.exists():
        skipped += 1
        continue

    submission_id = submission.get("id")

    if not submission_id:
        skipped += 1
        continue

    print(
        f"Fetching source: "
        f"{contest_id}{index} "
        f"(submission {submission_id})"
    )

    source = fetch_source_code(
        contest_id,
        submission_id
    )

    if not source:
        skipped += 1
        continue

    header = (
        f"// Codeforces Problem: "
        f"{contest_id}{index}\n"
        f"// Title: {problem_name}\n"
        f"// Language: {language}\n"
        f"// Submission ID: {submission_id}\n"
        f"// Rating: "
        f"{problem.get('rating', 'N/A')}\n"
        f"// Tags: "
        f"{', '.join(problem.get('tags', []))}\n"
        f"// URL: "
        f"https://codeforces.com/problemset/problem/"
        f"{contest_id}/{index}\n"
        "\n"
    )

    output_file.write_text(
        header + source,
        encoding="utf-8"
    )

    print(f"Added: {output_file}")

    created += 1

    # Small delay to avoid making many requests too quickly.
    time.sleep(1)


print()
print("========================================")
print("Codeforces → GitHub Sync Complete")
print("========================================")
print(f"New solutions: {created}")
print(f"Skipped:       {skipped}")
print("========================================")
