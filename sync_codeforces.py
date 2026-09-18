import json
import os
import re
import time
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

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


# ============================================================
# FILE NAME HELPERS
# ============================================================

def sanitize_filename(name):
    """
    Make a problem name safe to use as a filename.
    """

    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', '_', name)
    name = name.strip("._")

    return name[:100] or "Problem"


# ============================================================
# LANGUAGE EXTENSIONS
# ============================================================

def get_extension(language):
    language = language.lower()

    if "java" in language:
        return ".java"

    if "python" in language:
        return ".py"

    if (
        "gnu c++" in language
        or "g++" in language
        or "c++" in language
    ):
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


# ============================================================
# LANGUAGE FOLDERS
# ============================================================

def get_language_folder(language):
    language = language.lower()

    if "java" in language:
        return "Java"

    if "python" in language:
        return "Python"

    if (
        "gnu c++" in language
        or "g++" in language
        or "c++" in language
    ):
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


# ============================================================
# FETCH SOURCE CODE
# ============================================================

def fetch_source_code(contest_id, submission_id):
    """
    Fetch source code from a Codeforces submission page.
    """

    urls = [
        (
            f"https://codeforces.com/contest/"
            f"{contest_id}/submission/{submission_id}"
        ),
        (
            f"https://codeforces.com/problemset/"
            f"submission/{contest_id}/{submission_id}"
        )
    ]

    for url in urls:

        print(f"Opening submission page: {url}")

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/131.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,*/*;q=0.8"
                )
            }
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=30
            ) as response:

                html = response.read().decode(
                    "utf-8",
                    errors="replace"
                )

            print(
                f"Downloaded submission page "
                f"({len(html)} characters)"
            )

            # ------------------------------------------------
            # Codeforces normally stores the source code in:
            #
            # <pre id="program-source-text">...</pre>
            # ------------------------------------------------

            patterns = [

                r'<pre[^>]+id=["\']program-source-text["\']'
                r'[^>]*>(.*?)</pre>',

                r'<pre[^>]+class=["\'][^"\']*'
                r'program-source-text[^"\']*["\'][^>]*>'
                r'(.*?)</pre>'
            ]

            source = None

            for pattern in patterns:

                match = re.search(
                    pattern,
                    html,
                    re.DOTALL | re.IGNORECASE
                )

                if match:
                    source = match.group(1)
                    break

            # ------------------------------------------------
            # If source code wasn't found
            # ------------------------------------------------

            if source is None:

                print(
                    "Source code element was not found "
                    "on this page."
                )

                continue

            # ------------------------------------------------
            # Decode HTML entities
            # ------------------------------------------------

            source = unescape(source)

            # ------------------------------------------------
            # Remove HTML tags if any exist
            # ------------------------------------------------

            source = re.sub(
                r"<[^>]+>",
                "",
                source
            )

            # ------------------------------------------------
            # Normalize line endings
            # ------------------------------------------------

            source = source.replace(
                "\r\n",
                "\n"
            )

            source = source.replace(
                "\r",
                "\n"
            )

            source = source.strip("\n")

            # ------------------------------------------------
            # Verify source isn't empty
            # ------------------------------------------------

            if source:

                print(
                    "Source code successfully extracted."
                )

                return source

        except Exception as e:

            print(
                f"Could not fetch submission page: {e}"
            )

    print(
        f"FAILED: Could not obtain source code "
        f"for submission {submission_id}"
    )

    return None


# ============================================================
# GET CODEFORCES SUBMISSIONS
# ============================================================

print(
    f"Fetching Codeforces submissions for: {HANDLE}"
)

request = urllib.request.Request(
    API_URL,
    headers={
        "User-Agent": "Codeforces-GitHub-Sync/1.0"
    }
)

try:

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        data = json.loads(
            response.read().decode("utf-8")
        )

except Exception as e:

    raise RuntimeError(
        f"Failed to contact Codeforces API: {e}"
    )


# ============================================================
# CHECK API RESPONSE
# ============================================================

if data.get("status") != "OK":

    raise RuntimeError(
        "Codeforces API error: "
        + data.get(
            "comment",
            "Unknown error"
        )
    )


submissions = data["result"]

print(
    f"Fetched {len(submissions)} submissions."
)


# ============================================================
# SYNC ACCEPTED SOLUTIONS
# ============================================================

created = 0
skipped = 0


for submission in submissions:

    # --------------------------------------------------------
    # Only accepted submissions
    # --------------------------------------------------------

    if submission.get("verdict") != "OK":
        continue


    problem = submission.get(
        "problem",
        {}
    )


    # --------------------------------------------------------
    # Problem information
    # --------------------------------------------------------

    contest_id = problem.get(
        "contestId"
    )

    index = problem.get(
        "index",
        "Unknown"
    )


    if not contest_id:

        print(
            "Skipping submission because "
            "contest ID is missing."
        )

        skipped += 1
        continue


    problem_name = problem.get(
        "name",
        f"Problem_{contest_id}_{index}"
    )


    # --------------------------------------------------------
    # Language
    # --------------------------------------------------------

    language = submission.get(
        "programmingLanguage",
        "Unknown"
    )


    extension = get_extension(
        language
    )

    language_folder = get_language_folder(
        language
    )


    # --------------------------------------------------------
    # File name
    # --------------------------------------------------------

    safe_name = sanitize_filename(
        problem_name
    )


    output_dir = (
        SOLUTIONS_DIR
        / language_folder
    )


    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    filename = (
        f"{contest_id}_"
        f"{index}_"
        f"{safe_name}"
        f"{extension}"
    )


    output_file = (
        output_dir
        / filename
    )


    # --------------------------------------------------------
    # Don't duplicate existing solutions
    # --------------------------------------------------------

    if output_file.exists():

        print(
            f"Already exists: {output_file}"
        )

        skipped += 1
        continue


    # --------------------------------------------------------
    # Submission ID
    # --------------------------------------------------------

    submission_id = submission.get(
        "id"
    )


    if not submission_id:

        print(
            "Skipping submission because "
            "submission ID is missing."
        )

        skipped += 1
        continue


    # --------------------------------------------------------
    # Fetch actual source code
    # --------------------------------------------------------

    print()
    print(
        f"Fetching source for "
        f"{contest_id}{index}"
    )

    print(
        f"Submission ID: {submission_id}"
    )

    print(
        f"Language: {language}"
    )


    source = fetch_source_code(
        contest_id,
        submission_id
    )


    # --------------------------------------------------------
    # Source unavailable
    # --------------------------------------------------------

    if not source:

        print(
            f"SKIPPED submission "
            f"{submission_id}: "
            f"source code could not be retrieved."
        )

        skipped += 1
        continue


    # ========================================================
    # CREATE HEADER
    # ========================================================

    header = (
        f"// Codeforces Problem: "
        f"{contest_id}{index}\n"

        f"// Title: "
        f"{problem_name}\n"

        f"// Language: "
        f"{language}\n"

        f"// Submission ID: "
        f"{submission_id}\n"

        f"// Rating: "
        f"{problem.get('rating', 'N/A')}\n"

        f"// Tags: "
        f"{', '.join(problem.get('tags', []))}\n"

        f"// URL: "
        f"https://codeforces.com/problemset/problem/"
        f"{contest_id}/{index}\n"

        "\n"
    )


    # ========================================================
    # WRITE SOLUTION FILE
    # ========================================================

    output_file.write_text(
        header + source,
        encoding="utf-8"
    )


    print()
    print(
        f"Added: {output_file}"
    )


    created += 1


    # --------------------------------------------------------
    # Small delay between Codeforces requests
    # --------------------------------------------------------

    time.sleep(1)


# ============================================================
# FINAL REPORT
# ============================================================

print()
print("========================================")
print("Codeforces → GitHub Sync Complete")
print("========================================")
print(
    f"New solutions: {created}"
)
print(
    f"Skipped:       {skipped}"
)
print("========================================")
