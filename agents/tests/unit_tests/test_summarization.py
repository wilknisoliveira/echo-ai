import pytest
from langmem.short_term import SummarizationNode

from main_agent.utils.nodes.summarization_nodes import (
    DEFAULT_SUMMARIZATION_GUIDE,
    _make_guide_prompts,
    create_summarization_node,
)


class _FakeModel:
    def invoke(self, *args, **kwargs):
        return None


@pytest.fixture
def fake_model():
    return _FakeModel()


class TestSummarizationNodeFactory:
    def test_create_without_guide_uses_default_prompts(self, fake_model):
        node = create_summarization_node(model=fake_model, summary_guide=None)
        assert isinstance(node, SummarizationNode)
        assert node.initial_summary_prompt is not None
        assert node.existing_summary_prompt is not None

    def test_create_with_guide_uses_custom_prompts(self, fake_model):
        node = create_summarization_node(
            model=fake_model, summary_guide=DEFAULT_SUMMARIZATION_GUIDE
        )
        assert isinstance(node, SummarizationNode)
        assert node.initial_summary_prompt is not None
        assert node.existing_summary_prompt is not None

    def test_guide_text_appears_in_prompts(self, fake_model):
        custom_guide = "Only timestamp critical decisions."
        prompts = _make_guide_prompts(custom_guide)
        assert "initial_summary_prompt" in prompts
        assert "existing_summary_prompt" in prompts

    def test_no_guide_returns_empty_prompts(self):
        prompts = _make_guide_prompts(None)
        assert prompts == {}

    def test_empty_guide_returns_empty_prompts(self, fake_model):
        prompts = _make_guide_prompts("")
        assert prompts == {}

    def test_defaults_are_set_correctly(self, fake_model):
        node = create_summarization_node(model=fake_model, summary_guide=None)
        assert node.max_tokens == 10000
        assert node.max_summary_tokens == 3000
        assert node.max_tokens_before_summary == 9500
