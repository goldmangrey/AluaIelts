"""Source-owned sentence windows. IDs identify text, not a claim of entailment."""

import hashlib
import json
import re


def candidates(passage_id, blocks):
    result = []
    for index, block in enumerate(blocks):
        if block["type"] != "paragraph":
            continue
        text = block["text"]
        # Keep whitespace, newlines, Unicode and repeated occurrences unchanged.
        boundaries = [
            0,
            *[m.end() for m in re.finditer(r"[.!?](?:[\"\u201d\u2019])?\s+", text)],
            len(text),
        ]
        for start, end in zip(boundaries, boundaries[1:]):
            while start < end and text[start].isspace():
                start += 1
            while end > start and text[end - 1].isspace():
                end -= 1
            while end - start >= 8:
                stop = min(end, start + 700)
                if stop < end:
                    space = text.rfind(" ", start + 350, stop)
                    if space > start:
                        stop = space
                quote = text[start:stop]
                identity = json.dumps([passage_id, index, start, stop, quote], ensure_ascii=False)
                result.append(
                    {
                        "id": hashlib.sha256(identity.encode()).hexdigest()[:24],
                        "block_index": index,
                        "quote": quote,
                        "start_codepoint": start,
                        "end_codepoint": stop,
                    }
                )
                start = stop
                while start < end and text[start].isspace():
                    start += 1
    return result


def public_candidates(passage_id, blocks):
    return [
        {
            **{k: c[k] for k in ("id", "block_index", "quote")},
            "start": len(
                blocks[c["block_index"]]["text"][: c["start_codepoint"]].encode("utf-16-le")
            )
            // 2,
            "end": len(blocks[c["block_index"]]["text"][: c["end_codepoint"]].encode("utf-16-le"))
            // 2,
        }
        for c in candidates(passage_id, blocks)
    ]
