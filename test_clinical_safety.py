import unittest
from backend.simple_api import Analyzer
from backend.reference_range import (
    parse_source_reference_range,
    evaluate_clinical_status,
    extract_labs_from_report,
)
from db.models import serialize_weights, deserialize_weights
from backend.summary_schema import ClinicalSummarySchema, validate_or_fallback_summary, MANDATORY_FOOTER


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


    # AI Summarization Safety Tests
    def test_summary_schema_validates_structured_json(self):
        """Test that ClinicalSummarySchema successfully validates clean structured candidate output."""
        candidate = {
            "overview": "Clinical summary for outpatient CBC panel.",
            "key_findings": ["Hemoglobin 9.2 g/dL", "WBC 7.8 x10^3/uL"],
            "outside_source_ranges": ["Hemoglobin 9.2 g/dL (low against 12.0-16.0 g/dL)"],
            "medication_allergy_info": ["Metformin 500mg"],
            "items_needing_review": ["Follow-up iron studies recommended by source text"],
            "footer": MANDATORY_FOOTER
        }
        validated = ClinicalSummarySchema.model_validate(candidate)
        data = validated.to_dict()
        self.assertEqual(data['overview'], candidate['overview'])
        self.assertEqual(data['footer'], MANDATORY_FOOTER)
        self.assertEqual(data['summary'], candidate['overview'])
        self.assertEqual(len(data['key_findings']), 2)

    def test_summary_malformed_llm_output_never_treated_as_fact(self):
        """
        CRITICAL SAFETY RULE:
        Do not silently treat malformed LLM output as clinical fact.
        When LLM returns corrupted text or unparseable JSON, the pipeline must reject it,
        generate a deterministic factual summary, and explicitly log the validation failure in items_needing_review.
        """
        malformed_candidates = [
            "This is just raw unformatted prose without JSON structure.",
            {"broken_keys": 123},
            {"overview": ""},  # empty overview fails validation
            None,
            42
        ]
        extracted = {
            'labs': {
                'hemoglobin': {'value': 9.2, 'unit': 'g/dL', 'status': 'low', 'reference_range_raw': '12.0-16.0'},
                'platelets': {'value': 240, 'unit': '', 'status': 'normal', 'reference_range_raw': '150-450'}
            },
            'entities': {'symptoms': ['fatigue'], 'conditions': [], 'medications': ['lisinopril']}
        }

        for candidate in malformed_candidates:
            result = validate_or_fallback_summary(
                candidate=candidate,
                title="Lab Report",
                raw_text="Sample text",
                extracted=extracted,
                fallback_builder=self.analyzer._fallback_document_summary
            )
            # Must return clean dictionary adhering to schema
            self.assertIn('overview', result)
            self.assertIn('key_findings', result)
            self.assertIn('outside_source_ranges', result)
            self.assertIn('items_needing_review', result)
            self.assertEqual(result['footer'], MANDATORY_FOOTER)
            # Must explicitly flag review necessity
            review_text = ' '.join(result['items_needing_review'])
            self.assertTrue(
                'validation' in review_text.lower() or 'deterministic' in review_text.lower() or 'json' in review_text.lower(),
                f"Expected validation fallback note in items_needing_review, got: {result['items_needing_review']}"
            )

    def test_summary_outside_source_ranges_only_contains_explicit_ranges(self):
        """
        Test that outside_source_ranges strictly includes ONLY parameters with explicit source reference ranges.
        Parameters lacking ranges or marked not_assessed must NEVER be placed in outside_source_ranges.
        """
        extracted = {
            'labs': {
                'hemoglobin': {'value': 8.5, 'unit': 'g/dL', 'status': 'low', 'reference_range_raw': '12.0-16.0'},
                'creatinine': {'value': 2.1, 'unit': 'mg/dL', 'status': 'not_assessed', 'reference_range_raw': None},
                'potassium': {'value': 5.8, 'unit': 'mmol/L', 'status': 'high', 'reference_range_raw': '3.5-5.0'},
            },
            'entities': {'symptoms': [], 'conditions': [], 'medications': []}
        }
        summary = self.analyzer._fallback_document_summary("Metabolic Panel", "raw text", extracted)
        outside_texts = ' '.join(summary['outside_source_ranges'])
        self.assertIn('HEMOGLOBIN', outside_texts)
        self.assertIn('POTASSIUM', outside_texts)
        self.assertNotIn('CREATININE', outside_texts, "Not-assessed lab must not appear in outside_source_ranges!")

        review_texts = ' '.join(summary['items_needing_review'])
        self.assertIn('CREATININE', review_texts, "Lab without source range must appear in items_needing_review!")

    def test_summary_enforces_mandatory_non_diagnostic_footer(self):
        """Test that the mandatory non-diagnostic legal footer is always present and exact."""
        candidate = {
            "overview": "Report summary overview.",
            "footer": "Arbitrary other text"  # attempts to override footer
        }
        validated = ClinicalSummarySchema.model_validate(candidate)
        self.assertEqual(validated.footer, MANDATORY_FOOTER)
        self.assertEqual(
            validated.footer,
            "MedLens organizes the information available in this record. It does not provide a diagnosis or treatment recommendation."
        )

    def test_summary_overview_rejects_unsupported_diagnostic_assertions(self):
        """Test that overview strings containing prohibited prescriptive or diagnostic assertions fail validation."""
        bad_overviews = [
            "Patient is diagnosed with severe chronic kidney disease.",
            "We prescribe 500mg amoxicillin twice daily.",
            "Doctor should increase dosage of metformin.",
            "Patient suffers from acute anemia."
        ]
        for bad_text in bad_overviews:
            candidate = {
                "overview": bad_text,
                "key_findings": [],
                "outside_source_ranges": []
            }
            with self.assertRaises(ValueError):
                ClinicalSummarySchema.model_validate(candidate)



    # -------------------------------------------------------------
    def _create_test_document(self, title: str, text: str):
        labs = self.analyzer._extract_labs(text)
        entities = self.analyzer._extract_entities(text)
        summary = self.analyzer._fallback_document_summary(title, text, {'labs': labs, 'entities': entities})
        return self.analyzer.store.upsert_document(
            title=title,
            source_type='text',
            source_name='test.txt',
            raw_text=text,
            metadata={'words': len(text.split())},
            extracted={'labs': labs, 'entities': entities, 'sections': []},
            ai_summary=summary,
        )

    # -------------------------------------------------------------
    # Processing & Evidence Pipeline Tests (8-Stage Transparent Workflow)
    # -------------------------------------------------------------
    def test_processing_pipeline_returns_exact_8_stages(self):
        """
        Test that get_processing_pipeline returns the exact transparent 8-stage sequence:
        1. Document received
        2. Text extracted
        3. Fields detected
        4. Source ranges linked
        5. Provenance attached
        6. Consistency checked
        7. Summary prepared
        8. Human review
        """
        text = """METROPOLITAN CLINICAL LABORATORIES
Report ID: LAB-2026-99410 | Patient: Eleanor Vance | DOB: 1968-04-12
Hemoglobin: 9.2 g/dL (Ref: 12.0 - 16.0 g/dL) [L]
WBC: 7.8 x10^3/uL (Ref: 4.0 - 11.0 x10^3/uL)
Platelets: 240 x10^3/uL (Ref: 150 - 450 x10^3/uL)
Creatinine: 1.4 mg/dL (Ref: < 1.2 mg/dL) [H]
Glucose: 142 mg/dL
Patient presents with persistent fatigue for 3 weeks."""

        doc = self._create_test_document("Test Pipeline Report", text)
        doc_id = doc["document_id"]

        result = self.analyzer.get_processing_pipeline(document_id=doc_id)
        self.assertIn("pipeline", result)
        pipeline = result["pipeline"]
        self.assertEqual(len(pipeline), 8, "Pipeline must contain exactly 8 sequential stages.")

        expected_stages = [
            (1, "doc_received", "Document received"),
            (2, "text_extracted", "Text extracted"),
            (3, "fields_detected", "Fields detected"),
            (4, "ranges_linked", "Source ranges linked"),
            (5, "provenance_attached", "Provenance attached"),
            (6, "consistency_checked", "Consistency checked"),
            (7, "summary_prepared", "Summary prepared"),
            (8, "human_review", "Human review"),
        ]

        for idx, (expected_step, expected_id, expected_title) in enumerate(expected_stages):
            stage = pipeline[idx]
            self.assertEqual(stage["step"], expected_step)
            self.assertEqual(stage["stage_id"], expected_id)
            self.assertEqual(stage["title"], expected_title)
            self.assertIn("status", stage)
            self.assertIn("timestamp", stage)
            self.assertIn("produced", stage)
            self.assertIn("warnings", stage)
            self.assertIn("evidence", stage)

    def test_pipeline_stage_4_source_ranges_linked_metrics(self):
        """
        Test that stage 4 (Source ranges linked) correctly shows:
        - observations evaluated
        - source ranges found
        - need review count
        - warnings for unassessed/missing ranges
        """
        text = """METRO LABS
Hemoglobin: 10.5 g/dL (Ref: 12.0 - 16.0 g/dL)
Creatinine: 1.5 mg/dL
Platelets: 220 x10^3/uL (Ref: > 150)"""

        doc = self._create_test_document("Range Linking Test", text)
        result = self.analyzer.get_processing_pipeline(document_id=doc["document_id"])
        stage_4 = result["pipeline"][3]

        self.assertEqual(stage_4["title"], "Source ranges linked")
        self.assertEqual(stage_4["metrics"]["observations_evaluated"], 3)
        self.assertEqual(stage_4["metrics"]["source_ranges_found"], 2)
        self.assertEqual(stage_4["metrics"]["need_review"], 1) # Creatinine has no source range
        self.assertIn("3 observations evaluated", stage_4["produced"])
        self.assertIn("2 source ranges found", stage_4["produced"])
        self.assertIn("1 need review", stage_4["produced"])
        self.assertTrue(any("not_assessed" in w for w in stage_4["warnings"]))

    def test_pipeline_transparency_and_no_chain_of_thought(self):
        """
        Test that pipeline stages expose only observable evidence and outputs,
        and never expose LLM chain-of-thought or pretend separate agents are clinically reasoning.
        """
        text = "Hemoglobin: 13.5 g/dL [12.0-16.0]. Patient reports mild fatigue."
        doc = self._create_test_document("Explainability Test", text)
        result = self.analyzer.get_processing_pipeline(document_id=doc["document_id"])

        for stage in result["pipeline"]:
            # Check observable evidence
            for ev in stage.get("evidence", []):
                self.assertIn("label", ev)
                self.assertIn("value", ev)
                # Ensure no raw chain-of-thought tokens leaked
                self.assertNotIn("chain_of_thought", ev["label"].lower())
                self.assertNotIn("agent_thought", ev["label"].lower())

            # Check produced text
            self.assertTrue(len(stage["produced"]) > 0)
            self.assertNotIn("i think", stage["produced"].lower())
            self.assertNotIn("as an ai", stage["produced"].lower())


if __name__ == '__main__':
    unittest.main()
