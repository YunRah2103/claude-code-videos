import hashlib
import json
import os
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import publish


class SchedulingTests(unittest.TestCase):
    def test_london_offsets_and_clock_changes(self):
        self.assertEqual(publish.london_time("2027-06-01T18:00:00+01:00").hour, 18)
        with self.assertRaises(publish.WorkflowError):
            publish.london_time("2027-03-28T01:30:00+00:00")
        first = publish.london_time("2027-10-31T01:30:00+01:00").astimezone(UTC)
        second = publish.london_time("2027-10-31T01:30:00+00:00").astimezone(UTC)
        self.assertEqual(second - first, timedelta(hours=1))

    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.request = Path(directory) / "request.json"
        self.video = self.request.with_suffix(".mp4")
        self.video.write_bytes(b"\x00\x00\x00\x14ftypisom")
        self.digest = hashlib.sha256(self.video.read_bytes()).hexdigest()
        when = datetime.now(publish.LONDON) + timedelta(hours=2)
        self.manifest = {"sha256": self.digest, "scheduled_for": when.isoformat(timespec="seconds"),
                         "video": {"path": "mock.mp4"}}
        self.enterContext(patch.dict(os.environ, {"APPROVED_COMMIT": "a" * 40}))
        self.enterContext(patch.object(publish, "report"))

    def run_schedule(self):
        self.request.write_text(json.dumps(self.manifest))
        publish.schedule(self.request)

    def test_schedules_only_after_reservation_and_sends_idempotency_key(self):
        calls = []

        def fake_api(base, path, **kwargs):
            calls.append(path)
            if path == "/git/refs":
                self.assertEqual(kwargs["payload"]["ref"], f"refs/tags/zernio-reserved/{self.digest}")
                return {"ref": "created"}
            body = kwargs["payload"]
            self.assertEqual(body["externalId"], kwargs["idem"])
            self.assertEqual(body["timezone"], "Europe/London")
            self.assertNotIn("publishNow", body)
            self.assertEqual(body["mediaItems"], [{"type": "video", "url": "https://example.test/mp4"}])
            return {"post": {"_id": "test"}}

        def fake_upload(video):
            calls.append("upload")
            return "https://example.test/mp4"

        with patch.object(publish, "api", side_effect=fake_api), \
             patch.object(publish, "upload", side_effect=fake_upload), \
             patch.object(publish, "video_file", return_value=self.video), \
             patch.object(publish, "prepare_post", return_value={}), \
             patch.object(publish, "find_post", return_value=None), \
             patch.object(publish, "status") as status:
            self.run_schedule()
        self.assertEqual(calls, ["/git/refs", "upload", "/posts"])
        status.assert_called_once_with(self.digest)

    def test_existing_post_skips_reservation_and_upload(self):
        with patch.object(publish, "find_post", return_value={"_id": "existing"}), \
             patch.object(publish, "status") as status, patch.object(publish, "api") as api, \
             patch.object(publish, "upload") as upload:
            self.run_schedule()
        status.assert_called_once_with(self.digest)
        api.assert_not_called()
        upload.assert_not_called()

    def test_reservation_conflict_blocks_upload(self):
        with patch.object(publish, "find_post", return_value=None), \
             patch.object(publish, "video_file", return_value=self.video), \
             patch.object(publish, "prepare_post"), \
             patch.object(publish, "api", return_value=None), patch.object(publish, "upload") as upload:
            with self.assertRaisesRegex(publish.WorkflowError, "declined the upload reservation"):
                self.run_schedule()
        upload.assert_not_called()

    def test_modified_video_and_past_time_block_writes(self):
        with patch.object(publish, "find_post", return_value=None), \
             patch.object(publish, "video_file", return_value=self.video), \
             patch.object(publish, "api") as api:
            self.video.write_bytes(b"different file")
            with self.assertRaisesRegex(publish.WorkflowError, "does not match"):
                self.run_schedule()
            self.manifest["scheduled_for"] = "2000-01-01T18:00:00+00:00"
            with self.assertRaisesRegex(publish.WorkflowError, "more than two minutes"):
                self.run_schedule()
        api.assert_not_called()

    def test_partial_publication_fails_status_check(self):
        post = {"status": "partial", "platforms": [
            {"platform": "tiktok", "status": "failed", "errorCategory": "media"},
            {"platform": "youtube", "status": "published"},
        ]}
        with patch.object(publish, "find_post", return_value=post):
            with self.assertRaisesRegex(publish.WorkflowError, "publications failed"):
                publish.status(self.digest)
        publish.report.assert_any_call("youtube: published.")


if __name__ == "__main__":
    unittest.main()
