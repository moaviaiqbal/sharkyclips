"""Tests run against a throwaway settings folder and workspace, never the real ones."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

_home = Path(tempfile.mkdtemp(prefix="sharkyclips-test-home-"))
(_home / "workspace").mkdir()
(_home / "config.json").write_text(json.dumps({"workspace_dir": str(_home / "workspace"),
                                               "llm_enabled": False}), encoding="utf-8")
os.environ["SHARKYCLIPS_HOME"] = str(_home)
os.environ["SHARKYCLIPS_NO_MIGRATE"] = "1"  # never touch the real shortcuts / ~/.clipforge
os.environ["SHARKYCLIPS_PUBLISH_LOOP"] = "0"  # tests tick the publish scheduler themselves
os.environ["SHARKYCLIPS_LIVE_LOOP"] = "0"  # no watcher / hotkey / chat / Telegram threads in tests
os.environ.pop("SHARKYCLIPS_TG_ENDPOINT", None)
os.environ.pop("SHARKYCLIPS_TWITCH_IRC", None)
os.environ["OBS_HOME"] = str(_home / "no-obs")  # never read the real OBS settings
os.environ["SHARKYCLIPS_NO_KEYCHAIN"] = "1"  # macOS: never touch the real login Keychain
os.environ.pop("SHARKYCLIPS_YT_ENDPOINT", None)
os.environ["SHARKYCLIPS_NO_BROWSER"] = "1"  # "Connect with Google" must not open a real browser
os.environ["SHARKYCLIPS_NO_BLEEP_CHECK"] = "1"  # renders never load Whisper to re-listen to bleeps (tested directly)
# no built-in Google client unless a test sets one (the shipped google_client.json may be filled in)
os.environ["SHARKYCLIPS_SHARED_CLIENT"] = str(_home / "no-shared-client.json")
# never the real Downloads/SharkyClips (semi-automatic posts) or ~/SharkyClips (publish queue):
# 1.2.40's tests left 16 "Stream pub-mp-*" folders in a real Downloads folder
os.environ["SHARKYCLIPS_DOWNLOADS"] = str(_home / "downloads" / "SharkyClips")
os.environ["SHARKYCLIPS_QUEUE_HOME"] = str(_home / "queue-home")
os.environ.pop("CLIPFORGE_HOME", None)
os.environ.pop("SHARKYCLIPS_SUPERVISED", None)


def pytest_collection_modifyitems(config, items):
    """Skip tests that need ffmpeg when it is not installed (CI installs it, so they run there)."""
    if shutil.which("ffmpeg"):
        return
    skip = pytest.mark.skip(reason="ffmpeg is not installed")
    for item in items:
        if "requires_ffmpeg" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _fresh_length_target():
    """The channel length target is cached for 10 minutes: every test starts without it."""
    from sharkyclips import lengthfit

    lengthfit.clear_cache()
    yield
    lengthfit.clear_cache()


@pytest.fixture(autouse=True)
def _no_leaked_pause():
    """A test that ticks a real Governor reads this PC's real state: while someone plays a game or
    watches a fullscreen video it decides to pause, and procs.suspend_all() then suspends every
    ffmpeg the NEXT tests start (an export hung forever). Never let a pause or an installed
    governor outlive its test."""
    from sharkyclips import governor, procs

    gov = governor._gov
    yield
    if procs._paused or procs._suspended:
        procs.resume_all()
    if governor._gov is not gov:
        if governor._gov is not None:
            governor._gov._go.set()
        governor._gov = gov
    governor.set_current_job(None)



@pytest.fixture
def old_limits(monkeypatch):
    """1.2.50 capped automatic posting (3 a day per platform, one automatic retry). Tests of the
    retry / limit machinery itself run with the old, wider numbers."""
    from sharkyclips import platforms as PF, publishing as P
    from sharkyclips.web import multipost as M

    monkeypatch.setattr(M, "MAX_TRIES", 6)
    monkeypatch.setattr(PF, "DAILY_POST_MAX", 15)
    monkeypatch.setattr(PF, "AUTO_RETRY_MAX", 2)
    monkeypatch.setattr(P, "BACKOFF_S", [60, 300, 900, 3600, 3 * 3600])
    monkeypatch.setattr(P, "DAILY_MAX", 50)
    yield


@pytest.fixture
def meta_on(monkeypatch, old_limits):
    """1.2.50: Meta automation is off in the product (platforms.META_AUTOMATION). The tests of the
    Instagram API engine turn it on, so that code stays tested should it ever come back."""
    from sharkyclips import platforms as PF

    monkeypatch.setattr(PF, "META_AUTOMATION", True)
    yield
