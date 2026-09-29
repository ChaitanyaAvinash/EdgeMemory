# Labelling worksheet: test (40 cases). SYNTHETIC DATA.

Label blind: don't look at any system output. Use `config/verdict_guide.md` (copy it into
`data/ground_truth/LABELLING_GUIDE.md` with the family rules), `data/seed/history.csv` for the
precedents, and `data/seed/policy.md` for uncovered cases. The format is `docs/ground_truth_format.md`.
Fill `data/labelling/test_skeleton.json`, then save it as `data/ground_truth/test.json`.

## TEST-001 · 2026-09-15 · Shamshabad Hydraulics · 1.55 lakh · CC-MACH · 1 quote(s)

**Justification:** The hydraulic power pack on the broaching machine failed, and the maintenance log confirms the breakdown. A replacement pump and valve block are required for line 1. The request is for 1.55 lakh to Shamshabad Hydraulics under cost centre CC-MACH.

**Email thread:** From: S. Rao <srao@kaveriprecision.com>
Date: 2026-09-15 08:30
Subject: Request for hydraulic pump & valve block

line 1 is down. Need 1.55 lakh to Shamshabad Hydraulics, cost centre CC-MACH. Please attach quote.
---
From: A. Mehta <amehta@shamshabadhydraulics.com>
Date: 2026-09-15 09:10
Subject: Re: Request for hydraulic pump & valve block

Got your request. Quote attached. Let me know if any changes.
---
From: S. Rao <srao@kaveriprecision.com>
Date: 2026-09-15 09:45
Subject: Re: Request for hydraulic pump & valve block

Thanks. maintenance log confirms the failure. K. Raghavan is on leave, so I will forward to finance.
---
From: Finance Dept <finance@kaveriprecision.com>
Date: 2026-09-15 10:20
Subject: Re: Request for hydraulic pump & valve block

We will process 1.55 lakh under CC-MACH. Approve and forward PO.


**Attachment:** (none)

**Ledger on that date:**

- Vendor V-121 Shamshabad Hydraulics: active; GST registration active; ISO 9001 certificate valid until 2027-02-28; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-MACH FY 2026-27: ₹0 left of ₹80,00,000; this request would take it 1.9% over.
- Approver for ₹1,55,000 in CC-MACH: E-104 (K. Raghavan, cc_head), on leave 2026-09-14 to 2026-09-18; delegate E-112 (T. Naidu) up to ₹2,00,000, valid 2026-04-01 to 2027-03-31.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** budget (overrun), approver (approver_on_leave)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-002 · 2026-09-23 · Balanagar Machine Tools · 1.65L · CC-MAINT · 1 quote(s)

**Justification:** We need to procure a new portable hydraulic press for the maintenance workshop. The asset will be capitalised as a fixed asset and charged to cost centre CC-MAINT. The cost centre head is on leave, so the request is routed to the delegate.

**Email thread:** From: Rajesh Kumar (Purchase Dept)
Date: 23-Sep-2026
Subject: Request for 1.65L hydraulic press for Balanagar Machine Tools

Please arrange purchase of 1.65L hydraulic press for Balanagar Machine Tools. Cost centre CC-MAINT. Quote attached. Thanks.
---
From: Meena Rao (Cost Centre Delegate)
Date: 24-Sep-2026
Subject: Re: Request for 1.65L hydraulic press for Balanagar Machine Tools

Got it. Forwarding to finance for approval. Ensure asset is capitalised as per policy.
---
From: Finance Team
Date: 25-Sep-2026
Subject: Re: Request for 1.65L hydraulic press for Balanagar Machine Tools

Finance approves. Please proceed with purchase and asset registration.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-135 Balanagar Machine Tools: active; GST registration active; ISO 9001 certificate valid until 2027-03-31; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-MAINT FY 2026-27: ₹25,00,000 left of ₹40,00,000.
- Approver for ₹1,65,000 in CC-MAINT: E-107 (S. Fathima, cc_head), on leave 2026-09-21 to 2026-10-02; delegate E-115 (R. Kulkarni) up to ₹2,00,000, valid 2026-04-01 to 2027-03-31.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** approver (approver_on_leave)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-003 · 2026-09-28 · Golconda Electricals · ₹6,20,000 · CC-MACH · 3 quote(s)

**Justification:** The request is for ₹6,20,000 to purchase a replacement servo drive and spindle motor from Golconda Electricals. The cost centre CC-MACH has exhausted its budget, and the maintenance log confirms the breakdown. Three quotes were obtained and Golconda is the lowest. Plant head approval is pending until his return.

**Email thread:** From: Rajesh Kumar (Shop Floor Engineer)
Subject: Request for purchase - Golconda Electricals
line 2 is down. Need replacement servo drive and spindle motor. Budget CC-MACH used up.
---
From: Priya Singh (Purchasing Officer)
Re: Request for purchase - Golconda Electricals
Got three quotes, Golconda lowest. Will forward for approval.
---
From: Suresh Patel (Maintenance Supervisor)
Re: Request for purchase - Golconda Electricals
maintenance log confirms the burnt out drive and motor. No other options.
---
From: Anil Reddy (Plant Head - on leave)
Re: Request for purchase - Golconda Electricals
Will sign off on ₹6,20,000 after I return on 2 Oct.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-113 Golconda Electricals: active; GST registration active; ISO 9001 certificate valid until 2027-02-28; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-MACH FY 2026-27: ₹0 left of ₹80,00,000; this request would take it 7.8% over.
- Approver for ₹6,20,000 in CC-MACH: E-201 (V. Iyer, plant_head), on leave 2026-09-21 to 2026-10-02; delegate E-205 (H. Siddiqui) up to ₹10,00,000, valid 2026-04-01 to 2027-03-31.
- Quotes: 3 attached; 3 needed above ₹2,00,000.

**Built to fail:** budget (overrun), approver (approver_on_leave)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-004 · 2026-10-01 · Golconda Electricals · ₹1,48,000 · CC-MAINT · 1 quote(s)

**Justification:** The workshop needs a new 30 kVA UPS for the test bench and it will be capitalised as a fixed asset. The cost centre head is on leave, so the request is routed through the shop floor manager.

**Email thread:** From: Rajesh Kumar <rkumar@kaveriprecision.com>
Date: 2026-09-28
Subject: Request for UPS purchase

Sir, need a 30 kVA UPS for the maintenance workshop test bench. It will be capitalised as a fixed asset. Please approve the ₹1,48,000 spend to Golconda Electricals, cost centre CC-MAINT.
---
From: Meena Patel <mpatel@kaveriprecision.com>
Date: 2026-09-28
Subject: Re: Request for UPS purchase

Got it, Rajesh. I will forward to finance. As head is on leave till 2 Oct, I’ll sign off for now. Thanks.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-113 Golconda Electricals: active; GST registration active; ISO 9001 certificate valid until 2027-02-28; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-MAINT FY 2026-27: ₹25,00,000 left of ₹40,00,000.
- Approver for ₹1,48,000 in CC-MAINT: E-107 (S. Fathima, cc_head), on leave 2026-09-21 to 2026-10-02; delegate E-115 (R. Kulkarni) up to ₹2,00,000, valid 2026-04-01 to 2027-03-31.
- Earlier request TEST-003 to this vendor on 2026-09-28 for ₹6,20,000 (-76.1% against it).
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** approver (approver_on_leave)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-005 · 2026-10-02 · Patancheru Electricals · 1.62L · CC-MACH · 1 quote(s)

**Justification:** The request is for 1.62L of motor starters and contactors to replace the burnt out units on line 3. The maintenance log confirms the breakdown and the purchase needs to be logged under cost centre CC-MACH.

**Email thread:** From: Rajesh Kumar <rkumar@kaveriprecision.com>
Subject: Request for 1.62L to Patancheru Electricals
Hi Team,
Please raise a purchase for 1.62L of motor starters & contactors to Patancheru Electricals. cost centre CC-MACH. line 3 is down. Thanks.
---
From: Anjali Mehta <amehta@kaveriprecision.com>
Subject: Re: Request for 1.62L to Patancheru Electricals
Rajesh,
Got it. I will forward to procurement. maintenance log confirms the issue.
---
From: Procurement Dept <procurement@kaveriprecision.com>
Subject: Re: Request for 1.62L to Patancheru Electricals
Anjali,
Quote received, attached. Will process under CC-MACH.


**Attachment:** (none)

**Ledger on that date:**

- Vendor V-128 Patancheru Electricals: active; GST registration active; ISO 9001 certificate valid until 2027-05-31; bank details changed 2026-09-10 (22 days before the request); not flagged sole-source.
- Budget CC-MACH FY 2026-27: ₹0 left of ₹80,00,000; this request would take it 2.0% over.
- Approver for ₹1,62,000 in CC-MACH: E-104 (K. Raghavan, cc_head), available.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** budget (overrun), bank (bank_details_changed)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-006 · 2026-10-06 · Uppal Gear Drives · 1.35L · CC-MACH · 1 quote(s)

**Justification:** The transfer machine gearbox has failed as per the maintenance log. Line 4 is down and a replacement gearbox is needed for the cost centre CC-MACH. A quote for 1.35L has been attached and was submitted on 2026-10-06.

**Email thread:** From: Rajesh Kumar (Shop Floor Supervisor)
Subject: Gearbox failure on line 4
Message: Sir, line 4 is down since night shift. Main gearbox of transfer machine failed. Maintenance log confirms. Please approve purchase request for 1.35L to Uppal Gear Drives, cost centre CC-MACH.
---
From: Anita Verma (Purchasing Officer)
Subject: Re: Gearbox failure on line 4
Message: Got it, Rajesh. I will raise the PO. Quote attached, 1.35L. Let me know if any extra details needed. Thanks.
---
From: Suresh Patel (Finance Lead)
Subject: Re: Gearbox failure on line 4
Message: Approved from budget side, though CC-MACH is used up. Proceed with the order. Keep me posted.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-120 Uppal Gear Drives: active; GST registration active; ISO 9001 certificate valid until 2027-01-31; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-MACH FY 2026-27: ₹0 left of ₹80,00,000; this request would take it 1.7% over.
- Approver for ₹1,35,000 in CC-MACH: E-104 (K. Raghavan, cc_head), available.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** budget (overrun)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-007 · 2026-10-06 · Patancheru Electricals Pvt. Ltd. · 1,85,000 · CC-MAINT · 1 quote(s)

**Justification:** The maintenance department needs a new 5‑tonne electric chain hoist for the bay. It will be recorded as a capitalised fixed asset under cost centre CC‑MAINT. One vendor quote is attached for approval.

**Email thread:** From: ramesh.kumar@kaveriprecision.com
To: patancheru.elec@pvtltd.com
Subject: Request for 5‑tonne chain hoist

Hi,
We need a new 5‑tonne electric chain hoist for the maintenance bay. Please send us your quote.
Thanks,
Ramesh
---
From: ananya.s@patancheru.com
To: ramesh.kumar@kaveriprecision.com
Subject: Re: Request for 5‑tonne chain hoist

Hello Sir,
Attached is our quote for the chain hoist. Let us know if any clarification needed.
Regards,
Ananya

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-128 Patancheru Electricals: active; GST registration active; ISO 9001 certificate valid until 2027-05-31; bank details changed 2026-09-10 (26 days before the request); not flagged sole-source.
- Budget CC-MAINT FY 2026-27: ₹25,00,000 left of ₹40,00,000.
- Approver for ₹1,85,000 in CC-MAINT: E-107 (S. Fathima, cc_head), available.
- Earlier request TEST-005 to this vendor on 2026-10-02 for ₹1,62,000 (+14.2% against it).
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** bank (bank_details_changed)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-008 · 2026-10-09 · Medak Machined Parts · 14.5 L · CC-ASSY · 3 quote(s)

**Justification:** The purchase request is for 14.5 L of machined valve bodies to be supplied to Medak Machined Parts. Three quotes were received and Medak offers the lowest price. Their ISO 9001 renewal audit is done and they have no quality complaints, with a good delivery record.

**Email thread:** From: Ravi Kumar <ravi.kumar@kaveriprecision.com>
Sent: 2026-10-08
Subject: Request for 14.5 L order to Medak

Please raise PO for 14.5 L to Medak Machined Parts, cost centre CC-ASSY. Attach the three quotes.
---
From: Sita Rao <sita.rao@kaveriprecision.com>
Sent: 2026-10-08
Subject: Re: Request for 14.5 L order to Medak

Checked quotes. Medak is lowest. Their ISO 9001 | renewal audit is done | no quality complaints. Ready to proceed.
---
From: Anil Singh <anil.singh@kaveriprecision.com>
Sent: 2026-10-09
Subject: Approval

Approved. Please issue PO and send to Medak. Keep copy on CC-ASSY.

**Attachment:** ISO 9001  Certi ficate
No. 2024/5678
Issued: 03 Oct 2024
Valid   till: 02 Oct 2026
Holder: Medak Machined Parts

(Seal)   *

Note: Renewal audit is done. New certi- ficate will be issued shortly.

**Ledger on that date:**

- Vendor V-119 Medak Machined Parts: active; GST registration active; ISO 9001 certificate expired 2026-10-03 (6 days before the request); bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹14,50,000 in CC-ASSY: E-301 (N. Chandra, cfo), available.
- Earlier request PR-2026-0846 to this vendor on 2026-09-22 for ₹98,000 (+1379.6% against it).
- Quotes: 3 attached; 3 needed above ₹2,00,000.

**Built to fail:** vendor (cert_expired)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-009 · 2026-10-09 · Ramoji Facility Services · ₹8,400 · CC-ADMIN · 1 quote(s)

**Justification:** Monthly pest control for the admin block and canteen is a standing arrangement with Ramoji Facility Services. They have been handling it for the past two years and the cost is ₹8,400 to cost centre CC-ADMIN.

**Email thread:** (none)

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-114 Ramoji Facility Services: active; GST registration active; ISO 9001 certificate valid until 2027-04-30; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-ADMIN FY 2026-27: ₹10,000 left of ₹4,00,000.
- Approver for ₹8,400 in CC-ADMIN: E-113 (A. Varma, cc_head), available.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** nothing

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-010 · 2026-10-12 · Banjara Alloys · 9.6L · CC-MACH · 1 quote(s)

**Justification:** The purchase request is for a 9.6L special alloy bar needed for Line 5. Banjari Alloys is the only approved source and a single quote is attached. The cost centre CC-MACH budget is already allocated.

**Email thread:** From: Ravi Kumar <ravi.kumar@kaveriprecision.com>
Subject: Request for 9.6L alloy bar
Hi Team,
We need to place an order for a 9.6L special alloy bar for line 5. line 5 is down and we need the material ASAP.
---
From: Anjali Singh <anjali.singh@kaveriprecision.com>
Subject: Re: Request for 9.6L alloy bar
Ravi,
Got it. I see that Banjara Alloys is the only approved source. Please forward the quote.
---
From: Ravi Kumar <ravi.kumar@kaveriprecision.com>
Subject: Re: Request for 9.6L alloy bar
Here is the quote from Banjara Alloys (attached). production log confirms line 5 has been stopped since morning.
---
From: Suresh Patel <suresh.patel@kaveriprecision.com>
Subject: Re: Request for 9.6L alloy bar
Thanks Ravi. I will raise the PO under cost centre CC-MACH and get it processed.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-109 Banjara Alloys: active; GST registration active; IATF 16949 certificate valid until 2027-08-31; bank details not changed in the 30 days before the request; flagged sole-source.
- Budget CC-MACH FY 2026-27: ₹0 left of ₹80,00,000; this request would take it 12.0% over.
- Approver for ₹9,60,000 in CC-MACH: E-201 (V. Iyer, plant_head), available.
- Quotes: 1 attached; 3 needed above ₹2,00,000.

**Built to fail:** budget (overrun), quotes (insufficient_quotes)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-011 · 2026-10-12 · M/s Sultanpur Precision Castings · 4.4L · CC-ASSY · 1 quote(s)

**Justification:** We need to purchase 4.4L of investment-cast impeller blanks for a customer order. Sultanpur Precision Castings is the only approved source and their IATF 16949 certification is being renewed, so we must proceed with the attached quote.

**Email thread:** From: Rajesh Kumar (Purchasing)
To: Procurement Team
Subject: Request for 4.4L to M/s Sultanpur Precision Castings
We need 4.4L of impeller blanks. Cost centre CC-ASSY. Only approved source is Sultanpur. Please see attached quote.
---
From: Ananya Rao (Procurement Lead)
To: Rajesh Kumar
Subject: Re: Request for 4.4L to M/s Sultanpur Precision Castings
Thanks Rajesh. Noted that no other supplier can make these. Their IATF 16949 certificate expired on 6 Oct but recertification audit is done. Expect new cert in ~10 days.
---
From: Sunil Patel (Quality)
To: Procurement Team
Subject: Re: Request for 4.4L to M/s Sultanpur Precision Castings
Sultanpur has clean quality record. Since they are the only approved source, we can proceed once the new certificate arrives.
---
From: Priya Menon (Finance)
To: Procurement Team
Subject: Re: Request for 4.4L to M/s Sultanpur Precision Castings
All good. Please raise the PO under CC-ASSY. Let me know if any change.

**Attachment:** IATF 16949 CERTIFICATE
Company: Sultanpur Precision Castings
Certificate No: 2023-XYZ-09
Valid From: 07 Oct 2023   Valid To: 06 Oct 2026
Audit Status: recertification audit is done

( OCR mis‑read: 1 9 6 6 may appear as 1 9 6 8 )

**Ledger on that date:**

- Vendor V-138 Sultanpur Precision Castings: active; GST registration active; IATF 16949 certificate expired 2026-10-06 (6 days before the request); bank details not changed in the 30 days before the request; flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹4,40,000 in CC-ASSY: E-201 (V. Iyer, plant_head), available.
- Quotes: 1 attached; 3 needed above ₹2,00,000.

**Built to fail:** vendor (cert_expired), quotes (insufficient_quotes)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-012 · 2026-10-12 · Medak Machined Parts · 1,02,000 · CC-ASSY · 1 quote(s)

**Justification:** The purchase request for 1,02,000 INR to Medak Machined Parts is documented with reference to the second shipment of turned pins and confirms the balance quantity delivery. It notes the ISO 9001 renewal audit is done and there are no invoice issues, supporting the cost centre allocation.

**Email thread:** From: Ravi Kumar <ravi.kumar@kaveri.com>
Date: 2026-09-22
Subject: PR-2026-0846 second shipment request

Hi Team,
We raised the second shipment of the turned‑pin order (PR-2026-0846) on 22 Sep. Medak is now delivering the balance quantity. Please process the purchase request for 1,02,000 to Medak Machined Parts, cost centre CC-ASSY.
---
From: Anjali Rao <anjali.rao@kaveri.com>
Date: 2026-09-23
Subject: Re: second shipment details

Thanks Ravi. Noted the balance quantity. Medak's ISO 9001 certificate expired on 3 Oct but the renewal audit is done and the new cert will be up soon. Their delivery record is good and there are no invoice issues.
---
From: Suresh Patel <suresh.patel@kaveri.com>
Date: 2026-09-24
Subject: Approval

Approved. Attach the quote and proceed.


**Attachment:** ISO 9OO1 Certificate

Certificate No:  MDP/2025/0589
Issued to: Medak Machined Parts
Valid From: 04 Oct 2023  To: 03 Oct 2026

Renewal audit is done – new cert pending issuance.


**Ledger on that date:**

- Vendor V-119 Medak Machined Parts: active; GST registration active; ISO 9001 certificate expired 2026-10-03 (9 days before the request); bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹1,02,000 in CC-ASSY: E-110 (P. Reddy, cc_head), available.
- Earlier request PR-2026-0846 to this vendor on 2026-09-22 for ₹98,000 (+4.1% against it).
- Earlier request TEST-008 to this vendor on 2026-10-09 for ₹14,50,000 (-93.0% against it).
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** vendor (cert_expired), duplicate (possible_duplicate)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-013 · 2026-10-13 · Kakatiya Motors · 1.7 lakh · CC-MACH · 1 quote(s)

**Justification:** The purchase request is for a spare spindle motor needed for line 2. The maintenance supervisor’s log entry contradicts the claim that line 2 is down, prompting a review of the request.

**Email thread:** From: Ramesh Patel <r.patel@kavprecision.com>
Subject: Request for spare spindle motor – 1.7 lakh

Line 2 is down. Need 1.7 lakh for spare spindle motor for line 2. Cost centre CC-MACH. Please approve urgent emergency order.
---
From: Sunita Rao <s.rao@kavprecision.com>
Subject: Re: Request for spare spindle motor – 1.7 lakh

Ramesh, maintenance log shows line 2 running. Only a planned changeover last night, no breakdown recorded.
---
From: Ramesh Patel <r.patel@kavprecision.com>
Subject: Re: Request for spare spindle motor – 1.7 lakh

Okay, I will double‑check with floor. Still think we need the motor, but will wait for final confirmation.
---
From: Anil Kumar <a.kumar@kavprecision.com>
Subject: Re: Request for spare spindle motor – 1.7 lakh

Please attach the quote. Once we have the doc we can close this.
---

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-106 Kakatiya Motors: active; GST registration active; ISO 9001 certificate valid until 2027-01-31; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-MACH FY 2026-27: ₹0 left of ₹80,00,000; this request would take it 2.1% over.
- Approver for ₹1,70,000 in CC-MACH: E-104 (K. Raghavan, cc_head), available.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** budget (overrun)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-014 · 2026-10-14 · Himayatnagar Test Instruments · Rs 1,90,000 · CC-QA · 1 quote(s)

**Justification:** We need to purchase a Rockwell hardness tester for the QA lab to increase testing capacity for heat-treated parts. The equipment will be capitalised as a fixed asset under cost centre CC-QA.

**Email thread:** From: purchase@kaveriprecision.com
Subject: Request for approval - hardness tester

Please approve Rs 1,90,000 to Himayatnagar Test Instruments for the new hardness tester. It will be capitalised under CC-QA. Quote attached.
---
From: manager.qa@kaveriprecision.com
Subject: Re: Request for approval - hardness tester

Approved. Go ahead with Himayatnagar Test Instruments. Ensure the asset is capitalised correctly.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-134 Himayatnagar Test Instruments: active; GST registration active; ISO 9001 certificate valid until 2027-06-30; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-QA FY 2026-27: ₹17,00,000 left of ₹25,00,000.
- Approver for ₹1,90,000 in CC-QA: E-111 (M. Joshi, cc_head), available.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** nothing

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-015 · 2026-10-15 · Sultanpur Precision Castings · ₹3,30,000 · CC-ASSY · 1 quote(s)

**Justification:** The purchase request is for ₹3,30,000 to acquire investment-cast pump housings from the only approved source. Sultanpur Precision Castings holds a clean quality record and the recertification audit is done, ensuring compliance with IATF 16949 standards.

**Email thread:** From: Rajesh Kumar (Purchasing) <rajesh.kumar@kaveriprecision.com>
Sent: 2026-10-15 09:12 AM
Subject: Request for PO to Sultanpur Precision Castings

Please raise PO for ₹3,30,000 to Sultanpur Precision Castings, cost centre CC-ASSY. They are only approved source for this casting. Attach the quote.
---
From: Meena Singh (Finance) <meena.singh@kaveriprecision.com>
Sent: 2026-10-15 10:05 AM
Subject: Re: Request for PO to Sultanpur Precision Castings

Got it. Check that the IATF 16949 certificate is valid. Their old one expired 6 Oct but recertification audit is done, new cert due next week. All good.
---
From: Arjun Rao (Shop Floor) <arjun.rao@kaveriprecision.com>
Sent: 2026-10-15 10:45 AM
Subject: Re: Request for PO to Sultanpur Precision Castings

Thanks, Rajesh. Let’s get this moving, need the housings soon. Sultanpur ka quality record badiya hai, so no issue.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-138 Sultanpur Precision Castings: active; GST registration active; IATF 16949 certificate expired 2026-10-06 (9 days before the request); bank details not changed in the 30 days before the request; flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹3,30,000 in CC-ASSY: E-201 (V. Iyer, plant_head), available.
- Earlier request TEST-011 to this vendor on 2026-10-12 for ₹4,40,000 (-25.0% against it).
- Quotes: 1 attached; 3 needed above ₹2,00,000.

**Built to fail:** vendor (cert_expired), quotes (insufficient_quotes)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-016 · 2026-10-15 · Kukatpally Calibration Labs · 1.2L · CC-QA · 1 quote(s)

**Justification:** The request includes a personal relationship claim ('is my sister') which is prohibited by policy.

**Email thread:** (none)

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-118 Kukatpally Calibration Labs: active; GST registration active; ISO/IEC 17025 certificate valid until 2027-03-15; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-QA FY 2026-27: ₹17,00,000 left of ₹25,00,000.
- Approver for ₹1,20,000 in CC-QA: E-111 (M. Joshi, cc_head), available.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** related_party (related_party)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-017 · 2026-10-19 · Kompally Fasteners · 1,06,000 · CC-ASSY · 1 quote(s)

**Justification:** The purchase request repeats a previously raised order (PR-2026-0934) for high‑tensile fasteners but with a higher quantity for a new customer schedule. It is a fresh order, not a split delivery, and a single quote is attached for reference.

**Email thread:** From: Sandeep Kumar <sandeep.kumar@kavprecision.com>
Date: Tue, 17 Oct 2026 10:15 AM
Subject: New PR for Kompally Fasteners

Hi Team,
Please raise PR for 1,06,000 pcs of the high‑tensile fasteners. Same specs as PR-2026-0934 | new order but qty a bit higher. Cost centre CC-ASSY. Quote attached.
Thanks,
Sandeep
---
From: Ananya Rao <ananya.rao@kavprecision.com>
Date: Tue, 17 Oct 2026 10:45 AM
Subject: Re: New PR for Kompally Fasteners

Got it, Sandeep. Will forward to procurement. Ensure the quote matches the new qty. Let me know if any changes.
Regards,
Ananya

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-133 Kompally Fasteners: active; GST registration active; ISO 9001 certificate valid until 2026-11-20; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹1,06,000 in CC-ASSY: E-110 (P. Reddy, cc_head), available.
- Earlier request PR-2026-0934 to this vendor on 2026-10-01 for ₹1,00,000 (+6.0% against it).
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** nothing

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-018 · 2026-10-20 · Hyderabad Tooling Works · 72,000 · CC-MAINT · 1 quote(s)

**Justification:** Need to purchase carbide inserts and boring bars for the maintenance tool crib. The items are required ahead of the upcoming customer audit. Cost centre CC-MAINT is allocated for this spend.

**Email thread:** From: Rajesh Kumar (Shop Floor) <rkumar@kaveriprecision.com>
Subject: Request for purchase - carbide inserts

Need to order carbide inserts and boring bars for the maintenance tool crib. Please process.
---
From: Priya Nair (Purchasing) <pnair@kaveriprecision.com>
Subject: Re: Request for purchase - carbide inserts

Got it, Rajesh. I will raise the PO. Can you confirm the cost centre?
---
From: Rajesh Kumar (Shop Floor) <rkumar@kaveriprecision.com>
Subject: Re: Request for purchase - carbide inserts

Yes, cost centre is CC-MAINT. Thanks. Looking forward to get them before the customer audit.


**Attachment:** (none)

**Ledger on that date:**

- Vendor V-103 Hyderabad Tooling Works: active; GST registration active; ISO 9001 certificate valid until 2027-02-28; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-MAINT FY 2026-27: ₹25,00,000 left of ₹40,00,000.
- Approver for ₹72,000 in CC-MAINT: E-107 (S. Fathima, cc_head), available.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** nothing

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-019 · 2026-10-21 · Hyderabad Tooling Works · 3.9 lakh · CC-MACH · 3 quote(s)

**Justification:** The purchase request is for Rs. 3.9 lakh to replace the broken gang‑milling cutter set for line 3, with three vendor quotes attached and the cost centre budget allocated.

**Email thread:** From: akhilesh.patel@kaveri.com
Subject: Re: Purchase request for cutter set

line 3 is down. need new cutter set asap. attached 3 quotes.
---
From: vendor.accounts@hyderabadtooling.com
Subject: Re: RE: Purchase request for cutter set

We have a new bank account. Please remit payment to the updated details.
---
From: rina.sharma@kaveri.com
Subject: Re: RE: Purchase request for cutter set

maintenance log confirms the breakdown. ok, will process payment to new account.
---
From: akhilesh.patel@kaveri.com
Subject: Re: RE: Purchase request for cutter set

cost centre CC-MACH budget is used up, but we have approval. proceeding with Hyderabad Tooling Works.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-103 Hyderabad Tooling Works: active; GST registration active; ISO 9001 certificate valid until 2027-02-28; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-MACH FY 2026-27: ₹0 left of ₹80,00,000; this request would take it 4.9% over.
- Approver for ₹3,90,000 in CC-MACH: E-201 (V. Iyer, plant_head), available.
- Earlier request TEST-018 to this vendor on 2026-10-20 for ₹72,000 (+441.7% against it).
- Quotes: 3 attached; 3 needed above ₹2,00,000.

**Built to fail:** budget (overrun), bank (bank_details_changed)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-020 · 2026-10-22 · Kushaiguda Crate Makers · Rs 96,000 · CC-MAINT · 1 quote(s)

**Justification:** The purchase request is for the balance quantity of crates from the second shipment. Accounts flagged a duplicate invoice from the vendor that was caught by internal audit.

**Email thread:** From: Anil Sharma (Procurement)
Date: 2026-10-20
Subject: PR-2026-0953 - Second shipment of crates

Please note this is the second shipment of the crate order raised on 6 Oct (PR-2026-0953). The balance quantity is arriving now. Kindly process Rs 96,000 to Kushaiguda Crate Makers, cost centre CC-MAINT.
---
From: Meena Rao (Accounts)
Date: 2026-10-21
Subject: Re: PR-2026-0953 - Second shipment of crates

We have a duplicate invoice from Kushaiguda for the same crates dated 2025. Internal audit has already flagged it. Please confirm the correct invoice before payment.
---
From: Anil Sharma (Procurement)
Date: 2026-10-22
Subject: Re: PR-2026-0953 - Second shipment of crates

Acknowledged. We will request the vendor to resend the correct invoice. Once received, will forward for payment processing.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-136 Kushaiguda Crate Makers: active; GST registration active; ISO 9001 certificate valid until 2027-01-31; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-MAINT FY 2026-27: ₹25,00,000 left of ₹40,00,000.
- Approver for ₹96,000 in CC-MAINT: E-107 (S. Fathima, cc_head), available.
- Earlier request PR-2026-0953 to this vendor on 2026-10-06 for ₹94,000 (+2.1% against it).
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** duplicate (possible_duplicate)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-021 · 2026-10-23 · Bhongir Forgings · 12.4 L · CC-ASSY · 3 quote(s)

**Justification:** The quarterly order for forged flange blanks is being placed as per the Q3 schedule. Three quotes were received and the lowest price is from Bhongir Forgings. The standard four‑week delivery term applies.

**Email thread:** From: purchase@kaveriprecision.com
Subject: Request for order - forged flange blanks
Date: 2026-10-23

Please raise PO for 12.4 L of forged flange blanks to Bhongir Forgings. Cost centre CC-ASSY. Attach three quotes.
---
From: bhongir.forgings@example.com
Subject: Re: Request for order - forged flange blanks
Date: 2026-10-24

We confirm availability and price. Lowest among three quotes.
---
From: purchase@kaveriprecision.com
Subject: Re: Request for order - forged flange blanks
Date: 2026-10-25

Thanks, we will process the PO. Delivery in four weeks as usual.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-117 Bhongir Forgings: active; GST registration active; ISO 9001 certificate valid until 2027-05-31; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹12,40,000 in CC-ASSY: E-301 (N. Chandra, cfo), available.
- Quotes: 3 attached; 3 needed above ₹2,00,000.

**Built to fail:** nothing

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-022 · 2026-10-27 · Telangana Fab Works · ₹1,10,000 · CC-ASSY · 1 quote(s)

**Justification:** The purchase request is for welded fixture bases needed for a customer tooling order. The quote from Telangana Fab Works includes the GSTIN and standard rates, and the cost centre is CC-ASSY.

**Email thread:** From: purchase@kaveriprecision.com
Subject: PR for Welded Fixture Bases
Date: 2026-10-27

Please raise PO for ₹1,10,000 to Telangana Fab Works, cost centre CC-ASSY. Quote attached shows GSTIN and normal rates.
---
From: finance@kaveriprecision.com
Subject: Re: PR for Welded Fixture Bases
Date: 2026-10-27

Acknowledged. We will process the payment as per the quoted GSTIN details.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-110 Telangana Fab Works: active; GST registration cancelled; ISO 9001 certificate valid until 2027-01-31; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹1,10,000 in CC-ASSY: E-110 (P. Reddy, cc_head), available.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** vendor (gst_cancelled)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-023 · 2026-10-27 · Kazipet Die Castings · ₹1,18,000 · CC-ASSY · 1 quote(s)

**Justification:** The purchase request is for the second shipment of die‑cast housings, confirming the balance quantity and noting that Kazipet has no invoice issues.

**Email thread:** From: Anil Kumar (Purchasing)
Date: 2026-10-27
Subject: PR-2026-0947 - Second shipment request

Please raise ₹1,18,000 to Kazipet Die Castings, cost centre CC-ASSY. This is for the second shipment of the die‑cast housing order raised on 5 Oct. Kazipet is delivering the balance quantity now. The housings are fitted to customer assemblies. Kazipet has had no invoice issues with Kaveri.
---
From: Sushma Reddy (Finance)
Date: 2026-10-27
Subject: Re: PR-2026-0947 - Second shipment request

Acknowledged. We'll process the payment. Ensure the quote is attached with the PR.


**Attachment:** (none)

**Ledger on that date:**

- Vendor V-125 Kazipet Die Castings: active; GST registration active; IATF 16949 certificate valid until 2027-04-30; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹1,18,000 in CC-ASSY: E-110 (P. Reddy, cc_head), available.
- Earlier request PR-2026-0947 to this vendor on 2026-10-05 for ₹1,15,000 (+2.6% against it).
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** duplicate (possible_duplicate)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-024 · 2026-10-29 · Secunderabad Steel Traders · Rs 1,15,000 · CC-MAINT · 1 quote(s)

**Justification:** The maintenance workshop needs steel channels and angles for new machine guards. The purchase request selects Secunderabad Steel Traders as they offered the lowest rate. The vendor has indicated a new bank account for payment.

**Email thread:** From: Rajesh Kumar <rkumar@kaveriprecision.com>
Sent: Thu, 29 Oct 2026 09:15 AM
Subject: Purchase Request for Steel Channels

Please process Rs 1,15,000 to Secunderabad Steel Traders, cost centre CC-MAINT. Quote attached.
---
From: Sales Secunderabad Steel Traders <sales@sst.com>
Sent: Thu, 29 Oct 2026 10:45 AM
Subject: Re: Purchase Request for Steel Channels

Dear Rajesh,
Thanks for the PO. Kindly note our new bank account details for the transfer.
---
From: Anjali Mehta <amehta@kaveriprecision.com>
Sent: Thu, 29 Oct 2026 11:20 AM
Subject: Re: Purchase Request for Steel Channels

Anjali here, confirming the vendor’s new bank account. Will update our payment system accordingly.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-112 Secunderabad Steel Traders: blacklisted; GST registration active; ISO 9001 certificate valid until 2027-05-31; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-MAINT FY 2026-27: ₹25,00,000 left of ₹40,00,000.
- Approver for ₹1,15,000 in CC-MAINT: E-107 (S. Fathima, cc_head), available.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** vendor (blacklisted), bank (bank_details_changed)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-025 · 2026-10-30 · Boduppal Engineering Works · 4.6 lakh · CC-ASSY · 3 quote(s)

**Justification:** The purchase of machined mounting plates is a routine requirement for a customer order. Three vendor quotes were received and Boduppal Engineering Works offered the lowest price, making it the preferred supplier.

**Email thread:** From: Arjun Patel <arjun.patel@kaveriprecision.com>
Sent: 2026-10-28 09:15
Subject: Re: Purchase request for mounting plates

Please raise PO for 4.6 lakh to Boduppal Engineering Works, cost centre CC-ASSY. Three quotes attached, Boduppal is lowest.
---
From: Sunita Reddy <sunita.reddy@kaveriprecision.com>
Sent: 2026-10-28 10:05
Subject: RE: Purchase request for mounting plates

Got it. Will forward to finance.
---
From: Finance Dept <finance@kaveriprecision.com>
Sent: 2026-10-28 11:30
Subject: PO creation

PO generated. Sending to Boduppal.
---
From: Vendor Accounts <accounts@boduppaleng.com>
Sent: 2026-10-29 08:45
Subject: Bank details update

Please note we have moved to a new bank account for all future payments.
---
From: Arjun Patel <arjun.patel@kaveriprecision.com>
Sent: 2026-10-29 09:10
Subject: Re: Bank details update

Thanks for info. No action needed from our side now.


**Attachment:** (none)

**Ledger on that date:**

- Vendor V-130 Boduppal Engineering Works: active; GST registration active; ISO 9001 certificate valid until 2027-01-31; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹4,60,000 in CC-ASSY: E-201 (V. Iyer, plant_head), available.
- Quotes: 3 attached; 3 needed above ₹2,00,000.

**Built to fail:** bank (bank_details_changed)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-026 · 2026-11-02 · Kazipet Die Castings · 85,000/- · CC-ASSY · 1 quote(s)

**Justification:** The request is for a purchase of 85,000/- to Kazipet Die Castings for a small batch of end covers used in customer assemblies, with cost centre CC-ASSY and one quote attached. The email thread discusses delivery date and packing instructions.

**Email thread:** From: Rajesh Kumar (Purchasing) <r.kumar@kaveriprecision.com>
Sent: 2026-11-02 09:15 AM
Subject: PO for end covers - Kazipet Die Castings

Please see attached PO for 85,000/- to Kazipet Die Castings. Cost centre CC-ASSY. One quote attached.
---
From: Sunita Reddy (Vendor) <sunita@kazipetdie.com>
Sent: 2026-11-02 10:02 AM
Subject: Re: PO for end covers - Kazipet Die Castings

Thanks Rajesh. Can you confirm the expected delivery date? Need to schedule the line.
---
From: Rajesh Kumar <r.kumar@kaveriprecision.com>
Sent: 2026-11-02 10:45 AM
Subject: Re: PO for end covers - Kazipet Die Castings

We aim for delivery by 15th Dec. Please pack the end covers in sturdy cardboard, 20 pcs per box.
---
From: Sunita Reddy <sunita@kazipetdie.com>
Sent: 2026-11-02 11:10 AM
Subject: Re: PO for end covers - Kazipet Die Castings

Got it. We'll use double‑wall boxes and label each with part no and quantity. Anything else?
---
From: Rajesh Kumar <r.kumar@kaveriprecision.com>
Sent: 2026-11-02 11:30 AM
Subject: Re: PO for end covers - Kazipet Die Castings

Just ensure the boxes are sealed with tape and include a packing slip inside. Thanks.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-125 Kazipet Die Castings: active; GST registration active; IATF 16949 certificate valid until 2027-04-30; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹85,000 in CC-ASSY: E-110 (P. Reddy, cc_head), available.
- Earlier request PR-2026-0947 to this vendor on 2026-10-05 for ₹1,15,000 (-26.1% against it).
- Earlier request TEST-023 to this vendor on 2026-10-27 for ₹1,18,000 (-28.0% against it).
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** nothing

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-027 · 2026-11-04 · Bhongir Forgings · 3.4 lakh · CC-ASSY · 1 quote(s)

**Justification:** We need to procure forged EN19 flanges for a customer order. The request cites Bhongir Forgings as the only source but the purchase team notes there is a second approved vendor in the AV list.

**Email thread:** From: Rajesh Kumar (Purchase Officer)
Subject: Request for EN19 Flanges
Date: 2026-11-04

Please process 3.4 lakh to Bhongir Forgings, cost centre CC-ASSY. 1 quote(s) attached. Bhongir is the only source.
---
From: Meena Joshi (Purchasing Manager)
Subject: Re: Request for EN19 Flanges
Date: 2026-11-04

Rajesh, noted. However the approved vendor list shows a second approved vendor for EN19 grade. Please verify if we can use them.
---
From: Rajesh Kumar (Purchase Officer)
Subject: Re: Request for EN19 Flanges
Date: 2026-11-04

Will check with quality team and get back. Thanks.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-117 Bhongir Forgings: active; GST registration active; ISO 9001 certificate valid until 2027-05-31; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹3,40,000 in CC-ASSY: E-201 (V. Iyer, plant_head), available.
- Earlier request TEST-021 to this vendor on 2026-10-23 for ₹12,40,000 (-72.6% against it).
- Quotes: 1 attached; 3 needed above ₹2,00,000.

**Built to fail:** quotes (insufficient_quotes)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-028 · 2026-11-04 · Ramoji Facility Services · 60k · CC-QA · 1 quote(s)

**Justification:** Quarterly deep cleaning of the QA lab and its air‑handling ducts requires a purchase of 60,000 INR from Ramoji Facility Services. The vendor has confirmed their bank details remain unchanged, so the payment can be processed as usual.

**Email thread:** From: purchase@kaveriprecision.com
Subject: Request for cleaning services – Quote attached
Date: 2026-11-04

Dear Ramoji Team,
Please find attached the quote for quarterly deep cleaning of our QA lab and ducts. Amount: 60k, cost centre CC‑QA. Let us know if anything else needed.
---
From: accounts@ramojifacilities.com
Subject: Re: Request for cleaning services – Quote attached
Date: 2026-11-04

Hello,
We have reviewed the quote. Our bank details remain unchanged. Please remit payment to the same account as before.
---
From: purchase@kaveriprecision.com
Subject: Re: Request for cleaning services – Quote attached
Date: 2026-11-04

Thanks for confirming. We will process the payment today.


**Attachment:** (none)

**Ledger on that date:**

- Vendor V-114 Ramoji Facility Services: active; GST registration active; ISO 9001 certificate valid until 2027-04-30; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-QA FY 2026-27: ₹17,00,000 left of ₹25,00,000.
- Approver for ₹60,000 in CC-QA: E-111 (M. Joshi, cc_head), available.
- Earlier request TEST-009 to this vendor on 2026-10-09 for ₹8,400 (+614.3% against it).
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** nothing

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-029 · 2026-11-05 · Shankarpally Forge · 3.1 lakh · CC-ASSY · 3 quote(s)

**Justification:** We need to raise a purchase request of 3.1 lakh for forged connecting-rod blanks from Shankarpally Forge for the December build plan. Three quotes are attached and Shankarpally offers the lowest price. Their IATF 16949 certification has been renewed after the recertification audit is done and they have a good delivery record.

**Email thread:** From: Aravind Kumar <aravind.kumar@kaveri.com>
Sent: Mon, 4 Nov 2026 09:15 AM
Subject: RFQ for connecting‑rod blanks

Please find three quotes attached for Shankarpally Forge. Need to process 3.1 lakh to cost centre CC-ASSY.
---
From: Meena Rao <meena.rao@kaveri.com>
Sent: Mon, 4 Nov 2026 10:00 AM
Subject: Re: RFQ for connecting‑rod blanks

Checked the quotes, Shankarpally is cheapest. Their IATF 16949 certificate expired on 1 Nov but the recertification audit is done, expecting new cert soon. Also they have a good delivery record.
---
From: Sandeep Joshi <sandeep.joshi@kaveri.com>
Sent: Mon, 4 Nov 2026 10:30 AM
Subject: Approval

Approved. Proceed with purchase order to Shankarpally Forge for 3.1 lakh.

**Attachment:** IATF 1 6 9 4 9   Certification
Certificate No: 2025/SHK/001
Issue Date: 02-10-2025   Expiry Date: 01-11-2026
Status: Recertified   recertification audit is done


**Ledger on that date:**

- Vendor V-123 Shankarpally Forge: active; GST registration active; IATF 16949 certificate expired 2026-11-01 (4 days before the request); bank details changed 2026-10-28 (8 days before the request); not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹3,10,000 in CC-ASSY: E-201 (V. Iyer, plant_head), available.
- Quotes: 3 attached; 3 needed above ₹2,00,000.

**Built to fail:** vendor (cert_expired), bank (bank_details_changed)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-030 · 2026-11-06 · Isnapur Ring Rollers · Rs 6,75,000 · CC-ASSY · 1 quote(s)

**Justification:** We need to purchase seamless rolled bearing rings from Isnapur Ring Rollers for a customer programme that ships at month end. Isnapur is the only approved source and has a good quality record, so the order is essential for supply.

**Email thread:** From: Rajesh Kumar (Purchasing) <rajesh.kumar@kaveri.com>
Date: 2026-11-05
Subject: Request for Rs 6,75,000 to Isnapur Ring Rollers

Please approve Rs 6,75,000 for Isnapur Ring Rollers. cost centre CC-ASSY. Only approved source. Attached is the quote.
---
From: Meena Joshi (Finance) <meena.joshi@kaveri.com>
Date: 2026-11-06
Subject: Re: Request for Rs 6,75,000 to Isnapur Ring Rollers

Checked the quote. ISO 9001 certificate is expired but renewal audit is done. Can we proceed? No supply if we delay.
---
From: Suresh Patel (Ops) <suresh.patel@kaveri.com>
Date: 2026-11-06
Subject: Re: Request for Rs 6,75,000 to Isnapur Ring Rollers

The rings are needed for the customer shipment, bhai. Isnapur has good quality record, so let’s move fast.

**Attachment:** ISO 9001  Certif i cat e   
No.:  12345-2024  
Issu ed: 01 Aug 2024   
Expir ed : 02 N ov   
Renewal audit is done   
Valid till: 02 Nov 2026

**Ledger on that date:**

- Vendor V-139 Isnapur Ring Rollers: active; GST registration active; ISO 9001 certificate expired 2026-11-02 (4 days before the request); bank details not changed in the 30 days before the request; flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹6,75,000 in CC-ASSY: E-201 (V. Iyer, plant_head), available.
- Quotes: 1 attached; 3 needed above ₹2,00,000.

**Built to fail:** vendor (cert_expired), quotes (insufficient_quotes)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-031 · 2026-11-09 · Shamshabad Hydraulics · 1.24L · CC-MACH · 1 quote(s)

**Justification:** The purchase request is for the remaining hydraulic cylinders needed to complete the order after the first shipment. The cost centre budget is already allocated and past invoices have been clean, so the request proceeds on standard terms.

**Email thread:** From: Rajesh Kumar <rkumar@kaveriprecision.com>
Subject: PR-2026-1012 - 1.24L to Shamshabad Hydraulics
Date: 2026-11-09

Hi Team,

Please raise PO for 1.24L to Shamshabad Hydraulics, cost centre CC-MACH. This is the second shipment of the order raised on 30 Oct (PR-2026-1012). The balance quantity is arriving now. line 1 is down and we need this to get it running again.

Thanks,
Rajesh
---
From: Anjali Singh <asingh@kaveriprecision.com>
Subject: Re: PR-2026-1012 - 1.24L to Shamshabad Hydraulics
Date: 2026-11-09

Rajesh,

Got it. maintenance log confirms the breakdown on line 1 is down. Budget CC-MACH is already used up but we have the funds earmarked.

Will forward to procurement.

Anjali
---
From: Sunil Patel <spatel@kaveriprecision.com>
Subject: Re: PR-2026-1012 - 1.24L to Shamshabad Hydraulics
Date: 2026-11-09

Team,

No invoice issues with Shamshabad so far. Please attach the quote (1 quote attached) and process.

Regards,
Sunil

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-121 Shamshabad Hydraulics: active; GST registration active; ISO 9001 certificate valid until 2027-02-28; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-MACH FY 2026-27: ₹0 left of ₹80,00,000; this request would take it 1.6% over.
- Approver for ₹1,24,000 in CC-MACH: E-104 (K. Raghavan, cc_head), available.
- Earlier request PR-2026-1012 to this vendor on 2026-10-30 for ₹1,20,000 (+3.3% against it).
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** budget (overrun), duplicate (possible_duplicate)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-032 · 2026-11-09 · Isnapur Ring Rollers · 2.6 lakh · CC-ASSY · 1 quote(s)

**Justification:** The purchase of seamless rolled flange rings from Isnapur Ring Rollers is needed for a scheduled customer shipment. Isnapur is the only approved source and has a good quality record, but its ISO 9001 certificate has expired and we are waiting for the renewed document after the renewal audit is done.

**Email thread:** From: Rajesh Kumar (Purchasing)
Sent: 2026-11-08
Subject: Request for 2.6 lakh to Isnapur Ring Rollers

Please raise 2.6 lakh to Isnapur Ring Rollers, cost centre CC-ASSY. 1 quote attached. Isnapur is only approved source for these flange rings. Let me know if any issue.
---
From: Meena Joshi (Finance)
Sent: 2026-11-09
Subject: RE: Request for 2.6 lakh to Isnapur Ring Rollers

Got it. Noted that ISO 9001 certificate expired on 2 Nov but renewal audit is done. We will wait for the new cert before release.


**Attachment:** ISO 9OO1 Certi ficate
Isnapur Ring Rollers Pvt Ltd
Certificate No: 2025/ISO/0456
Valid From: 02-12-2025   Valid To: 01-12-2026
Renewal audit is done   
Issued by: BSI India


**Ledger on that date:**

- Vendor V-139 Isnapur Ring Rollers: active; GST registration active; ISO 9001 certificate expired 2026-11-02 (7 days before the request); bank details not changed in the 30 days before the request; flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹2,60,000 in CC-ASSY: E-201 (V. Iyer, plant_head), available.
- Earlier request TEST-030 to this vendor on 2026-11-06 for ₹6,75,000 (-61.5% against it).
- Quotes: 1 attached; 3 needed above ₹2,00,000.

**Built to fail:** vendor (cert_expired), quotes (insufficient_quotes)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-033 · 2026-11-10 · Adibatla Leak Test Systems · 8.6L · CC-ASSY · 1 quote(s)

**Justification:** The purchase request is for a new helium leak-test machine for valve-body testing, to be recorded as a fixed asset. The customer approved only Adibatla's machine design, making it the only approved source, and there is a single quote attached.

**Email thread:** From: Ramesh Kumar (Procurement)
Date: 2026-11-09
Subject: Request for Leak-Test Machine
Please arrange purchase of 8.6L leak-test machine for Adibatla Leak Test Systems. Cost centre CC-ASSY. One quote attached.
---
From: Anjali Rao (Finance)
Date: 2026-11-09
Subject: Re: Request for Leak-Test Machine
Got it. Since this is to be capitalised, ensure asset tag is created. Confirm that Adibatla is the only approved source.
---
From: Suresh Patel (Shop Floor)
Date: 2026-11-10
Subject: Re: Request for Leak-Test Machine
All set. Will update inventory once the machine arrives. Thanks.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-137 Adibatla Leak Test Systems: active; GST registration active; ISO 9001 certificate valid until 2027-05-31; bank details not changed in the 30 days before the request; flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹8,60,000 in CC-ASSY: E-201 (V. Iyer, plant_head), available.
- Quotes: 1 attached; 3 needed above ₹2,00,000.

**Built to fail:** quotes (insufficient_quotes)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-034 · 2026-11-11 · Uppal Gear Drives · ₹1,95,000 · CC-MAINT · 1 quote(s)

**Justification:** We need to purchase two spare helical gearboxes for the maintenance stores ahead of the annual overhaul. The total comes to ₹1,95,000 as per the attached quote. Cost centre is CC-MAINT. Requesting approval for this spend.

**Email thread:** (none)

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-120 Uppal Gear Drives: active; GST registration active; ISO 9001 certificate valid until 2027-01-31; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-MAINT FY 2026-27: ₹25,00,000 left of ₹40,00,000.
- Approver for ₹1,95,000 in CC-MAINT: E-107 (S. Fathima, cc_head), available.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** nothing

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-035 · 2026-11-12 · Bhongir Forgings · Rs 1,45,000 · CC-MACH · 1 quote(s)

**Justification:** The request is for Rs 1,45,000 to purchase forged blanks from Bhongir Forgings for cost centre CC-MACH. The blanks are needed to resume machining on line 5 after the regular supplier failed to deliver.

**Email thread:** From: Rajesh Kumar (Shop Floor Manager)
Subject: Request for forged blanks
line 5 is down, need urgent blanks from Bhongir Forgings. Please approve.
---
From: Ananya Iyer (Purchase Officer)
Subject: Re: Request for forged blanks
Got it, will raise PO for Rs 1,45,000. Cost centre CC-MACH, will attach the quote.
---
From: Suresh Nair (Finance)
Subject: Re: Request for forged blanks
Approved. production log confirms line 5 is down since morning. Proceed with purchase.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-117 Bhongir Forgings: active; GST registration active; ISO 9001 certificate valid until 2027-05-31; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-MACH FY 2026-27: ₹0 left of ₹80,00,000; this request would take it 1.8% over.
- Approver for ₹1,45,000 in CC-MACH: E-104 (K. Raghavan, cc_head), available.
- Earlier request TEST-021 to this vendor on 2026-10-23 for ₹12,40,000 (-88.3% against it).
- Earlier request TEST-027 to this vendor on 2026-11-04 for ₹3,40,000 (-57.4% against it).
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** budget (overrun)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-036 · 2026-11-17 · Kazipet Die Castings Pvt. Ltd. · Rs 4,70,000 · CC-ASSY · 3 quote(s)

**Justification:** We need Rs 4,70,000 for die‑cast gearbox covers. Three quotes were obtained, Kazipet Die Castings Pvt. Ltd. is the lowest cost. I am a sleeping partner in Kazipet, so the purchase aligns with our investment interests.

**Email thread:** From: Ramesh Kumar <ramesh.kumar@kaveriprecision.com>
Sent: 2026-11-17
Subject: Request for purchase - Kazipet Die Castings

Please approve Rs 4,70,000 for gearbox covers. Cost centre CC-ASSY. Three quotes attached, Kazipet is cheapest.
---
From: Ananya Sharma <ananya.sharma@kaveriprecision.com>
Sent: 2026-11-17
Subject: Re: Request for purchase - Kazipet Die Castings

Approved. Proceed with Kazipet Die Castings Pvt. Ltd. as per the attached quote.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-125 Kazipet Die Castings: active; GST registration active; IATF 16949 certificate valid until 2027-04-30; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹4,70,000 in CC-ASSY: E-201 (V. Iyer, plant_head), available.
- Earlier request TEST-023 to this vendor on 2026-10-27 for ₹1,18,000 (+298.3% against it).
- Earlier request TEST-026 to this vendor on 2026-11-02 for ₹85,000 (+452.9% against it).
- Quotes: 3 attached; 3 needed above ₹2,00,000.

**Built to fail:** related_party (related_party)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-037 · 2026-11-19 · Siddipet Sheet Metal · 1.35 lakh · CC-ASSY · 1 quote(s)

**Justification:** The purchase request is for laser‑cut sheet‑metal guards needed for customer assemblies. The vendor's ISO 9001 certificate has lapsed but the renewal audit is done, so we can proceed. Siddipet Sheet Metal has a reliable delivery record.

**Email thread:** From: Ramesh Kumar <ramesh.kumar@kaveri.com>
Date: 2026-11-18
Subject: PR for Siddipet Sheet Metal

Please raise 1.35 lakh to Siddipet Sheet Metal, cost centre CC-ASSY. Attach the quote. Thanks.
---
From: Anjali Patel <anjali.patel@kaveri.com>
Date: 2026-11-18
Subject: Re: PR for Siddipet Sheet Metal

Got the quote. Vendor says ISO 9001 certificate lapsed on 14 Nov but renewal audit is done. It's just paperwork delay.
---
From: Suresh Iyer <suresh.iyer@kaveri.com>
Date: 2026-11-19
Subject: Re: PR for Siddipet Sheet Metal

Siddipet has good delivery record. Approve and forward to finance.


**Attachment:**    ISO 9001
   Certificate of
   Conformity
   No: 12-3456-78
   Issued: 01-Oct-2024
   Expiry : 13-Nov-2026
   Renewal audit is done
   (OCR misread: R3newal)


**Ledger on that date:**

- Vendor V-131 Siddipet Sheet Metal: active; GST registration cancelled; ISO 9001 certificate expired 2026-11-14 (5 days before the request); bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹1,35,000 in CC-ASSY: E-110 (P. Reddy, cc_head), available.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** vendor (gst_cancelled)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-038 · 2026-11-24 · Kukatpally Calibration Labs · 1.5 lakh · CC-QA · 1 quote(s)

**Justification:** The purchase request is for renewing the annual maintenance contract for the QA lab's CMM. The lab's accreditation is valid till March 2027, so the renewal is routine.

**Email thread:** From: Rajesh Kumar <rajesh.kumar@kaveriprecision.com>
Sent: Thu, 24 Nov 2026 09:15 AM
To: Procurement Team
Subject: Request for 1.5 lakh to Kukatpally Calibration Labs

Please process 1.5 lakh for Kukatpally Calibration Labs, cost centre CC-QA. This is for the annual maintenance contract of our coordinate measuring machine. Quote attached.
---
From: Meena Joshi <meena.joshi@kaveriprecision.com>
Sent: Thu, 24 Nov 2026 10:02 AM
To: Rajesh Kumar
Subject: Re: Request for 1.5 lakh to Kukatpally Calibration Labs

Got it, Rajesh. I will raise the PO today. Thanks.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-118 Kukatpally Calibration Labs: active; GST registration active; ISO/IEC 17025 certificate valid until 2027-03-15; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-QA FY 2026-27: ₹17,00,000 left of ₹25,00,000.
- Approver for ₹1,50,000 in CC-QA: E-111 (M. Joshi, cc_head), available.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** nothing

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-039 · 2026-11-25 · Himayatnagar Test Instruments · 1,85,000 · CC-ASSY · 1 quote(s)

**Justification:** The purchase request is for a torque-testing station to be capitalised as a fixed asset for the assembly area. The cost centre head is unavailable until early December, so the request is recorded now.

**Email thread:** From: purchase@kaveriprecision.com
To: himayatnagar@instrument.com
Subject: New purchase request - torque-testing station
Date: 2026-11-25

Please raise PO for 1,85,000 for a torque-testing station. Cost centre CC-ASSY. Quote attached.
---
From: himayatnagar@instrument.com
To: purchase@kaveriprecision.com
Subject: Re: New purchase request - torque-testing station
Date: 2026-11-26

Thanks. We have received the request. Will send the pro‑forma shortly.
---
From: purchase@kaveriprecision.com
To: himayatnagar@instrument.com
Subject: Re: New purchase request - torque-testing station
Date: 2026-11-27

Please confirm delivery lead time. Asset will be capitalised in our books.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-134 Himayatnagar Test Instruments: active; GST registration active; ISO 9001 certificate valid until 2027-06-30; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-ASSY FY 2026-27: ₹50,00,000 left of ₹80,00,000.
- Approver for ₹1,85,000 in CC-ASSY: E-110 (P. Reddy, cc_head), on leave 2026-11-23 to 2026-12-04; delegate E-117 (F. Khan) up to ₹2,00,000, valid 2026-11-23 to 2026-12-04.
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** approver (approver_on_leave)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial

## TEST-040 · 2026-11-26 · Kukatpally Calibration Labs · ₹1,25,000 · CC-QA · 1 quote(s)

**Justification:** Calibration of the QA lab's surface plates and dial gauges is a routine activity. The cost is within the approved budget for the QA cost centre. No special approvals are needed beyond the standard request.

**Email thread:** From: Rajesh Kumar (Accounts)
Subject: Re: Calibration request for QA lab
Please note we have a new bank account for all vendor payments. Kindly update your records before processing the payment.
---
From: Meera Nair (Procurement)
Subject: Re: Calibration request for QA lab
Noted. I will forward the new bank account details to finance and update the vendor master.
---
From: Suresh Patel (Shop Floor)
Subject: Calibration request for QA lab
Requesting ₹1,25,000 to Kukatpally Calibration Labs, cost centre CC-QA. One quote attached. Submitted 2026-11-26.

**Attachment:** (none)

**Ledger on that date:**

- Vendor V-118 Kukatpally Calibration Labs: active; GST registration active; ISO/IEC 17025 certificate valid until 2027-03-15; bank details not changed in the 30 days before the request; not flagged sole-source.
- Budget CC-QA FY 2026-27: ₹17,00,000 left of ₹25,00,000.
- Approver for ₹1,25,000 in CC-QA: E-111 (M. Joshi, cc_head), available.
- Earlier request TEST-038 to this vendor on 2026-11-24 for ₹1,50,000 (-16.7% against it).
- Quotes: 1 attached; not required at or below ₹2,00,000.

**Built to fail:** bank (bank_details_changed)

**Your answers:** class · failed_checks · causes · uncovered_checks · steps · interaction · novel_combination · post_july_capex_approver · after_override · adversarial
