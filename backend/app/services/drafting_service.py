import re

from app.core.logging import get_logger

logger = get_logger(__name__)


DRAFT_TEMPLATES = {
    "fir": {
        "title": "First Information Report (FIR)",
        "template": """FIR No: _______________
Date: ________________
Police Station: ________________
District: ________________

FIRST INFORMATION REPORT
(Under BNSS Section 173)

1. Name of Informant: ____________________________________________
2. Father's/Husband's Name: ______________________________________
3. Address: _______________________________________________________
4. Occupation: ____________________________________________________
5. Contact No: ___________________________________________________

DETAILS OF OFFENSE:

I, the above-named informant, state that on ______/______/______ at approximately ______ hours, at _____________________________________ (place) the following offense was committed:

_______________________________________________________________
_______________________________________________________________
_______________________________________________________________

DESCRIPTION OF INCIDENT:
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________

NAME(S) OF ACCUSED (if known):
1. _______________________________________________________________
2. _______________________________________________________________
3. _______________________________________________________________

DESCRIPTION OF ACCUSED (if name not known):
_______________________________________________________________

WITNESSES:
1. Name: ____________________ Address: ___________________________
2. Name: ____________________ Address: ___________________________
3. Name: ____________________ Address: ___________________________

PROPERTY TAKEN/DAMAGED (if applicable):
_______________________________________________________________
Value: Rs. _______________

I affirm that the information given above is true and correct to the best of my knowledge and belief.

Signature of Informant: _______________
Date: ________________
Time: ________________

RECEIVED AND RECORDED:

Signature of Investigating Officer: _______________
Name: ________________
Rank: ________________
Date: ________________
Time: ________________

_______________________________________________________________
(Original FIR copy given to informant free of cost)
""",
    },
    "legal_notice": {
        "title": "Legal Notice",
        "template": """From:
[Name]
[Address]
[City, State, PIN]

Date: ________________

To,
[Name]
[Address]
[City, State, PIN]

SUBJECT: ________________

Dear Sir/Madam,

I, ______________________________, son/daughter of ______________________________, resident of ______________________________, do hereby serve you with the following legal notice:

1. ________________________________________________________________
2. ________________________________________________________________
3. ________________________________________________________________

That you are hereby called upon to ______________________________ within __________ days from the receipt of this notice.

In case of your failure to comply with the above demands, I shall be constrained to initiate appropriate legal proceedings against you before the competent court of law, wherein you shall be held liable for all costs and consequences thereof.

This notice is being sent without prejudice to my rights and contentions.

Yours faithfully,

__________________
(Signature)

Place: ________________
Date: ________________

__________________
(Seal/Stamp of Advocate, if applicable)
""",
    },
    "bail_application": {
        "title": "Bail Application",
        "template": """IN THE COURT OF ______________________________

Case No: ______________________________
FIR No: ______________________________
Police Station: ______________________________

IN THE MATTER OF:
State vs. [Name of Accused]

APPLICATION FOR REGULAR BAIL
(Under BNSS Section 478)

MOST RESPECTFULLY SHOWETH:

1. That the applicant/accused, namely ______________________________, son of ______________________________, aged about ____ years, resident of ______________________________, is in judicial custody since ______/______/______ in connection with the above-mentioned case.

2. That the applicant has been falsely implicated in the present case and has not committed any offense as alleged.

3. That the investigation is complete and the charge sheet has been filed. The applicant's further custody is not required.

4. That the applicant is a permanent resident of the above address and undertakes to appear before this Hon'ble Court as and when required.

5. That the applicant undertakes not to tamper with evidence or influence witnesses.

6. That the applicant is ready and willing to furnish bail bonds and sureties as may be directed by this Hon'ble Court.

PRAYER

In view of the above, it is most respectfully prayed that this Hon'ble Court may be pleased to release the applicant on regular bail on such terms and conditions as this Hon'ble Court may deem fit and proper.

Place: ________________
Date: ________________

                                          __________________
                                          (Counsel for Applicant)

BOND AND SURETY:

I, ______________________________, do hereby bind myself to attend the Court on all hearing dates and abide by the conditions of bail.

__________________
(Applicant)

__________________
(Surety)
""",
    },
    "affidavit": {
        "title": "Affidavit",
        "template": """AFFIDAVIT

I, ______________________________, son/daughter/wife of ______________________________, aged about ____ years, by occupation ______________________________, resident of ______________________________, do hereby solemnly affirm and state on oath as follows:

1. I am the deponent herein and am fully conversant with the facts and circumstances of this case.

2. ________________________________________________________________
3. ________________________________________________________________
4. ________________________________________________________________
5. ________________________________________________________________

I state that the contents of the above affidavit are true and correct to my knowledge and belief, and nothing material has been concealed therefrom.

DEPONENT

VERIFICATION

I, the above-named deponent, do hereby verify that the contents of this affidavit are true and correct to my knowledge and belief. No part of this affidavit is false and nothing material has been concealed therefrom.

Verified at ________________ on this ______ day of ____________, ______.

DEPONENT

SOLEMNLY AFFIRMED BEFORE ME

__________________
(Oath Commissioner / Notary Public)

Place: ________________
Date: ________________
""",
    },
    "consumer_complaint": {
        "title": "Consumer Complaint",
        "template": """BEFORE THE HON'BLE ______________________________ CONSUMER DISPUTES REDRESSAL COMMISSION

Complaint No: ______________________________

IN THE MATTER OF:

[Name of Complainant]
[Address]
[City, State, PIN]
                                                      ...Complainant

VERSUS

[Name of Opposite Party]
[Address]
[City, State, PIN]
                                                      ...Opposite Party

COMPLAINT UNDER SECTION 35 OF THE CONSUMER PROTECTION ACT, 2019

MOST RESPECTFULLY SHOWETH:

1. The complainant is a consumer as defined under Section 2(7) of the Consumer Protection Act, 2019.

2. The opposite party is engaged in the business of ______________________________.

3. That the complainant availed the services/purchased goods from the opposite party on ______/______/______ vide invoice/receipt no. ________________ for a consideration of Rs. _______________.

4. That there was a deficiency in service/defect in goods as follows:
   _______________________________________________________________
   _______________________________________________________________

5. Despite repeated requests, the opposite party has failed to redress the grievance.

PRAYER

It is therefore most respectfully prayed that this Hon'ble Commission may be pleased to:

a) Direct the opposite party to ______________________________
b) Award compensation of Rs. _______________ for mental agony and harassment
c) Award cost of litigation
d) Pass any other order this Hon'ble Commission may deem fit

Place: ________________
Date: ________________

                                          __________________
                                          (Complainant/Advocate)

List of Documents Attached:
1. Copy of invoice/receipt
2. Correspondence copies
3. Other supporting documents
""",
    },
    "agreement": {
        "title": "Agreement / Contract",
        "template": """THIS AGREEMENT is made on this ______ day of ____________, ______

BETWEEN

[Name], son/daughter of ________________, aged ______ years, resident of ______________________________ (hereinafter called "Party A")

AND

[Name], son/daughter of ________________, aged ______ years, resident of ______________________________ (hereinafter called "Party B")

WHEREAS:

A. _______________________________________________________________
B. _______________________________________________________________
C. _______________________________________________________________

NOW, IT IS HEREBY AGREED AS FOLLOWS:

1. **TERM:** This Agreement shall remain in force from ______/______/______ to ______/______/______.

2. **CONSIDERATION:** Party A agrees to pay Party B a sum of Rs. _______________ (Rupees ________________________________ only).

3. **OBLIGATIONS OF PARTY A:**
   _______________________________________________________________

4. **OBLIGATIONS OF PARTY B:**
   _______________________________________________________________

5. **TERMINATION:** Either party may terminate this Agreement by giving ____ days' written notice.

6. **INDEMNITY:** Each party shall indemnify the other against any loss arising from breach of this Agreement.

7. **DISPUTE RESOLUTION:** Any dispute shall be referred to arbitration under the Arbitration and Conciliation Act, 1996.

8. **JURISDICTION:** The courts at ________________ shall have exclusive jurisdiction.

9. **GOVERNING LAW:** This Agreement shall be governed by the Indian Contract Act, 1872.

IN WITNESS WHEREOF, the parties have signed this Agreement on the date first above written.

__________________                            __________________
(Signature of Party A)                       (Signature of Party B)

WITNESSES:
1. ____________________                      2. ____________________
   _______________                              _______________
""",
    },
    "civil_plaint": {
        "title": "Civil Plaint",
        "template": """IN THE COURT OF ______________________________

Original Suit No: ______________________________

IN THE MATTER OF:

[Name of Plaintiff]
[Address]
[City, State, PIN]
                                                      ...Plaintiff

VERSUS

[Name of Defendant]
[Address]
[City, State, PIN]
                                                      ...Defendant

SUIT FOR ______________________________

PLAINT UNDER ORDER IV RULE 1 OF CPC, 1908

MOST RESPECTFULLY SHOWETH:

1. The plaintiff is the ________________ of the suit property/person.

2. The defendant is ______________________________.

3. The cause of action arose on ______/______/______ at ________________ when ______________________________.

4. The value of the suit for the purpose of court fees and jurisdiction is Rs. _______________.

5. This Hon'ble Court has jurisdiction to try the present suit.

6. The plaintiff has not filed any other suit or proceeding regarding the same cause of action.

PRAYER

In view of the above, it is most respectfully prayed that this Hon'ble Court may be pleased to:

a) Decree the suit in favor of the plaintiff
b) Award cost of the suit
c) Grant any other relief deemed fit

Place: ________________
Date: ________________

                                          __________________
                                          (Plaintiff/Advocate)

VERIFICATION

I, ______________________________, plaintiff above named, do hereby verify that the contents of this plaint are true and correct to my knowledge and belief.

Verified at ________________ on ______/______/______.

__________________
(Plaintiff)
""",
    },
    "divorce_petition": {
        "title": "Divorce Petition",
        "template": """IN THE FAMILY COURT AT ______________________________

Matrimonial Petition No: ______________________________

IN THE MATTER OF:

[Name of Petitioner]
[Address]
[City, State, PIN]
                                                      ...Petitioner

VERSUS

[Name of Respondent]
[Address]
[City, State, PIN]
                                                      ...Respondent

PETITION FOR DISSOLUTION OF MARRIAGE BY DECREE OF DIVORCE
(Under Section 13 of the Hindu Marriage Act, 1955)

MOST RESPECTFULLY SHOWETH:

1. The petitioner was lawfully married to the respondent on ______/______/______ at ________________ according to Hindu rites and ceremonies.

2. After the marriage, the petitioner and respondent lived together at ________________.

3. That the marriage has broken down irretrievably due to the following acts of the respondent:
   (a) ______________________________________________________________
   (b) ______________________________________________________________
   (c) ______________________________________________________________

4. That there is no reasonable probability of reconciliation between the parties.

5. That there is no collusion between the petitioner and the respondent in presenting this petition.

PRAYER

In view of the above, it is most respectfully prayed that this Hon'ble Court may be pleased to:

a) Pass a decree of divorce dissolving the marriage
b) Pass orders regarding maintenance/custody as deemed fit
c) Award cost of the petition

Place: ________________
Date: ________________

                                          __________________
                                          (Petitioner/Advocate)
""",
    },
    "will": {
        "title": "Will / Testament",
        "template": """LAST WILL AND TESTAMENT

I, ______________________________, son/daughter/wife of ______________________________, aged about ____ years, resident of ______________________________, do hereby revoke all former wills and testamentary dispositions made by me and declare this to be my Last Will and Testament.

1. I declare that I am of sound mind and under no undue influence or coercion.

2. I appoint ______________________________, son/daughter of ______________________________, resident of ______________________________, as the Executor of this Will.

3. I give, devise, and bequeath my property as follows:

   A. IMMOVABLE PROPERTY:
      1. ______________________________ - to ______________________________
      2. ______________________________ - to ______________________________

   B. MOVABLE PROPERTY:
      1. ______________________________ - to ______________________________
      2. ______________________________ - to ______________________________

   C. BANK ACCOUNTS, INVESTMENTS, AND CASH:
      1. ______________________________ - to ______________________________

4. If any beneficiary predeceases me, the share shall pass to their legal heirs.

5. I direct that all my just debts, funeral expenses, and testamentary expenses be paid first out of my estate.

IN WITNESS WHEREOF, I have hereunto set my hand to this Will on this ______ day of ____________, ______ at ________________.

__________________
(Testator)

SIGNED by the above-named Testator in our presence and we, in the presence of the Testator and of each other, have hereunto subscribed our names as witnesses.

WITNESSES:

1. Name: ______________________________
   Address: ______________________________
   Signature: _______________________

2. Name: ______________________________
   Address: ______________________________
   Signature: _______________________
""",
    },
}


DRAFT_PROMPTS = {
    "fir": "Draft a complete First Information Report (FIR) under BNSS Section 173 based on the following details. Use proper legal format and Indian police FIR conventions.",
    "legal_notice": "Draft a formal legal notice under Indian law based on the following details. Use professional legal language and proper format.",
    "bail_application": "Draft a regular bail application under BNSS Section 478 based on the following details. Include all standard grounds and prayer.",
    "affidavit": "Draft a sworn affidavit based on the following details. Use proper legal format with verification and oath clauses.",
    "consumer_complaint": "Draft a consumer complaint under Section 35 of the Consumer Protection Act, 2019 based on the following details.",
    "agreement": "Draft a legal agreement/contract under the Indian Contract Act, 1872 based on the following details.",
    "civil_plaint": "Draft a civil plaint under Order IV Rule 1 of CPC, 1908 based on the following details.",
    "divorce_petition": "Draft a divorce petition under Section 13 of the Hindu Marriage Act, 1955 based on the following details.",
    "will": "Draft a Last Will and Testament based on the following details. Use proper legal format with attestation clauses.",
}


def get_draft_types() -> list[str]:
    return list(DRAFT_TEMPLATES.keys())


def get_draft_template(draft_type: str) -> dict | None:
    return DRAFT_TEMPLATES.get(draft_type)


FIELD_BLANK_MAP: dict[str, dict[str, str]] = {
    "fir": {
        "complainant_name": "1. Name of Informant: ____________________________________________",
        "father_name": "2. Father's/Husband's Name: ______________________________________",
        "complainant_address": "3. Address: _______________________________________________________",
        "occupation": "4. Occupation: ____________________________________________________",
        "contact_no": "5. Contact No: ___________________________________________________",
        "incident_date": "on ______/______/______",
        "incident_time": "at approximately ______ hours",
        "incident_place": "at _____________________________________ (place)",
        "description": "DESCRIPTION OF INCIDENT:\n_______________________________________________________________\n_______________________________________________________________\n_______________________________________________________________\n_______________________________________________________________\n_______________________________________________________________",
        "accused_name": "1. _______________________________________________________________",
        "accused_description": "DESCRIPTION OF ACCUSED (if name not known):\n_______________________________________________________________",
        "police_station": "Police Station: ________________",
        "district": "District: ________________",
        "suspected_offence": "_______________________________________________________________\n_______________________________________________________________\n_______________________________________________________________",
        "property_type": "PROPERTY TAKEN/DAMAGED (if applicable):\n_______________________________________________________________",
        "property_value": "Value: Rs. _______________",
        "witness_name": "1. Name: ____________________",
        "witness_address": "Address: ___________________________",
    },
    "legal_notice": {
        "sender_name": "From:\n[Name]",
        "sender_father_name": "son/daughter of ______________________________",
        "sender_address": "[Address]",
        "advocate_name": "__________________\n(Seal/Stamp of Advocate, if applicable)",
        "recipient_name": "To,\n[Name]",
        "recipient_address": "[Address]",
        "subject": "SUBJECT: ________________",
        "facts": "1. ________________________________________________________________\n2. ________________________________________________________________\n3. ________________________________________________________________",
        "relief_sought": "That you are hereby called upon to ______________________________",
        "time_limit_days": "within __________ days",
    },
    "bail_application": {
        "court_name": "IN THE COURT OF ______________________________",
        "case_no": "Case No: ______________________________",
        "fir_number": "FIR No: ______________________________",
        "police_station": "Police Station: ______________________________",
        "applicant_name": "namely ______________________________",
        "father_name": "son of ______________________________",
        "age": "aged about ____ years",
        "address": "resident of ______________________________",
        "arrest_date": "since ______/______/______",
    },
    "affidavit": {
        "deponent_name": "I, ______________________________",
        "father_name": "son/daughter/wife of ______________________________",
        "age": "aged about ____ years",
        "occupation": "by occupation ______________________________",
        "address": "resident of ______________________________",
        "declaration_1": "1. ______________________________",
        "declaration_2": "2. ______________________________",
        "declaration_3": "3. ______________________________",
        "declaration_4": "4. ______________________________",
        "declaration_5": "5. ______________________________",
        "place": "Verified at ________________",
        "oath_commissioner": "__________________\n(Oath Commissioner / Notary Public)",
    },
    "consumer_complaint": {
        "complainant_name": "[Name of Complainant]",
        "complainant_address": "[Address]",
        "opposite_party": "[Name of Opposite Party]",
        "opposite_address": "[Address]",
        "product_service": "The opposite party is engaged in the business of ______________________________",
        "purchase_date": "on ______/______/______",
        "invoice_number": "vide invoice/receipt no. ________________",
        "price_paid": "for a consideration of Rs. _______________",
        "defect_details": "deficiency in service/defect in goods as follows:\n   _______________________________________________________________\n   _______________________________________________________________",
        "relief_requested": "Direct the opposite party to ______________________________",
    },
    "agreement": {
        "party_a_name": '[Name], son/daughter of ________________, aged ______ years, resident of ______________________________ (hereinafter called "Party A")',
        "party_b_name": '[Name], son/daughter of ________________, aged ______ years, resident of ______________________________ (hereinafter called "Party B")',
        "purpose": "A. _______________________________________________________________",
        "effective_date": "on this ______ day of ____________, ______",
        "payment_terms": "a sum of Rs. _______________",
        "party_a_responsibilities": "3. **OBLIGATIONS OF PARTY A:**\n   _______________________________________________________________",
        "party_b_responsibilities": "4. **OBLIGATIONS OF PARTY B:**\n   _______________________________________________________________",
        "termination_notice": "giving ____ days' written notice",
        "jurisdiction": "The courts at ________________",
    },
    "civil_plaint": {
        "court_name": "IN THE COURT OF ______________________________",
        "plaintiff_name": "[Name of Plaintiff]",
        "plaintiff_address": "[Address]",
        "defendant_name": "[Name of Defendant]",
        "defendant_address": "[Address]",
        "suit_type": "SUIT FOR ______________________________",
        "facts": "when ______________________________",
        "cause_date": "on ______/______/______",
        "cause_place": "at ________________",
        "court_fee_value": "The value of the suit for the purpose of court fees and jurisdiction is Rs. _______________",
        "relief_sought": "a) Decree the suit in favor of the plaintiff",
    },
    "divorce_petition": {
        "petitioner_name": "[Name of Petitioner]",
        "petitioner_address": "[Address]",
        "respondent_name": "[Name of Respondent]",
        "respondent_address": "[Address]",
        "marriage_date": "on ______/______/______",
        "marriage_place": "at ________________",
        "last_residence": "lived together at ________________",
        "ground_details": "(a) ______________________________________________________________",
        "relief": "a) Pass a decree of divorce dissolving the marriage",
    },
    "will": {
        "testator_name": "I, ______________________________",
        "testator_father_name": "son/daughter/wife of ______________________________",
        "testator_age": "aged about ____ years",
        "testator_address": "resident of ______________________________",
        "executor_name": "I appoint ______________________________",
        "executor_address": "resident of ______________________________",
        "immovable_property": "      1. ______________________________ - to ______________________________\n      2. ______________________________ - to ______________________________",
        "movable_property": "      1. ______________________________ - to ______________________________\n      2. ______________________________ - to ______________________________",
        "bank_accounts": "      1. ______________________________ - to ______________________________",
        "witness_1_name": "1. Name: ______________________________",
        "witness_1_address": "Address: ______________________________",
        "witness_2_name": "2. Name: ______________________________",
        "witness_2_address": "Address: ______________________________",
    },
}


def _fill_runs(fragment: str, value: str) -> str:
    runs = re.findall(r"_+", fragment)
    if not runs:
        return fragment
    if len(runs) == 1:
        return re.sub(r"_+", lambda m: value, fragment, count=1)

    if re.fullmatch(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", value):
        parts = re.split(r"[-/]", value)
        segments = re.split(r"_+", fragment)
        separators = segments[1:-1]
        if len(parts) == len(runs) and all(re.fullmatch(r"[\/\-\s]*", s) for s in separators):
            return re.sub(r"_+", lambda m: parts.pop(0), fragment)

    return re.sub(r"_+", lambda m: value, fragment, count=1)


def _fill_blanks(content: str, draft_type: str, details: dict) -> str:
    field_map = FIELD_BLANK_MAP.get(draft_type, {})
    if not field_map:
        return content

    lines = content.split("\n")

    for key, value in details.items():
        str_val = str(value).strip()
        if not str_val:
            continue
        blank_pattern = field_map.get(key)
        if not blank_pattern:
            continue

        if "\n" in blank_pattern and "\n" in str_val:
            filled = str_val
        elif "_" not in blank_pattern:
            filled = str_val
        else:
            filled = _fill_runs(blank_pattern, str_val)

        if blank_pattern in content:
            content = content.replace(blank_pattern, filled, 1)
            lines = content.split("\n")
            continue

        for i, line in enumerate(lines):
            if blank_pattern in line:
                lines[i] = line.replace(blank_pattern, filled, 1)
                break

    return "\n".join(lines)


def generate_draft(draft_type: str, details: dict | None = None) -> str | None:
    template_data = DRAFT_TEMPLATES.get(draft_type)
    if not template_data:
        return None

    content = template_data["template"]

    if details:
        for key, value in details.items():
            placeholder = f"[{key}]"
            content = content.replace(placeholder, str(value))

        content = _fill_blanks(content, draft_type, details)

    return content
