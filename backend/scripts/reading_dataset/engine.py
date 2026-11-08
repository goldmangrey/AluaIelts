"""Deterministic Cambridge Reading ingestion. Never modifies source materials."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from labels import required_labels

ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / "backend/app/content/reading_v1"
VERSION = "1.0.0"
DASH = r"[-–—−]"
TYPES = [
    "multiple_choice_single",
    "multiple_choice_multiple",
    "true_false_not_given",
    "yes_no_not_given",
    "matching_headings",
    "matching_information",
    "matching_features",
    "matching_sentence_endings",
    "sentence_completion",
    "summary_completion",
    "note_completion",
    "table_completion",
    "flow_chart_completion",
    "diagram_labelling",
    "short_answer",
    "unknown",
]
TEST = re.compile(
    (
        "^(?:ACADEMIC READING\\s*[—–-]\\s*TEST (\\d+)\\s*$|TEST "
        "(\\d+)\\s*[—–|]\\s*(?:ACADEMIC )?READING(?! PASSAGE)[^\\n]*)"
    ),
    re.M,
)
KEY = re.compile(r"^.*(?:ANSWER KEY|CORRECT ANSWERS FOR PASSAGE|OFFICIAL ANSWERS).*$", re.M)
GROUP = re.compile(
    r"^\s*(?:---\s*)?Questions?\s*(\d{1,2})(?:\s*(?:[-–—−]+|and|&)\s*(\d{1,2}))?([^\n]*)",
    re.M | re.I,
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", dir=path.parent, encoding="utf-8", delete=False) as f:
        f.write(content)
        temp = f.name
    os.replace(temp, path)


def clean(s):
    lines = []
    for line in s.splitlines():
        if re.fullmatch(r"\s*[=\-─#_.·]{3,}\s*", line):
            continue
        if re.match(
            (
                "^\\s*(?:\\[(?:.*(?:PDF|SOURCE PAGE|source page|From "
                "original).*|PASSAGE TEXT.*|READING TEXT.*|READING PASSAGE "
                "—.*)\\]|--- (?:From original|SOURCE PAGE).*)\\s*$"
            ),
            line,
            re.I,
        ):
            if re.search(r"QUESTIONS?\s+\d", line, re.I):
                line = re.sub(r"\s*\(SOURCE.*", "", line, flags=re.I).strip(" -")
            else:
                continue
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


def numbers(m):
    a = int(m[1])
    b = int(m[2] or a)
    return list(range(a, b + 1)) if 1 <= a <= b <= 40 else []


def pages(s):
    """Extract only explicitly PDF-qualified page coordinates, never printed pages."""
    out = []
    for line in s.splitlines():
        if "PDF" not in line.upper():
            continue
        if re.search(r"PDF reading pages|pages in PDF", line, re.I):
            tail = re.split(r"PDF reading pages:|pages in PDF:", line, flags=re.I)[-1]
            out.extend(expand_pages(tail))
        # A line can contain several PDF clauses. Semicolons separate printed references.
        for m in re.finditer(
            (
                "PDF\\s*(?:PAGES?|pp?\\.?|PAGES\\s*—\\s*ARTICLE:)?\\s*[:—]?\\s*((?:\\d+[\\"
                "d ,–—-]*)(?:;\\s*questions\\s+\\d+[\\d ,–—-]*)?)"
            ),
            line,
            re.I,
        ):
            out.extend(expand_pages(m[1]))
        if re.search(r"Source PDF pages: passages|SOURCE PDF PAGES\s*—\s*ARTICLE", line, re.I):
            out.extend(expand_pages(re.split(r"pages", line, flags=re.I)[-1].split("(")[0]))
        if "questions on pages" in line.lower():
            out.extend(expand_pages(line.lower().split("questions on pages")[1].split("]")[0]))
    return sorted(set(n for n in out if 1 <= n <= 250))


def expand_pages(s):
    out = []
    for m in re.finditer(r"(\d+)(?:\s*[-–—]\s*(\d+))?", s):
        a = int(m[1])
        b = int(m[2] or a)
        if 0 <= b - a < 30:
            out.extend(range(a, b + 1))
    return out


def ref(file, start, end, pdf, pp):
    return {
        "txt_file": str(file.relative_to(ROOT)),
        "line_start": start,
        "line_end": end,
        "pdf_file": str(pdf.relative_to(ROOT)),
        "pdf_pages": pp,
    }


def options(s, roman=False):
    if not roman:
        expanded = []
        for line in s.splitlines():
            markers = list(re.finditer(r"(?<!\w)([A-Z])[.)_]?[ \t_]+", line))
            labels = [m[1] for m in markers]
            if (
                len(markers) > 1
                and len(set(labels)) == len(labels)
                and labels == sorted(labels)
                and markers[0].start() == 0
            ):
                for marker in reversed(markers[1:]):
                    line = line[: marker.start()] + "\n" + line[marker.start() :]
            expanded.append(line)
        s = "\n".join(expanded)
    s = re.sub(r"(?:List of [^:\n]+:|;)\s*(?=[A-Z]\s)", "\n", s)
    pat = r"^\s*([ivxlcdm]{1,6})[.)]?\s+(.+)" if roman else r"^\s*([A-Z])[.)]?\s*[_ ]*\s+(.+)"
    # Labels on their own line are common in older OCR.
    if not roman:
        pat = r"^\s*([A-Z])(?:[.)_—–-]|[ \t]|$)[ \t_]*([^\n]*)"
    found = list(re.finditer(pat, s, re.M))
    out = []
    for i, m in enumerate(found):
        end = found[i + 1].start() if i + 1 < len(found) else len(s)
        body = s[m.start() : end]
        body = re.sub(pat, r"\2", body, count=1, flags=re.M).strip()
        body = re.split(r"\n\s*(?:\d{1,2}[.)]?\s|Questions?\s+\d)", body)[0].strip()
        if body:
            out.append({"label": m[1], "text": " ".join(body.split())})
    # A lone prose paragraph ("A team...", "A major reason...") is not a bank.
    # A usable choice bank has at least two distinct labels.
    return out if len({item["label"] for item in out}) >= 2 else []


def classify(s, nums):
    t = s.lower()
    lead = re.split(r"\n\s*(?:\d{1,2}[.)]?\s+|a[._ ]|i[.)]?\s)", t, 1)[0][:1400]
    if len(lead) < 30:
        lead = t[:350]
    if (
        re.search(r"\btrue\b", t[:1400])
        and re.search(r"\bfalse\b", t[:1400])
        and "not given" in t[:1400]
    ):
        return "true_false_not_given"
    if (
        re.search(r"\byes\b", t[:1400])
        and re.search(r"\bno\b", t[:1400])
        and "not given" in t[:1400]
    ):
        return "yes_no_not_given"
    if re.search(r"(?:label|complete).*diagram|diagram.*(?:below|labell)", lead):
        return "diagram_labelling"
    if re.search(r"flow[ -]?chart", lead):
        return "flow_chart_completion"
    if re.search(r"(?:correct|suitable|appropriate|list of) headings?|matching headings", lead):
        return "matching_headings"
    if re.search(r"(?:which|what) (?:section|paragraph)|contains the following information", lead):
        return "matching_information"
    if re.search(r"(?:complete|completing|completion).*table|table.*completion", lead):
        return "table_completion"
    if re.search(r"(?:complete|completing|completion).*notes?|notes?.*completion", lead):
        return "note_completion"
    if re.search(r"(?:complete|completing|completion).*summary|summary.*completion", lead):
        return "summary_completion"
    if re.search(
        r"(?:complete|completing).*sentence.*(?:ending|a[–-])|sentence endings|correct ending", lead
    ):
        return "matching_sentence_endings"
    if re.search(
        (
            "(?:choose|which|select|give)\\s+(?:the\\s+)?(?:two|three|four|five|"
            "six|\\d)\\b|choose.*(?:two|three) letters"
        ),
        lead,
    ):
        return "multiple_choice_multiple"
    if re.search(r"match each", lead):
        return "matching_features"
    if re.search(r"choose the correct (?:[l/]etter|answer)|multiple.choice", lead):
        return "multiple_choice_single"
    if re.search(r"which six.*statements", lead):
        return "multiple_choice_multiple"
    if re.search(
        (
            "match|classify|list of (?:people|researchers|scientists|nationali"
            "ties|countries|companies)|correct (?:letter|person)"
        ),
        lead,
    ):
        return "matching_features"
    if re.search(r"complete.*sentences?|sentence.*completion", lead):
        return "sentence_completion"
    if re.search(r"answer the (?:following )?questions|short.answer", lead):
        return "short_answer"
    return "unknown"


def constraints(s, typ, opts):
    limit = None
    m = re.search(r"(?:NO MORE THAN\s+)?(ONE|TWO|THREE|FOUR|FIVE|\d+)\s+WORDS?", s, re.I)
    if m:
        limit = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}.get(
            m[1].upper(), int(m[1]) if m[1].isdigit() else None
        )
    return {
        "max_words": limit,
        "allow_number": bool(re.search(r"(?:AND/OR|OR|A)\s+(?:A\s+)?NUMBER", s, re.I)),
        "allowed_values": (
            ["TRUE", "FALSE", "NOT GIVEN"]
            if typ == "true_false_not_given"
            else ["YES", "NO", "NOT GIVEN"]
            if typ == "yes_no_not_given"
            else [o["label"] for o in opts]
        ),
        "reuse_allowed": bool(re.search(r"(?:more than once|as often as)", s, re.I)),
        "selection_count": None,
    }


def rich_text(s, nums):
    """Lossless text plus explicit answer slots, not guessed table coordinates."""
    segments = []
    last = 0
    leader = r"(?:_{2,}|\.{3,}|…{2,}|[.·][ \t]*[.·][ \t]*[.·](?:[.· \t])*)"
    pat = rf"(?<!\d)(\d{{1,2}})[.)]?[ \t]*(?:\[)?{leader}(?:\])?|_{{2,}}\s*\(?(\d{{1,2}})\)?"
    for m in re.finditer(pat, s):
        n = int(m[1] or m[2])
        if n not in nums:
            continue
        if m.start() > last:
            segments.append({"type": "text", "text": s[last : m.start()]})
        segments.append({"type": "blank", "number": n})
        last = m.end()
    if last < len(s):
        segments.append({"type": "text", "text": s[last:]})
    return segments or [{"type": "text", "text": s}]


def paragraphs(s, title, allowed_labels):
    # Editorial section labels in some TXT editions represent the original margin label.
    s = re.sub(r"^(?:Paragraph|Section)\s*([A-Z])[^\n]*\n", r"\1 ", s, flags=re.M)
    prefix = re.compile(r"^\[?([A-Z])(?:\]\s*|[_.]\s*|\s+)", re.M)
    markers = []
    for match in prefix.finditer(s):
        if allowed_labels and match[1] not in allowed_labels:
            continue
        following = s[match.end() : match.end() + 1]
        explicit = any(c in match[0] for c in "[_.")
        if match[1] in "AI" and not explicit and not (following.isupper() or following in '‘“"'):
            continue
        line = s[
            match.start() : s.find("\n", match.start()) if "\n" in s[match.start() :] else len(s)
        ]
        if line.strip().casefold() != title.casefold():
            markers.append(match)
    sequential = []
    last_label = 0
    for marker in markers:
        if ord(marker[1]) > last_label:
            sequential.append(marker)
            last_label = ord(marker[1])
    markers = sequential
    # A normal article is never stripped without evidence of a series of section labels.
    if not allowed_labels and len({m[1] for m in markers}) < 3:
        markers = []
    boundaries = [(0, None, 0)] + [(m.start(), m[1], m.end()) for m in markers]
    out = []
    for i, (start, label, body) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(s)
        parts = [para.strip() for para in re.split(r"\n\s*\n", s[body:end]) if para.strip()]
        for j, para in enumerate(parts):
            is_title = " ".join(para.split()).casefold() == title.casefold()
            out.append(
                {
                    "type": "heading" if is_title else "paragraph",
                    "text": para,
                    "label": label if j == 0 else None,
                }
            )
    return out


def answers_from(s):
    out = {}
    conflicts = []
    for m in KEY.finditer(s):
        tail = s[m.end() :]
        stop = re.search(r"^.*(?:READING PASSAGE [123]|TEST \d+\s*[—|]).*$", tail, re.M)
        # Passage headings inside a key must not truncate the key.
        stop = re.search(
            r"^(?:TEST \d+.*(?:ACADEMIC )?READING|READING PASSAGE [123]\s*[:—]).*$", tail, re.M
        )
        if stop:
            tail = tail[: stop.start()]
        for a in re.finditer(r"^\s*(\d{1,2})[.)]\s*(.+)$", tail, re.M):
            n = int(a[1])
            v = a[2].strip()
            if not 1 <= n <= 40:
                continue
            if n in out and out[n] != v:
                conflicts.append({"number": n, "values": [out[n], v]})
            out[n] = v
    return out, conflicts


def variants(s):
    """Expand only explicit key notation: optional parentheses and slash alternatives."""
    s = re.sub(r"\s*\[.*?\]|\s*\([^)]*(?:ORDER|REQUIRED)[^)]*\)|\*", "", s, flags=re.I).strip()
    s = re.sub(r"\s+or\s+", " / ", s, flags=re.I)

    # Slash within parentheses belongs to its optional phrase, not the outer expression.
    def expand(t):
        m = re.search(r"\(([^()]*)\)", t)
        if m:
            inside = m[1]
            choices = [""] + [v.strip() for v in inside.split("/")]
            return [v for c in choices for v in expand(t[: m.start()] + c + t[m.end() :])]
        return [re.sub(r"\s+", " ", re.sub(r"\s+-\s+", "-", t)).strip()]

    masked = re.sub(r"\([^()]*\)", lambda m: m[0].replace("/", "\u0001"), s)
    parts = re.split(r"\s*/\s*", masked)
    return sorted(set(v for p in parts for v in expand(p.replace("\u0001", "/")) if v))


def parse_passage(raw, header, pid, source):
    pn = int(re.search(r"PASSAGE ([123])", header)[1])
    declared = None
    intro = re.search(
        r"You should spend.{0,100}?Questions\s+(\d{1,2})\s*[-–—]+\s*(\d{1,2})",
        raw[:2000],
        re.S | re.I,
    )
    if not intro:
        prefix = (
            raw[: re.search(r"(?:PASSAGE TEXT|READING TEXT)", raw, re.I).start()]
            if re.search(r"(?:PASSAGE TEXT|READING TEXT)", raw, re.I)
            else raw[:200]
        )
        intro = re.search(
            r"QUESTIONS?\s*[: ]\s*(\d{1,2})\s*[-–—]+\s*(\d{1,2})", header + "\n" + prefix, re.I
        )
    if intro:
        declared = list(range(int(intro[1]), int(intro[2]) + 1))
    key = KEY.search(raw)
    public = raw[: key.start()] if key else raw
    # Explicit editorial question-section marker, then group headings.
    marker = re.search(
        (
            "^(?:\\[QUESTIONS[^\\n]*\\]|QUESTIONS(?: FOR "
            "PASSAGE[^\\n]*)?|QUESTIONS \\d+[^\\n]*— Passage \\d+)\\s*$"
        ),
        public,
        re.M,
    )
    if marker:
        ptext = public[: marker.start()]
        qtext = public[marker.end() :]
        early = [
            m
            for m in GROUP.finditer(ptext)
            if m.start() > 200 and not re.search(r"PDF|~20|\|", m[3])
        ]
        if early:
            qtext = ptext[early[0].start() :] + "\n" + qtext
            ptext = ptext[: early[0].start()]
    else:
        gm = list(GROUP.finditer(public))
        gm = [
            m
            for m in gm
            if not re.search(r"~20|\|", m[3])
            and ("PDF" not in m[3] or m[0].lstrip().startswith("---"))
        ]
        # 17 has no standalone question-section marker; first --- QUESTIONS marks it.
        first = next((m for m in gm if m.start() > 150), None)
        if first:
            ptext = public[: first.start()]
            qtext = public[first.start() :]
        else:
            ptext = public
            qtext = ""
    title = re.sub(r"^.*?PASSAGE [123]\s*[:—–-]?\s*", "", header).strip()
    if re.match(r"[|\s]*QUESTIONS?\b", title, re.I) or not title:
        title = None
    pm = re.search(
        (
            "^(?:\\[?(?:PASSAGE TEXT|READING TEXT|READING PASSAGE — FULL "
            "TEXT)[^\\n]*|TEXT \\(original[^\\n]*)\\]?\\s*$"
        ),
        ptext,
        re.M,
    )
    subtitle = None
    if pm:
        prefix = ptext[: pm.start()]
        candidates = [
            line.strip()
            for line in prefix.splitlines()
            if len(line.strip()) > 45
            and not re.match(r"^(?:Source|Questions|Original|TEXT|[=\-#_\[─])", line.strip(), re.I)
        ]
        if candidates:
            subtitle = " ".join(candidates)
        ptext = ptext[pm.end() :]
    ptext = clean(ptext)
    ptext = re.sub(r"^READING(?:\s+PASSAGE [123])?\s*\n", "", ptext)
    ptext = re.sub(r"^You should spend.*?(?:below\.|Passage [123]\.)\s*", "", ptext, flags=re.S)
    ptext = re.sub(
        r"^(?:Questions?[^\n]*|Source[^\n]*|Original pages:[^\n]*)\n", "", ptext, flags=re.I
    )
    ptext = clean(ptext)
    if not title and ptext:
        first = ptext.split("\n\n")[0].strip()
        if len(first) < 160:
            title = " ".join(first.split())
    title = title or "Untitled"
    qtext = clean(qtext)
    for boundary in list(
        re.finditer(r"^Complete (?:each sentence|the sentences) (?:below|with)[^\n]*", qtext, re.M)
    )[::-1]:
        before = qtext[: boundary.start()]
        after = qtext[boundary.start() :]
        found = [
            int(m[1])
            for m in re.finditer(r"^\s*(\d{1,2})[.)]?\s+\S", after.split("Questions ", 1)[0], re.M)
        ]
        previous = list(GROUP.finditer(before))
        if found and previous and min(found) > max(numbers(previous[-1]) or [0]):
            qtext = (
                qtext[: boundary.start()]
                + f"Questions {min(found)}–{max(found)}\n"
                + qtext[boundary.start() :]
            )
    matches = list(GROUP.finditer(qtext))
    groups = []
    for i, m in enumerate(matches):
        ns = numbers(m)
        if i + 1 < len(matches):
            next_ns = numbers(matches[i + 1])
            if next_ns and ns and next_ns[0] == ns[0]:
                continue
            if next_ns and ns and ns[0] < next_ns[0] <= ns[-1]:
                ns = list(range(ns[0], next_ns[0]))
        if not ns:
            continue
        text = qtext[
            m.start() : matches[i + 1].start() if i + 1 < len(matches) else len(qtext)
        ].strip()
        # Page markers and mirrored headings sometimes introduce no actual task.
        if len(clean(text).split()) < 6:
            continue
        if ns == [13] and "boxes 14" in text:
            ns = [14, 15, 16, 17]
        typ = classify(text, ns)
        gid = f"{pid}-g-{ns[0]:02}-{ns[-1]:02}"
        opts = options(text, typ == "matching_headings")
        inp = (
            "boolean"
            if typ in ["true_false_not_given", "yes_no_not_given"]
            else "multi_select"
            if typ == "multiple_choice_multiple"
            else "single_select"
            if typ.startswith("matching") or typ == "multiple_choice_single"
            else "single_select"
            if opts
            else "text"
        )
        c = constraints(text, typ, opts)
        if typ == "multiple_choice_multiple":
            c["selection_count"] = len(ns)
        numbered = list(re.finditer(r"^\s*(\d{1,2})[.)]?\s+(\S.*)", text, re.M))
        questions = []
        for n in ns:
            nm = next((a for a in numbered if int(a[1]) == n), None)
            localopts = []
            if not nm and typ == "multiple_choice_single" and len(ns) == 1:
                localopts = opts
            if nm:
                following = next((a for a in numbered if a.start() > nm.start()), None)
                segment = text[nm.end(1) : following.start() if following else len(text)].lstrip(
                    ".) \n"
                )
                if typ == "multiple_choice_single":
                    localopts = options(segment)
                prompt = (
                    re.split(r"\n\s*A(?:[.)]|\s|$)", segment)[0].strip()
                    if localopts
                    else segment.strip()
                )
            else:
                # Embedded summary blanks retain the entire original shared context.
                prompt = (
                    f"Paragraph {chr(65 + ns.index(n))}"
                    if typ == "matching_headings"
                    and re.search(r"heading matching blank for Question " + str(n), public)
                    else text
                )
            questions.append(
                {
                    "id": f"{pid.rsplit('-p-', 1)[0]}-q-{n:02}",
                    "number": n,
                    "group_id": gid,
                    "type": typ,
                    "prompt": prompt,
                    "answer_input_type": inp,
                    "options": localopts,
                    "constraints": dict(c),
                    "source_reference": source,
                }
            )
        instruction_end = numbered[0].start() if numbered else len(text)
        groups.append(
            {
                "id": gid,
                "type": typ,
                "instructions": text[:instruction_end].strip(),
                "question_numbers": ns,
                "options": opts if typ != "multiple_choice_single" else [],
                "content_blocks": [{"type": "rich_text", "segments": rich_text(text, ns)}],
                "assets": [],
                "constraints": c,
                "questions": questions,
                "source_reference": source,
                "representation": "structured_text",
                "source_verified": False,
            }
        )
    return {
        "id": pid,
        "number": pn,
        "title": title,
        "subtitle": subtitle,
        "content": paragraphs(ptext, title, required_labels({"question_groups": groups})),
        "question_groups": groups,
        "question_numbers": sorted({q for g in groups for q in g["question_numbers"]}),
        "source_pages": source["pdf_pages"],
        "source_question_range": declared,
        "source_reference": source,
    }


def parse_book(f):
    book_number = int(re.search(r"IELTS_(\d+)", f.name)[1])
    s = f.read_text(encoding="utf-8")
    original = s
    for edit in json.loads(Path(__file__).with_name("source_edits.json").read_text()):
        if edit["source_file"] == str(f.relative_to(ROOT)):
            if edit["old_value"] not in s:
                raise ValueError("Source correction no longer applies")
            s = s.replace(edit["old_value"], edit["new_value"], 1)
    pdf = ROOT / f"ieltsbooks/Cambridge-IELTS-{book_number:02}.pdf"
    import difflib

    line_map = {}
    for tag, i, j, a, z in difflib.SequenceMatcher(
        None, original.splitlines(), s.splitlines(), autojunk=False
    ).get_opcodes():
        for offset, ln in enumerate(range(a + 1, z + 1)):
            line_map[ln] = i + 1 + min(offset, max(0, j - i - 1))
    tests = list(TEST.finditer(s))
    out = []
    for ordinal, t in enumerate(tests, 1):
        tn = int(t[1] or t[2])
        eid = f"cambridge-{book_number:02}-test-{tn:02}"
        start = t.end()
        end = tests[ordinal].start() if ordinal < len(tests) else len(s)
        text = s[start:end]
        # Headers are separated from body duplicates by decorative rule lines or source metadata.
        ph = []
        for m in re.finditer(
            r"^(?:(?:TEST \d+)\s*[—|]\s*)?(?:READING )?PASSAGE ([123])[^\n]*", text, re.M
        ):
            line = m[0]
            before = text[max(0, m.start() - 180) : m.start()]
            if "ANSWER" in line.upper():
                continue
            if re.search(r"^[=─\-]{10,}\s*$", before, re.M) and (
                ":" in line or "—" in line or "|" in line
            ):
                ph.append(m)
        # Only the first body header for each passage, before terminal key.
        picked = []
        for n in [1, 2, 3]:
            cand = [
                m for m in ph if int(m[1]) == n and (not picked or m.start() > picked[-1].start())
            ]
            if cand:
                picked.append(cand[0])
        ps = []
        terminal_key = re.search(
            (
                "^.*(?:OFFICIAL (?:ACADEMIC )?READING ANSWER KEY|COMPLETE "
                "OFFICIAL READING ANSWER KEY|TEST \\d+ — ANSWER KEY|TEST \\d+ — "
                "OFFICIAL READING ANSWER KEY).*$"
            ),
            text,
            re.M,
        )
        for ix, m in enumerate(picked):
            pend = (
                picked[ix + 1].start()
                if ix + 1 < len(picked)
                else terminal_key.start()
                if terminal_key
                else len(text)
            )
            raw = text[m.end() : pend]
            pp = pages(raw)
            src = ref(
                f,
                s[: start + m.start()].count("\n") + 1,
                s[: start + pend].count("\n") + 1,
                pdf,
                pp,
            )
            ps.append(parse_passage(raw, m[0], f"{eid}-p-{int(m[1])}", src))
        transfers = []
        for passage in ps:
            expected = passage["source_question_range"]
            if expected:
                for group in passage["question_groups"]:
                    if not set(group["question_numbers"]) <= set(expected):
                        targets = [
                            p
                            for p in ps
                            if p["source_question_range"]
                            and set(group["question_numbers"]) <= set(p["source_question_range"])
                        ]
                        if len(targets) == 1:
                            transfers.append((passage, targets[0], group))
        for prior, target, group in transfers:
            prior["question_groups"].remove(group)
            group["id"] = group["id"].replace(prior["id"], target["id"], 1)
            for question in group["questions"]:
                question["group_id"] = group["id"]
            target["question_groups"].append(group)
        for passage in ps:
            passage["question_groups"].sort(key=lambda group: group["question_numbers"][0])
            passage["question_numbers"] = sorted(
                q["number"] for group in passage["question_groups"] for q in group["questions"]
            )
        keys, conflicts = answers_from(text)
        allqs = [q for p in ps for g in p["question_groups"] for q in g["questions"]]
        # Book 04 keys are trustworthy only as supplied, not attributed to absent key pages.
        keysrc = ref(
            f,
            s[:start].count("\n") + 1,
            s[:end].count("\n") + 1,
            pdf,
            pages(text[terminal_key.start() :]) if terminal_key else [],
        )
        keylist = [
            {
                "question_id": f"{eid}-q-{n:02}",
                "number": n,
                "canonical_answer": v,
                "accepted_answers": variants(v),
                "normalization_rules": [
                    "unicode_nfkc",
                    "casefold",
                    "trim",
                    "collapse_whitespace",
                    "normalize_apostrophe",
                    "numeric_thousands_separator",
                ],
                "grading_group": None,
                "source_reference": dict(keysrc),
                "verification_status": "transcribed_unverified",
                "grading": {"mode": "variants", "parts": []},
            }
            for n, v in sorted(keys.items())
        ]
        for keyitem in keylist:
            occurrences = list(
                re.finditer(
                    r"^[ \t]*0?"
                    + str(keyitem["number"])
                    + r"[.)][ \t]*"
                    + re.escape(keyitem["canonical_answer"])
                    + r"[ \t]*$",
                    text,
                    re.M,
                )
            )
            if occurrences:
                line = s[:start].count("\n") + text[: occurrences[-1].start()].count("\n") + 1
                keyitem["source_reference"]["line_start"] = line
                keyitem["source_reference"]["line_end"] = line
            raw_answer = keyitem["canonical_answer"]
            if "BOTH" in raw_answer.upper():
                body = re.sub(
                    r"\s*\[.*?\]|\s*\([^)]*(?:ORDER|REQUIRED)[^)]*\)", "", raw_answer, flags=re.I
                ).strip()
                parts = re.split(r"\s*(?:\+|\(and\)|\bAND\b)\s*", body, flags=re.I)
                if len(parts) > 1:
                    keyitem["grading"] = {
                        "mode": "unordered_parts",
                        "parts": [variants(part) for part in parts],
                    }
                    keyitem["accepted_answers"] = [
                        " ".join(part[0] for part in keyitem["grading"]["parts"])
                    ]
        for p in ps:
            for g in p["question_groups"]:
                if g["type"] == "multiple_choice_multiple":
                    groupkeys = [k for k in keylist if k["number"] in g["question_numbers"]]
                    if len(groupkeys) == len(g["question_numbers"]):
                        for k in groupkeys:
                            k["grading_group"] = {
                                "id": g["id"],
                                "mode": "unordered_unique",
                                "question_numbers": g["question_numbers"],
                            }
        for a, b in zip(keylist, keylist[1:]):
            if (
                a["number"] + 1 == b["number"]
                and "*" in a["canonical_answer"]
                and "*" in b["canonical_answer"]
                and not a["grading_group"]
                and not b["grading_group"]
            ):
                shared = {
                    "id": f"{eid}-grading-{a['number']:02}-{b['number']:02}",
                    "mode": "unordered_unique",
                    "question_numbers": [a["number"], b["number"]],
                }
                a["grading_group"] = shared
                b["grading_group"] = shared
        for line in text.splitlines():
            if re.search(r"(?:either|any) order", line, re.I) and "e.g." not in line:
                for pair in re.finditer(
                    r"(?:Q(?:uestions?\s*)?)?(\d{1,2})\s*(?:[-–—/]|and\s+Q?)\s*(\d{1,2})",
                    line,
                    re.I,
                ):
                    a, b = map(int, pair.groups())
                    if b != a + 1:
                        continue
                    members = [v for v in keylist if v["number"] in [a, b]]
                    if len(members) == 2 and all(v["grading_group"] is None for v in members):
                        group = {
                            "id": f"{eid}-grading-{a:02}-{b:02}",
                            "mode": "unordered_unique",
                            "question_numbers": [a, b],
                        }
                        for v in members:
                            v["grading_group"] = group
        grading_members = collections.defaultdict(list)
        for answer in keylist:
            if answer["grading_group"]:
                grading_members[answer["grading_group"]["id"]].append(answer)
        for members in grading_members.values():
            all_variants = {v for member in members for v in member["accepted_answers"]}
            if all(re.fullmatch(r"[A-Z]", v) for v in all_variants):
                units = [[v] for v in sorted(all_variants)]
            else:
                units = []
                for member in members:
                    masked = re.sub(
                        r"\([^()]*\)",
                        lambda m: m[0].replace("/", "\u0001"),
                        member["canonical_answer"],
                    )
                    primary = masked.split("/", 1)[0].replace("\u0001", "/")
                    units.append(variants(primary))
            for member in members:
                member["grading_group"]["expected_units"] = units
        exam = {
            "id": eid,
            "dataset_version": VERSION,
            "source_book": book_number,
            "source_test_number": tn,
            "test_ordinal": ordinal,
            "module": "academic_reading",
            "duration_seconds": 3600,
            "passages": ps,
            "question_count": len(allqs),
            "content_status": "needs_review",
            "source_verified": False,
            "verification": {
                "text": "transcribed_unverified",
                "questions": "transcribed_unverified",
                "keys": "transcribed_unverified",
            },
            "source_references": [
                ref(
                    f,
                    s[:start].count("\n") + 1,
                    s[:end].count("\n") + 1,
                    pdf,
                    sorted(set(n for p in ps for n in p["source_pages"])),
                )
            ],
        }
        for reference in (
            [exam["source_references"][0], keysrc]
            + [a["source_reference"] for a in keylist]
            + [p["source_reference"] for p in ps]
        ):
            reference["line_start"] = line_map.get(
                reference["line_start"], len(original.splitlines())
            )
            reference["line_end"] = line_map.get(reference["line_end"], len(original.splitlines()))
            reference["line_coordinate_space"] = "original_txt"
        out.append(
            (exam, {"exam_id": eid, "dataset_version": VERSION, "answers": keylist}, conflicts)
        )
    return out


def structural_issues(exam, keys, base):
    issues = []

    def add(code, detail, passage=None, question=None, pdf_pages=None):
        issues.append(
            {
                "code": code,
                "detail": detail,
                "exam_id": exam["id"],
                "book": exam["source_book"],
                "test": exam["source_test_number"],
                "passage": passage,
                "question": question,
                "pdf_pages": pdf_pages
                if pdf_pages is not None
                else exam["source_references"][0]["pdf_pages"],
            }
        )

    ps = exam["passages"]
    qs = [q for p in ps for g in p["question_groups"] for q in g["questions"]]
    ns = [q["number"] for q in qs]
    kn = [k["number"] for k in keys["answers"]]
    if len(ps) != 3:
        add("passage_count", f"Expected 3, found {len(ps)}")
    if sorted(ns) != list(range(1, 41)):
        add(
            "question_positions",
            f"Missing {sorted(set(range(1, 41)) - set(ns))}; "
            f"duplicate {[n for n, c in collections.Counter(ns).items() if c > 1]}",
        )
    if sorted(kn) != list(range(1, 41)):
        add("key_positions", f"Missing {sorted(set(range(1, 41)) - set(kn))}")
    for p in ps:
        expected_labels = required_labels(p)
        actual_labels = [block["label"] for block in p["content"] if block["label"]]
        missing_labels = expected_labels - set(actual_labels)
        if missing_labels:
            add(
                "paragraph_labels_missing",
                f"Source labels not recovered: {sorted(missing_labels)}",
                p["number"],
                p["question_numbers"],
                p["source_pages"],
            )
        repeated_labels = sorted(
            {label for label in actual_labels if actual_labels.count(label) > 1}
        )
        if repeated_labels:
            add(
                "paragraph_labels_ambiguous",
                f"Repeated labels need alignment: {repeated_labels}",
                p["number"],
                p["question_numbers"],
                p["source_pages"],
            )
        if p["source_question_range"] and p["question_numbers"] != p["source_question_range"]:
            add(
                "passage_question_range",
                "paragraph_labels_missing",
                "paragraph_labels_ambiguous",
                "Positions do not agree with the passage source instructions.",
                p["number"],
                p["question_numbers"],
                p["source_pages"],
            )
        if not p["content"]:
            add("empty_passage", "No passage text", p["number"])
        for g in p["question_groups"]:
            if g["type"] == "unknown":
                add(
                    "unknown_type",
                    "Task requires source classification",
                    p["number"],
                    g["question_numbers"],
                    p["source_pages"],
                )
            if not g["instructions"]:
                add("empty_instructions", "No instruction text", p["number"], g["question_numbers"])
            if g["type"] == "diagram_labelling" and not g["assets"]:
                add(
                    "missing_diagram",
                    "Source diagram not extracted",
                    p["number"],
                    g["question_numbers"],
                    p["source_pages"],
                )
            for a in g["assets"]:
                if not (base / a["path"]).is_file():
                    add("missing_asset", a["path"], p["number"], g["question_numbers"])
            if g["type"] == "multiple_choice_single":
                for q in g["questions"]:
                    if len(q["options"]) < 2 and not g["assets"]:
                        add(
                            "missing_options",
                            "Single choice lacks separate options",
                            p["number"],
                            q["number"],
                            p["source_pages"],
                        )
    return issues


def build(destination=DEST):
    inputs = sorted((ROOT / "ieltsReading").glob("*.txt"))
    sources = {
        str(f.relative_to(ROOT)): digest(f)
        for f in inputs + sorted((ROOT / "ieltsbooks").glob("*.pdf"))
    }
    entries = []
    issues = []
    stats = collections.Counter(
        {
            "exams": 0,
            "passages": 0,
            "questions": 0,
            "answers": 0,
            "ready": 0,
            "needs_review": 0,
            "blocked": 0,
            "structurally_valid": 0,
            "fully_converted": 0,
        }
    )
    types = collections.Counter()
    for f in inputs:
        for e, k, conflicts in parse_book(f):
            from enrich import content_issues, enrich_exam

            enrich_exam(e, k, destination)
            probs = structural_issues(e, k, destination)
            review = content_issues(e, k)
            issues += review
            critical = {
                "passage_count",
                "passage_question_range",
                "paragraph_labels_missing",
                "paragraph_labels_ambiguous",
                "question_positions",
                "key_positions",
                "empty_passage",
                "missing_diagram",
                "missing_options",
                "unknown_type",
            }
            e["content_status"] = (
                "blocked"
                if any(i["code"] in critical for i in probs)
                or any(
                    i["code"]
                    in {
                        "source_option_label_anomaly",
                        "source_required",
                        "source_obscured_by_watermark",
                        "layout_not_recovered",
                        "matching_options_missing",
                        "paragraph_labels_missing",
                        "paragraph_labels_ambiguous",
                    }
                    for i in review
                )
                else "needs_review"
            )
            issues += probs
            issues.append(
                {
                    "code": "source_proofreading_required",
                    "detail": (
                        "TXT content and official keys have not been fully checked "
                        "against local PDF page images."
                    ),
                    "exam_id": e["id"],
                    "book": e["source_book"],
                    "test": e["source_test_number"],
                    "passage": None,
                    "question": None,
                    "pdf_pages": e["source_references"][0]["pdf_pages"],
                }
            )
            for c in conflicts:
                issues.append({"code": "conflicting_key_transcriptions", "exam_id": e["id"], **c})
            b = f"cambridge_{e['source_book']:02}"
            name = f"test_{e['source_test_number']:02}.json"
            ep = f"exams/{b}/{name}"
            kp = f"answer_keys/{b}/{name}"
            write(destination / ep, e)
            write(destination / kp, k)
            entries.append(
                {
                    "id": e["id"],
                    "source_book": e["source_book"],
                    "source_test_number": e["source_test_number"],
                    "test_ordinal": e["test_ordinal"],
                    "exam_path": ep,
                    "answer_key_path": kp,
                    "content_status": e["content_status"],
                    "source_verified": e["source_verified"],
                    "passage_count": len(e["passages"]),
                    "question_count": e["question_count"],
                    "answer_count": len(k["answers"]),
                    "assets": [
                        a["path"]
                        for p in e["passages"]
                        for g in p["question_groups"]
                        for a in g["assets"]
                    ],
                    "sha256": digest(destination / ep),
                    "answer_key_sha256": digest(destination / kp),
                }
            )
            stats["exams"] += 1
            stats["passages"] += len(e["passages"])
            stats["questions"] += e["question_count"]
            stats["answers"] += len(k["answers"])
            stats[e["content_status"]] += 1
            stats["structurally_valid"] += not probs
            stats["fully_converted"] += not probs
            for p in e["passages"]:
                for g in p["question_groups"]:
                    types[g["type"]] += len(g["questions"])
    edits = json.loads(Path(__file__).with_name("source_edits.json").read_text())
    from labels import overlays

    edits += [
        dict(
            source_file=row["source_file"],
            location={"passage_id": row["passage_id"], "anchor": row["anchor"]},
            old_value=None,
            new_value=row["label"],
            pdf_file=row["pdf_file"],
            pdf_pages=[row["pdf_page"]],
            reason="Restore paragraph label from visually inspected original page image.",
            evidence={"crop_box": row["bbox"], "coordinate_system": "pdf_points_top_left"},
        )
        for row in overlays()
    ]
    from repairs import records

    edits += [dict(row, kind=kind) for kind, rows in records().items() for row in rows]
    from confirmed_hotfixes import materialize_assets
    from confirmed_hotfixes import records as confirmed_records

    hotfixes = confirmed_records()
    edits += [dict(row, kind="confirmed_fidelity_v1") for row in hotfixes["repairs"]]
    materialize_assets(hotfixes, destination)
    (destination / "corrections.jsonl").write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in edits), encoding="utf-8"
    )
    if sources != {
        str(f.relative_to(ROOT)): digest(f)
        for f in inputs + sorted((ROOT / "ieltsbooks").glob("*.pdf"))
    }:
        raise RuntimeError("Sources changed during build")
    generator = {
        p.name: digest(p)
        for p in sorted(Path(__file__).parent.iterdir())
        if p.suffix in {".py", ".json", ".txt"}
    }
    schema_hashes = {p.name: digest(p) for p in sorted((destination / "schema").glob("*.json"))}
    revision = hashlib.sha256(
        json.dumps(
            {
                "sources": sources,
                "exams": entries,
                "generator": generator,
                "schemas": schema_hashes,
                "retained_assets": hotfixes["retained_assets"],
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    write(
        destination / "manifest.json",
        {
            "dataset_version": VERSION,
            "content_revision": revision,
            "generator_sha256": generator,
            "schema_sha256": schema_hashes,
            "module": "academic_reading",
            "books": sorted({e["source_book"] for e in entries}),
            "sources": sources,
            "exams": entries,
            "retained_assets": hotfixes["retained_assets"],
        },
    )
    key_verification = collections.Counter(
        answer["verification_status"]
        for file in (destination / "answer_keys").rglob("*.json")
        for answer in json.loads(file.read_text())["answers"]
    )
    all_groups = [
        group
        for file in (destination / "exams").rglob("*.json")
        for passage in json.loads(file.read_text())["passages"]
        for group in passage["question_groups"]
    ]
    graphic_groups = [
        group
        for group in all_groups
        if group["type"] in {"table_completion", "diagram_labelling", "flow_chart_completion"}
        or re.search(r"following diagrams|following figures", group["instructions"], re.I)
    ]
    write(
        destination / "audit_report.json",
        {
            "counts": dict(stats),
            "question_types": dict(types),
            "source_verified": 0,
            "answer_verification": dict(key_verification),
            "source_integrity_verified": True,
            "schema_validation": (
                "run validator.py; generation via generate.py validates before publication"
            ),
            "graphics_found": len(graphic_groups),
            "graphics_extracted": sum(bool(group["assets"]) for group in graphic_groups),
            "png_assets_extracted": sum(len(item["assets"]) for item in entries),
            "question_groups_with_source_images": sum(
                bool(group["assets"]) for group in all_groups
            ),
            "graphic_count_definition": (
                "A graphic element is a question group requiring a table, diagram or flow-chart; "
                "multi-page crops count as one graphic group. PNG count also includes task-layout "
                "fallbacks."
            ),
            "paragraph_labels_restored": len(overlays()),
            "ocr_corrections": len(edits),
            "issues": issues,
        },
    )
    print(
        json.dumps(
            {
                "counts": dict(stats),
                "types": dict(types),
                "issues": collections.Counter(i["code"] for i in issues),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=DEST)
    from generate import generate

    generate(ap.parse_args().output)
