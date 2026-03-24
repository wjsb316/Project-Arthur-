
from ap.friend_brain import FriendBrain
from ap.ops_brain import OpsBrainGate


class _StubGate(OpsBrainGate):
    def __init__(self, allowed: bool):
        self.called = False
        self._allowed = allowed

    def allow_action(self, request_id):  # type: ignore[override]
        self.called = True
        return self._allowed


def test_opsbrain_gating_called_before_action(monkeypatch):
    gate = _StubGate(allowed=False)
    friend = FriendBrain(ops_gate=gate)

    allowed = friend.consider_side_effect("send_note", "req-1")

    assert gate.called is True
    assert allowed is False


def test_friend_response_drops_side_effect_without_permission():
    gate = _StubGate(allowed=False)
    friend = FriendBrain(ops_gate=gate)

    allowed = friend.consider_side_effect("send_note", "req-2")
    toned = friend.apply_tone("please send a note")

    assert allowed is False
    assert "I'm here for you" in toned
