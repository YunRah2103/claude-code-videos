# Low-token Pixel Explainer Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline; the user requested minimum token usage and no further questions.

**Goal:** Make fresh sessions reuse the pixel pipeline with minimal context.
**Architecture:** Small shared settings and instructions, official Ponytail, one local Python CLI.
**Tech Stack:** Python 3.11+, Pillow, NumPy, PocketSphinx, FFmpeg, Claude Code.
**Spec:** docs/superpowers/specs/2026-10-27-low-token-pixel-design.md

## Global Constraints
- Preserve existing sprites, poses, narration and visual style.
- Sonnet low effort; Ponytail lite; no new MCP servers or automatic agent teams.
- Cloud instructions fallback; do not claim a plugin is active in hosted cloud.
- Ignore new renders and logs; preserve command exit codes.

## Review Focus
- Failed commands must fail even when their logs are shortened.
- Very long single-line output must remain bounded, with full logs on disk.
- Preview must work without a machine-specific font or current directory.
- Invalid preview times and missing media must fail clearly.
- Local plugin settings must contain no temporary installation paths.

## Task 1: Shared setup
- [x] Install official Ponytail through the real CLI and verify its manifest/hooks.
- [x] Write short CLAUDE.md, portable settings, ignores and dependency setup.
- [x] Document cloud limits and a compact pixel production workflow.

## Task 2: Local helpers
- [x] Write subprocess tests for exit-code/log preservation, bounded output,
  preview generation and invalid preview times; run and observe failure.
- [x] Implement tools/video.py: run, doctor, preview and probe.
- [x] Make font choice portable and propagate FFmpeg failures in the renderer.
- [x] Run tests, generate and inspect a preview sheet, validate settings/plugin.
- [x] Review changes and prepare the verified commit for repository publication.

## Verification record

- Six subprocess tests passed, including another episode duration and failure-log preservation.
- Official Ponytail 5.3.2 installed/enabled using Claude Code 2.1.311; upstream manifest validated.
- Official SessionStart hook emits lite rules with the project environment.
- Preview sheet visually inspected; existing reference MP4 has 1080x1920/60fps H.264 and AAC audio.
- Linux host had an invalid CC=clang setting; install succeeded with CC=gcc CXX=g++.
- No authenticated Claude inference or claimed percentage savings. Hosted cloud plugin limitations documented.
- Independent review: no important findings. Minor: doctor checks package availability; pinned versions and dependency compatibility were separately verified with pip check.
