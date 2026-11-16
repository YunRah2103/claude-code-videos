"""Forced alignment of the single VO clip, reusing brake-explainer's PocketSphinx align() -> words.json."""
import importlib.util, json, sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("brake_align", Path(__file__).resolve().parents[2] / "brake-explainer/src/align.py")
BA = importlib.util.module_from_spec(spec); spec.loader.exec_module(BA)

# spoken form (digits/acronyms spelled out) of tts.SCRIPT, word-for-word
SPOKEN = ("everything a car does speeding up braking turning goes through four patches of rubber "
          "each one is about the size of your hand all four together barely a sheet of paper "
          "at a hundred kilometres an hour each tyre spins about fourteen times a second "
          "and that's all that's holding you to the road")

if __name__ == "__main__":
    words = BA.align(Path(sys.argv[1]), SPOKEN)
    json.dump(words, open(Path(__file__).with_name("words.json"), "w"))
    voiced = [w for w in words if w["e"] - w["s"] >= 0.03]
    print(len(words), "words aligned;", len(voiced), f"with real duration ({100 * len(voiced) / len(words):.0f}%)")
    print(" ".join(f"{w['w']}@{w['s']}" for w in words))
