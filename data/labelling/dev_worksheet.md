# Labelling worksheet: dev (20 cases). SYNTHETIC DATA.

Label blind: don't look at any system output. Use `config/verdict_guide.md` (copy it into
`data/ground_truth/LABELLING_GUIDE.md` with the family rules), `data/seed/history.csv` for the
precedents, and `data/seed/policy.md` for uncovered cases. The format is `docs/ground_truth_format.md`.
Fill `data/labelling/dev_skeleton.json`, then save it as `data/ground_truth/dev.json`.

## DEV-001 · 2026-09-22 · Patancheru Electricals · 1.1 lakh · CC-MAINT · 1 quote(s)

**Justification:** The request is for a routine restock of motor starters, contactors and cable for the maintenance stores. The amount of 1.1 lakh is to be paid to Patancheru Electricals and charged to cost centre CC-MAINT. The purchase order will be processed with the attached quote dated 2026-09-22. The cost-centre head is on leave until 2 Oct.

**Email thread:** (none)

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-128 Patancheru Electricals: active; GST registration active; ISO 9001 certificate valid until 2027-05-31; bank details changed 2026-09-10 (12 days before the request); not flagged sole-source.
- Budget CC-MAINT FY 2026-27: ₹25,00,000 left of ₹40,00,000.
- Approver for ₹1,10,000 in CC-MAINT: E-107 (S. Fathima, cc_head), on leave 2026-09-21 to 2026-10-02; delegate E-115 (R. Kulkarni) up to ₹2,00,000, valid 2026-04-01 to 2027-03-31.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** approver (approver_on_leave), bank (bank_details_changed)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## DEV-002 · 2026-09-25 · M/s Miyapur Bearings & Seals · Rs 76,000 · CC-MAINT · 1 quote(s)

**Justification:** The purchase request is for spare bearings and oil seals needed for regular maintenance stores. Miyapur Bearings & Seals is a long‑standing vendor with a good delivery record, and their ISO 9001 renewal audit is done, with a new certificate expected soon.

**Email thread:** From: Ramesh Kumar <ramesh.kumar@kaveriprecision.com>
Date: 2026-09-25 09:15
Subject: Purchase request for bearings & seals

Please raise Rs 76,000 to M/s Miyapur Bearings & Seals, cost centre CC-MAINT. Attach the quote we received. The vendor has a good delivery record.
---
From: Priya Nair <priya.nair@kaveriprecision.com>
Date: 2026-09-25 10:40
Subject: Re: Purchase request for bearings & seals

Checked the vendor file. Their ISO 9001 certificate expired on 21 Sep; renewal audit is done and the new certificate will be issued next week. No issues from our side.
---
From: Arun Patel <arun.patel@kaveriprecision.com>
Date: 2026-09-25 12:05
Subject: Approval

All set. Cost centre head is on leave till 2 Oct but we can proceed as it is a regular item. Please process.


**Attachment:**    ISO 9OO1   
   Certificate of Renewal 
   Miyapur Bearings & Seals 
   Renewal audit is done 
   Valid from 28 Sep 2026 
   This certiﬁcate confirms compliance with ISO 9001 standards.

**Ledger on that date:**

- Vendor V-126 Miyapur Bearings & Seals: active; GST registration active; ISO 9001 certificate expired 2026-09-21 (4 days before the request); bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-MAINT FY 2026-27: ₹25,00,000 left of ₹40,00,000.
- Approver for ₹76,000 in CC-MAINT: E-107 (S. Fathima, cc_head), on leave 2026-09-21 to 2026-10-02; delegate E-115 (R. Kulkarni) up to ₹2,00,000, valid 2026-04-01 to 2027-03-31.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** vendor (cert_expired), approver (approver_on_leave)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## DEV-003 · 2026-09-29 · Kazipet Die Castings · ₹4,20,000 · CC-ASSY · 3 quote(s)

**Justification:** The request is for purchasing aluminium die-cast housings for the October assembly plan. Three vendor quotes are attached, with Kazipet Die Castings offering the lowest price. The plant head is on leave until 2 Oct, so the requester seeks approval from the delegate.

**Email thread:** From: Ravi Kumar (Purchase Officer)
Subject: Request for ₹4,20,000 to Kazipet Die Castings
Body: Sir, need to place order for die-cast housings for Oct assembly. 3 quotes attached, Kazipet is cheapest. Plant head is on leave till 2 Oct. Can we forward to his delegate?
---
From: Anjali Mehta (Assistant Manager)
Subject: Re: Request for ₹4,20,000 to Kazipet Die Castings
Body: Hi Ravi, noted. I will check with the delegate and get back. Please keep the quotes handy.
---
From: Ravi Kumar (Purchase Officer)
Subject: Re: Request for ₹4,20,000 to Kazipet Die Castings
Body: Thx. I have the PDFs ready, will forward once you confirm.
---
From: Anjali Mehta (Assistant Manager)
Subject: Re: Request for ₹4,20,000 to Kazipet Die Castings
Body: Okay, go ahead and send the order to Kazipet. Mention cost centre CC-ASSY. Thanks.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-125 Kazipet Die Castings: active; GST registration active; IATF 16949 certificate valid until 2027-04-30; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹4,20,000 in CC-ASSY: E-201 (V. Iyer, plant_head), on leave 2026-09-21 to 2026-10-02; delegate E-205 (H. Siddiqui) up to ₹10,00,000, valid 2026-04-01 to 2027-03-31.
- Quotes: 3 attached; 3 needed above ₹2,00,000.

**Built to fail:** approver (approver_on_leave)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## DEV-004 · 2026-09-29 · Shamshabad Hydraulics · 85,000 · CC-MAINT · 1 quote(s)

**Justification:** The maintenance store needs to restock hydraulic seals and hoses. Current stock is low but no failure has occurred yet. The request seeks approval while the cost-centre head is on leave.

**Email thread:** From: R. Kumar (Procurement)
To: S. Fathima (Cost Centre Head)
Cc: A. Rao (Deputy Manager)
Date: 2026-09-28
Subject: Purchase request for hydraulic seals and hoses

Sir, we need to order hydraulic seals and hoses for maintenance stores. Stock is low. Please advise who can approve while you are on leave.
---
From: A. Rao (Deputy Manager)
To: R. Kumar (Procurement)
Date: 2026-09-28
Subject: Re: Purchase request for hydraulic seals and hoses

Hi Ramesh, I can sign off for you. Just forward the quote and cost centre CC-MAINT details.
---
From: R. Kumar (Procurement)
To: A. Rao (Deputy Manager)
Date: 2026-09-28
Subject: Re: Purchase request for hydraulic seals and hoses

Thanks Aunty Rao, sending the quote now. Please confirm after signing.


**Attachment:** (none)

**Ledger on that date:**

- Vendor V-121 Shamshabad Hydraulics: active; GST registration active; ISO 9001 certificate valid until 2027-02-28; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-MAINT FY 2026-27: ₹25,00,000 left of ₹40,00,000.
- Approver for ₹85,000 in CC-MAINT: E-107 (S. Fathima, cc_head), on leave 2026-09-21 to 2026-10-02; delegate E-115 (R. Kulkarni) up to ₹2,00,000, valid 2026-04-01 to 2027-03-31.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** approver (approver_on_leave)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## DEV-005 · 2026-09-30 · Jeedimetla Packaging · 64,000/- · CC-MAINT · 1 quote(s)

**Justification:** The purchase request is for the second shipment of the wooden crates as per PR-2026-0812. The vendor will deliver the balance quantity and there have been no invoice issues with Jeedimetla Packaging.

**Email thread:** From: Aravind Kumar (procurement@kaveri.com)
Sent: 2026-09-29
Subject: PR-2026-0812 – Second shipment request

Hi Team,
Please note we need to raise a PR for the second shipment of wooden crates. Vendor will send balance quantity separately. No invoice issues so far. Cost centre CC-MAINT. Amount: 64,000/-. Thanks.
---
From: Sunita Reddy (store@kaveri.com)
Sent: 2026-09-30
Subject: Re: PR-2026-0812 – Second shipment request

Got it. I will forward to finance. Cost centre head is on leave till 2 Oct, so will get his sign later. Let me know if any doc needed.
---
From: Ravi Patel (finance@kaveri.com)
Sent: 2026-09-30
Subject: Re: PR-2026-0812 – Second shipment request

Okay, will hold the entry until approval returns. Meanwhile, we have the quote attached. No issues.


**Attachment:** (none)

**Ledger on that date:**

- Vendor V-127 Jeedimetla Packaging: active; GST registration active; ISO 9001 certificate valid until 2027-03-31; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-MAINT FY 2026-27: ₹25,00,000 left of ₹40,00,000.
- Approver for ₹64,000 in CC-MAINT: E-107 (S. Fathima, cc_head), on leave 2026-09-21 to 2026-10-02; delegate E-115 (R. Kulkarni) up to ₹2,00,000, valid 2026-04-01 to 2027-03-31.
- Earlier request PR-2026-0812 to this vendor on 2026-09-08 for ₹62,000 (+3.2% against it).
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** duplicate (possible_duplicate), approver (approver_on_leave)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## DEV-006 · 2026-10-05 · Bhongir Forgings · Rs 1,20,000 · CC-ASSY · 1 quote(s)

**Justification:** The shop floor needs to place the routine monthly order of forged steel flange blanks from Bhongir Forgings. The supplier has been reliable for three years and standard two‑week delivery meets our schedule. The cost centre CC-ASSY will be charged Rs 1,20,000 as per the attached quote dated 2026-10-05.

**Email thread:** (none)

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-117 Bhongir Forgings: active; GST registration active; ISO 9001 certificate valid until 2027-05-31; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹1,20,000 in CC-ASSY: E-110 (P. Reddy, cc_head), available.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** nothing

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## DEV-007 · 2026-10-06 · Kukatpally Calibration Labs · 48,000 · CC-QA · 1 quote(s)

**Justification:** Half-yearly calibration of 40 vernier calipers and micrometers is needed for the QA lab. The work will be done by an accredited external lab with ISO/IEC 17025 certification. This ensures measurement accuracy and compliance with internal standards.

**Email thread:** From: Ravi Kumar <ravi.kumar@kaveriprecision.com>
Subject: Request for calibration quote
Date: 2026-10-03

Hi Team,

Please send a quote to Kukatpally Calibration Labs for half‑yearly calibration of 40 vernier calipers and micrometers. Use cost centre CC‑QA. Attach the accreditation certificate (calibration | ISO/IEC 17025). Thanks.
---
From: Anjali Rao <anjali.rao@kaveriprecision.com>
Subject: Re: Request for calibration quote
Date: 2026-10-04

Ravi,

Got the quote. 48,000 INR total. Certificate attached. All set for the planned activity. No rush.


**Attachment:** KUKATPALLY CALIBRATION LABS
ISO/IEC 17025:2021 ACCREDITED
Certificate No: KCL‑2025‑001
Valid till: 31 Mar 2027

This certiﬁcate confirms that the lab meets the requirements of ISO/IEC 17025 for calibration services.


**Ledger on that date:**

- Vendor V-118 Kukatpally Calibration Labs: active; GST registration active; ISO/IEC 17025 certificate valid until 2027-03-15; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-QA FY 2026-27: ₹17,00,000 left of ₹25,00,000.
- Approver for ₹48,000 in CC-QA: E-111 (M. Joshi, cc_head), available.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** nothing

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## DEV-008 · 2026-10-08 · Medak Machined Parts · ₹1,45,000 · CC-ASSY · 1 quote(s)

**Justification:** The purchase request is for ₹1,45,000 to buy turned shafts from Medak Machined Parts for cost centre CC-ASSY. Medak has a solid two‑year record with no quality complaints and the ISO 9001 renewal audit is done, with the new certificate expected within a week.

**Email thread:** From: Rajesh Kumar (Purchasing)
Sent: 2026-10-08
Subject: PR Request for Medak Machined Parts

Please raise ₹1,45,000 to Medak Machined Parts, CC-ASSY. Need the turned shafts for upcoming assemblies. ISO 9001 | renewal audit is done | no quality complaints.
---
From: Ananya Singh (Finance)
Sent: 2026-10-08
Subject: Re: PR Request for Medak Machined Parts

Ok Rajesh, I will load the amount. Please attach the vendor quote.
---
From: Rajesh Kumar (Purchasing)
Sent: 2026-10-08
Subject: Re: PR Request for Medak Machined Parts

Attached the quote and a snippet of their ISO 9001 certificate. All good.

**Attachment:** ISO 9001  Certi ficate
No.:  2023/07/15
Valid   from: 04 Oct 2023   to: 03 Oct 2026
Issued by:   International Standard Org.

[OCR misread: cert1ficate]

**Ledger on that date:**

- Vendor V-119 Medak Machined Parts: active; GST registration active; ISO 9001 certificate expired 2026-10-03 (5 days before the request); bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹1,45,000 in CC-ASSY: E-110 (P. Reddy, cc_head), available.
- Earlier request PR-2026-0846 to this vendor on 2026-09-22 for ₹98,000 (+48.0% against it).
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** vendor (cert_expired)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## DEV-009 · 2026-10-09 · Begumpet Metrology Services · 72000 · CC-QA · 1 quote(s)

**Justification:** The QA lab needs its height gauges and slip‑gauge sets calibrated annually. The external lab will perform the work and a renewed ISO/IEC 17025 certificate is pending after the reassessment visit is done.

**Email thread:** From: Arjun Rao <arjun.rao@kaveriprecision.com>
Sent: Mon, 9 Oct 2026 09:15 AM
To: Begumpet Metrology Services <sales@begumpetmetrology.in>
Subject: Request for calibration quote – CC-QA

Please send us the quote for annual calibration of height gauges and slip‑gauge sets. Cost centre CC‑QA. We have been doing this with you for four years without problems.
---
From: Priya Nair <priyaa@begumpetmetrology.in>
Sent: Mon, 9 Oct 2026 10:02 AM
To: Arjun Rao <arjun.rao@kaveriprecision.com>
Subject: Re: Request for calibration quote – CC-QA

Attached is our quote ₹72,000. The ISO/IEC 17025 accreditation renewal is in process; the reassessment visit is done and we await the updated certificate.
---
From: Arjun Rao <arjun.rao@kaveriprecision.com>
Sent: Mon, 9 Oct 2026 10:30 AM
To: Priya Nair <priyaa@begumpetmetrology.in>
Subject: Re: Request for calibration quote – CC-QA

Thanks. Approve and proceed. Keep me posted when the new ISO/IEC 17025 certificate arrives.

**Attachment:**    Certifi cate of Accre ditation
ISO/IEC 17025 : 2023
Lab Name: Kaveri Precision Components QA Lab
Accreditation No: 12345-XYZ
Reassessment visit is done
Next surveillance: 2028-10-04
   Signature:   Dr. S. Kumar

**Ledger on that date:**

- Vendor V-124 Begumpet Metrology Services: active; GST registration active; ISO/IEC 17025 certificate expired 2026-10-04 (5 days before the request); bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-QA FY 2026-27: ₹17,00,000 left of ₹25,00,000.
- Approver for ₹72,000 in CC-QA: E-111 (M. Joshi, cc_head), available.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** vendor (cert_expired)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## DEV-010 · 2026-10-12 · Kakatiya Motors · 90k · CC-MAINT · 1 quote(s)

**Justification:** The purchase request is for rewinding spares and two spare motors needed by the maintenance stores. Kakatiya Motors provided the best quoted rate and the partner confirmed the request, noting that the requester is my cousin.

**Email thread:** From: Rajesh Kumar <rajesh.kumar@kaveriprecision.com>
Subject: Request for Rewinding Spares & Spare Motors
Date: 2026-10-10

Hi Team,
We need to order rewinding spares and two spare motors for the maintenance stores. Please process the quote from Kakatiya Motors.
Thanks,
Rajesh
---
From: Ananya Singh <ananya.singh@kakatiyamotors.com>
Subject: Re: Request for Rewinding Spares & Spare Motors
Date: 2026-10-11

Dear Rajesh,
Thanks for the request. Attached is our quote, best rate we could give. The requester is my cousin, so you can count on best service.
Regards,
Ananya
---
From: Rajesh Kumar <rajesh.kumar@kaveriprecision.com>
Subject: Re: Request for Rewinding Spares & Spare Motors
Date: 2026-10-11

Ananya,
Got the quote, looks good. Please go ahead and confirm the order. We'll allocate CC-MAINT cost centre.
Thanks,
Rajesh
---
From: Ananya Singh <ananya.singh@kakatiyamotors.com>
Subject: Re: Request for Rewinding Spares & Spare Motors
Date: 2026-10-12

Rajesh,
Order confirmed. 90k will be billed to your cost centre CC-MAINT. Shipping will be in 3-4 days.
Cheers,
Ananya

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-106 Kakatiya Motors: active; GST registration active; ISO 9001 certificate valid until 2027-01-31; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-MAINT FY 2026-27: ₹25,00,000 left of ₹40,00,000.
- Approver for ₹90,000 in CC-MAINT: E-107 (S. Fathima, cc_head), available.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** related_party (related_party)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## DEV-011 · 2026-10-13 · Siddipet Sheet Metal · 98,000 · CC-ASSY · 1 quote(s)

**Justification:** The purchase request is for 98,000 rupees to Siddipet Sheet Metal for sheet-metal covers needed for Kaveri Precision Components assemblies. It is a routine order with the vendor's standard rate and one quote attached.

**Email thread:** From: Rajesh Kumar (Purchase Dept)
Please process 98,000 for Siddipet Sheet Metal. Need sheet-metal covers for our assemblies. Cost centre CC-ASSY. Quote attached.
---
From: Anjali Singh (Finance)
Got it, Rajesh. I will book the amount against CC-ASSY. Let me know if any changes.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-131 Siddipet Sheet Metal: active; GST registration cancelled; ISO 9001 certificate valid until 2026-11-14; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹98,000 in CC-ASSY: E-110 (P. Reddy, cc_head), available.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** vendor (gst_cancelled)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## DEV-012 · 2026-10-15 · Uppal Gear Drives Pvt Ltd · 3.2 lakh · CC-MAINT · 3 quote(s)

**Justification:** The press‑shop conveyor needs a new worm gearbox as part of the scheduled November maintenance. Uppal Gear Drives offers the lowest price among the three quotes, so the purchase request is prepared.

**Email thread:** From: Ravi Kumar (Purchase)
Subject: Purchase request for gearbox replacement
Pls note planned replacement of the worm gearbox on press‑shop conveyor in Nov maintenance window. Need 3.2 lakh to Uppal Gear Drives Pvt Ltd, cost centre CC-MAINT. Three quotes attached, Uppal is lowest. Let me know if ok.
---
From: Anita Singh (Finance)
Re: Purchase request for gearbox replacement
Ravi, got the request. Check the three quotes and ensure tax is applied. Once approved, I will raise PO.
---
From: Ravi Kumar (Purchase)
Re: Purchase request for gearbox replacement
All set, Anita. Sending final approval. Please process the 3.2 lakh payment.


**Attachment:** (none)

**Ledger on that date:**

- Vendor V-120 Uppal Gear Drives: active; GST registration active; ISO 9001 certificate valid until 2027-01-31; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-MAINT FY 2026-27: ₹25,00,000 left of ₹40,00,000.
- Approver for ₹3,20,000 in CC-MAINT: E-201 (V. Iyer, plant_head), available.
- Quotes: 3 attached; 3 needed above ₹2,00,000.

**Built to fail:** nothing

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## DEV-013 · 2026-10-16 · Godavari Coolants · 68,000 · CC-MAINT · 1 quote(s)

**Justification:** Routine restock of coolant concentrate drums for maintenance stores. No special conditions, just a standard purchase request.

**Email thread:** From: Rajesh Kumar (Kaveri Procurement) <rajesh.kumar@kaveri.com>
Date: 2026-10-15
Subject: Re: Quote for Coolant Concentrate Drums

Hi,
Please find attached the quote from Godavari Coolants for 68,000. Cost centre CC-MAINT. Let me know if any changes.
Thanks,
Rajesh
---
From: Sita Devi (Godavari Coolants) <sita.devi@godavari.com>
Date: 2026-10-15
Subject: Re: Quote for Coolant Concentrate Drums

Dear Rajesh,
We have attached the formal quotation as requested. Qty as per your spec. Price as discussed.
Regards,
Sita
---
From: Anil Sharma (Kaveri Stores) <anil.sharma@kaveri.com>
Date: 2026-10-16
Subject: Approval Needed

Hi Rajesh,
Looks good. Please forward to accounts for processing.
Thanks,
Anil
---
From: Meena Rao (Godavari Accounts) <meena.rao@godavari.com>
Date: 2026-10-16
Subject: Payment Details

Hello,
We have moved to a new bank account. Kindly update your records for payment of the 68,000 invoice.
Thank you.
Meena

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-104 Godavari Coolants: active; GST registration active; ISO 9001 certificate valid until 2027-03-31; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-MAINT FY 2026-27: ₹25,00,000 left of ₹40,00,000.
- Approver for ₹68,000 in CC-MAINT: E-107 (S. Fathima, cc_head), available.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** bank (bank_details_changed)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## DEV-014 · 2026-10-19 · Zaheerabad Special Alloys · 2.8L · CC-ASSY · 1 quote(s)

**Justification:** The purchase request is for a 2.8L titanium grade 5 bar needed for a medical-device part. Zaheerabad Special Alloys is the only approved source per the drawing, and we have one vendor quote attached.

**Email thread:** From: Ramesh Kumar <r.kumar@kaveriprecision.com>
Subject: Re: 2.8L Titanium Bar Request

Please see the attached quote from Zaheerabad Special Alloys. They are the only approved source for this grade.
---
From: Anil Patel <a.patel@zaheerabadalloys.com>
Subject: Re: 2.8L Titanium Bar Request

We have a new bank account for payments. Kindly use the details in the invoice once it is raised.
---
From: Meena Singh <m.singh@kaveriprecision.com>
Subject: Re: 2.8L Titanium Bar Request

Noted the new bank account. We will update our payment system.
---
From: Ramesh Kumar <r.kumar@kaveriprecision.com>
Subject: Re: 2.8L Titanium Bar Request

Proceed with the order. Cost centre CC-ASSY, submitted 2026-10-19.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-122 Zaheerabad Special Alloys: active; GST registration active; IATF 16949 certificate valid until 2027-06-30; bank details not changed in the 30 days before the request; flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹2,80,000 in CC-ASSY: E-201 (V. Iyer, plant_head), available.
- Quotes: 1 attached; 3 needed above ₹2,00,000.

**Built to fail:** bank (bank_details_changed), quotes (insufficient_quotes)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## DEV-015 · 2026-10-20 · Banjara Alloys · 5.4L · CC-ASSY · 1 quote(s)

**Justification:** The request is for a 5.4L order of Inconel 718 bar for an aerospace bracket, with Banjara Alloys as the only approved source. One quote is attached as per the requirement. No special issues are mentioned.

**Email thread:** From: purchase@kaveri.co.in
Subject: Request for Inconel 718 bar
Message: Please raise PO for 5.4L Inconet 718 for Banjara Alloys. Inconel 718 | only approved source. Cost centre CC-ASSY.
---
From: sales@kaveri.co.in
Subject: Re: Request for Inconel 718 bar
Message: Got it. We will send the quote today. One quote as per Banjara Alloys requirement.
---
From: purchase@kaveri.co.in
Subject: Re: Re: Request for Inconel 718 bar
Message: Thanks. Attach the quote and forward to logistics. Normal delivery expected.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-109 Banjara Alloys: active; GST registration active; IATF 16949 certificate valid until 2027-08-31; bank details not changed in the 30 days before the request; flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹5,40,000 in CC-ASSY: E-201 (V. Iyer, plant_head), available.
- Quotes: 1 attached; 3 needed above ₹2,00,000.

**Built to fail:** quotes (insufficient_quotes)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## DEV-016 · 2026-10-22 · Kompally Fasteners · ₹1,10,000 · CC-ASSY · 1 quote(s)

**Justification:** The purchase is for a routine monthly supply of high‑tensile fasteners from Kompally Fasteners. The vendor has a good delivery record and the request is for cost centre CC-ASSY.

**Email thread:** From: Anil Reddy <anil.reddy@kaveriprecision.com>
Sent: 22 Oct 2026 09:15 AM
Subject: Purchase request for Kompally Fasteners

Please raise PO for ₹1,10,000 to Kompally Fasteners, cost centre CC-ASSY. 1 quote attached. Routine monthly order of high‑tensile fasteners.
---
From: Priya Sharma <priya.sharma@kaveriprecision.com>
Sent: 22 Oct 2026 10:02 AM
Subject: Re: Purchase request for Kompally Fasteners

Got it, Anil. I will forward to procurement. Their ISO 9001 certificate shows expiry 20 Nov 2026, renewal audit is early Nov. No issues from our side.

**Attachment:** Kompally Fasteners Ltd.
ISO 9OO1 Certified
Certificate No: KF/ISO/2023-45
Expiry Date: 20 Nov 2026

This certiﬁcate is valid for the scope of fastener manufacturing and supply.


**Ledger on that date:**

- Vendor V-133 Kompally Fasteners: active; GST registration active; ISO 9001 certificate valid until 2026-11-20; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹1,10,000 in CC-ASSY: E-110 (P. Reddy, cc_head), available.
- Earlier request PR-2026-0934 to this vendor on 2026-10-01 for ₹1,00,000 (+10.0% against it).
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** nothing

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## DEV-017 · 2026-10-30 · Shankarpally Forge · Rs. 3.6 lakhs · CC-ASSY · 3 quote(s)

**Justification:** The purchase request is for Rs. 3.6 lakhs to Shankarpally Forge for crankshaft blanks needed for the November build plan. Three quotes were reviewed and Shankarpally Forge offered the lowest price, so we are proceeding with the routine order.

**Email thread:** From: Arjun Patel <arjun.patel@kaveriprecision.com>
Sent: 30 Oct 2026 09:15 AM
Subject: Re: Purchase request for crankshaft blanks

Please raise the PO for Rs. 3.6 lakhs to Shankarpally Forge. Cost centre CC-ASSY. Three quotes attached, theirs is the lowest. Thanks.
---
From: Meena Rao <meena.rao@kaveriprecision.com>
Sent: 30 Oct 2026 09:45 AM
Subject: Re: Purchase request for crankshaft blanks

Got it, will process today. Let me know if any change. Regards, Meena.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-123 Shankarpally Forge: active; GST registration active; IATF 16949 certificate valid until 2026-11-01; bank details changed 2026-10-28 (2 days before the request); not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹3,60,000 in CC-ASSY: E-201 (V. Iyer, plant_head), available.
- Quotes: 3 attached; 3 needed above ₹2,00,000.

**Built to fail:** bank (bank_details_changed)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## DEV-018 · 2026-11-03 · Ghatkesar Aluminium Extrusions · ₹1,44,000 · CC-ASSY · 1 quote(s)

**Justification:** The purchase request is for ₹1,44,000 to Ghatkesar Aluminium Extrusions for cost centre CC-ASSY. It references the second shipment of the order and the balance quantity being sent, and notes that there are no invoice issues with the vendor.

**Email thread:** From: procurement@kaveriprecision.com
Subject: PR-2026-0988 - Second shipment update

Hi Team,

We have raised the second shipment of the aluminium extrusion order on 20 Oct (PR-2026-0988). Ghatkesar is now sending the balance quantity. Please process the payment of ₹1,44,000 to cost centre CC-ASSY.

Thanks,
Anil
---
From: accounts@kaveriprecision.com
Subject: Re: PR-2026-0988 - Second shipment update

Anil,

Noted the second shipment and balance quantity. As usual, there are no invoice issues with Ghatkesar. We'll clear the amount.

Regards,
Sanjay

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-129 Ghatkesar Aluminium Extrusions: active; GST registration active; ISO 9001 certificate valid until 2027-02-28; bank details changed 2026-10-24 (10 days before the request); not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹1,44,000 in CC-ASSY: E-110 (P. Reddy, cc_head), available.
- Earlier request PR-2026-0988 to this vendor on 2026-10-20 for ₹1,40,000 (+2.9% against it).
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** duplicate (possible_duplicate), bank (bank_details_changed)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## DEV-019 · 2026-11-05 · Boduppal Engineering Works · Rs 1,30,000 · CC-ASSY · 1 quote(s)

**Justification:** We need Rs 1,30,000 for machined brackets that go into customer assemblies. Boduppal Engineering Works is run by my brother and the rate is the best available.

**Email thread:** (none)

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-130 Boduppal Engineering Works: active; GST registration active; ISO 9001 certificate valid until 2027-01-31; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹1,30,000 in CC-ASSY: E-110 (P. Reddy, cc_head), available.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** related_party (related_party)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## DEV-020 · 2026-11-12 · Nacharam Gauge Works · 1.6 lakh · CC-QA · 1 quote(s)

**Justification:** The purchase request is for thread plug gauges and ring gauges for the QA lab, amounting to 1.6 lakh to Nacharam Gauge Works. The vendor has a long history with no quality complaints and the ISO 9001 renewal audit is done, with the new certificate pending.

**Email thread:** From: Ramesh Kumar <ramesh.kumar@kaveriprecision.com>
Date: 2026-11-10
Subject: Request for Quote – Thread Plug & Ring Gauges

Please prepare a quote for thread plug gauges and ring gauges for our QA lab. Amount needed is 1.6 lakh, cost centre CC‑QA. Attach the quote and send back.
---
From: Anjali Rao <anjali.rao@nacharamgauge.com>
Date: 2026-11-11
Subject: Re: Request for Quote – Thread Plug & Ring Gauges

Sure, we will send the quote tomorrow. Our ISO 9001 certificate expired on 7 Nov but renewal audit is done, new cert will be with us soon.
---
From: Ramesh Kumar <ramesh.kumar@kaveriprecision.com>
Date: 2026-11-12
Subject: Re: Request for Quote – Thread Plug & Ring Gauges

Got the quote, thanks. Noted that there are no quality complaints from you. Please forward the certificate snippet when you get it. QA head is on leave till 20 Nov, so proceed as normal.

**Attachment:** ISO  9 0 1   Certi ficate
No.  2025/NRG-07
Issued: 08-Nov-2026
Valid  Till: 07-Nov-2029
Renewal audit is done
Issuer: Bureau of Indian Standards



**Ledger on that date:**

- Vendor V-132 Nacharam Gauge Works: active; GST registration active; ISO 9001 certificate expired 2026-11-07 (5 days before the request); bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-QA FY 2026-27: ₹17,00,000 left of ₹25,00,000.
- Approver for ₹1,60,000 in CC-QA: E-111 (M. Joshi, cc_head), on leave 2026-11-09 to 2026-11-20; delegate E-116 (J. Pillai) up to ₹1,00,000, valid 2026-11-09 to 2026-11-20.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** vendor (cert_expired), approver (approver_on_leave)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial
