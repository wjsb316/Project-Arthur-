import pytest

from ap.pinset import PinsetService


def test_pinset_returns_two_pins_in_correct_format():
    service = PinsetService(
        pinset_id="default",
        pins=("sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=", "sha256/BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB="),
    )

    pins = service.get_spki_pins()

    assert len(pins) == 2
    assert all(pin.startswith("sha256/") for pin in pins)


def test_pinset_rejects_invalid_pin_format():
    service = PinsetService(pinset_id="default", pins=("invalidpin", "sha256/validpin=="))

    with pytest.raises(ValueError):
        service.get_spki_pins()
