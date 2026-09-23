"""
PDF Geometry & Coordinate Filtering Helper.
"""

from __future__ import annotations

import re
from typing import Optional
import fitz  # PyMuPDF


class PdfGeometryHelper:
    """Provides coordinate-based filtering for headers, footers, and scene dividers."""

    SCENE_DIVIDER_PAT = re.compile(r'^[\*\-\s]+$')

    @staticmethod
    def find_footer_separator_y(page: fitz.Page) -> Optional[float]:
        """Finds y-coordinate of the horizontal separator line preceding footnotes."""
        for drawing in page.get_drawings():
            rect = drawing.get('rect')
            if (rect and rect.height < 3.0 and rect.width > 30.0
                    and rect.x0 < 120.0 and 200.0 < rect.y0 < 745.0):
                return float(rect.y0)
        return None

    @staticmethod
    def is_header_block(y0: float, min_header_y: float) -> bool:
        """Identifies running header blocks at the top of the page."""
        return y0 < min_header_y

    @staticmethod
    def is_header_line(y0: float, min_header_y: float) -> bool:
        """Identifies running header lines at the top of the page."""
        return y0 < min_header_y

    @staticmethod
    def is_footer_block(
        y0: float,
        block_text: str,
        h_sep_y: Optional[float],
        max_footer_y: float,
        footer_fallback_y: float
    ) -> bool:
        """Identifies footer / footnote blocks at the bottom of the page."""
        if y0 > max_footer_y:
            return True
        if h_sep_y is not None:
            return y0 >= (h_sep_y - 20.0)
        # Fallback when no drawn separator line exists
        return y0 > footer_fallback_y and bool(re.match(r'^\d+[\.\s]+[A-ZÀ-Ỵ]', block_text.strip()))

    @staticmethod
    def is_footer_line(
        y0: float,
        line_text: str,
        h_sep_y: Optional[float],
        max_footer_y: float,
        footer_fallback_y: float
    ) -> bool:
        """Identifies footer / footnote lines at the bottom of the page."""
        if y0 > max_footer_y:
            return True
        if h_sep_y is not None:
            return y0 >= (h_sep_y - 5.0)
        return y0 > footer_fallback_y and bool(re.match(r'^\d+[\.\s]+[A-ZÀ-Ỵ]', line_text.strip()))

    @classmethod
    def is_scene_divider(cls, text: str) -> bool:
        """Detects scene divider markers like * or * * *."""
        return bool(cls.SCENE_DIVIDER_PAT.match(text.strip()))
