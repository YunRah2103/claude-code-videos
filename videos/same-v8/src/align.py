"""Forced alignment of the single VO clip, reusing brake-explainer's PocketSphinx align() -> words.json."""
import importlib.util, json, sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("brake_align", Path(__file__).resolve().parents[2] / "brake-explainer/src/align.py")
BA = importlib.util.module_from_spec(spec); spec.loader.exec_module(BA)

# spoken form (digits/acronyms spelled out) of tts.SCRIPT, word-for-word
SPOKEN = ("two s u v's same v eight same platform one costs about two hundred thirty thousand dollars "
          "the other about one hundred twenty one thousand dollars even the engine covers reportedly fit each other "
          "so what's the extra money for the badge a bit more power and sharper tuning would you pay it yes or no")

if __name__ == "__main__":
    words = BA.align(Path(sys.argv[1]), SPOKEN)
    json.dump(words, open(Path(__file__).with_name("words.json"), "w"))
    voiced = [w for w in words if w["e"] - w["s"] >= 0.03]
    print(len(words), "words aligned;", len(voiced), f"with real duration ({100 * len(voiced) / len(words):.0f}%)")
    print(" ".join(f"{w['w']}@{w['s']}" for w in words))
