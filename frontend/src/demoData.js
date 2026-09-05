// Fallback demonstration dataset for standalone browser / GitHub Pages preview
export const DEMO_DATA = {
  health: {
    status: 'ok',
    mode: 'browser_demo',
    message: 'MedLens Clinical Workspace running in standalone browser preview. Connect to localhost:8000 for live API.'
  },
  patients: [
    {
      patient_id: 'pat-001',
      name: 'Eleanor Vance',
      age: 58,
      sex: 'Female',
      symptoms: [
        'Persistent generalized fatigue for 3 weeks',
        'Mild dyspnea on exertion (climbing stairs)',
        'Intermittent lightheadedness when standing'
      ],
      conditions: [
        'Essential hypertension (diagnosed 2019)',
        'Type 2 diabetes mellitus without complications'
      ],
      allergies: [
        'Penicillin (Urticaria/Hives, Moderate)'
      ],
      medications: [
        'Lisinopril 20 mg oral tablet daily',
        'Metformin hydrochloride 500 mg oral tablet twice daily with meals'
      ],
      notes: 'Patient presented for routine periodic evaluation and follow-up on recent complete blood count showing microcytic anemia.',
      documents: [
        {
          document_id: 'doc-001',
          title: 'Complete Blood Count & Metabolic Panel - Metro Health',
          source_type: 'file',
          source_filename: 'CBC_Metabolic_Report_2026-09-01.pdf',
          created_at: '2026-09-01T09:15:00Z',
          patient_id: 'pat-001',
          raw_text: `METROPOLITAN CLINICAL LABORATORIES
Report ID: LAB-2026-99410 | Patient: Eleanor Vance | DOB: 1968-04-12
Age: 58 | Sex: Female | Ordering Physician: Dr. Marcus Hayes, MD
Collection Date: 2026-09-01 08:30 AM | Status: FINAL

COMPLETE BLOOD COUNT (CBC) & METABOLIC PANEL
Test Name                   Result     Units     Reference Range      Flag
-------------------------------------------------------------------------
Hemoglobin                  9.2        g/dL      12.0 - 16.0 g/dL     [L]
WBC                         7.8        x10^3/uL  4.0 - 11.0 x10^3/uL
Platelets                   240        x10^3/uL  150 - 450 x10^3/uL
Creatinine                  1.4        mg/dL     < 1.2 mg/dL          [H]
Glucose                     142        mg/dL     70 - 99 mg/dL        [H]
Sodium                      138        mmol/L    135 - 145 mmol/L
Potassium                   4.1        mmol/L    3.5 - 5.0 mmol/L
Urinalysis Glucose          Negative             Negative

CLINICAL NOTES & INTERPRETATION:
Microcytic hypochromic indices noted with low hemoglobin (9.2 g/dL). 
Patient presents with symptomatic fatigue and exertion-associated dyspnea.
Elevated fasting glucose (142 mg/dL) consistent with patient history of diabetes.
Mild elevation in serum creatinine (1.4 mg/dL against upper threshold of 1.2 mg/dL).
Recommend clinical correlation with serum ferritin, total iron-binding capacity (TIBC), and renal function monitoring.`,
          ai_summary: {
            overview: "Factual record overview for Complete Blood Count & Metabolic Panel (LAB-2026-99410). The document reports 8 laboratory observations, patient-reported symptoms (fatigue, mild exertional dyspnea), and documented outpatient medications.",
            key_findings: [
              "Hemoglobin measured at 9.2 g/dL (classified low against source reference interval 12.0 - 16.0 g/dL)",
              "Creatinine measured at 1.4 mg/dL (classified high against source reference interval < 1.2 mg/dL)",
              "Fasting glucose measured at 142 mg/dL (classified high against source reference interval 70 - 99 mg/dL)",
              "WBC count: 7.8 x10^3/uL (within source reference interval 4.0 - 11.0 x10^3/uL)",
              "Platelet count: 240 x10^3/uL (within source reference interval 150 - 450 x10^3/uL)",
              "Urinalysis Glucose reported as Negative"
            ],
            outside_source_ranges: [
              "HEMOGLOBIN: 9.2 g/dL (classified low against source reference range: 12.0 - 16.0 g/dL)",
              "CREATININE: 1.4 mg/dL (classified high against source reference range: < 1.2 mg/dL)",
              "GLUCOSE: 142 mg/dL (classified high against source reference range: 70 - 99 mg/dL)"
            ],
            medication_allergy_info: [
              "Documented medication(s): Lisinopril 20 mg daily, Metformin 500 mg twice daily",
              "Documented allergy: Penicillin (Urticaria/Hives, Moderate)"
            ],
            items_needing_review: [
              "Borderline elevated serum creatinine (1.4 mg/dL) relative to source threshold (<1.2 mg/dL) requires clinician review.",
              "Source text notes microcytic indices; correlation with iron studies suggested in report text."
            ],
            footer: "MedLens organizes the information available in this record. It does not provide a diagnosis or treatment recommendation.",
            summary: "Factual record overview for Complete Blood Count & Metabolic Panel (LAB-2026-99410).",
            bullet_points: [
              "Hemoglobin: 9.2 g/dL (classified low against source range 12.0 - 16.0 g/dL)",
              "Creatinine: 1.4 mg/dL (classified high against source range < 1.2 mg/dL)",
              "Glucose: 142 mg/dL (classified high against source range 70 - 99 mg/dL)"
            ]
          },
          extracted: {
            labs: {
              hemoglobin: {
                test_name: 'hemoglobin',
                display_name: 'Hemoglobin',
                value: 9.2,
                unit: 'g/dL',
                reference_range_raw: '12.0 - 16.0 g/dL',
                reference_range_low: 12.0,
                reference_range_high: 16.0,
                reference_range_operator: 'between',
                reference_range: { min: 12.0, max: 16.0 },
                parsed_min: 12.0,
                parsed_max: 16.0,
                reference_range_text: 'Source reference: 12.0 - 16.0 g/dL',
                status: 'low',
                needs_review: false,
                source_flag: 'L',
                observation_date: '2026-09-01',
                source_page: 1,
                source_snippet: 'Hemoglobin                  9.2        g/dL      12.0 - 16.0 g/dL     [L]',
                extraction_confidence: 0.97,
                verification_status: 'verified',
                provenance_type: 'user_verified'
              },
              wbc: {
                test_name: 'wbc',
                display_name: 'WBC',
                value: 7.8,
                unit: 'x10^3/uL',
                reference_range_raw: '4.0 - 11.0 x10^3/uL',
                reference_range_low: 4.0,
                reference_range_high: 11.0,
                reference_range_operator: 'between',
                reference_range: { min: 4.0, max: 11.0 },
                parsed_min: 4.0,
                parsed_max: 11.0,
                reference_range_text: 'Source reference: 4.0 - 11.0 x10^3/uL',
                status: 'normal',
                needs_review: false,
                source_flag: null,
                observation_date: '2026-09-01',
                source_page: 1,
                source_snippet: 'WBC                         7.8        x10^3/uL  4.0 - 11.0 x10^3/uL',
                extraction_confidence: 0.95,
                verification_status: 'unverified',
                provenance_type: 'source_extracted'
              },
              platelets: {
                test_name: 'platelets',
                display_name: 'Platelets',
                value: 240,
                unit: 'x10^3/uL',
                reference_range_raw: '150 - 450 x10^3/uL',
                reference_range_low: 150.0,
                reference_range_high: 450.0,
                reference_range_operator: 'between',
                reference_range: { min: 150.0, max: 450.0 },
                parsed_min: 150.0,
                parsed_max: 450.0,
                reference_range_text: 'Source reference: 150 - 450 x10^3/uL',
                status: 'normal',
                needs_review: false,
                source_flag: null,
                observation_date: '2026-09-01',
                source_page: 1,
                source_snippet: 'Platelets                   240        x10^3/uL  150 - 450 x10^3/uL',
                extraction_confidence: 0.96,
                verification_status: 'unverified',
                provenance_type: 'source_extracted'
              },
              creatinine: {
                test_name: 'creatinine',
                display_name: 'Creatinine',
                value: 1.4,
                unit: 'mg/dL',
                reference_range_raw: '< 1.2 mg/dL',
                reference_range_low: null,
                reference_range_high: 1.2,
                reference_range_operator: '<',
                reference_range: null,
                parsed_min: null,
                parsed_max: 1.2,
                reference_range_text: 'Source reference: < 1.2 mg/dL',
                status: 'high',
                needs_review: false,
                source_flag: 'H',
                observation_date: '2026-09-01',
                source_page: 1,
                source_snippet: 'Creatinine                  1.4        mg/dL     < 1.2 mg/dL          [H]',
                extraction_confidence: 0.93,
                verification_status: 'unverified',
                provenance_type: 'source_extracted'
              },
              glucose: {
                test_name: 'glucose',
                display_name: 'Glucose',
                value: 142,
                unit: 'mg/dL',
                reference_range_raw: '70 - 99 mg/dL',
                reference_range_low: 70.0,
                reference_range_high: 99.0,
                reference_range_operator: 'between',
                reference_range: { min: 70.0, max: 99.0 },
                parsed_min: 70.0,
                parsed_max: 99.0,
                reference_range_text: 'Source reference: 70 - 99 mg/dL',
                status: 'high',
                needs_review: false,
                source_flag: 'H',
                observation_date: '2026-09-01',
                source_page: 1,
                source_snippet: 'Glucose                     142        mg/dL     70 - 99 mg/dL        [H]',
                extraction_confidence: 0.95,
                verification_status: 'unverified',
                provenance_type: 'source_extracted'
              },
              sodium: {
                test_name: 'sodium',
                display_name: 'Sodium',
                value: 138,
                unit: 'mmol/L',
                reference_range_raw: '135 - 145 mmol/L',
                reference_range_low: 135.0,
                reference_range_high: 145.0,
                reference_range_operator: 'between',
                reference_range: { min: 135.0, max: 145.0 },
                parsed_min: 135.0,
                parsed_max: 145.0,
                reference_range_text: 'Source reference: 135 - 145 mmol/L',
                status: 'normal',
                needs_review: false,
                source_flag: null,
                observation_date: '2026-09-01',
                source_page: 1,
                source_snippet: 'Sodium                      138        mmol/L    135 - 145 mmol/L',
                extraction_confidence: 0.94,
                verification_status: 'unverified',
                provenance_type: 'source_extracted'
              },
              potassium: {
                test_name: 'potassium',
                display_name: 'Potassium',
                value: 4.1,
                unit: 'mmol/L',
                reference_range_raw: '3.5 - 5.0 mmol/L',
                reference_range_low: 3.5,
                reference_range_high: 5.0,
                reference_range_operator: 'between',
                reference_range: { min: 3.5, max: 5.0 },
                parsed_min: 3.5,
                parsed_max: 5.0,
                reference_range_text: 'Source reference: 3.5 - 5.0 mmol/L',
                status: 'normal',
                needs_review: false,
                source_flag: null,
                observation_date: '2026-09-01',
                source_page: 1,
                source_snippet: 'Potassium                   4.1        mmol/L    3.5 - 5.0 mmol/L',
                extraction_confidence: 0.95,
                verification_status: 'unverified',
                provenance_type: 'source_extracted'
              },
              urinalysis_glucose: {
                test_name: 'urinalysis_glucose',
                display_name: 'Urinalysis Glucose',
                value: 'Negative',
                unit: '',
                reference_range_raw: 'Negative',
                reference_range_low: null,
                reference_range_high: null,
                reference_range_operator: 'textual',
                reference_range: null,
                parsed_min: null,
                parsed_max: null,
                reference_range_text: 'Source reference: Negative',
                status: 'normal',
                needs_review: false,
                source_flag: null,
                observation_date: '2026-09-01',
                source_page: 1,
                source_snippet: 'Urinalysis Glucose          Negative             Negative',
                extraction_confidence: 0.98,
                verification_status: 'unverified',
                provenance_type: 'source_extracted'
              }
            },
            entities: {
              symptoms: ['fatigue', 'dyspnea', 'lightheadedness'],
              conditions: ['hypertension', 'diabetes', 'microcytic anemia'],
              medications: ['lisinopril', 'metformin']
            },
            tables: [],
            sections: [
              { title: 'COMPLETE BLOOD COUNT', text: 'Hemoglobin: 9.2 g/dL, WBC: 7.8, Platelets: 240' },
              { title: 'METABOLIC PANEL', text: 'Creatinine: 1.4 mg/dL, Glucose: 142 mg/dL, Sodium: 138, Potassium: 4.1' }
            ]
          }
        },
        {
          document_id: 'doc-002',
          title: 'Prior Hematology Panel - St. Jude Medical Center',
          source_type: 'file',
          source_filename: 'Hematology_Prior_2026-08-10.pdf',
          created_at: '2026-08-10T11:00:00Z',
          patient_id: 'pat-001',
          raw_text: `ST. JUDE MEDICAL CENTER - OUTPATIENT SERVICES
Patient: Eleanor Vance | Date: 2026-08-10
CBC Results:
Hemoglobin: 11.4 g/dL (Ref: 12.0 - 16.0 g/dL) [L]
Platelets: 255 x10^3/uL (Ref: 150 - 450 x10^3/uL)
WBC: 6.9 x10^3/uL (Ref: 4.0 - 11.0 x10^3/uL)`,
          ai_summary: {
            overview: "Factual record overview for Complete Blood Count & Metabolic Panel (LAB-2026-99410). The document reports 8 laboratory observations, patient-reported symptoms (fatigue, mild exertional dyspnea), and documented outpatient medications.",
            key_findings: [
              "Hemoglobin measured at 9.2 g/dL (classified low against source reference interval 12.0 - 16.0 g/dL)",
              "Creatinine measured at 1.4 mg/dL (classified high against source reference interval < 1.2 mg/dL)",
              "Fasting glucose measured at 142 mg/dL (classified high against source reference interval 70 - 99 mg/dL)",
              "WBC count: 7.8 x10^3/uL (within source reference interval 4.0 - 11.0 x10^3/uL)",
              "Platelet count: 240 x10^3/uL (within source reference interval 150 - 450 x10^3/uL)",
              "Urinalysis Glucose reported as Negative"
            ],
            outside_source_ranges: [
              "HEMOGLOBIN: 9.2 g/dL (classified low against source reference range: 12.0 - 16.0 g/dL)",
              "CREATININE: 1.4 mg/dL (classified high against source reference range: < 1.2 mg/dL)",
              "GLUCOSE: 142 mg/dL (classified high against source reference range: 70 - 99 mg/dL)"
            ],
            medication_allergy_info: [
              "Documented medication(s): Lisinopril 20 mg daily, Metformin 500 mg twice daily",
              "Documented allergy: Penicillin (Urticaria/Hives, Moderate)"
            ],
            items_needing_review: [
              "Borderline elevated serum creatinine (1.4 mg/dL) relative to source threshold (<1.2 mg/dL) requires clinician review.",
              "Source text notes microcytic indices; correlation with iron studies suggested in report text."
            ],
            footer: "MedLens organizes the information available in this record. It does not provide a diagnosis or treatment recommendation.",
            summary: "Factual record overview for Complete Blood Count & Metabolic Panel (LAB-2026-99410).",
            bullet_points: [
              "Hemoglobin: 9.2 g/dL (classified low against source range 12.0 - 16.0 g/dL)",
              "Creatinine: 1.4 mg/dL (classified high against source range < 1.2 mg/dL)",
              "Glucose: 142 mg/dL (classified high against source range 70 - 99 mg/dL)"
            ]
          },
          extracted: {
            labs: {
              hemoglobin: {
                test_name: 'hemoglobin',
                display_name: 'Hemoglobin',
                value: 11.4,
                unit: 'g/dL',
                reference_range_raw: '12.0 - 16.0 g/dL',
                reference_range_low: 12.0,
                reference_range_high: 16.0,
                reference_range_operator: 'between',
                reference_range: { min: 12.0, max: 16.0 },
                parsed_min: 12.0,
                parsed_max: 16.0,
                reference_range_text: 'Source reference: 12.0 - 16.0 g/dL',
                status: 'low',
                needs_review: false,
                source_flag: 'L',
                observation_date: '2026-08-10',
                source_page: 1,
                source_snippet: 'Hemoglobin: 11.4 g/dL (Ref: 12.0 - 16.0 g/dL) [L]',
                extraction_confidence: 0.96,
                verification_status: 'verified',
                provenance_type: 'user_verified'
              },
              platelets: {
                test_name: 'platelets',
                display_name: 'Platelets',
                value: 255,
                unit: 'x10^3/uL',
                reference_range_raw: '150 - 450 x10^3/uL',
                reference_range_low: 150.0,
                reference_range_high: 450.0,
                reference_range_operator: 'between',
                reference_range: { min: 150.0, max: 450.0 },
                parsed_min: 150.0,
                parsed_max: 450.0,
                reference_range_text: 'Source reference: 150 - 450 x10^3/uL',
                status: 'normal',
                needs_review: false,
                source_flag: null,
                observation_date: '2026-08-10',
                source_page: 1,
                source_snippet: 'Platelets: 255 x10^3/uL (Ref: 150 - 450 x10^3/uL)',
                extraction_confidence: 0.95,
                verification_status: 'unverified',
                provenance_type: 'source_extracted'
              }
            }
          }
        }
      ]
    }
  ]
}
