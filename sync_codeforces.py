import html
import json
import os
import re
import urllib.parse
import urllib.request
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
    urls = [
        f"https://codeforces.com/contest/{contest_id}/submission/{submission_id}",
        f"https://codeforces.com/problemset/submission/{contest_id}/{submission_id}"
    ]

    for url in urls:
        print(f"Opening submission page: {url}")

        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 "
                        "(KHTML, like Gecko) "
                        "Chrome/120.0 Safari/537.36"
                    )
                }
            )

            with urllib.request.urlopen(request, timeout=30) as response:
                page = response.read().decode("utf-8", errors="ignore")

            print(f"Downloaded submission page ({len(page)} bytes).")

            match = re.search(
                r'<pre[^>]*id="program-source-text"[^>]*>(.*?)</pre>',
                page,
                re.DOTALL
            )

            if not match:
                match = re.search(
                    r'<pre[^>]*class="[^"]*program-source-text[^"]*"[^>]*>(.*?)</pre>',
                    page,
                    re.DOTALL
                )

            if match:
                source = match.group(1)

                source = html.unescape(source)

                source = re.sub(
                    r'<br\s*/?>',
                    '\n',
                    source,
                    flags=re.IGNORECASE
                )

                source = re.sub(r'<[^>]+>', '', source)

                print("Source code successfully extracted.")

                return source.strip()

            print("Source code was not found on this page.")

        except Exception as e:
            print(f"Could not fetch submission page: {e}")

    return None


print(f"Fetching Codeforces submissions for: {HANDLE}")

request = urllib.request.Request(
    API_URL,
    headers={
        "User-Agent": "Codeforces-GitHub-Sync/2.0"
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

    if submission.get("verdict") != "OK":
        continue

    problem = submission.get("problem", {})

    contest_id = problem.get("contestId")
    index = problem.get("index", "Unknown")
    submission_id = submission.get("id")

    problem_name = problem.get(
        "name",
        f"Problem_{contest_id}_{index}"
    )

    language = submission.get(
        "programmingLanguage",
        "Unknown"
    )

    print()
    print(f"Fetching source for {contest_id}{index}")
    print(f"Submission ID: {submission_id}")
    print(f"Problem: {problem_name}")

    source = fetch_source_code(
        contest_id,
        submission_id
    )

    if not source:
        print("Skipping: source code could not be retrieved.")
        skipped += 1
        continue

    extension = get_extension(language)
    language_folder = get_language_folder(language)

    safe_name = sanitize_filename(problem_name)

    output_dir = SOLUTIONS_DIR / language_folder
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = (
        f"{contest_id}_{index}_{safe_name}{extension}"
    )

    output_file = output_dir / filename

    if output_file.exists():
        print(f"Already exists: {output_file}")
        skipped += 1
        continue

    header = (
        f"// Codeforces Problem: {contest_id}{index}\n"
        f"// Title: {problem_name}\n"
        f"// Language: {language}\n"
        f"// Submission ID: {submission_id}\n"
        f"// Rating: {problem.get('rating', 'N/A')}\n"
        f"// Tags: {', '.join(problem.get('tags', []))}\n"
        f"// URL: https://codeforces.com/problemset/problem/"
        f"{contest_id}/{index}\n"
        "\n"
    )

    output_file.write_text(
        header + source,
        encoding="utf-8"
    )

    print(f"Added: {output_file}")

    created += 1


print()
print("========================================")
print("Codeforces → GitHub Sync Complete")
print("========================================")
print(f"New solutions: {created}")
print(f"Skipped:       {skipped}")
print("========================================")
