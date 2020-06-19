from autoreactor import reactions_for_message_content
from reactions import REACTION_OPTIONS


def test_reactions():
    mock_emoji_map = {key: key for key in REACTION_OPTIONS}
    test_data = [
        ("of me", []),
        ("fm", ["fm"]),
        ("ᵖꜞᵗᶜʰ ˢʰꜞᶠᵗᵉʳ", ["pitch shifter"]),
        ("vocal filter pro", []),
        ("vocal filter", ["vocal filter"]),
        ("filter", ["filter"]),
        ("filter pro", ["filter pro"]),
        ("golf ozone", []),
        ("i am using a lfo (or is it 'an lfo'?)", ["lfo"]),
    ]
    for content, expected_reactions in test_data:
        reactions = reactions_for_message_content(
            content=content,
            emoji_map=mock_emoji_map,
            reaction_options=REACTION_OPTIONS,
        )
        assert reactions == expected_reactions
