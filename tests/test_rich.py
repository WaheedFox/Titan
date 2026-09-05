import pytest

from titan import RichContent


class TestRichContentConstructors:
    def test_html(self):
        content = RichContent.html("<b>Hello</b>")

        assert content.mode == "html"
        assert content.representation == "<b>Hello</b>"

    def test_markdown(self):
        content = RichContent.markdown("**Hello**")

        assert content.mode == "markdown"
        assert content.representation == "**Hello**"

    def test_blocks(self):
        blocks = [{"future_field": {"enabled": True}}]
        content = RichContent.blocks(blocks)

        assert content.mode == "blocks"
        assert content.representation is blocks

    def test_generic_constructor_is_not_public(self):
        with pytest.raises(TypeError):
            RichContent()

    def test_no_public_serialize(self):
        assert not hasattr(RichContent.html("hello"), "serialize")


class TestRichContentValidation:
    @pytest.mark.parametrize("constructor", [RichContent.html, RichContent.markdown])
    def test_markup_requires_string(self, constructor):
        with pytest.raises(TypeError):
            constructor(None)

    def test_empty_sequence_is_valid(self):
        content = RichContent.blocks([])

        assert content.mode == "blocks"
        assert content.representation == []

    def test_empty_mapping_is_valid(self):
        content = RichContent.blocks([{}])

        assert content.representation == [{}]

    def test_type_is_not_required(self):
        content = RichContent.blocks([{"unknown": "field"}])

        assert content.representation == [{"unknown": "field"}]

    def test_unknown_fields_are_preserved(self):
        block = {
            "type": "paragraph",
            "unknown": {"nested": ["value"]},
        }

        assert RichContent.blocks([block]).representation == [block]

    @pytest.mark.parametrize(
        "blocks",
        [
            "not blocks",
            b"not blocks",
            {"type": "paragraph"},
            iter([{"type": "paragraph"}]),
        ],
    )
    def test_invalid_outer_shape(self, blocks):
        with pytest.raises(TypeError):
            RichContent.blocks(blocks)

    def test_block_elements_must_be_mappings(self):
        with pytest.raises(TypeError):
            RichContent.blocks(["not a mapping"])