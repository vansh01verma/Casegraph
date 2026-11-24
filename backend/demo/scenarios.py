"""Seeded ("precomputed demo intelligence") findings.

Every evidence reference uses a record *key*; the seeder resolves keys to real
evidence IDs, and refuses to seed if a key does not exist. Confidence values
here are analyst-style seeded estimates for the demo, NOT calibrated
probabilities.
"""
from __future__ import annotations

CONTRADICTIONS = [
    {
        "id": "CON-1",
        "title": "Person C says she was at home at 9:20 PM; her phone reports Sector 18",
        "statement": "“At 9:20 PM I was at home watching TV.” – Chitra Nair (Person C)",
        "statement_key": "stmt_chitra",
        "conflicting": ["gps_c_2120", "wa_c_2121", "upi_log_c", "tx_c_raju"],
        "supporting": ["tv_c_active", "rtr_c_disc"],
        "time_info": {"claimed": "2026-03-14T21:20:00", "gps_device_time": "2026-03-14T21:17:00",
                      "gps_corrected_time": "2026-03-14T21:20:00", "clock_offset_s": -180,
                      "note": "DEV-C1 clock runs 3 minutes behind the master clock; the ping is corrected from 21:17 to 21:20."},
        "explanation": ("After clock correction, a GPS fix from Chitra's phone places the DEVICE at Orion Business Park, "
                        "Sector 18 at exactly 21:20, a message from the phone says 'Pahunch gayi hu, lobby mein hu', and "
                        "a ₹4,85,000 UPI payment was authorised from the phone four minutes later. "
                        "This conflicts with her statement. It does not by itself prove she was physically there."),
        "caveats": ["Device location is not proof of the owner's physical presence; someone else could have carried or used the phone.",
                    "Authorship of the WhatsApp message is unverified (no biometric or typing evidence).",
                    "Smart-TV and router logs are consistent with someone being at home, but do not identify who.",
                    "No CCTV is available for 21:08–21:31 to confirm who entered the lobby."],
        "confidence": 0.74, "review_status": "needs_review",
    },
    {
        "id": "CON-2",
        "title": "Witness says Arjun left at 8:45 PM; his phone is at the office until at least 9:12 PM",
        "statement": "“I saw Arjun sir leave the building around 8:45 PM.” – Esha Verma (witness)",
        "statement_key": "stmt_esha",
        "conflicting": ["gps_a_2110", "gps_a_2112", "cdr_a_2111"],
        "supporting": ["cctv_2040"],
        "time_info": {"claimed": "2026-03-14T20:45:00", "gps_corrected_time": "2026-03-14T21:10:00",
                      "clock_offset_s": 0,
                      "note": "DEV-A1 clock matches the master clock; no correction applied."},
        "explanation": ("Arjun's phone reports GPS fixes at the Sector 18 office at 21:10 and 21:12, and a call placed at 21:11 "
                        "connects through the Sector 18 tower. Arjun's own statement says he stayed until about 9:15 PM, "
                        "agreeing with the phone and contradicting the witness. A lobby frame at 20:40 shows an unidentified "
                        "adult male heading out, which could be what the witness remembers."),
        "caveats": ["The witness may be misremembering the time or may have seen someone else leave.",
                    "Arjun's phone could have stayed in the office after he left.",
                    "The 20:40 CCTV frame does not identify the person."],
        "confidence": 0.66, "review_status": "needs_review",
    },
    {
        "id": "CON-3",
        "title": "Timestamp mismatch resolved: UPI app log vs bank record differ by exactly 3 minutes",
        "statement": "Chitra's phone logs the UPI payment at 21:21; the bank records it at 21:24.",
        "statement_key": "upi_log_c",
        "conflicting": ["tx_c_raju"],
        "supporting": [],
        "time_info": {"device_time": "2026-03-14T21:21:00", "bank_time": "2026-03-14T21:24:00", "clock_offset_s": -180,
                      "note": "Applying the DEV-C1 offset (+180 s) makes both records agree at 21:24."},
        "explanation": ("The mismatch disappears once DEV-C1's 3-minute clock lag is corrected, which also supports using the "
                        "same correction for the GPS and WhatsApp records from that phone."),
        "caveats": ["Agreement of one pair is supporting evidence for the offset, not a full clock audit."],
        "confidence": 0.92, "review_status": "resolved_by_correction",
    },
]

HYPOTHESES = [
    {
        "id": "H-1",
        "title": "Scenario 1 – Coordinated hand-off at Sector 18",
        "description": ("Arjun, Raju and Chitra coordinated a pre-planned transfer. Arjun told the team to meet at Sector 18; "
                        "Raju and Arjun were in the same tower region around 21:10–21:22; Chitra's phone reached the office "
                        "at 21:20 and paid ₹4,85,000 to Raju's UPI ID at 21:24; Raju replied from a second number."),
        "supporting": [("wa_group_2030", "Arjun tells the team to finalise 'tonight's transfer' and meet Raju at Sector 18."),
                       ("cdr_a_b1_2044", "Arjun calls Raju's primary number for 92 s shortly before."),
                       ("gps_a_2110", "Arjun's phone at the office at 21:10."),
                       ("cdr_b1_2114", "Raju's primary number on the Sector 18 tower at 21:14."),
                       ("gps_c_2120", "Chitra's phone at the office at 21:20 (corrected)."),
                       ("wa_c_2121", "Message from Chitra's phone: 'lobby mein hu. Amount ready hai.'"),
                       ("tx_c_raju", "₹4,85,000 paid to raju.m@demobank at 21:24."),
                       ("wa_b2_2126", "Reply from the second number acknowledges receipt."),
                       ("cctv_2108", "Two adults near the lift immediately before the CCTV gap.")],
        "contradicting": [("stmt_chitra", "Chitra denies leaving home."),
                          ("stmt_esha", "Witness says Arjun left at 8:45 PM."),
                          ("tv_c_active", "Smart TV at Chitra's home shows an uninterrupted session.")],
        "confidence": 0.58,
        "reasoning": ("Independent sources (GPS, tower, messages, bank) converge on the same 15-minute window and place. "
                      "The group message supports planning but never names Chitra. Presence of persons, as opposed to devices, "
                      "is inferred rather than observed because CCTV is missing 21:08–21:31."),
        "missing": ["CCTV for 21:08–21:31", "GPS or handset location for Raju's phones", "Confirmation that +91 90000 10003 is Raju's",
                    "Purpose of Chitra's payment"],
        "critic": [
            {"claim": "All three were physically at Sector 18 together.",
             "challenge": "Only Arjun's and Chitra's DEVICES are located by GPS; Raju is located only by a tower region, which covers a wide area. No CCTV covers the key window.",
             "keys": ["gps_a_2110", "gps_c_2120", "cdr_b1_2114", "cctv_2108", "cctv_2131"], "verdict": "weakened"},
            {"claim": "The payment was planned in advance.",
             "challenge": "The group message and the 20:44 call support a planned meeting, but nothing in the record ties Chitra's payment to that plan.",
             "keys": ["wa_group_2030", "cdr_a_b1_2044", "tx_c_raju"], "verdict": "partially supported"},
            {"claim": "Chitra wrote the 21:21 message.",
             "challenge": "Authorship is assumed from the account. Her statement and the home TV session point the other way.",
             "keys": ["wa_c_2121", "stmt_chitra", "tv_c_active"], "verdict": "unsupported without further evidence"},
        ],
    },
    {
        "id": "H-2",
        "title": "Scenario 2 – Chitra stayed home; her phone was used by someone else",
        "description": ("Chitra was at home as she says. Her phone left the home Wi-Fi at 20:52, was carried to Sector 18 by another person, "
                        "who sent the 'lobby' message and authorised the payment, possibly under pressure or by knowing her UPI credentials."),
        "supporting": [("stmt_chitra", "Chitra's own account."),
                       ("tv_c_active", "Home TV session ran uninterrupted 20:30–22:40."),
                       ("rtr_c_disc", "The phone left the home network at 20:52, which does not say who carried it.")],
        "contradicting": [("wa_c_2121", "First-person message from the phone ('pahunch gayi hu'); authorship unverified."),
                          ("upi_log_c", "Payment authorised in-app; authentication method unknown."),
                          ("tx_c_raju", "Payment completed to a recipient Chitra's colleagues were already coordinating with.")],
        "confidence": 0.24,
        "reasoning": ("Possible if the phone changed hands, but no evidence shows anyone else holding it. It does explain the conflict with her "
                      "statement. The TV session supports 'someone was home' but could be left running."),
        "missing": ["Bank authentication logs for the UPI payment (PIN / biometric / device binding)", "Who had physical access to the phone",
                    "Greenview Residency entrance or lift CCTV", "Smart-TV remote/interaction logs"],
        "critic": [
            {"claim": "Another person used Chitra's phone.",
             "challenge": "No record names or places a second person with the phone. The scenario is built only on the absence of proof that Chitra was there.",
             "keys": ["gps_c_2120", "stmt_chitra"], "verdict": "unsupported without further evidence"},
            {"claim": "The TV session proves someone was at home.",
             "challenge": "A streaming session can run unattended; no remote or voice interaction is logged after 20:31.",
             "keys": ["tv_c_active"], "verdict": "weakened"},
        ],
    },
    {
        "id": "H-3",
        "title": "Scenario 3 – Private Chitra–Raju arrangement; Arjun not involved at the time",
        "description": ("Raju and Chitra met at Sector 18 for an arrangement of their own. Arjun left around 20:45 as the witness says and his phone stayed at the office, "
                        "so his GPS fixes do not show where he was."),
        "supporting": [("stmt_esha", "Witness: Arjun left at about 8:45 PM."),
                       ("cctv_2040", "An unidentified adult male leaves the lobby at 20:40."),
                       ("wa_c_2121", "Chitra's device messages Raju directly, not the group."),
                       ("wa_b2_2126", "Raju replies one-to-one from the second number."),
                       ("tx_c_raju", "The payment goes from Chitra to Raju directly.")],
        "contradicting": [("wa_group_2030", "Arjun announced the transfer and meeting at 20:30."),
                          ("cdr_a_b1_2044", "Arjun phoned Raju at 20:44."),
                          ("gps_a_2112", "Arjun's phone is at the office at 21:12 and he states he stayed until about 9:15."),
                          ("tx_nexa_d", "Upstream, the Nexa account moved ₹6.2 lakh to Deepak at 20:40, which later fed Raju.")],
        "confidence": 0.18,
        "reasoning": ("Resolves the witness conflict but needs Arjun's phone to have been left behind and his own statement to be wrong. "
                      "It also leaves the upstream Nexa-to-Deepak transfer unexplained."),
        "missing": ["Sensor or unlock logs for Arjun's phone after 20:45", "Interview of Raju", "Purpose of the Chitra→Raju payment"],
        "critic": [
            {"claim": "Arjun was not involved that evening.",
             "challenge": "His 20:30 message and 20:44 call show involvement before and during the window; his phone and tower data place it at the scene.",
             "keys": ["wa_group_2030", "cdr_a_b1_2044", "gps_a_2112"], "verdict": "weakened"},
            {"claim": "The witness is correct about 8:45 PM.",
             "challenge": "The witness may have seen someone else; the 20:40 frame does not identify who left.",
             "keys": ["stmt_esha", "cctv_2040"], "verdict": "partially supported"},
        ],
    },
]

GAP_STEPS = {
    "cctv": ["Request DVR export and system logs for CAM-S18-LOBBY covering 21:00–21:45.",
             "Check whether other cameras (parking, lift, stairwell) cover the same interval.",
             "Ask building management whether the camera was serviced, powered off or overwritten."],
    "financial": ["Obtain the statement for the account that sent ₹4,50,000 to a/c ****9917 at 22:31.",
                  "Request KYC for the beneficiary account ****9917 and for UPI ID raju.m@demobank.",
                  "Get the bank's UPI authentication/device-binding logs for the 21:24 payment."],
    "phone": ["Request subscriber details (CAF) for +91 90000 10009 and +91 90000 10003 from the carrier.",
              "Request IMEI history for the handset in DEV-B2."],
    "location": ["Request handset location history for Person B's primary phone.",
                 "Seek additional GPS/Wi-Fi location history for Person A's phone between 21:12 and 22:35."],
    "identity": ["Review the proposed identity matches in Identity Resolution and accept or reject each.",
                 "Seek corroboration (KYC, subscriber data, interview) before treating any match as established."],
}
