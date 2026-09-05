import unittest
from backend.simple_api import Analyzer
from backend.reference_range import (
    parse_source_reference_range,
    evaluate_clinical_status,
    extract_labs_from_report,
)
from db.models import serialize_weights, deserialize_weights


class TestMedLensClinicalSafety(unittest.TestCase):
    """
    Unit test suite enforcing MedLens Clinical Safety and Reference Range extraction.
    ABSOLUTE RULE: MedLens may not contain built-in clinical normal ranges used to label patient results.
    """
    def setUp(self):
        self.analyzer = Analyzer()

    # 1. Complete numeric range
    def test_complete_numeric_range_formats(self):
        """
        Test that complete numeric ranges in various source formats (e.g., '12.0-16.0',
        '12 - 16', '[12.0-16.0]', 'Reference Range: 12.0–16.0') correctly extract bounds
        and assign low/normal/high.
        """
        # Format A: hyphen with spaces
        text_a = "Hemoglobin: 9.5 g/dL (Ref: 12.0 - 16.0 g/dL)"
        labs_a = self.analyzer._extract_labs(text_a)
        self.assertIn('hemoglobin', labs_a)
        hb = labs_a['hemoglobin']
        self.assertEqual(hb['value'], 9.5)
        self.assertEqual(hb['unit'], 'g/dL')
        self.assertEqual(hb['reference_range_low'], 12.0)
        self.assertEqual(hb['reference_range_high'], 16.0)
        self.assertEqual(hb['reference_range_operator'], 'between')
        self.assertEqual(hb['status'], 'low')
        self.assertFalse(hb['needs_review'])

        # Format B: brackets
        text_b = "Hemoglobin 13.2 g/dL [12.0-16.0]"
        labs_b = self.analyzer._extract_labs(text_b)
        self.assertEqual(labs_b['hemoglobin']['status'], 'normal')
        self.assertEqual(labs_b['hemoglobin']['reference_range_low'], 12.0)
        self.assertEqual(labs_b['hemoglobin']['reference_range_high'], 16.0)

        # Format C: en-dash with 'Reference Range:'
        text_c = "Hemoglobin: 17.5 g/dL. Reference Range: 12.0–16.0 g/dL"
        labs_c = self.analyzer._extract_labs(text_c)
        self.assertEqual(labs_c['hemoglobin']['status'], 'high')

    # 2. Lower-bound-only range (>10)
    def test_lower_bound_only_range(self):
        """
        Test lower-bound-only ranges (e.g., '>10').
        Never manufacture a missing upper bound.
        """
        text = "Platelets: 8 x10^9/L (Ref: >10)"
        labs = self.analyzer._extract_labs(text)
        plt = labs['platelets']
        self.assertEqual(plt['value'], 8.0)
        self.assertEqual(plt['reference_range_low'], 10.0)
        self.assertIsNone(plt['reference_range_high'], "Must NEVER manufacture a missing upper bound!")
        self.assertEqual(plt['reference_range_operator'], '>')
        self.assertEqual(plt['status'], 'low')
        self.assertFalse(plt['needs_review'])

        # Value satisfying the lower bound (>10)
        text_ok = "Platelets: 15 x10^9/L (Ref: >10)"
        labs_ok = self.analyzer._extract_labs(text_ok)
        self.assertEqual(labs_ok['platelets']['status'], 'normal')

    # 3. Upper-bound-only range (<5)
    def test_upper_bound_only_range(self):
        """
        Test upper-bound-only ranges (e.g., '<5').
        Never manufacture a missing lower bound.
        """
        text = "Creatinine: 7.2 mg/dL (Ref: <5)"
        labs = self.analyzer._extract_labs(text)
        cr = labs['creatinine']
        self.assertEqual(cr['value'], 7.2)
        self.assertIsNone(cr['reference_range_low'], "Must NEVER manufacture a missing lower bound!")
        self.assertEqual(cr['reference_range_high'], 5.0)
        self.assertEqual(cr['reference_range_operator'], '<')
        self.assertEqual(cr['status'], 'high')
        self.assertFalse(cr['needs_review'])

        # Value within upper bound (<5)
        text_ok = "Creatinine: 3.1 mg/dL (Ref: <5)"
        labs_ok = self.analyzer._extract_labs(text_ok)
        self.assertEqual(labs_ok['creatinine']['status'], 'normal')

    # 4. Textual range (Negative, Non-reactive)
    def test_textual_range(self):
        """
        Test qualitative/textual ranges and observations (Negative, Non-reactive, Positive).
        """
        text = "Urinalysis Glucose: Negative (Ref: Negative)"
        labs = self.analyzer._extract_labs(text)
        self.assertIn('glucose', labs)
        gl = labs['glucose']
        self.assertEqual(gl['value'], 'Negative')
        self.assertEqual(gl['reference_range_operator'], 'textual')
        self.assertEqual(gl['status'], 'normal')

        text_abnormal = "Urinalysis Glucose: Positive (Ref: Negative)"
        labs_abnormal = self.analyzer._extract_labs(text_abnormal)
        self.assertEqual(labs_abnormal['glucose']['status'], 'high')

    # 5. Missing range
    def test_missing_range_is_not_assessed(self):
        """
        CRITICAL SAFETY RULE:
        When source contains NO reference range, MedLens must NEVER invent or assume clinical normal ranges.
        status MUST be 'not_assessed' and needs_review MUST be True.
        """
        text = "Hemoglobin: 10.5 g/dL. Creatinine: 1.1 mg/dL."
        labs = self.analyzer._extract_labs(text)
        
        self.assertIn('hemoglobin', labs)
        self.assertEqual(labs['hemoglobin']['value'], 10.5)
        self.assertIsNone(labs['hemoglobin']['reference_range'])
        self.assertIsNone(labs['hemoglobin']['reference_range_raw'])
        self.assertEqual(labs['hemoglobin']['status'], 'not_assessed')
        self.assertTrue(labs['hemoglobin']['needs_review'])
        self.assertEqual(labs['hemoglobin']['reference_range_text'], 'Reference range not available in source report.')

        self.assertIn('creatinine', labs)
        self.assertEqual(labs['creatinine']['status'], 'not_assessed')
        self.assertTrue(labs['creatinine']['needs_review'])

    # 6. Malformed or ambiguous range
    def test_malformed_and_ambiguous_range(self):
        """
        Test malformed ranges (e.g. inverted bounds '16.0-12.0' or unparseable text).
        Must produce status='not_assessed' and needs_review=True.
        """
        text = "Hemoglobin: 13.0 g/dL (Ref: 16.0 - 12.0)"
        labs = self.analyzer._extract_labs(text)
        hb = labs['hemoglobin']
        self.assertEqual(hb['status'], 'not_assessed')
        self.assertTrue(hb['needs_review'])

    # 7. Value without unit
    def test_value_without_unit(self):
        """
        Test values that appear without an explicit unit (e.g., 'Platelets: 250 (150-450)').
        """
        text = "Platelets: 250 (150 - 450)"
        labs = self.analyzer._extract_labs(text)
        self.assertIn('platelets', labs)
        plt = labs['platelets']
        self.assertEqual(plt['value'], 250.0)
        self.assertEqual(plt['unit'], '')
        self.assertEqual(plt['status'], 'normal')
        self.assertEqual(plt['reference_range_low'], 150.0)
        self.assertEqual(plt['reference_range_high'], 450.0)

    # 8. Duplicated tests
    def test_duplicated_tests_in_same_report(self):
        """
        Test report containing multiple/duplicated instances of the same test.
        Both must be captured without collision.
        """
        text = "Hemoglobin: 13.5 g/dL (12.0-16.0)\nRepeated Hemoglobin: 13.8 g/dL (12.0-16.0)"
        labs = self.analyzer._extract_labs(text)
        self.assertIn('hemoglobin', labs)
        self.assertIn('hemoglobin_2', labs)
        self.assertEqual(labs['hemoglobin']['value'], 13.5)
        self.assertEqual(labs['hemoglobin_2']['value'], 13.8)

    # 9. Multiple report dates
    def test_multiple_report_dates_tracking(self):
        """
        Test that observations accurately associate with date headers present in the document.
        """
        text = (
            "Date: 2026-08-10\nHemoglobin: 14.0 g/dL (12.0-16.0)\n"
            "Date: 2026-09-01\nHemoglobin: 11.0 g/dL (12.0-16.0)"
        )
        labs = self.analyzer._extract_labs(text)
        self.assertEqual(labs['hemoglobin']['observation_date'], '2026-08-10')
        self.assertEqual(labs['hemoglobin_2']['observation_date'], '2026-09-01')

    # Existing audit & safety tests
    def test_audit_reference_ranges_categorization(self):
        """Test that audit correctly identifies values outside, within, and with unspecified ranges."""
        labs = {
            'hemoglobin': {'value': 8.5, 'unit': 'g/dL', 'reference_range_raw': '12.0–16.0', 'reference_range': {'min': 12.0, 'max': 16.0}, 'status': 'low'},
            'glucose': {'value': 95.0, 'unit': 'mg/dL', 'reference_range_raw': '70.0–100.0', 'reference_range': {'min': 70.0, 'max': 100.0}, 'status': 'normal'},
            'potassium': {'value': 4.2, 'unit': 'mmol/L', 'reference_range_raw': None, 'reference_range': None, 'status': 'not_assessed'},
        }
        audit = self.analyzer._audit_reference_ranges(labs)

        outside = [x['test'] for x in audit['outside_source_range']]
        within = [x['test'] for x in audit['within_source_range']]
        unspecified = [x['test'] for x in audit['unspecified_reference_range']]

        self.assertIn('hemoglobin', outside)
        self.assertIn('glucose', within)
        self.assertIn('potassium', unspecified)

    def test_clinical_corroboration_non_diagnostic(self):
        """Test that corroboration generates factual observations without diagnosing diseases."""
        labs = {
            'hemoglobin': {'value': 7.8, 'unit': 'g/dL', 'reference_range': {'min': 12.0, 'max': 16.0}, 'status': 'low'}
        }
        entities = {
            'symptoms': ['fatigue', 'dizziness'],
            'conditions': ['hypertension']
        }
        corroboration = self.analyzer._corroborate_clinical_context(labs, entities, [])

        self.assertTrue(len(corroboration['contextual_observations']) > 0)
        self.assertIn('safety_note', corroboration)
        for obs in corroboration['contextual_observations']:
            self.assertNotIn('diagnosed with', obs.lower())

    def test_safe_json_weight_serialization_no_pickle(self):
        """Test that neural weights serialization uses safe JSON without pickle."""
        test_weights = [0.12, 0.45, -0.78, 0.99]
        serialized = serialize_weights(test_weights)
        deserialized = deserialize_weights(serialized)
        self.assertEqual(test_weights, deserialized)
        import json
        self.assertTrue(isinstance(json.loads(serialized), list))


if __name__ == '__main__':
    unittest.main()
