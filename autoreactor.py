import logging
from typing import Any, Dict, List

from discord import Emoji
from normality.transliteration import ascii_text


log = logging.getLogger(__name__)


def reactions_for_message_content(
    content: str,
    emoji_map: Dict[str, Emoji],
    reaction_options: Dict[str, Dict[str, Any]],
) -> List[Emoji]:
    # extract salt 😎
    searchtext = content.replace("ꜞ", "i").replace("\u2006", " ")
    # 6-bit distortion 🎸
    searchtext = ascii_text(searchtext).lower()
    log.debug("searchtext transformed %r -> %r", content, searchtext)
    reactions_by_index = {}
    for ename in set(emoji_map).intersection(set(reaction_options)):
        start = 0
        overrides = reaction_options.get(ename)
        while True:
            try:
                idx = searchtext.index(ename, start)
            except ValueError:
                break
            start = idx + len(ename)
            override_found = False
            if overrides:
                nobefore = overrides.get("nobefore", [])
                noafter = overrides.get("noafter", [])
                for override in nobefore:
                    first = idx - len(override) - 1
                    if first >= 0:
                        searchbefore = searchtext[first:idx]
                        if searchbefore == override + " ":
                            override_found = True
                            break
                if not override_found:
                    for override in noafter:
                        last = start + len(override) + 1
                        if last <= len(searchtext):
                            searchafter = searchtext[start:last]
                            if searchafter == " " + override:
                                override_found = True
                                break
            inside_an_emoji = (
                idx > 0
                and searchtext[idx - 1] == ":"
                and start < len(searchtext)
                and searchtext[start] == ":"
            )
            if inside_an_emoji:
                override_found = True
            if idx > 0 and searchtext[idx - 1].isalnum():
                override_found = True
            elif searchtext[start : start + 1].isalnum():
                override_found = True
            if not override_found:
                reactions_by_index[idx] = ename
    reactions = []
    for idx, ename in sorted(reactions_by_index.items()):
        emoji = emoji_map[ename]
        if emoji not in reactions:
            reactions.append(emoji)
    return reactions
    