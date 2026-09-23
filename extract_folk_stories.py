#!/usr/bin/env python3
"""
Folk Story & Footnote Extractor for Vietnamese Folk Tales (data.pdf)
--------------------------------------------------------------------
Extracts structured stories, Roman numeral category headers, KHẢO DỊ sections,
and linked footnotes from data.pdf into clean individual Markdown files and
a hierarchical Table of Contents JSON (table_of_contents.json).

Features:
- Automated discovery and segmentation of Roman numeral category headers (I to X)
- Sequential story detection, boundary calculation, and metadata parsing
- Clean Markdown generation per story (story_001.md, story_002.md, ...)
- Strict exclusion of page numbers, running headers, cover page noise, and dividers
- Scoped footnote numbering ([^1], [^2], ...) per story with superscript span detection
- Hierarchical Table of Contents JSON mapping sections to stories and page ranges
"""

import os
import sys
import re
import json
import argparse
import fitz  # PyMuPDF

def fix_vietnamese_encoding(text: str) -> str:
    """Fix legacy encoding artifacts in the PDF text layer."""
    replacements = {
        'ñ': 'đ',
        'Ñ': 'Đ',
        'Ð': 'Đ',
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

def clean_inline_spaces(text: str) -> str:
    """Normalize whitespace and clean punctuation spacing."""
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r' +([,.;:!?])', r'\1', text)
    text = re.sub(r'“\s+', '“', text)
    text = re.sub(r'\s+”', '”', text)
    # Fix hyphenated words with broken spaces across lines (e.g. TRÓI- CỘT -> TRÓI-CỘT)
    text = re.sub(r'(\w+)-\s+(\w+)', r'\1-\2', text)
    # Ensure dialogue dash has a space following it
    if text.startswith('-') and not text.startswith('- '):
        text = '- ' + text[1:].lstrip()
    return text.strip()

def find_footer_separator_y(page) -> float:
    """
    Finds the y-coordinate of the horizontal separator line
    that precedes the footnote/footer on a page.
    """
    drawings = page.get_drawings()
    for d in drawings:
        r = d.get('rect')
        if r and r.height < 3 and r.width > 30 and r.y0 > 500:
            return float(r.y0)
    return None

def parse_multiple_footnotes(text: str, page_num: int) -> list:
    """
    Splits text blocks that may contain one or multiple numbered footnotes.
    Example: '1 Theo Bản khai...  2 Theo Truyện cổ...'
    """
    items = []
    pattern = r'(?:^|\s+)(\d+)\s+(.+?)(?=(?:\s+\d+\s+[A-ZÀ-Ỵ\"])|\Z)'
    for m in re.finditer(pattern, text.strip(), re.DOTALL):
        num = int(m.group(1))
        content = clean_inline_spaces(m.group(2))
        items.append({
            'orig_num': num,
            'page': page_num,
            'text': content
        })
    return items

def is_all_caps(text: str) -> bool:
    """Checks if a string contains letters and all letters are uppercase."""
    letters = re.sub(r'[^a-zA-Zà-ỹÀ-Ỹ]', '', text)
    return bool(letters) and letters.isupper()

def discover_stories(doc, start_page: int, end_page: int):
    """
    Scans PDF pages to discover Roman category headers and story titles,
    calculating precise page ranges for each story.
    """
    roman_header_pat = re.compile(r'^([IVXLCDM]+)\.\s+([A-ZÀ-Ỵ\s\-]+)$')
    story_title_pat = re.compile(r'^(\d+)\.\s+(.+)$')

    story_definitions = []
    current_roman = "I. NGUỒN GỐC SỰ VẬT"

    # Search up to end_page + 5 to ensure we detect the next story/section boundary
    max_scan_page = min(len(doc), end_page + 5)

    for pno in range(start_page - 1, max_scan_page):
        pnum = pno + 1
        page = doc[pno]
        page_dict = page.get_text('dict')
        blocks = page_dict.get('blocks', [])
        blocks.sort(key=lambda b: (b['bbox'][1], b['bbox'][0]))

        for b_idx, b in enumerate(blocks):
            if b.get('type') != 0:
                continue
            y0 = b['bbox'][1]
            if y0 > 220 or y0 < 50:
                continue

            full_text = fix_vietnamese_encoding(' '.join(''.join(s['text'] for s in l['spans']).strip() for l in b['lines']))
            full_text = clean_inline_spaces(full_text)

            # Check Roman numeral header (e.g. 'I. NGUỒN GỐC SỰ VẬT')
            m_rom = roman_header_pat.match(full_text)
            if m_rom:
                current_roman = full_text
                continue

            # Check Story Title (e.g. '1. SỰ TÍCH DƯA HẤU')
            m_st = story_title_pat.match(full_text)
            if m_st:
                snum = int(m_st.group(1))
                stitle = m_st.group(2).strip()
                # Remove trailing footnote digits or inline footnote numbers in title
                stitle_clean = re.sub(r'(\d+)\s*$', '', stitle).strip()
                stitle_clean = re.sub(r'([A-ZÀ-Ỵ])\d+(\s+)', r'\1\2', stitle_clean)
                if is_all_caps(stitle_clean):
                    story_definitions.append({
                        'story_number': snum,
                        'title': stitle_clean,
                        'category': current_roman,
                        'start_page': pnum,
                        'start_y0': y0
                    })

    # Select stories that start on or before end_page
    selected_stories = [s for s in story_definitions if s['start_page'] <= end_page]

    # Calculate end_page for each selected story
    for i, s in enumerate(selected_stories):
        # Look at the subsequent story definition in story_definitions
        idx_in_all = story_definitions.index(s)
        if idx_in_all + 1 < len(story_definitions):
            next_s = story_definitions[idx_in_all + 1]
            # If the next story starts at the top of next page (y0 < 150), this story ends on previous page
            s['end_page'] = next_s['start_page'] - 1
        else:
            s['end_page'] = min(len(doc), s['start_page'] + 4)

    return selected_stories

def extract_single_story(doc, story_info: dict) -> dict:
    """
    Extracts body text, dialogues, KHẢO DỊ section, and footnotes for a single story.
    Footnotes are locally re-indexed from [^1] without page numbers.
    """
    start_page = story_info['start_page']
    end_page = story_info['end_page']

    # 1. Pass 1: Collect footnotes belonging to this story's page range
    page_footnotes = {}
    all_footnotes = []
    global_fn_counter = 0

    for pno in range(start_page - 1, end_page):
        page = doc[pno]
        page_num = pno + 1
        page_footnotes[page_num] = []

        h_sep_y = find_footer_separator_y(page)
        blocks = page.get_text('blocks')
        blocks.sort(key=lambda b: (b[1], b[0]))

        for b in blocks:
            if b[1] > 745:  # skip bottom page number
                continue
            is_fn = (h_sep_y is not None and b[1] >= (h_sep_y - 25)) or \
                    (h_sep_y is None and b[1] > 680 and re.match(r'^\d+\s+[A-ZÀ-Ỵ]', b[4].strip()))

            if is_fn:
                fixed_text = fix_vietnamese_encoding(b[4].replace('\n', ' '))
                parsed_list = parse_multiple_footnotes(fixed_text, page_num)
                if not parsed_list and fixed_text.strip():
                    parsed_list = [{'orig_num': 1, 'page': page_num, 'text': clean_inline_spaces(fixed_text)}]

                for fn in parsed_list:
                    global_fn_counter += 1
                    fn_item = {
                        'id': global_fn_counter,
                        'orig_num': fn['orig_num'],
                        'page': page_num,
                        'text': fn['text']
                    }
                    page_footnotes[page_num].append(fn_item)
                    all_footnotes.append(fn_item)

    # 2. Pass 2: Extract structured story content
    paragraphs = []
    khao_di_paragraphs = []
    in_khao_di = False
    current_para = []

    def flush_para():
        nonlocal current_para, in_khao_di
        if current_para:
            p_text = clean_inline_spaces(' '.join(current_para))
            if p_text:
                if in_khao_di:
                    khao_di_paragraphs.append(p_text)
                else:
                    paragraphs.append(p_text)
            current_para = []

    for pno in range(start_page - 1, end_page):
        page = doc[pno]
        page_num = pno + 1
        h_sep_y = find_footer_separator_y(page)

        page_dict = page.get_text('dict')
        page_blocks = page_dict.get('blocks', [])
        page_blocks.sort(key=lambda b: (b['bbox'][1], b['bbox'][0]))

        for b in page_blocks:
            if b.get('type') != 0:
                continue

            y0 = b['bbox'][1]
            if y0 > 745 or y0 < 60:  # skip running header and bottom page number
                continue

            # Skip footer block
            if (h_sep_y is not None and y0 >= (h_sep_y - 25)) or \
               (h_sep_y is None and y0 > 680 and re.match(r'^\d+\s+[A-ZÀ-Ỵ]', ''.join(s['text'] for l in b['lines'] for s in l['spans']).strip())):
                continue

            # Reconstruct lines with inline footnote superscripts
            block_lines = []
            for l in b['lines']:
                line_text = ''
                for s in l['spans']:
                    stext = fix_vietnamese_encoding(s['text'])
                    # Footnote superscript detection
                    if s['size'] < 10.0 and stext.strip().isdigit() and y0 < 700:
                        fn_num = int(stext.strip())
                        matched_fn = next((f for f in page_footnotes.get(page_num, []) if f['orig_num'] == fn_num), None)
                        if matched_fn:
                            line_text += f"[^{matched_fn['id']}]"
                        else:
                            line_text += f"[^{fn_num}]"
                    else:
                        line_text += stext

                clean_l = clean_inline_spaces(line_text)
                if clean_l:
                    block_lines.append(clean_l)

            if not block_lines:
                continue

            combined_block_text = ' '.join(block_lines)

            # Skip Roman section header or Story Title block on start_page
            if pno == start_page - 1:
                if re.match(r'^[IVXLCDM]+\.\s+[A-ZÀ-Ỵ\s\-]+$', combined_block_text):
                    continue
                if re.match(r'^\d+\.\s+[A-ZÀ-Ỵ]', combined_block_text) and is_all_caps(re.sub(r'^\d+\.\s*', '', combined_block_text)):
                    continue

            # Check KHẢO DỊ Header
            if combined_block_text.strip().upper() == 'KHẢO DỊ':
                flush_para()
                in_khao_di = True
                continue

            # Skip scene dividers (* or * * *)
            if re.match(r'^[\*\s]+$', combined_block_text):
                flush_para()
                continue

            # Dialogue or numbered point
            is_dialogue = combined_block_text.startswith('-')
            is_numbered_point = bool(re.match(r'^\d+\.\s+', combined_block_text))

            if is_dialogue or is_numbered_point:
                flush_para()
                if in_khao_di:
                    khao_di_paragraphs.append(combined_block_text)
                else:
                    paragraphs.append(combined_block_text)
            else:
                if current_para:
                    prev_text = current_para[-1]
                    if not re.search(r'[.!?]["”\']?(\[\^\d+\])?$', prev_text.strip()):
                        current_para.append(combined_block_text)
                    else:
                        flush_para()
                        current_para = [combined_block_text]
                else:
                    current_para = [combined_block_text]

    flush_para()

    return {
        'category': story_info['category'],
        'story_number': story_info['story_number'],
        'title': story_info['title'],
        'start_page': start_page,
        'end_page': end_page,
        'paragraphs': paragraphs,
        'khao_di': khao_di_paragraphs,
        'footnotes': all_footnotes
    }

def format_markdown(story_data: dict) -> str:
    """
    Formats extracted story data into clean Markdown without page numbers.
    """
    lines = []
    if story_data.get('category'):
        lines.append(f"# {story_data['category']}\n")
    if story_data.get('title'):
        lines.append(f"## {story_data['story_number']}. {story_data['title']}\n")

    # Format story paragraphs
    for p in story_data.get('paragraphs', []):
        lines.append(f"{p}\n")

    # Format KHẢO DỊ section if present
    if story_data.get('khao_di'):
        lines.append("### KHẢO DỊ\n")
        for p in story_data['khao_di']:
            lines.append(f"{p}\n")

    # Format Footnotes (clean without page numbers)
    if story_data.get('footnotes'):
        lines.append("---\n")
        lines.append("### Chú thích\n")
        for fn in story_data['footnotes']:
            lines.append(f"[^{fn['id']}]: {fn['text']}\n")

    return "\n".join(lines)

def build_toc_json(sections_map: dict, total_stories: int, range_str: str) -> dict:
    """Builds hierarchical Table of Contents dictionary."""
    sections_list = []
    for sec_title, stories in sections_map.items():
        sec_id_match = re.match(r'^([IVXLCDM]+)\.', sec_title)
        sec_id = sec_id_match.group(1) if sec_id_match else "OTHER"
        sections_list.append({
            'section_id': sec_id,
            'section_title': sec_title,
            'stories': stories
        })

    return {
        'book_title': 'KHO TÀNG TRUYỆN CỔ TÍCH VIỆT-NAM',
        'extracted_range': range_str,
        'total_stories': total_stories,
        'sections': sections_list
    }

def batch_extract(pdf_path: str, start_page: int, end_page: int, output_dir: str):
    """Executes full extraction pipeline from start_page to end_page."""
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)

    print(f"Discovering stories between page {start_page} and {end_page}...")
    stories_info = discover_stories(doc, start_page, end_page)
    print(f"Discovered {len(stories_info)} stories.")

    sections_map = {}
    actual_max_page = start_page

    for info in stories_info:
        story_num = info['story_number']
        cat = info['category']
        if cat not in sections_map:
            sections_map[cat] = []

        print(f"Extracting Story #{story_num:03d}: {info['title']} (Pages {info['start_page']} - {info['end_page']})...")
        story_data = extract_single_story(doc, info)

        actual_max_page = max(actual_max_page, story_data['end_page'])
        md_filename = f"story_{story_num:03d}.md"
        md_path = os.path.join(output_dir, md_filename)

        md_content = format_markdown(story_data)
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        sections_map[cat].append({
            'story_number': story_num,
            'title': info['title'],
            'start_page': story_data['start_page'],
            'end_page': story_data['end_page'],
            'markdown_file': md_filename,
            'has_khao_di': len(story_data['khao_di']) > 0,
            'footnote_count': len(story_data['footnotes'])
        })

    # Save Table of Contents JSON
    toc_data = build_toc_json(sections_map, len(stories_info), f"{start_page} - {actual_max_page}")
    toc_path = os.path.join(output_dir, "table_of_contents.json")
    with open(toc_path, 'w', encoding='utf-8') as f:
        json.dump(toc_data, f, ensure_ascii=False, indent=2)

    doc.close()
    print(f"\nExtraction complete!")
    print(f"- Total stories extracted: {len(stories_info)}")
    print(f"- Table of contents saved to: {toc_path}")
    print(f"- Markdown files saved in: {output_dir}")
    return toc_data

def main():
    parser = argparse.ArgumentParser(description="Extract Vietnamese Folk Tales and Table of Contents from data.pdf")
    parser.add_argument("--pdf", default="data.pdf", help="Path to data.pdf")
    parser.add_argument("--start-page", type=int, default=86, help="Start page number (1-based)")
    parser.add_argument("--end-page", type=int, default=200, help="End page number (1-based)")
    parser.add_argument("--output-dir", default="extracted_stories", help="Output directory")

    args = parser.parse_args()
    batch_extract(args.pdf, args.start_page, args.end_page, args.output_dir)

if __name__ == "__main__":
    main()
