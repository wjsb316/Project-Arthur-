import time


class PipelineTimer:
    """Lightweight pipeline stage timer.

    Captures wall-clock timestamps at named checkpoints and computes
    per-stage deltas by simple subtraction.  Uses time.time() only.

    Stages
    ------
    t0  Input received (chat submit / voice transcription done)
    t1  Context search pipeline complete  → delta from t0
    t2  LLM call complete                 → delta from t1
    t3  First TTS audio token yielded     → delta from t2  (voice only)
    t4  TTS audio stream fully complete   → delta from t2  (voice only)
    """

    __slots__ = ("_stamps",)

    def __init__(self) -> None:
        self._stamps: dict[str, float] = {}

    def stamp(self, name: str) -> None:
        """Record current wall-clock time for *name*."""
        self._stamps[name] = time.time()

    def delta(self, start: str, end: str) -> float | None:
        """Elapsed seconds between two stamps; None if either is missing."""
        t0 = self._stamps.get(start)
        t1 = self._stamps.get(end)
        if t0 is None or t1 is None:
            return None
        return t1 - t0

    @staticmethod
    def fmt(seconds: float | None) -> str:
        """Format seconds as 00.000s (zero-padded, 3 decimal places)."""
        if seconds is None:
            return "   N/A "
        return f"{seconds:06.3f}s"

    def report(self, is_voice: bool = False) -> str:
        """Return a single-line or multiline timing summary for the logger."""
        t1 = self.delta("t0", "t1")
        t2 = self.delta("t1", "t2")
        lines = [
            "Pipeline timing —",
            f"  t1 context search : {self.fmt(t1)}  (since t0)",
            f"  t2 LLM call       : {self.fmt(t2)}  (since t1)",
        ]
        if is_voice:
            t3 = self.delta("t2", "t3")
            t4 = self.delta("t2", "t4")
            lines.append(f"  t3 first TTS token: {self.fmt(t3)}  (since t2)")
            lines.append(f"  t4 TTS stream done: {self.fmt(t4)}  (since t2)")
        return "\n".join(lines)
