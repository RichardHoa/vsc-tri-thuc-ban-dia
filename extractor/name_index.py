"""
Story Name Index builder (one-off).

Turns the printed Bảng tra cứu tên truyện (PDF pages 1518–1551) into Index Name
records and resolves each target against the published Story markdown, so the
reader can highlight the name as the Story text spells it.

Each page's text layer is one column of tokens per record::

    <name, possibly wrapped>[, <qualifier>][ Chú thích]
    <Khảo dị | blank>
    số
    <story number>
    tập
    <Roman numeral>

A record may instead be a ``Xem <name>`` cross-reference with no number, or a
nameless continuation (location, số, number, tập, numeral) that adds a target
to the previous name. A "Chú thích" after the name (glued to it, on its own
line, or spilled onto the next page) means the name is in a Footnote.
"""

from __future__ import annotations

import difflib
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from .normalizer import TextNormalizer

ROMAN = {"I", "II", "III", "IV", "V"}
TAP_LABELS = {"tập", "tạp"}
STORY_NUMBER = re.compile(r"^\[?(\d+)\]?$")
QUALIFIER = re.compile(r"^(?P<name>.+?),\s*(?P<qualifier>truyện\b.*)$")
CHU_THICH_MARKER = re.compile(r",?\s*Chú thích$")
TRAILING_PARENTHETICAL = re.compile(r"\s*\([^()]*\)$")
STORY_FILE = re.compile(r"^story_(\d+)\.md$")

# Same delimiter and definition syntax the website's parseStoryMarkdown uses:
# the reader identifies a Footnote by the ordinal of its definition.
FOOTNOTE_SECTION = re.compile(r"\n-{3,}[ \t]*\n\s*#{2,3}[ \t]*Chú thích[ \t]*\n")
FOOTNOTE_DEFINITION = re.compile(r"^\[\^\d+\]:[ \t]?")
FOOTNOTE_MARKER = re.compile(r"\[\^\d+\]")

NAME_SEPARATOR = re.compile(r"[\s\-–—]+")
FUZZY_THRESHOLD = 0.9


@dataclass
class NameIndexResult:
    """Index Name records (the JSON shape), the targets left unresolved, and the
    targets resolved only by fuzzy match (worth a maintainer's look)."""
    names: List[dict]
    unresolved: List[dict] = field(default_factory=list)
    fuzzy: List[dict] = field(default_factory=list)


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------

def _page_tokens(page_text: str) -> List[str]:
    """Non-blank lines of one page, minus the page number and the first page's preamble."""
    lines = [TextNormalizer.normalize_encoding(l).strip() for l in page_text.splitlines()]
    lines = [l for l in lines if l]
    if lines and lines[0].isdigit():
        lines = lines[1:]
    if lines and lines[0].startswith("BẢNG TRA CỨU"):
        # Heading and intro paragraph: everything through the last sentence-final
        # line before the first record's "số".
        first_so = lines.index("số")
        prose_end = max(i for i in range(first_so) if lines[i].endswith("."))
        lines = lines[prose_end + 1:]
    return lines


def _join_name(lines: List[str]) -> str:
    name = ""
    for line in lines:
        if not name or name.endswith("-"):
            name += line
        else:
            name += " " + line
    return re.sub(r"\s+", " ", name).strip()


def _split_qualifier(name: str) -> Tuple[str, Optional[str]]:
    match = QUALIFIER.match(name)
    if not match:
        return name, None
    return match.group("name").strip(), match.group("qualifier").strip()


def _split_line_qualifier(lines: List[str], name: str) -> Tuple[str, Optional[str]]:
    """A comma-less qualifier that starts its own line ("Gái ngoan dạy chồn" /
    "truyện Nam Trung Bộ"), or whose "truyện" ends the line before ("Khiên Ngưu
    Chức Nữ truyện" / "khác")."""
    for k in range(1, len(lines)):
        if lines[k].startswith("truyện ") and not lines[k - 1].endswith(" là"):  # "X hay là / truyện Y"
            return _join_name(lines[:k]), _join_name(lines[k:])
    if len(lines) >= 2 and lines[-2].endswith(" truyện") and not lines[-2].endswith(" là truyện"):
        head = lines[:-2] + [lines[-2][:-len(" truyện")]]
        return _join_name(head), "truyện " + lines[-1]
    return name, None


def _strip_chu_thich_marker(lines: List[str]) -> bool:
    """Removes a trailing "Chú thích" marker from the name lines; True when there was one."""
    if not lines:
        return False
    stripped = CHU_THICH_MARKER.sub("", lines[-1])
    if stripped == lines[-1]:
        return False
    if stripped:
        lines[-1] = stripped
    else:
        lines.pop()
    return True


def parse_index_pages(page_texts: Iterable[str]) -> List[dict]:
    """Index records in printed order; aliases carry ``aliasOf`` and no targets yet."""
    rows: List[dict] = []  # {"lines", "alias", "targets"} before the name is finalised
    buffer: List[str] = []
    for page in page_texts:
        tokens = _page_tokens(page)
        # A row can spill its last name line, or its "Chú thích" marker, onto the
        # top of the next page; a new name never starts lowercase.
        if not buffer and rows and tokens and tokens[0] != "số" and not tokens[0].startswith("Xem "):
            if tokens[0] == "Chú thích" and rows[-1]["targets"]:
                rows[-1]["targets"][-1]["location"] = "chu-thich"
                tokens = tokens[1:]
            elif tokens[0][:1].islower():
                rows[-1]["lines"].append(tokens[0])
                tokens = tokens[1:]

        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.startswith("Xem "):
                rows.append({"lines": buffer, "alias": token[4:].strip(), "targets": []})
                buffer = []
                i += 1
                continue
            if token != "số":
                buffer.append(token)
                i += 1
                continue

            location = "story"
            if buffer and buffer[-1] == "Khảo dị":
                buffer.pop()
                location = "khao-di"
            if _strip_chu_thich_marker(buffer):
                location = "chu-thich"  # a Footnote (usually of the Khảo dị)
            # The print is not always clean: "[50]", a stray or misplaced "tập"/"tạp",
            # or no number at all. A row without both a number and a Tập keeps its
            # name but gets no target, and is reported.
            number: Optional[int] = None
            tap: Optional[str] = None
            i += 1
            while i < len(tokens):
                if tokens[i] in TAP_LABELS:
                    i += 1
                elif number is None and STORY_NUMBER.match(tokens[i]):
                    number = int(STORY_NUMBER.match(tokens[i]).group(1))
                    i += 1
                else:
                    if tokens[i] in ROMAN:
                        tap = tokens[i]
                        i += 1
                    break
            if buffer:
                rows.append({"lines": buffer, "alias": None, "targets": []})
            elif not rows:
                raise ValueError("Index starts with a nameless continuation record")
            if number is not None and tap is not None:
                rows[-1]["targets"].append({"story": number, "tap": tap, "location": location})
            buffer = []

    records = []
    for row in rows:
        printed, qualifier = _split_qualifier(_join_name(row["lines"]))
        if not qualifier:
            printed, qualifier = _split_line_qualifier(row["lines"], printed)
        record: dict = {"printed": printed}
        if qualifier:
            record["qualifier"] = qualifier
        if row["alias"]:
            record["aliasOf"] = row["alias"]
        record["targets"] = row["targets"]
        records.append(record)
    return records


# --------------------------------------------------------------------------
# Resolving
# --------------------------------------------------------------------------

def _fold_char(ch: str) -> str:
    """One character, lowercased, diacritics removed, đ → d (length-preserving)."""
    if ch in "đĐ":
        return "d"
    return unicodedata.normalize("NFD", ch)[0].lower()


def _fold(text: str) -> str:
    return "".join(_fold_char(ch) for ch in text)


def _name_pattern(name: str) -> re.Pattern:
    words = [w for w in NAME_SEPARATOR.split(name) if w]
    body = r"[\s\-–—]+".join(re.escape(w) for w in words)
    return re.compile(rf"(?<!\w){body}(?!\w)", re.IGNORECASE)


def _find_exact(text: str, name: str) -> Optional[str]:
    """Case-insensitive, whitespace and hyphens loosened, whole name only."""
    match = _name_pattern(name).search(text)
    return match.group(0) if match else None


def _find_folded(text: str, name: str) -> Optional[str]:
    """As exact, but also ignoring diacritics, with đ and d alike."""
    match = _name_pattern(_fold(name)).search(_fold(text))
    return text[match.start():match.end()] if match else None


def _find_fuzzy(text: str, name: str) -> Optional[str]:
    """The best window of about the same word count (±1, as a word may be missing
    or split differently), if it scores at least FUZZY_THRESHOLD."""
    target_words = [w for w in NAME_SEPARATOR.split(_fold(name)) if w]
    n = len(target_words)
    words = list(re.finditer(r"\w+", _fold(text)))
    best: Tuple[float, int, int] = (0.0, 0, 0)
    matcher = difflib.SequenceMatcher(autojunk=False)
    matcher.set_seq2(" ".join(target_words))
    for size in (n, n - 1, n + 1):
        if size < 1:
            continue
        for start in range(len(words) - size + 1):
            matcher.set_seq1(" ".join(m.group(0) for m in words[start:start + size]))
            if matcher.real_quick_ratio() < FUZZY_THRESHOLD or matcher.quick_ratio() < FUZZY_THRESHOLD:
                continue
            ratio = matcher.ratio()
            if ratio > best[0]:
                best = (ratio, words[start].start(), words[start + size - 1].end())
    return text[best[1]:best[2]] if best[0] >= FUZZY_THRESHOLD else None


FINDERS = (_find_exact, _find_folded, _find_fuzzy)


@dataclass
class _Story:
    body: str
    footnotes: List[str]


def _load_story(path: str) -> _Story:
    with open(path, encoding="utf-8") as f:
        raw = unicodedata.normalize("NFC", f.read().replace("\r\n", "\n"))
    split = FOOTNOTE_SECTION.search(raw)
    body = raw[:split.start()] if split else raw
    footnotes: List[List[str]] = []
    if split:
        for line in raw[split.end():].split("\n"):
            if FOOTNOTE_DEFINITION.match(line):
                footnotes.append([FOOTNOTE_DEFINITION.sub("", line)])
            elif footnotes:
                footnotes[-1].append(line.strip())
    return _Story(
        body=FOOTNOTE_MARKER.sub(" ", body),  # a marker can be glued to the next word
        footnotes=[" ".join(lines).strip() for lines in footnotes],
    )


def _story_files(story_dir: str) -> Dict[int, str]:
    files: Dict[int, str] = {}
    for dirpath, _, filenames in os.walk(story_dir):
        for filename in filenames:
            match = STORY_FILE.match(filename)
            if match:
                files[int(match.group(1))] = os.path.join(dirpath, filename)
    return files


def _search_names(printed: str) -> List[str]:
    """The printed name, then (as a fallback) without a trailing parenthetical."""
    names = [printed]
    bare = TRAILING_PARENTHETICAL.sub("", printed)
    if bare and bare != printed:
        names.append(bare)
    return names


def _resolve(target: dict, printed: str, story: _Story) -> Optional[str]:
    """Sets ``textName`` (and ``footnote``) from the strictest tier that finds the name,
    and returns that tier's finder name (None when not found).

    A Chú thích target searches the Footnotes before the body; other targets the
    body first. Within a tier, the first text in that order wins.
    """
    footnotes = [(text, str(ordinal)) for ordinal, text in enumerate(story.footnotes, start=1)]
    body = [(story.body, None)]
    texts = footnotes + body if target["location"] == "chu-thich" else body + footnotes
    for finder in FINDERS:
        for name in _search_names(printed):
            for text, footnote in texts:
                found = finder(text, name)
                if found:
                    target["textName"] = found
                    if footnote and target["location"] == "chu-thich":
                        target["footnote"] = footnote
                    return finder.__name__
    return None


def _report_row(record: dict, reason: str, target: Optional[dict] = None) -> dict:
    return {
        "printed": record["printed"],
        "qualifier": record.get("qualifier"),
        "story": target["story"] if target else None,
        "location": target["location"] if target else None,
        "textName": target.get("textName") if target else None,
        "reason": reason,
    }


def _alias_key(name: str) -> str:
    return " ".join(w for w in NAME_SEPARATOR.split(_fold(name)) if w)


def build_name_index(page_texts: Iterable[str], story_dir: str) -> NameIndexResult:
    """Parses the index pages and resolves every target against ``story_dir``'s Story markdown.

    ``story_dir`` is searched recursively for ``story_NNN.md`` files (the
    website's published Kho Tàng data). A target's ``footnote`` is the 1-based
    ordinal (as a string) of the Footnote definition under "Chú thích" that holds
    the name, i.e. the reader's 0-based ``#fn-i`` index plus one.
    """
    records = parse_index_pages(page_texts)
    files = _story_files(story_dir)
    stories: Dict[int, _Story] = {}
    unresolved: List[dict] = []
    fuzzy: List[dict] = []

    for record in records:
        if "aliasOf" not in record and not record["targets"]:
            unresolved.append(_report_row(record, "no Story number printed"))
        for target in record["targets"]:
            number = target["story"]
            if number not in stories and number in files:
                stories[number] = _load_story(files[number])
            tier = _resolve(target, record["printed"], stories[number]) if number in stories else None
            if tier is None:
                reason = "name not found in Story text" if number in files else "Story file missing"
                unresolved.append(_report_row(record, reason, target))
            elif tier == _find_fuzzy.__name__:
                fuzzy.append(_report_row(record, "fuzzy match", target))

    # "Xem X" names X in full, or only the first half of an "X hay là Y" name.
    by_name: Dict[str, List[dict]] = {}
    by_first_half: Dict[str, List[dict]] = {}
    for record in records:
        if "aliasOf" not in record:
            by_name.setdefault(_alias_key(record["printed"]), []).append(record)
            first_half = record["printed"].split(" hay là ")[0]
            by_first_half.setdefault(_alias_key(first_half), []).append(record)
    for record in records:
        if "aliasOf" in record:
            key = _alias_key(record["aliasOf"])
            for named in by_name.get(key) or by_first_half.get(key, []):
                record["targets"].extend(dict(t) for t in named["targets"])
            if not record["targets"]:
                unresolved.append(_report_row(record, f"Xem target not in index: {record['aliasOf']}"))

    return NameIndexResult(names=records, unresolved=unresolved, fuzzy=fuzzy)
