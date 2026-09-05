import unittest
import re
from pathlib import Path

ROOT_DIR = Path(__file__).parent
FRONTEND_DIR = ROOT_DIR / "frontend"
SRC_DIR = FRONTEND_DIR / "src"
STYLES_FILE = SRC_DIR / "styles.css"


def parse_hex_color(hex_str: str):
    hex_str = hex_str.strip().lstrip('#')
    if len(hex_str) == 3:
        hex_str = ''.join([c * 2 for c in hex_str])
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    return r, g, b


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_str: str) -> float:
    r, g, b = parse_hex_color(hex_str)
    rl = srgb_to_linear(r)
    gl = srgb_to_linear(g)
    bl = srgb_to_linear(b)
    return 0.2126 * rl + 0.7152 * gl + 0.0722 * bl


def contrast_ratio(hex1: str, hex2: str) -> float:
    l1 = relative_luminance(hex1)
    l2 = relative_luminance(hex2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


class TestFrontendAccessibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css_content = STYLES_FILE.read_text(encoding="utf-8")
        cls.jsx_files = list(SRC_DIR.rglob("*.jsx"))
        cls.jsx_contents = {f.name: f.read_text(encoding="utf-8") for f in cls.jsx_files}

    def test_text_muted_contrast_meets_wcag_aa(self):
        muted_match = re.search(r'--text-muted:\s*(#[0-9a-fA-F]{3,6});', self.css_content)
        self.assertTrue(muted_match, "Could not find --text-muted in styles.css")
        muted_hex = muted_match.group(1)
        white_bg = "#FFFFFF"
        ratio = contrast_ratio(muted_hex, white_bg)
        self.assertGreaterEqual(
            ratio,
            4.5,
            f"--text-muted ({muted_hex}) on {white_bg} ratio is {ratio:.2f}:1, fails WCAG AA (>= 4.5:1)!"
        )

    def test_text_secondary_contrast_meets_wcag_aa(self):
        sec_match = re.search(r'--text-secondary:\s*(#[0-9a-fA-F]{3,6});', self.css_content)
        self.assertTrue(sec_match, "Could not find --text-secondary in styles.css")
        sec_hex = sec_match.group(1)
        ratio = contrast_ratio(sec_hex, "#FFFFFF")
        self.assertGreaterEqual(ratio, 4.5)

    def test_status_text_contrast_on_tinted_backgrounds(self):
        status_pairs = [
            ("warning", "--status-warning", "--status-warning-bg", 4.5),
            ("danger", "--status-danger", "--status-danger-bg", 4.5),
            ("success", "--status-success", "--status-success-bg", 4.5),
        ]
        for name, text_var, bg_var, min_ratio in status_pairs:
            text_match = re.search(rf'{text_var}:\s*(#[0-9a-fA-F]{{3,6}});', self.css_content)
            bg_match = re.search(rf'{bg_var}:\s*(#[0-9a-fA-F]{{3,6}});', self.css_content)
            self.assertTrue(text_match, f"Missing {text_var}")
            self.assertTrue(bg_match, f"Missing {bg_var}")
            ratio = contrast_ratio(text_match.group(1), bg_match.group(1))
            self.assertGreaterEqual(ratio, min_ratio)

    def test_focus_visible_rule_exists_with_offset(self):
        self.assertIn(":focus-visible", self.css_content)
        self.assertIn("outline-offset", self.css_content)
        self.assertIn("outline:", self.css_content)

    def test_skip_link_exists_and_styled(self):
        self.assertIn(".skip-link", self.css_content)
        self.assertIn(".skip-link:focus", self.css_content)
        app_jsx = self.jsx_contents["App.jsx"]
        self.assertIn('className="skip-link"', app_jsx)
        self.assertIn('href="#main-content"', app_jsx)

    def test_reduced_motion_media_query_present(self):
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.css_content)

    def test_screen_reader_utility_class_present(self):
        self.assertIn(".sr-only", self.css_content)
        self.assertIn("clip: rect(0, 0, 0, 0)", self.css_content)

    def test_minimum_interactive_target_sizing(self):
        self.assertIn("min-height: 36px", self.css_content)
        self.assertIn("min-width: 36px", self.css_content)

    def test_inputs_have_associated_labels_or_aria_labels(self):
        input_tag_pattern = re.compile(r'<(input|textarea|select)\b([^>]*)>', re.DOTALL | re.IGNORECASE)
        for filename, content in self.jsx_contents.items():
            for match in input_tag_pattern.finditer(content):
                tag_name = match.group(1)
                tag_attrs = match.group(2)
                input_id_match = re.search(r'id=["\']([^"\']+)["\']', tag_attrs)
                has_aria_label = 'aria-label=' in tag_attrs or 'aria-labelledby=' in tag_attrs
                if input_id_match:
                    input_id = input_id_match.group(1)
                    has_matching_label = f'htmlFor="{input_id}"' in content or f"htmlFor='{input_id}'" in content
                else:
                    has_matching_label = False
                self.assertTrue(
                    has_matching_label or has_aria_label,
                    f"File {filename} contains <{tag_name}> without associated <label htmlFor=...> or aria-label! Attributes: {tag_attrs.strip()}"
                )

    def test_modals_have_dialog_role_and_modal_attributes(self):
        for modal_file in ["HelpModal.jsx", "SettingsModal.jsx"]:
            content = self.jsx_contents[modal_file]
            self.assertIn('role="dialog"', content, f"{modal_file} missing role='dialog'")
            self.assertIn('aria-modal="true"', content, f"{modal_file} missing aria-modal='true'")
            self.assertIn('aria-labelledby=', content, f"{modal_file} missing aria-labelledby")
            self.assertIn("'Escape'", content, f"{modal_file} missing Escape key dismissal")

    def test_structured_record_table_semantics(self):
        content = self.jsx_contents["StructuredRecordPage.jsx"]
        self.assertIn("<caption", content, "StructuredRecordPage table missing <caption>!")
        self.assertIn('scope="col"', content, "StructuredRecordPage table missing <th scope='col'>!")
        self.assertIn("<thead", content, "StructuredRecordPage table missing <thead>!")
        self.assertIn("<tbody", content, "StructuredRecordPage table missing <tbody>!")

    def test_status_indicators_contain_text_and_symbols(self):
        content = self.jsx_contents["StructuredRecordPage.jsx"]
        self.assertIn("Low (Below range)", content)
        self.assertIn("High (Above range)", content)
        self.assertIn("Within range", content)
        self.assertIn("Not assessed", content)
        self.assertIn("▼", content)
        self.assertIn("▲", content)
        self.assertIn("✓", content)
        self.assertIn("—", content)

    def test_live_regions_exist_in_critical_views(self):
        self.assertIn('aria-live="polite"', self.jsx_contents["App.jsx"])
        self.assertIn('aria-live="polite"', self.jsx_contents["ReportsPage.jsx"])
        self.assertIn('aria-live="polite"', self.jsx_contents["ProcessingEvidencePage.jsx"])


if __name__ == '__main__':
    unittest.main()
