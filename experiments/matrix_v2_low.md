# 3 x 3 evaluation matrix (matrix_v2_low)

Model `gpt-6-luna`, prompt `v2`.

| Vendor | RFQ-001 | RFQ-002 | RFQ-003 |
|---|---|---|---|
| A | **30** (raw 77, gate ✗) | **0** (raw 0, gate ✗) | **12** (raw 12, gate ✓) |
| B | **38** (raw 38, gate ✓) | **0** (raw 0, gate ✗) | **12** (raw 12, gate ✗) |
| C | **0** (raw 0, gate ✗) | **0** (raw 0, gate ✗) | **0** (raw 0, gate ✗) |

## Vendor A x RFQ-001  (14.1s)

Score **30**, raw 77, gate passed: False. technical 33.3/40.0, required 35.0/35.0, preferred 8.3/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | AS9100D certification | not_evidenced |  |
| T1 | Tolerance +/-0.02 mm on critical features | met | Routine working tolerance +/-0.01 mm on 5-axis work |
| T2 | Surface finish Ra 1.6 | met | surface finishes to Ra 0.8 achieved in production on aluminium alloys. |
| T3 | 5-axis machining capability | met | including three DMG MORI 5-axis machines (DMU 50, DMU 65 monoBLOCK) |
| T4 | Material: 7075-T6 aluminium, supplied free-issue | partial | Extensive experience with 7075 and 6061 aluminium, including free-issue material programmes where customer-supplied stock is logged, segregated and tracked by heat lot through to despatch. |
| T5 | Quantity: 250 units | met | Typical lead time for batch quantities of 200-300 machined components is |
| T6 | Delivery: 6 weeks from PO | partial | four to five weeks from receipt of material. |
| R1 | CMM inspection with first-article inspection report per AS9102 | met | In-house metrology: two Zeiss CONTURA CMMs, calibrated annually and traceable to NABL standards. ... First-article inspection reports issued in AS9102 format on request; currently produced for two customers. |
| R2 | Material traceability to mill test certificate | met | Material traceability maintained against mill test certificates for all incoming stock. |
| P1 | In-house CMM | met | In-house metrology: two Zeiss CONTURA CMMs, calibrated annually and traceable to NABL standards. |
| P2 | Prior aerospace structural work | not_evidenced |  |
| P3 | NADCAP-accredited subcontractors for any outsourced process steps | not_evidenced |  |

Reasons:
- (T1) The vendor states a routine +/-0.01 mm tolerance on 5-axis work, tighter than the required +/-0.02 mm.
- (T3) The vendor identifies three DMG MORI 5-axis machines.
- (R2) The vendor states that incoming stock is traceable against mill test certificates.

Gaps:
- (M1) AS9100D certification is not evidenced; the profile instead lists ISO 9001:2015 and IATF 16949:2016.
- (T6) The stated four-to-five-week lead time starts from receipt of material, so delivery within six weeks from PO is not established.

## Vendor A x RFQ-002  (13.1s)

Score **0**, raw 0, gate passed: False. technical 0.0/40.0, required 0.0/35.0, preferred 0.0/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | NADCAP accreditation for Chemical Processing | not_evidenced |  |
| T1 | Coating per MIL-DTL-5541 Type II Class 1A | not_evidenced |  |
| T2 | Parts up to 600 mm | not_evidenced |  |
| T3 | Quantity: Batch sizes 50-400 units | not_evidenced |  |
| T4 | Delivery: 10 working days turnaround | not_evidenced |  |
| R1 | Certificate of conformance per batch | not_evidenced |  |
| R2 | Salt spray test reports on request | not_evidenced |  |
| R3 | RoHS-compliant process chemistry | not_evidenced |  |
| P1 | Co-located with machining capability | not_evidenced |  |
| P2 | Experience with space-grade hardware | not_evidenced |  |

Reasons:
- (T1) The profile does not document the requested coating process or specification, so no coating capability is supported for this RFQ.
- (M1) The profile lists ISO 9001:2015 and IATF 16949:2016, but provides no evidence of the mandatory NADCAP Chemical Processing accreditation.
- (P1) The profile documents machining capability, but does not establish that the requested coating service is available at the same location.

Gaps:
- (M1) Mandatory NADCAP accreditation for Chemical Processing is not evidenced in the profile.
- (T1) The profile describes a precision machining business and does not evidence chemical conversion coating to MIL-DTL-5541 Type II Class 1A.

## Vendor A x RFQ-003  (13.3s)

Score **12**, raw 12, gate passed: True. technical 0.0/40.0, required 11.7/35.0, preferred 0.0/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | Mill test certificates traceable to heat lot | met | Material traceability maintained against mill test certificates for all incoming stock...tracked by heat lot through to despatch. |
| T1 | AMS 4911 specification | not_evidenced |  |
| T2 | Thickness range 1.0-6.0 mm | not_evidenced |  |
| T3 | Cut-to-size capability | not_evidenced |  |
| T4 | Material: Ti-6Al-4V Grade 5, AMS 4911 sheet, 1.0-6.0 mm | not_evidenced |  |
| T5 | Quantity: Approx. 2 tonnes per year against a rate contract | not_evidenced |  |
| T6 | Delivery: Call-off against rate contract | not_evidenced |  |
| R1 | ISO 9001 certified | met | ISO 9001:2015 certified (TUV SUD, valid to March 2028). |
| R2 | Ability to supply cut-to-size | not_evidenced |  |
| R3 | DFARS-compliant sourcing documentation | not_evidenced |  |
| P1 | Existing stock holding in India | not_evidenced |  |
| P2 | Prior supply to space or defence programmes | not_evidenced |  |
| P3 | Consignment stocking arrangement | not_evidenced |  |

Reasons:
- (M1) The vendor states that incoming stock is traceable to mill test certificates and tracked by heat lot.
- (R1) The vendor reports ISO 9001:2015 certification valid through March 2028.
- (T1) Beyond traceability and ISO certification, the profile provides no further criterion-specific strength for the requested titanium raw-material supply.

Gaps:
- (T4) The profile does not establish supply of Ti-6Al-4V Grade 5 AMS 4911 sheet in the required 1.0–6.0 mm range.
- (T5) There is no evidence of capacity to supply approximately two tonnes per year against a rate contract.

## Vendor B x RFQ-001  (11.6s)

Score **38**, raw 38, gate passed: True. technical 3.3/40.0, required 35.0/35.0, preferred 0.0/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | AS9100D certification | met | AS9100D certified (valid to August 2027). |
| T1 | Tolerance +/-0.02 mm on critical features | not_met | Demonstrated working tolerance +/-0.05 mm. |
| T2 | Surface finish Ra 1.6 | not_met | Surface finish typically Ra 3.2 as machined; better finishes require outsourced grinding or polishing. |
| T3 | 5-axis machining capability | not_met | No 5-axis capability; |
| T4 | Material: 7075-T6 aluminium, supplied free-issue | partial | Limited 7075 experience — two prototype jobs to date, both under 20 pieces. |
| T5 | Quantity: 250 units | not_met | Largest single order to date: 120 pieces. |
| T6 | Delivery: 6 weeks from PO | not_met | Typical lead time for batches above 100 pieces is 9 to 11 weeks. |
| R1 | CMM inspection with first-article inspection report per AS9102 | met | CMM work is outsourced to a NABL-accredited laboratory in Bangalore, adding two to three working days per inspection cycle. AS9102 first-article reports prepared in-house using outsourced measurement data. |
| R2 | Material traceability to mill test certificate | met | Full material traceability to mill test certificate, maintained under the AS9100 quality system. |
| P1 | In-house CMM | not_met | No in-house CMM. |
| P2 | Prior aerospace structural work | not_met | Machining of aluminium and mild steel components for aerospace ground support equipment, tooling and non-flight hardware. |
| P3 | NADCAP-accredited subcontractors for any outsourced process steps | not_evidenced |  |

Reasons:
- (M1) The vendor holds AS9100D certification valid through August 2027.
- (R2) The vendor states that it maintains full material traceability to mill test certificates.
- (R1) The vendor offers outsourced CMM inspection and prepares AS9102 first-article reports using the measurement data.

Gaps:
- (T3) The vendor explicitly has no 5-axis capability, which fails a technical requirement for this RFQ.
- (T6) The stated 9–11 week lead time for batches above 100 pieces exceeds the six-week delivery requirement.

## Vendor B x RFQ-002  (11.8s)

Score **0**, raw 0, gate passed: False. technical 0.0/40.0, required 0.0/35.0, preferred 0.0/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | NADCAP accreditation for Chemical Processing | not_evidenced |  |
| T1 | Coating per MIL-DTL-5541 Type II Class 1A | not_evidenced |  |
| T2 | Parts up to 600 mm | not_evidenced |  |
| T3 | Quantity: Batch sizes 50-400 units | not_evidenced |  |
| T4 | Delivery: 10 working days turnaround | not_evidenced |  |
| R1 | Certificate of conformance per batch | not_evidenced |  |
| R2 | Salt spray test reports on request | not_evidenced |  |
| R3 | RoHS-compliant process chemistry | not_evidenced |  |
| P1 | Co-located with machining capability | not_evidenced |  |
| P2 | Experience with space-grade hardware | not_evidenced |  |

Reasons:
- (M1) No criteria are supported by specific evidence in the profile; in particular, it lists AS9100D and ISO 9001:2015 but not NADCAP Chemical Processing accreditation.
- (T1) The profile documents machining, not chemical conversion coating, and provides no evidence of compliance with MIL-DTL-5541 Type II Class 1A.
- (T4) The only stated delivery information concerns machining lead times, so coating turnaround against the 10-working-day requirement is unsubstantiated.

Gaps:
- (M1) Mandatory NADCAP Chemical Processing accreditation is not evidenced, leaving a critical qualification gap.
- (T1) The profile does not establish that the vendor offers chemical conversion coating or can meet the specified MIL-DTL-5541 treatment.

## Vendor B x RFQ-003  (11.8s)

Score **12**, raw 12, gate passed: False. technical 0.0/40.0, required 11.7/35.0, preferred 0.0/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | Mill test certificates traceable to heat lot | partial | Full material traceability to mill test certificate, maintained under the AS9100 quality system. |
| T1 | AMS 4911 specification | not_evidenced |  |
| T2 | Thickness range 1.0-6.0 mm | not_evidenced |  |
| T3 | Cut-to-size capability | not_evidenced |  |
| T4 | Material: Ti-6Al-4V Grade 5, AMS 4911 sheet, 1.0-6.0 mm | not_evidenced |  |
| T5 | Quantity: Approx. 2 tonnes per year against a rate contract | not_evidenced |  |
| T6 | Delivery: Call-off against rate contract | not_evidenced |  |
| R1 | ISO 9001 certified | met | ISO 9001:2015 certified. |
| R2 | Ability to supply cut-to-size | not_evidenced |  |
| R3 | DFARS-compliant sourcing documentation | not_evidenced |  |
| P1 | Existing stock holding in India | not_evidenced |  |
| P2 | Prior supply to space or defence programmes | not_evidenced |  |
| P3 | Consignment stocking arrangement | not_evidenced |  |

Reasons:
- (R1) The vendor states that it is ISO 9001:2015 certified, meeting the stated quality-system requirement.
- (M1) The vendor reports mill-test-certificate traceability, although the profile does not explicitly confirm heat-lot traceability.
- (T4) The profile does not establish the required titanium alloy and sheet specification, so suitability for this raw-material RFQ remains unsupported.

Gaps:
- (M1) Mandatory requirement not met: Mill test certificates traceable to heat lot.
- (T4) The profile does not evidence supply of Ti-6Al-4V Grade 5 AMS 4911 sheet in the required thickness range.

## Vendor C x RFQ-001  (11.3s)

Score **0**, raw 0, gate passed: False. technical 0.0/40.0, required 0.0/35.0, preferred 0.0/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | AS9100D certification | not_evidenced |  |
| T1 | Tolerance +/-0.02 mm on critical features | not_evidenced |  |
| T2 | Surface finish Ra 1.6 | not_evidenced |  |
| T3 | 5-axis machining capability | not_evidenced |  |
| T4 | Material: 7075-T6 aluminium, supplied free-issue | not_evidenced |  |
| T5 | Quantity: 250 units | not_evidenced |  |
| T6 | Delivery: 6 weeks from PO | not_evidenced |  |
| R1 | CMM inspection with first-article inspection report per AS9102 | not_evidenced |  |
| R2 | Material traceability to mill test certificate | not_evidenced |  |
| P1 | In-house CMM | not_evidenced |  |
| P2 | Prior aerospace structural work | not_evidenced |  |
| P3 | NADCAP-accredited subcontractors for any outsourced process steps | not_evidenced |  |

Reasons:
- (T3) The profile refers to complex multi-axis machining, but it does not confirm the required 5-axis capability.
- (P2) The profile identifies aerospace, defence and space customers, while leaving prior structural work unsupported.
- (R2) The profile claims that documentation and traceability are provided, but does not specify mill-test-certificate traceability.

Gaps:
- (M1) AS9100D certification is mandatory, but the profile gives no evidence that Vector holds it.
- (R1) CMM inspection and an AS9102 first-article report are required, and neither is specifically evidenced.

## Vendor C x RFQ-002  (11.3s)

Score **0**, raw 0, gate passed: False. technical 0.0/40.0, required 0.0/35.0, preferred 0.0/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | NADCAP accreditation for Chemical Processing | not_evidenced |  |
| T1 | Coating per MIL-DTL-5541 Type II Class 1A | not_evidenced |  |
| T2 | Parts up to 600 mm | not_evidenced |  |
| T3 | Quantity: Batch sizes 50-400 units | not_evidenced |  |
| T4 | Delivery: 10 working days turnaround | not_evidenced |  |
| R1 | Certificate of conformance per batch | not_evidenced |  |
| R2 | Salt spray test reports on request | not_evidenced |  |
| R3 | RoHS-compliant process chemistry | not_evidenced |  |
| P1 | Co-located with machining capability | not_evidenced |  |
| P2 | Experience with space-grade hardware | not_evidenced |  |

Reasons:
- (T1) The profile confirms that conversion coating is among its services, but it does not substantiate the required MIL-DTL-5541 Type II Class 1A specification.
- (P1) The profile identifies CNC equipment and surface-treatment services, but does not show that the capabilities are co-located.
- (R1) The profile refers to documentation and traceability as standard, but does not identify batch-specific certificates of conformance.

Gaps:
- (M1) The mandatory NADCAP Chemical Processing accreditation is not established; working with accredited partners does not show that Vector holds the accreditation.
- (T1) The profile does not confirm coating to MIL-DTL-5541 Type II Class 1A, so the required coating specification remains unverified.

## Vendor C x RFQ-003  (10.0s)

Score **0**, raw 0, gate passed: False. technical 0.0/40.0, required 0.0/35.0, preferred 0.0/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | Mill test certificates traceable to heat lot | not_evidenced |  |
| T1 | AMS 4911 specification | not_evidenced |  |
| T2 | Thickness range 1.0-6.0 mm | not_evidenced |  |
| T3 | Cut-to-size capability | not_evidenced |  |
| T4 | Material: Ti-6Al-4V Grade 5, AMS 4911 sheet, 1.0-6.0 mm | not_evidenced |  |
| T5 | Quantity: Approx. 2 tonnes per year against a rate contract | not_evidenced |  |
| T6 | Delivery: Call-off against rate contract | not_evidenced |  |
| R1 | ISO 9001 certified | not_evidenced |  |
| R2 | Ability to supply cut-to-size | not_evidenced |  |
| R3 | DFARS-compliant sourcing documentation | not_evidenced |  |
| P1 | Existing stock holding in India | not_evidenced |  |
| P2 | Prior supply to space or defence programmes | not_evidenced |  |
| P3 | Consignment stocking arrangement | not_evidenced |  |

Reasons:
- (M1) No criterion-specific strength is supported for M1; the profile's general documentation and traceability claim does not confirm heat-lot-traceable mill test certificates.
- (T1) No criterion-specific strength is supported for T1 because the profile does not identify AMS 4911.
- (R1) No criterion-specific strength is supported for R1 because the profile does not name ISO 9001 certification.

Gaps:
- (M1) The mandatory requirement for mill test certificates traceable to heat lot is not evidenced.
- (T4) The profile does not establish supply of the specified Ti-6Al-4V Grade 5 AMS 4911 sheet in the required thickness range.
