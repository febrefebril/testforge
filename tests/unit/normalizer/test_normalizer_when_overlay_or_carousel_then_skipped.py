"""NB-13: Normalizer must skip overlay + carousel auto-fire events."""
import pytest
from testforge.semantic.recording_normalizer import _is_noise_event


@pytest.mark.unit
class TestNormalizerWhenOverlayOrCarouselThenSkipped:
    def test_tf_btn_element_is_noise(self):
        event = {"type": "click", "target": {"element_id": "tf-btn-pause"}}
        assert _is_noise_event(event) is True

    def test_tf_panel_element_is_noise(self):
        event = {"type": "click", "target": {"element_id": "tf-panel"}}
        assert _is_noise_event(event) is True

    def test_double_underscore_tf_class_element_is_noise(self):
        event = {"type": "click", "target": {"element_id": "__tf-toast"}}
        assert _is_noise_event(event) is True

    def test_carousel_next_class_is_noise(self):
        event = {"type": "click", "target": {"element_id": "next", "class_list": ["carousel-control-next"]}}
        assert _is_noise_event(event) is True

    def test_swiper_next_is_noise(self):
        event = {"type": "click", "target": {"class_list": ["swiper-button-next"]}}
        assert _is_noise_event(event) is True

    def test_regular_button_is_not_noise(self):
        event = {"type": "click", "target": {"element_id": "submit-btn", "class_list": ["btn", "btn-primary"]}}
        assert _is_noise_event(event) is False
