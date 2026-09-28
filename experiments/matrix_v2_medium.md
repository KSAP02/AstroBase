# 3 x 3 evaluation matrix (matrix_v2_medium)

Model `gpt-6-luna`, prompt `v2`.

| Vendor | RFQ-001 | RFQ-002 | RFQ-003 |
|---|---|---|---|
| A | **30** (raw 80, gate ✗) | **0** (raw 0, gate ✗) | **12** (raw 12, gate ✓) |
| B | **42** (raw 42, gate ✓) | **5** (raw 5, gate ✗) | **12** (raw 12, gate ✗) |
| C | **0** (raw 0, gate ✗) | **0** (raw 0, gate ✗) | **0** (raw 0, gate ✗) |

## Vendor A x RFQ-001  (17.7s)

Score **30**, raw 80, gate passed: False. technical 36.7/40.0, required 35.0/35.0, preferred 8.3/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | AS9100D certification | not_met | ISO 9001:2015 certified (TUV SUD, valid to March 2028). ... IATF 16949:2016 certified. |
| T1 | Tolerance +/-0.02 mm on critical features | met | Routine working tolerance +/-0.01 mm on 5-axis work |
| T2 | Surface finish Ra 1.6 | met | surface finishes to Ra 0.8 achieved in production on aluminium alloys. |
| T3 | 5-axis machining capability | met | three DMG MORI 5-axis machines (DMU 50, DMU 65 monoBLOCK) |
| T4 | Material: 7075-T6 aluminium, supplied free-issue | met | Extensive experience with 7075 and 6061 aluminium, including free-issue material programmes where customer-supplied stock is logged, segregated and tracked by heat lot through to despatch. |
| T5 | Quantity: 250 units | met | Typical lead time for batch quantities of 200-300 machined components is four to five weeks from receipt of material. |
| T6 | Delivery: 6 weeks from PO | partial | Typical lead time for batch quantities of 200-300 machined components is four to five weeks from receipt of material. |
| R1 | CMM inspection with first-article inspection report per AS9102 | met | In-house metrology: two Zeiss CONTURA CMMs, calibrated annually and traceable to NABL standards. ... First-article inspection reports issued in AS9102 format on request; currently produced for two customers. |
| R2 | Material traceability to mill test certificate | met | Material traceability maintained against mill test certificates for all incoming stock. |
| P1 | In-house CMM | met | In-house metrology: two Zeiss CONTURA CMMs, calibrated annually and traceable to NABL standards. |
| P2 | Prior aerospace structural work | not_evidenced |  |
| P3 | NADCAP-accredited subcontractors for any outsourced process steps | not_evidenced |  |

Reasons:
- (T1) The vendor states a routine +/-0.01 mm tolerance on 5-axis work, tighter than the required +/-0.02 mm.
- (T3) The vendor identifies three DMG MORI 5-axis machines.
- (R2) The vendor maintains material traceability against mill test certificates for all incoming stock.

Gaps:
- (M1) The mandatory AS9100D certification is not stated; the profile lists ISO 9001:2015 and IATF 16949:2016 instead.
- (T6) The stated four-to-five-week lead time starts from receipt of material, so delivery within six weeks from PO is not established.

## Vendor A x RFQ-002  (17.7s)

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
- (P1) The profile describes in-house precision machining, but does not establish co-location with a chemical conversion coating operation.
- (R1) Material traceability is described, but batch-level certificates of conformance for surface treatment are not stated.
- (P2) The profile identifies automotive and orthopaedic customers, but provides no specific space-grade hardware experience.

Gaps:
- (M1) NADCAP Chemical Processing accreditation is not evidenced, leaving the mandatory accreditation requirement unverified.
- (T1) The profile does not identify chemical conversion coating capability or compliance with MIL-DTL-5541 Type II Class 1A.

## Vendor A x RFQ-003  (16.3s)

Score **12**, raw 12, gate passed: True. technical 0.0/40.0, required 11.7/35.0, preferred 0.0/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | Mill test certificates traceable to heat lot | met | customer-supplied stock is logged, segregated and tracked by heat lot through to despatch...Material traceability maintained against mill test certificates for all incoming stock. |
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
- (M1) M1 is supported: incoming stock is traceable against mill test certificates, and customer-supplied stock is tracked by heat lot through despatch.
- (R1) R1 is supported by the stated ISO 9001:2015 certification, valid to March 2028.
- (T1) No third criterion-specific strength is evidenced; the profile describes machining experience on aluminium alloys, not AMS 4911 titanium-sheet supply.

Gaps:
- (T1) The profile does not establish capability to supply material to the required AMS 4911 specification.
- (T4) The profile does not establish supply of Ti-6Al-4V Grade 5 AMS 4911 sheet in the specified thickness range.

## Vendor B x RFQ-001  (21.8s)

Score **42**, raw 42, gate passed: True. technical 6.7/40.0, required 35.0/35.0, preferred 0.0/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | AS9100D certification | met | AS9100D certified (valid to August 2027). |
| T1 | Tolerance +/-0.02 mm on critical features | not_met | Demonstrated working tolerance +/-0.05 mm. |
| T2 | Surface finish Ra 1.6 | not_met | Surface finish typically Ra 3.2 as machined; better finishes require outsourced grinding or polishing. |
| T3 | 5-axis machining capability | not_met | No 5-axis capability; |
| T4 | Material: 7075-T6 aluminium, supplied free-issue | partial | Limited 7075 experience — two prototype jobs to date, both under 20 pieces. |
| T5 | Quantity: 250 units | not_met | Largest single order to date: 120 pieces. |
| T6 | Delivery: 6 weeks from PO | partial | Typical lead time for batches above 100 pieces is 9 to 11 weeks. |
| R1 | CMM inspection with first-article inspection report per AS9102 | met | CMM work is outsourced to a NABL-accredited laboratory in Bangalore, adding two to three working days per inspection cycle. ... AS9102 first-article reports prepared in-house using outsourced measurement data. |
| R2 | Material traceability to mill test certificate | met | Full material traceability to mill test certificate, maintained under the AS9100 quality system. |
| P1 | In-house CMM | not_met | No in-house CMM. |
| P2 | Prior aerospace structural work | not_evidenced |  |
| P3 | NADCAP-accredited subcontractors for any outsourced process steps | not_evidenced |  |

Reasons:
- (M1) The vendor states that it holds AS9100D certification valid through August 2027.
- (R1) The vendor can provide outsourced CMM inspection and prepare AS9102 first-article reports using the measurement data.
- (R2) The profile confirms full traceability of material to mill test certificates.

Gaps:
- (T3) The vendor explicitly has no 5-axis capability, which does not meet the technical requirement.
- (T1) The demonstrated +/-0.05 mm tolerance is looser than the required +/-0.02 mm on critical features.

## Vendor B x RFQ-002  (24.4s)

Score **5**, raw 5, gate passed: False. technical 5.0/40.0, required 0.0/35.0, preferred 0.0/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | NADCAP accreditation for Chemical Processing | not_evidenced |  |
| T1 | Coating per MIL-DTL-5541 Type II Class 1A | not_evidenced |  |
| T2 | Parts up to 600 mm | not_evidenced |  |
| T3 | Quantity: Batch sizes 50-400 units | partial | Largest single order to date: 120 pieces. |
| T4 | Delivery: 10 working days turnaround | not_met | Typical lead time for batches above 100 pieces is 9 to 11 weeks. |
| R1 | Certificate of conformance per batch | not_evidenced |  |
| R2 | Salt spray test reports on request | not_evidenced |  |
| R3 | RoHS-compliant process chemistry | not_evidenced |  |
| P1 | Co-located with machining capability | not_evidenced |  |
| P2 | Experience with space-grade hardware | not_evidenced |  |

Reasons:
- (T3) T3 has a specific positive capability signal: the vendor has delivered a 120-piece order, within the requested batch range, though capacity up to 400 units is unestablished.
- (P1) P1 is not supported: the profile identifies machining capability but does not establish that the requested coating process is co-located.
- (P2) P2 is not supported because no space-grade hardware experience is identified in the profile.

Gaps:
- (M1) The mandatory NADCAP accreditation for Chemical Processing is not evidenced, so this qualification remains unverified.
- (T1) The profile does not evidence chemical conversion coating to MIL-DTL-5541 Type II Class 1A, the core technical requirement of this RFQ.

## Vendor B x RFQ-003  (15.5s)

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
- (R1) R1: The profile explicitly states that the vendor is ISO 9001:2015 certified.
- (M1) M1: The profile states full material traceability to mill test certificates, although heat-lot linkage is not confirmed.
- (T3) T3: The profile supports component machining capability, but does not establish cut-to-size supply of raw sheet.

Gaps:
- (M1) M1: The mandatory heat-lot traceability requirement is not specifically confirmed.
- (T4) T4: The profile does not establish supply of the specified Ti-6Al-4V Grade 5 AMS 4911 sheet.

## Vendor C x RFQ-001  (13.6s)

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
- (T3) The profile describes complex multi-axis machining, but does not confirm the required 5-axis capability.
- (T4) The vendor mentions sourcing aerospace-grade alloys, but does not specify 7075-T6 or free-issue material.
- (R2) The profile refers to documentation and traceability, but does not establish traceability to a mill test certificate.

Gaps:
- (M1) AS9100D certification is not stated, leaving the mandatory certification requirement unverified.
- (T1) No tolerance data is provided to verify the required +/-0.02 mm on critical features.

## Vendor C x RFQ-002  (15.8s)

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
- (T1) The profile identifies conversion coating as a service, but does not substantiate the RFQ's specific coating specification.
- (P1) The profile describes CNC machining capability, although it does not establish co-location with surface treatment.
- (R1) The profile states that documentation and traceability are provided as standard, but does not confirm batch-specific certificates of conformance.

Gaps:
- (M1) NADCAP Chemical Processing accreditation is not evidenced, leaving the mandatory accreditation requirement unverified.
- (T1) The profile does not confirm coating to MIL-DTL-5541 Type II Class 1A.

## Vendor C x RFQ-003  (13.9s)

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
- (M1) The profile makes a general claim of documentation and traceability, but does not establish heat-lot-traceable mill test certificates.
- (T1) The raw-material division can source aerospace-grade alloys, but the profile does not identify AMS 4911.
- (P2) The vendor lists aerospace, defence and space among the sectors it serves, but does not substantiate prior supply to a programme.

Gaps:
- (M1) The mandatory requirement for mill test certificates traceable to heat lot is not specifically supported by the profile.
- (T4) The profile does not confirm availability of Ti-6Al-4V Grade 5 AMS 4911 sheet in the required 1.0–6.0 mm thickness range.
