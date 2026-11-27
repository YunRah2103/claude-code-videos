# Sampled video QA

Run `python tools/visual_qa.py out/video.mp4 --samples 12` to get compact JSON:
resolution, average frame rate, duration, near-black sample timestamps and adjacent
similar sample pairs. FFmpeg, ffprobe and Pillow are required. Extraction failures
return a nonzero exit status. The default samples twelve evenly spaced midpoints;
choose 2–100 with `--samples`.

This is a quick triage tool, not a complete decoder test or quality certification.
Black means the mean of each RGB channel at a 64×64 nearest-neighbour sample is
at most 8/255. Similar means mean absolute RGB difference is at most 1/255. Both
are warnings: intentional fades and static compositions can trigger them, and
short problems between sample times can be missed. Compare motion in the actual
video and inspect full-resolution frames. The tool does not assess audio, missing
frames, pixel-grid consistency, artistic quality or whether a freeze is intentional.
It never modifies the source or writes generated frames to the repository.
