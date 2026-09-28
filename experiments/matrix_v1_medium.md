# 3 x 3 evaluation matrix (matrix_v1_medium)

Model `gpt-6-luna`, prompt `v1`.

| Vendor | RFQ-001 | RFQ-002 | RFQ-003 |
|---|---|---|---|
| A | **30** (raw 81, gate ✗) | **11** (raw 11, gate ✗) | **12** (raw 12, gate ✓) |
| B | **36** (raw 36, gate ✓) | **5** (raw 5, gate ✗) | **16** (raw 16, gate ✗) |
| C | **7** (raw 7, gate ✗) | **11** (raw 11, gate ✗) | **11** (raw 11, gate ✗) |

## Vendor A x RFQ-001  (28.7s)

Score **30**, raw 81, gate passed: False. technical 33.3/40.0, required 35.0/35.0, preferred 12.5/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | AS9100D certification | not_met | ISO 9001:2015 certified (TUV SUD, valid to March 2028). |
| T1 | Tolerance +/-0.02 mm on critical features | met | Routine working tolerance +/-0.01 mm on 5-axis work |
| T2 | Surface finish Ra 1.6 | met | surface finishes to Ra 0.8 achieved in production on aluminium alloys. |
| T3 | 5-axis machining capability | met | Eleven CNC machining centres including three DMG MORI 5-axis machines (DMU 50, DMU 65 monoBLOCK) |
| T4 | Material: 7075-T6 aluminium, supplied free-issue | partial | Extensive experience with 7075 and 6061 aluminium |
| T5 | Quantity: 250 units | met | Typical lead time for batch quantities of 200-300 machined components |
| T6 | Delivery: 6 weeks from PO | partial | Typical lead time for batch quantities of 200-300 machined components is four to five weeks from receipt of material. |
| R1 | CMM inspection with first-article inspection report per AS9102 | met | In-house metrology: two Zeiss CONTURA CMMs, calibrated annually and traceable to NABL standards...First-article inspection reports issued in AS9102 format on request; currently produced for two customers. |
| R2 | Material traceability to mill test certificate | met | Material traceability maintained against mill test certificates for all incoming stock. |
| P1 | In-house CMM | met | In-house metrology: two Zeiss CONTURA CMMs, calibrated annually and traceable to NABL standards. |
| P2 | Prior aerospace structural work | not_evidenced |  |
| P3 | NADCAP-accredited subcontractors for any outsourced process steps | not_applicable |  |

Reasons:
- (T3) The vendor has three named 5-axis machining centres, directly supporting the required machining capability.
- (R1) The vendor has two in-house CMMs and issues first-article reports in AS9102 format.
- (R2) The vendor states that incoming stock is traceable to mill test certificates.

Gaps:
- (M1) The profile lists ISO 9001:2015 and IATF 16949:2016, but does not establish the mandatory AS9100D certification.
- (T6) The four-to-five-week lead time is measured from receipt of material, so delivery within six weeks from PO is not confirmed.

## Vendor A x RFQ-002  (26.0s)

Score **11**, raw 11, gate passed: False. technical 5.0/40.0, required 0.0/35.0, preferred 6.2/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | NADCAP accreditation for Chemical Processing | not_evidenced |  |
| T1 | Coating per MIL-DTL-5541 Type II Class 1A | not_evidenced |  |
| T2 | Parts up to 600 mm | not_evidenced |  |
| T3 | Quantity: Batch sizes 50-400 units | partial | Typical lead time for batch quantities of 200-300 machined components is four to five weeks from receipt of material. |
| T4 | Delivery: 10 working days turnaround | not_evidenced |  |
| R1 | Certificate of conformance per batch | not_evidenced |  |
| R2 | Salt spray test reports on request | not_evidenced |  |
| R3 | RoHS-compliant process chemistry | not_evidenced |  |
| P1 | Co-located with machining capability | partial | Eleven CNC machining centres |
| P2 | Experience with space-grade hardware | not_evidenced |  |

Reasons:
- (T3) The stated 200–300-unit machining batches fall within the requested quantity range, although coating batch capability is unconfirmed.
- (P1) The profile confirms machining capability, but does not establish that chemical conversion coating is performed at the same site.
- (M1) The profile names ISO 9001 and IATF 16949 certifications, but does not support the required NADCAP Chemical Processing accreditation.

Gaps:
- (M1) The mandatory NADCAP Chemical Processing accreditation is not evidenced in the profile.
- (T1) The profile describes precision machining rather than chemical conversion coating, so MIL-DTL-5541 Type II Class 1A capability is not established.

## Vendor A x RFQ-003  (20.9s)

Score **12**, raw 12, gate passed: True. technical 0.0/40.0, required 11.7/35.0, preferred 0.0/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | Mill test certificates traceable to heat lot | met | tracked by heat lot through to despatch...Material traceability maintained against mill test certificates for all incoming stock. |
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
- (M1) Incoming-stock traceability is linked to mill test certificates, and the profile also describes tracking free-issue stock by heat lot.
- (R1) The vendor states ISO 9001:2015 certification valid to March 2028.
- (T3) The profile establishes precision-machining capability, but does not support a claim of raw-sheet cut-to-size supply.

Gaps:
- (T4) The profile does not establish supply of the specified Ti-6Al-4V Grade 5 AMS 4911 sheet in the required thickness range.
- (R3) DFARS-compliant sourcing documentation is not addressed in the profile.

## Vendor B x RFQ-001  (30.5s)

Score **36**, raw 36, gate passed: True. technical 10.0/40.0, required 26.2/35.0, preferred 0.0/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | AS9100D certification | met | AS9100D certified (valid to August 2027). |
| T1 | Tolerance +/-0.02 mm on critical features | not_met | Demonstrated working tolerance +/-0.05 mm. |
| T2 | Surface finish Ra 1.6 | partial | Surface finish typically Ra 3.2 as machined; better finishes require outsourced grinding or polishing. |
| T3 | 5-axis machining capability | not_met | No 5-axis capability; |
| T4 | Material: 7075-T6 aluminium, supplied free-issue | partial | Limited 7075 experience — two prototype jobs to date, both under 20 pieces. |
| T5 | Quantity: 250 units | not_met | Largest single order to date: 120 pieces. |
| T6 | Delivery: 6 weeks from PO | partial | Typical lead time for batches above 100 pieces is 9 to 11 weeks. |
| R1 | CMM inspection with first-article inspection report per AS9102 | partial | CMM work is outsourced to a NABL-accredited laboratory in Bangalore, adding two to three working days per inspection cycle. ... AS9102 first-article reports prepared in-house using outsourced measurement data. |
| R2 | Material traceability to mill test certificate | met | Full material traceability to mill test certificate, maintained under the AS9100 quality system. |
| P1 | In-house CMM | not_met | No in-house CMM. |
| P2 | Prior aerospace structural work | not_evidenced |  |
| P3 | NADCAP-accredited subcontractors for any outsourced process steps | not_evidenced |  |

Reasons:
- (M1) M1 is met because the vendor reports AS9100D certification valid through August 2027.
- (R2) R2 is met because the vendor confirms full traceability to mill test certificates.
- (R1) R1 is partially supported because the vendor arranges outsourced CMM inspection and prepares AS9102 first-article reports in-house.

Gaps:
- (T3) T3 is not met because the vendor explicitly has no 5-axis capability.
- (T1) T1 is not met because the demonstrated +/-0.05 mm tolerance is looser than the required +/-0.02 mm.

## Vendor B x RFQ-002  (27.7s)

Score **5**, raw 5, gate passed: False. technical 5.0/40.0, required 0.0/35.0, preferred 0.0/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | NADCAP accreditation for Chemical Processing | not_evidenced |  |
| T1 | Coating per MIL-DTL-5541 Type II Class 1A | not_evidenced |  |
| T2 | Parts up to 600 mm | not_evidenced |  |
| T3 | Quantity: Batch sizes 50-400 units | partial | Largest single order to date: 120 pieces. |
| T4 | Delivery: 10 working days turnaround | not_evidenced |  |
| R1 | Certificate of conformance per batch | not_evidenced |  |
| R2 | Salt spray test reports on request | not_evidenced |  |
| R3 | RoHS-compliant process chemistry | not_evidenced |  |
| P1 | Co-located with machining capability | not_evidenced |  |
| P2 | Experience with space-grade hardware | not_evidenced |  |

Reasons:
- (T3) A 120-piece largest order provides limited evidence within the requested 50–400-unit range, but does not establish capacity at the upper end or for coating batches.
- (P1) The profile lists CNC machining capability, but it does not establish that a chemical conversion coating operation is co-located.
- (R1) Material traceability to mill test certificates is documented, but that does not establish batch-specific certificates of conformance.

Gaps:
- (M1) The mandatory NADCAP accreditation for Chemical Processing is not evidenced in the profile.
- (T1) The profile does not describe chemical conversion coating services or qualification to MIL-DTL-5541 Type II Class 1A.

## Vendor B x RFQ-003  (17.6s)

Score **16**, raw 16, gate passed: False. technical 0.0/40.0, required 11.7/35.0, preferred 4.2/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | Mill test certificates traceable to heat lot | partial | Full material traceability to mill test certificate |
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
| P2 | Prior supply to space or defence programmes | partial | Two aerospace GSE manufacturers. |
| P3 | Consignment stocking arrangement | not_evidenced |  |

Reasons:
- (R1) The vendor states it is ISO 9001:2015 certified, satisfying the required quality-system criterion.
- (M1) The profile supports traceability to mill test certificates, although heat-lot traceability remains unconfirmed.
- (P2) The vendor lists two aerospace GSE manufacturers as references, but does not establish prior supply to space or defence programmes.

Gaps:
- (M1) The mandatory traceability statement does not specifically confirm that mill test certificates are traceable to heat lot.
- (T4) The profile provides no evidence that the vendor can supply Ti-6Al-4V Grade 5 AMS 4911 sheet in the requested thickness range.

## Vendor C x RFQ-001  (18.8s)

Score **7**, raw 7, gate passed: False. technical 6.7/40.0, required 0.0/35.0, preferred 0.0/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | AS9100D certification | not_evidenced |  |
| T1 | Tolerance +/-0.02 mm on critical features | not_evidenced |  |
| T2 | Surface finish Ra 1.6 | not_evidenced |  |
| T3 | 5-axis machining capability | partial | From complex multi-axis machined components to finished, treated and fully certified assemblies, we handle it end to end. |
| T4 | Material: 7075-T6 aluminium, supplied free-issue | partial | Our raw material division maintains strong relationships with leading global mills and can source aerospace-grade alloys in a wide range of forms and specifications. |
| T5 | Quantity: 250 units | not_evidenced |  |
| T6 | Delivery: 6 weeks from PO | not_evidenced |  |
| R1 | CMM inspection with first-article inspection report per AS9102 | not_evidenced |  |
| R2 | Material traceability to mill test certificate | not_evidenced |  |
| P1 | In-house CMM | not_evidenced |  |
| P2 | Prior aerospace structural work | not_evidenced |  |
| P3 | NADCAP-accredited subcontractors for any outsourced process steps | not_evidenced |  |

Reasons:
- (T3) The profile describes complex multi-axis machining, although it does not establish the required five-axis capability.
- (T4) The vendor states it can source aerospace-grade alloys, but leaves the required 7075-T6 grade and free-issue arrangement unconfirmed.
- (P2) The profile identifies aerospace-sector customer experience, but does not specify structural work.

Gaps:
- (M1) AS9100D certification is not evidenced, so the mandatory certification requirement remains unverified.
- (R1) CMM inspection and an AS9102 first-article report are not evidenced.

## Vendor C x RFQ-002  (23.3s)

Score **11**, raw 11, gate passed: False. technical 5.0/40.0, required 0.0/35.0, preferred 6.2/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | NADCAP accreditation for Chemical Processing | not_evidenced |  |
| T1 | Coating per MIL-DTL-5541 Type II Class 1A | partial | We offer a complete suite of surface treatment and special process services, including conversion coating, anodising and passivation, carried out to international aerospace specifications. |
| T2 | Parts up to 600 mm | not_evidenced |  |
| T3 | Quantity: Batch sizes 50-400 units | not_evidenced |  |
| T4 | Delivery: 10 working days turnaround | not_evidenced |  |
| R1 | Certificate of conformance per batch | not_evidenced |  |
| R2 | Salt spray test reports on request | not_evidenced |  |
| R3 | RoHS-compliant process chemistry | not_evidenced |  |
| P1 | Co-located with machining capability | partial | Our state-of-the-art facility houses a comprehensive range of modern CNC equipment capable of meeting the tightest tolerances demanded by today's aerospace programmes. ... We offer a complete suite of surface treatment and special process services, including conversion coating, anodising and passivation, carried out to international aerospace specifications. |
| P2 | Experience with space-grade hardware | not_evidenced |  |

Reasons:
- (T1) Conversion coating is explicitly included in the offered services, although the required MIL-DTL-5541 type and class are not identified.
- (P1) The profile describes both CNC equipment and surface treatment services, but does not confirm that they are co-located.
- (P2) The profile uses the phrase “Space-grade heritage,” but gives no specific hardware examples to substantiate this as relevant experience.

Gaps:
- (M1) NADCAP accreditation for Chemical Processing is not evidenced, leaving the mandatory accreditation requirement unverified.
- (T1) The profile does not confirm coating to MIL-DTL-5541 Type II Class 1A.

## Vendor C x RFQ-003  (25.4s)

Score **11**, raw 11, gate passed: False. technical 6.7/40.0, required 0.0/35.0, preferred 4.2/25.0

| Id | Requirement | Verdict | Evidence |
|---|---|---|---|
| M1 | Mill test certificates traceable to heat lot | not_evidenced |  |
| T1 | AMS 4911 specification | partial | a wide range of forms and specifications. |
| T2 | Thickness range 1.0-6.0 mm | not_evidenced |  |
| T3 | Cut-to-size capability | not_evidenced |  |
| T4 | Material: Ti-6Al-4V Grade 5, AMS 4911 sheet, 1.0-6.0 mm | partial | can source aerospace-grade alloys in a wide range of forms and specifications. |
| T5 | Quantity: Approx. 2 tonnes per year against a rate contract | not_evidenced |  |
| T6 | Delivery: Call-off against rate contract | not_evidenced |  |
| R1 | ISO 9001 certified | not_evidenced |  |
| R2 | Ability to supply cut-to-size | not_evidenced |  |
| R3 | DFARS-compliant sourcing documentation | not_evidenced |  |
| P1 | Existing stock holding in India | not_evidenced |  |
| P2 | Prior supply to space or defence programmes | partial | serving demanding customers across aerospace, defence, space and precision engineering. |
| P3 | Consignment stocking arrangement | not_evidenced |  |

Reasons:
- (T1) T1: The profile indicates broad aerospace-alloy sourcing, although it does not confirm AMS 4911.
- (T4) T4: The vendor describes sourcing aerospace-grade alloys, but the required titanium grade, sheet form, and thickness range remain unconfirmed.
- (P2) P2: The vendor claims to serve customers across space and defence, but provides no specific programme references.

Gaps:
- (M1) M1: The mandatory requirement for mill test certificates traceable to heat lot is not evidenced.
- (T4) T4: The profile does not confirm Ti-6Al-4V Grade 5 AMS 4911 sheet or the required 1.0–6.0 mm thickness range.
