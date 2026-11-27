# Schedule a Yub video with Zernio

The Zernio workflows run from `ccr-e1faef6c-0xpkp7`. The authentication workflow uses the existing `ZERNIO_API_KEY` GitHub Actions secret and reports the connected TikTok and YouTube account counts. The video scheduling workflow uses the same key and the job's built-in GitHub token.

## 1. Prepare the request

Preview the finished MP4 and confirm the captions, destination accounts, disclosure settings and publication time. Compute the MP4 SHA-256 with `sha256sum finished.mp4` (Linux), `shasum -a 256 finished.mp4` (macOS), or `Get-FileHash finished.mp4 -Algorithm SHA256` (PowerShell; lowercase the value). Save the request as `publishing/zernio/request.json` on the working branch. Use the public handle, exact display name, or Zernio account ID for each destination. This repository is public, so its request JSON, committed assets, workflow logs and artifacts may be visible to others.

```json
{
  "video": {"artifact_id": 123456789, "member": "Yub-video.mp4"},
  "sha256": "<64 lowercase hex characters>",
  "scheduled_for": "2027-05-15T18:00:00+01:00",
  "accounts": {"tiktok": "yub_cars", "youtube": "Yub_cars"},
  "captions": {
    "tiktok": "TikTok caption and hashtags",
    "youtube": "YouTube description and hashtags"
  },
  "tiktok": {
    "allow_comment": true,
    "allow_duet": false,
    "allow_stitch": false,
    "commercialContentType": "none"
  },
  "youtube": {
    "title": "Shorts title",
    "madeForKids": false,
    "containsSyntheticMedia": false
  }
}
```

The artifact ID is the numeric ID of an existing GitHub Actions artifact from this repository. Use the exact path of the MP4 inside the ZIP. An MP4 already committed to the branch can instead use `"video": {"path": "path/to/finished.mp4"}`. The workflow checks its bytes against the hash either way. The Zernio upload supports one MP4 within 4 GB per request and attaches it to both platforms.

Use the London offset for the chosen date, `+00:00` during GMT or `+01:00` during BST. On the autumn clock-change day the offset identifies which occurrence of a repeated time you mean. Allow time for the workflow to download and upload the file. The workflow requires over two minutes to remain when it submits the schedule.

## 2. Approve scheduling

Push the request commit to the working branch before approving it. Only the repository owner `YunRah2103` can trigger scheduling through this workflow. Creating and pushing the approval tag confirms that you previewed the exact approved MP4 and consent to public posting on both platforms at the requested time.

```bash
# Use the specific commit containing the request you reviewed.
commit=<full-reviewed-commit-sha>
git tag "zernio-approve/$commit" "$commit"
git push origin "refs/tags/zernio-approve/$commit"
```

The workflow checks the owner, the tag and its commit's ancestry before it can access the Zernio secret. The tag must be new. An ordinary working branch push runs offline tests. Zernio handles the actual publication from the approved schedule.

## 3. Check publication

The scheduling run reports the status on both platforms after submission. To check again after the scheduled time, create a new read-only status tag from a working-branch commit containing the workflow. Run the following in Bash or Git Bash.

```bash
digest=<approved-mp4-sha256>
git fetch origin ccr-e1faef6c-0xpkp7
tag="zernio-status/$digest-$(date +%s)"
git tag "$tag" FETCH_HEAD
git push origin "refs/tags/$tag"
```

Open the run summary under **Actions → Zernio video scheduling**. Failed, cancelled or partial results fail the check and identify the affected platform. The Zernio dashboard has the full provider error. Scheduled and processing results mean another status check is needed later. Status checks are run on demand, so no default-branch cron or webhook service is required.

### Duplicate prevention and recovery

Before uploading, the workflow checks Zernio for the MP4 hash and creates a durable Git tag named `zernio-reserved/<sha256>`. The tag creation is atomic, so concurrent runs cannot both upload the same MP4. It also sends the hash as the Zernio idempotency key and external ID. Keep reservation tags even after publishing.

If a run fails after reserving the MP4, use the read-only status check and inspect the Zernio dashboard. The reservation remains in place because GitHub may have lost the response after Zernio accepted an upload or scheduled a post. Resolve that attempt before intentionally releasing its reservation. Failed platform posts can be investigated and retried from the original post in Zernio when appropriate.

References are available in [Zernio's accounts API](https://docs.zernio.com/accounts/list-accounts), [media upload guide](https://docs.zernio.com/guides/media-uploads), [create post API](https://docs.zernio.com/posts/create-post), [post status API](https://docs.zernio.com/posts/list-posts), [TikTok posting guide](https://docs.zernio.com/platforms/tiktok/posts) and [YouTube posting guide](https://docs.zernio.com/platforms/youtube/posts).
