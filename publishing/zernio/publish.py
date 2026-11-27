"""Schedule an owner-approved MP4 and check its Zernio publication status."""

import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ZERNIO = "https://zernio.com/api/v1"
GITHUB = "https://api.github.com/repos/YunRah2103/claude-code-videos"
LONDON = ZoneInfo("Europe/London")
PLATFORMS = ("tiktok", "youtube")
MAX_BYTES = 4_000_000_000
INTERACTIONS = ("allow_comment", "allow_duet", "allow_stitch")


class WorkflowError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


CLIENT = urllib.request.build_opener(NoRedirect())


def require(test, message):
    if not test:
        raise WorkflowError(message)


def safe_code(value):
    if isinstance(value, str) and re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", value):
        return value
    return "unknown"


def report(message):
    for variable in ("ZERNIO_API_KEY", "GH_TOKEN"):
        secret = os.getenv(variable)
        if secret:
            message = message.replace(secret, "[redacted]")
    print(message, flush=True)
    if summary := os.getenv("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as output:
            print(message, file=output)


def api(base, path, *, payload=None, idem=None, method=None):
    github = base == GITHUB
    variable = "GH_TOKEN" if github else "ZERNIO_API_KEY"
    token = os.getenv(variable)
    require(token, f"{variable} is unavailable.")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if github:
        headers.update(Accept="application/vnd.github+json", **{"X-GitHub-Api-Version": "2022-11-28"})
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if idem:
        headers["Idempotency-Key"] = idem
    request = urllib.request.Request(
        base + path, headers=headers, method=method,
        data=json.dumps(payload).encode() if payload is not None else None,
    )
    service = "GitHub" if github else "Zernio"
    try:
        with CLIENT.open(request, timeout=45) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        with error:
            if github and error.code == 302 and path.endswith("/zip"):
                return error.headers.get("Location")
            if github and error.code == 422 and path == "/git/refs":
                return None
            try:
                code = safe_code(json.loads(error.read(8192)).get("code"))
            except (ValueError, AttributeError, OSError):
                code = "unknown"
        raise WorkflowError(f"{service} API returned HTTP {error.code} ({code}).") from None
    except (OSError, ValueError):
        raise WorkflowError(f"{service} API connection or response failed.") from None


def query(base, path, **params):
    return api(base, path + "?" + urllib.parse.urlencode(params))


def london_time(value):
    require(isinstance(value, str) and re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[+-][0-9]{2}:[0-9]{2}", value
    ), "scheduled_for must include seconds and a London UTC offset.")
    try:
        result = datetime.fromisoformat(value)
        local = result.astimezone(LONDON)
    except (ValueError, OverflowError):
        raise WorkflowError("scheduled_for is not a valid date.") from None
    require(local.replace(tzinfo=None) == result.replace(tzinfo=None)
            and local.utcoffset() == result.utcoffset(),
            "scheduled_for has an invalid London clock time or UTC offset.")
    return local


def require_future(when):
    # Zernio treats a past scheduledFor as a request to publish immediately.
    require(when.astimezone(UTC) > datetime.now(UTC) + timedelta(minutes=2),
            "The London publication time must still be more than two minutes away.")


def https_request(url, method, *, data=None, headers=None, zernio_upload=False):
    require(isinstance(url, str), "The storage URL is missing.")
    parsed = urllib.parse.urlsplit(url)
    require(parsed.scheme == "https" and parsed.hostname and not parsed.username
            and not parsed.password and parsed.port in (None, 443),
            "The storage URL must use HTTPS without credentials.")
    if zernio_upload:
        require(parsed.hostname.endswith((".r2.cloudflarestorage.com", ".zernio.com")),
                "Zernio returned an unexpected storage domain.")
    request = urllib.request.Request(url, method=method, data=data, headers=headers or {})
    try:
        return CLIENT.open(request, timeout=90)
    except urllib.error.HTTPError as error:
        error.close()
        raise WorkflowError(f"Storage {method} returned HTTP {error.code}.") from None
    except OSError:
        raise WorkflowError(f"Storage {method} failed.") from None


def copy_limited(source, destination, limit):
    size = 0
    with destination.open("wb") as output:
        while chunk := source.read(1024 * 1024):
            size += len(chunk)
            require(size <= limit, "The MP4 or artifact exceeds the size limit.")
            output.write(chunk)


def video_file(source, temp):
    if "path" in source:
        require(set(source) == {"path"}, "Use one MP4 source.")
        root = Path.cwd()
        path = (root / source["path"]).resolve()
        require(path.is_relative_to(root), "The MP4 path must be inside the repository.")
    else:
        require(set(source) == {"artifact_id", "member"}
                and type(source["artifact_id"]) is int and source["artifact_id"] > 0,
                "Supply a GitHub artifact ID and the exact MP4 member name.")
        artifact_id = source["artifact_id"]
        zip_url = api(GITHUB, f"/actions/artifacts/{artifact_id}/zip")
        archive = temp / "artifact.zip"
        with https_request(zip_url, "GET") as response:
            copy_limited(response, archive, MAX_BYTES + 10_000_000)
        with zipfile.ZipFile(archive) as bundle:
            member = bundle.getinfo(source["member"])
            path = temp / "video.mp4"
            require(not member.is_dir() and Path(member.filename).suffix.lower() == ".mp4"
                    and member.file_size <= MAX_BYTES,
                    "The selected artifact entry must be an MP4 within 4 GB.")
            with bundle.open(member) as data:
                copy_limited(data, path, MAX_BYTES)
    require(path.is_file() and path.suffix.lower() == ".mp4"
            and 12 <= path.stat().st_size <= MAX_BYTES,
            "Select an MP4 file within 4 GB.")
    with path.open("rb") as data:
        require(data.read(12)[4:8] == b"ftyp", "The selected file lacks an MP4 header.")
    return path


def account_id(platform, selector):
    result = query(ZERNIO, "/accounts", platform=platform, status="connected",
                   excludeHidden="true", search=selector, limit=100)
    matches = []
    for account in result["accounts"]:
        names = (account.get("_id"), account.get("username"), account.get("displayName"),
                 account.get("platformUserId"))
        if account["platform"] == platform and any(
            isinstance(name, str) and name.lstrip("@").casefold() == selector.casefold()
            for name in names
        ):
            matches.append(account["_id"])
    require(len(matches) == 1 and not (result.get("pagination") or {}).get("nextCursor"),
            f"Expected one exact connected {platform} account. Use its Zernio account ID if needed.")
    require(isinstance(matches[0], str) and re.fullmatch(r"[0-9a-fA-F]{24}", matches[0]),
            f"Zernio returned an invalid {platform} account ID.")
    return matches[0]


def prepare_post(manifest):
    captions = manifest["captions"]
    for platform, limit in (("tiktok", 2200), ("youtube", 5000)):
        require(isinstance(captions[platform], str) and len(captions[platform]) <= limit,
                f"The {platform} caption exceeds its limit or is missing.")
    youtube = manifest["youtube"]
    require(isinstance(youtube["title"], str) and 0 < len(youtube["title"].strip()) <= 100
            and type(youtube["madeForKids"]) is bool
            and type(youtube["containsSyntheticMedia"]) is bool,
            "Supply a YouTube title and explicit audience and synthetic media settings.")
    tiktok = manifest["tiktok"]
    require(all(type(tiktok.get(field)) is bool for field in INTERACTIONS),
            "Set all three TikTok interaction options explicitly.")
    require(tiktok["commercialContentType"] in ("none", "brand_organic", "brand_content"),
            "Set the TikTok commercial content disclosure.")
    targets = {platform: account_id(platform, manifest["accounts"][platform].lstrip("@"))
               for platform in PLATFORMS}
    info = query(ZERNIO, f"/accounts/{targets['tiktok']}/tiktok/creator-info", mediaType="video")
    require("PUBLIC_TO_EVERYONE" in {option["value"] for option in info["privacyLevels"]},
            "TikTok is not currently offering public video posting for this account.")
    require(info.get("creator", {}).get("canPostMore") is not False,
            "TikTok reports that this creator cannot post more right now.")
    commercial = tiktok["commercialContentType"]
    require(commercial == "none" or commercial in
            {option["value"] for option in info.get("commercialContentTypes", [])},
            "TikTok does not offer the approved commercial content setting for this account.")
    interactions = info.get("postingLimits", {}).get("interactionSettings", {})
    for field in INTERACTIONS:
        require(not tiktok[field] or (interactions.get(field) or {}).get("enabled") is True,
                f"TikTok disallows the approved {field} setting.")
    settings = {field: tiktok[field] for field in INTERACTIONS}
    settings.update(privacy_level="PUBLIC_TO_EVERYONE", content_preview_confirmed=True,
                    express_consent_given=True)
    if commercial != "none":
        settings["commercialContentType"] = commercial
    return {
        "content": captions["tiktok"],
        "platforms": [
            {"platform": "tiktok", "accountId": targets["tiktok"]},
            {"platform": "youtube", "accountId": targets["youtube"],
             "customContent": captions["youtube"],
             "platformSpecificData": {"visibility": "public", "title": youtube["title"],
                                      "madeForKids": youtube["madeForKids"],
                                      "containsSyntheticMedia": youtube["containsSyntheticMedia"]}},
        ],
        "tiktokSettings": settings,
    }


def upload(video):
    media = api(ZERNIO, "/media/presign", payload={
        "filename": "approved-video.mp4", "contentType": "video/mp4",
        "size": video.stat().st_size,
    })
    with video.open("rb") as data:
        headers = {"Content-Type": "video/mp4", "Content-Length": str(video.stat().st_size)}
        with https_request(media["uploadUrl"], "PUT", data=data, headers=headers, zernio_upload=True):
            pass
    return media["publicUrl"]


def external_id(digest):
    return "yub-sha256-" + digest


def find_post(digest):
    result = query(ZERNIO, "/posts", externalId=external_id(digest), limit=2, view="summary")
    posts = result["posts"]
    require(len(posts) <= 1, "Zernio already contains multiple posts for this MP4 hash.")
    return posts[0] if posts else None


def status(digest):
    post = find_post(digest)
    require(post, "Zernio has no post for this MP4 hash.")
    post_status = safe_code(post.get("status"))
    report(f"Zernio post status: {post_status}.")
    failed = post_status in {"failed", "partial", "cancelled", "unknown"}
    platform_statuses = {}
    for entry in post["platforms"]:
        platform = safe_code(entry["platform"])
        platform_status = safe_code(entry.get("status"))
        platform_statuses[platform] = platform_status
        category = entry.get("errorCategory")
        message = f"{platform}: {platform_status}."
        if category or entry.get("errorMessage"):
            message += f" Zernio reports an error ({safe_code(category)}). See the Zernio dashboard for details."
        report(message)
        failed |= platform_status in {"failed", "cancelled", "unknown"}
    require(set(platform_statuses) == set(PLATFORMS), "Zernio did not report both target platforms.")
    require(not failed, "One or more platform publications failed or were cancelled.")


def schedule(manifest_path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    when = london_time(manifest["scheduled_for"])
    digest = manifest["sha256"]
    require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest),
            "The manifest needs a lowercase SHA-256 of the approved MP4.")
    if find_post(digest):
        report("This MP4 already has a Zernio post. No upload was attempted.")
        status(digest)
        return
    require_future(when)
    with tempfile.TemporaryDirectory() as directory:
        video = video_file(manifest["video"], Path(directory))
        with video.open("rb") as data:
            actual = hashlib.file_digest(data, "sha256").hexdigest()
        require(actual == digest, "The MP4 does not match the approved SHA-256.")
        payload = prepare_post(manifest)
        require_future(when)
        ref = api(GITHUB, "/git/refs", payload={"ref": f"refs/tags/zernio-reserved/{digest}",
                                                "sha": os.environ["APPROVED_COMMIT"]})
        require(ref, "GitHub declined the upload reservation. Check for an existing reservation "
                "and look up this MP4 in Zernio before any retry.")
        report(f"Reserved MP4 SHA-256 {digest}.")
        media_url = upload(video)
        require_future(when)
        payload.update(
            scheduledFor=when.isoformat(), timezone=LONDON.key,
            externalId=external_id(digest),
            mediaItems=[{"type": "video", "url": media_url}],
        )
        created = api(ZERNIO, "/posts", payload=payload, idem=external_id(digest))
        require(created.get("post", {}).get("_id"), "Zernio did not return a post ID. Check status before retrying.")
        report(f"Zernio accepted the scheduling request for {when.isoformat()} Europe/London.")
    status(digest)


def main():
    try:
        command, argument = sys.argv[1:]
        if command == "schedule":
            schedule(Path(argument))
        elif command == "status" and re.fullmatch(r"[0-9a-f]{64}", argument):
            status(argument)
        else:
            raise WorkflowError("Invalid publishing command or MP4 hash.")
    except WorkflowError as error:
        report(str(error))
        return 1
    except (KeyError, TypeError, ValueError, AttributeError, OSError, zipfile.BadZipFile):
        report("Invalid manifest, artifact, or API response. Check the workflow inputs and Zernio dashboard.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
