"""Deterministic synthetic dataset for the demo case "Operation Silver Ledger".

EVERYTHING here is fictional: names, phone numbers (90000 1xxxx block), accounts,
banks ("DemoBank"), carriers ("DemoTel"), places and coordinates.

The generator hand-places the planted investigation clues (keys such as
``gps_c_2120``) and pads the vault with seeded filler records so the case
reaches ~250 records. Evidence IDs are assigned later (chronologically) by the
seeder; the ``key`` lets contradictions/hypotheses reference records safely.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from .config import DEMO_CASE_ID

CASE_DAY = datetime(2026, 3, 14)          # night of the incident (IST)
STATEMENT_DAY = datetime(2026, 3, 16, 11, 0)


def T(h: int, m: int = 0, s: int = 0, day: int = 14) -> datetime:
    return datetime(2026, 3, day, h, m, s)


# --------------------------------------------------------------------------- entities
def inr(n: int) -> str:
    """Indian digit grouping, e.g. 485000 -> 4,85,000."""
    s = str(int(n))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def phone(n: int) -> str:
    return f"+91 90000 {n:05d}"


PEOPLE = [
    ("P-A", "Arjun Mehra", "Director, Nexa Capital (fictional firm); active in the 'Nexa Team' chat"),
    ("P-B", "Rajesh Malhotra", "Associate of Nexa Capital; uses alias 'Raju'; multiple phone numbers"),
    ("P-C", "Chitra Nair", "Accounts manager, Nexa Capital; involved in key financial transactions"),
    ("P-D", "Deepak Sharma", "Holder of account that received pooled funds"),
    ("P-E", "Esha Verma", "Receptionist at the Sector 18 office; key witness"),
    ("P-F", "Farhan Qureshi", "Acquaintance of Person B; courier; partially identified"),
]

PHONES = {  # id: (number, owner person id or None)
    "PH-10001": (phone(10001), "P-A"),
    "PH-10002": (phone(10002), "P-B"),
    "PH-10003": (phone(10003), None),   # candidate second number of Person B (identity match pending)
    "PH-10004": (phone(10004), "P-C"),
    "PH-10005": (phone(10005), "P-D"),
    "PH-10006": (phone(10006), "P-E"),
    "PH-10007": (phone(10007), "P-F"),
    "PH-10009": (phone(10009), None),   # unknown number
}

DEVICES = {  # id: (label, type, owner, phone id, clock offset seconds vs master)
    "DEV-A1": ("Arjun's smartphone", "phone", "P-A", "PH-10001", 0),
    "DEV-B1": ("Rajesh's smartphone (primary)", "phone", "P-B", "PH-10002", 0),
    "DEV-B2": ("Handset with second SIM (+91 90000 10003)", "phone", None, "PH-10003", 0),
    "DEV-C1": ("Chitra's smartphone", "phone", "P-C", "PH-10004", -180),   # CLOCK 3 MIN BEHIND
    "DEV-D1": ("Deepak's smartphone", "phone", "P-D", "PH-10005", 0),
    "DEV-E1": ("Esha's smartphone", "phone", "P-E", "PH-10006", 0),
    "DEV-F1": ("Farhan's smartphone", "phone", "P-F", "PH-10007", 0),
    "DEV-RTR-C": ("Home Wi-Fi router, Greenview Residency", "router", "P-C", None, 0),
    "DEV-TV-C": ("Smart TV, Greenview Residency", "smart_tv", "P-C", None, 0),
    "CAM-S18-LOBBY": ("Lobby CCTV camera, Orion Business Park", "cctv", None, None, 0),
}

LOCATIONS = {
    "LOC-S18": ("Orion Business Park, Sector 18 (fictional)", 28.5702, 77.3215, "TWR-S18"),
    "LOC-GV": ("Greenview Residency (fictional)", 28.5458, 77.3395, "TWR-GV"),
    "LOC-HW": ("Mile-42 Toll Plaza (fictional)", 28.5001, 77.4102, "TWR-HW"),
    "LOC-LC": ("Lakeview Colony (fictional)", 28.6102, 77.2301, "TWR-LC"),
    "LOC-PC": ("Palm Court Apartments (fictional)", 28.5603, 77.3004, "TWR-PC"),
}
TOWER_TO_LOC = {v[3]: k for k, v in LOCATIONS.items()}

ACCOUNTS = {
    "ACC-NEXA": ("Nexa Capital Pvt Ltd, a/c ****4410 (fictional)", "P-A"),
    "ACC-C": ("Chitra Nair, a/c ****2207 (fictional)", "P-C"),
    "ACC-D": ("Deepak Sharma, a/c ****7731 (fictional)", "P-D"),
    "ACC-INV": ("Investor payer pool (40 synthetic payers)", None),
    "ACC-X9917": ("Unidentified account ****9917 (fictional)", None),
}
UPI = {"UPI-RAJU": ("raju.m@demobank", "RAJU M")}

TEAM_CHAT = "Nexa Team (group)"
NAME_OF_PHONE = {pid: next((n for p, n, _ in PEOPLE if p == own), "Unknown") if own else "Unknown"
                 for pid, (_, own) in PHONES.items()}
NAME_OF_PHONE["PH-10003"] = "(unregistered)"
NAME_OF_PHONE["PH-10009"] = "(unknown)"
PHONE_OF_DEVICE = {d: v[3] for d, v in DEVICES.items()}

CDR_SYSTEM = "SYS-DEMOTEL"
BANK_SYSTEM = "SYS-DEMOBANK"


# --------------------------------------------------------------------------- record builders
class Builder:
    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.rng = random.Random(20260314)

    def add(self, key, category, title, content, source, ts, persons=(), frame=None, event_ts=None):
        offset = DEVICES[source][4] if source in DEVICES else 0
        self.rows.append({
            "key": key, "category": category, "title": title, "content": content,
            "source_device": source, "corrected_ts": ts,
            "original_ts": ts + timedelta(seconds=offset), "offset": offset,
            "persons": list(persons), "frame": frame,
        })

    # -- helpers
    def cdr(self, key, ts, caller, callee, dur, tower, persons=()):
        c = {"caller": PHONES[caller][0], "callee": PHONES[callee][0], "caller_id": caller,
             "callee_id": callee, "duration_s": dur, "tower": tower, "type": "voice"}
        self.add(key, "cdr", f"Call {PHONES[caller][0]} → {PHONES[callee][0]} ({dur}s)",
                 c, CDR_SYSTEM, ts, persons)

    def wa(self, key, ts, sender_dev, sender_pid, recipient, chat, text, persons=()):
        c = {"chat": chat, "sender": PHONES[sender_pid][0], "sender_id": sender_pid,
             "recipient": recipient, "text": text, "language": "Hinglish"}
        self.add(key, "whatsapp", f"WhatsApp: {text[:48]}{'…' if len(text) > 48 else ''}",
                 c, sender_dev, ts, persons)

    def gps(self, key, ts, dev, loc, jitter=0.0003, acc=12, persons=()):
        name, lat, lon, tower = LOCATIONS[loc]
        r = self.rng
        c = {"device": dev, "lat": round(lat + r.uniform(-jitter, jitter), 6),
             "lon": round(lon + r.uniform(-jitter, jitter), 6), "accuracy_m": acc,
             "place": name, "location_id": loc}
        self.add(key, "gps", f"GPS fix {dev} near {name.split(' (')[0]}", c, dev, ts, persons)

    def txn(self, key, ts, n, frm, to, amt, channel, remark, persons=()):
        c = {"txn_id": f"TXN-{n:06d}", "amount_inr": amt, "from_account": frm, "to_account": to,
             "channel": channel, "remark": remark}
        self.add(key, "transaction", f"{channel} ₹{inr(amt)} {frm} → {to}", c, BANK_SYSTEM, ts, persons)

    def log(self, key, ts, dev, log_type, msg, persons=()):
        self.add(key, "device_log", f"{dev}: {log_type}",
                 {"device": dev, "log_type": log_type, "message": msg}, dev, ts, persons)

    def stmt(self, key, who, kind, text, claimed_time, claimed_loc, persons, ts=STATEMENT_DAY):
        c = {"witness": who, "statement_type": kind, "taken_by": "Insp. R. Iyer (fictional)", "text": text,
             "claimed_time": claimed_time.isoformat(), "claimed_location": claimed_loc, "language": "English"}
        self.add(key, "statement", f"{kind.title()} statement – {who}", c, "SYS-CASEFILE", ts, persons)

    def cctv(self, key, ts, desc, n_people, frame_name):
        c = {"camera": "CAM-S18-LOBBY", "description": desc, "persons_visible": n_people,
             "identified": False, "resolution": "640x360", "frame_label": frame_name}
        self.add(key, "cctv", f"CCTV lobby frame {ts:%H:%M}", c, "CAM-S18-LOBBY", ts, (), frame=desc)


HINGLISH_GROUP = [
    ("P-A", "Bhai kal ka collection kitna hua?"),
    ("P-C", "Abhi tak 3.2 lakh aaya hai, shaam tak update dungi."),
    ("P-A", "Investors ko bol do payout Monday ko hoga."),
    ("P-B", "Naya client aaya hai, main call karta hu."),
    ("P-C", "Statement bhej diya hai, ek baar check kar lena."),
    ("P-A", "Office mein kaun hai abhi?"),
    ("P-B", "Main nikal raha hu, kal milte hain."),
    ("P-F", "Parcel pahunch gaya, sab theek hai."),
    ("P-C", "Ye wala payment pending dikha raha hai, dekhna zara."),
    ("P-A", "Sab log apna kaam time pe khatam karo, review kal hai."),
]
HINGLISH_1TO1 = [
    "Kya haal hai? Free ho toh call karna.", "Haan bhai, bas abhi nikla hu.", "Kal subah milte hain office mein.",
    "Ye number save kar lo.", "Theek hai, dekhta hu.", "Paisa aaya kya?", "Abhi nahi, kal tak aa jayega.",
    "Chinta mat karo, sab ho jayega.", "Call kar, zaroori baat hai.", "Okay boss, samajh gaya.",
]


def build() -> list[dict]:
    b = Builder()
    r = b.rng

    # ---------------------------------------------------------- planted clues (hand-placed)
    b.wa("wa_group_2030", T(20, 30), "DEV-A1", "PH-10001", TEAM_CHAT, TEAM_CHAT,
         "Aaj raat ka transfer finalize karo. Raju ko bol diya hai, Sector 18 pe milna hai.", ("P-A",))
    b.txn("tx_nexa_d", T(20, 40), 482011, "ACC-NEXA", "ACC-D", 620000, "NEFT",
          "Pooled receipts transfer", ("P-A", "P-D"))
    b.cdr("cdr_a_b1_2044", T(20, 44), "PH-10001", "PH-10002", 92, "TWR-PC", ("P-A", "P-B"))
    b.log("rtr_c_disc", T(20, 52), "DEV-RTR-C", "wifi_disconnect",
          "Client 'Chitra smartphone' (DEV-C1) disconnected from home Wi-Fi.", ("P-C",))
    b.log("tv_c_active", T(20, 30), "DEV-TV-C", "streaming_session",
          "Streaming session active continuously 20:30–22:40 (no remote activity recorded after 20:31).", ("P-C",))
    b.log("sim_b2_act", T(20, 58), "DEV-B2", "sim_activation",
          "SIM +91 90000 10003 first network registration on this handset.", ("P-B",))
    b.log("upi_reg_b1", T(18, 5, day=11), "DEV-B1", "upi_registration",
          "UPI ID raju.m@demobank registered against mobile +91 90000 10002.", ("P-B",))
    b.wa("wa_b2_intro", T(21, 2), "DEV-B2", "PH-10003", PHONES["PH-10007"][0], "1:1",
         "Bhai ye mera naya number hai, save kar lo. – Raju", ("P-B", "P-F"))
    b.cctv("cctv_2040", T(20, 40), "Lobby: one adult male walking toward exit, face not clear; reception desk occupied.", 2, "F-2040")
    b.cctv("cctv_2108", T(21, 8), "Lobby: two adults standing near lift; faces not clear. LAST FRAME BEFORE GAP.", 2, "F-2108")
    b.cctv("cctv_2131", T(21, 31), "Lobby: empty. FIRST FRAME AFTER GAP.", 0, "F-2131")
    b.gps("gps_a_2110", T(21, 10), "DEV-A1", "LOC-S18", persons=("P-A",))
    b.gps("gps_a_2112", T(21, 12), "DEV-A1", "LOC-S18", persons=("P-A",))
    b.cdr("cdr_a_2111", T(21, 11), "PH-10001", "PH-10007", 58, "TWR-S18", ("P-A", "P-F"))
    b.cdr("cdr_b1_2114", T(21, 14), "PH-10002", "PH-10007", 41, "TWR-S18", ("P-B", "P-F"))
    b.cdr("cdr_b1_2122", T(21, 22), "PH-10002", "PH-10004", 33, "TWR-S18", ("P-B", "P-C"))
    b.gps("gps_c_2120", T(21, 20), "DEV-C1", "LOC-S18", persons=("P-C",))        # device time 21:17
    b.wa("wa_c_2121", T(21, 21), "DEV-C1", "PH-10004", PHONES["PH-10002"][0], "1:1",
         "Pahunch gayi hu, lobby mein hu. Amount ready hai.", ("P-C", "P-B"))     # device time 21:18
    b.log("upi_log_c", T(21, 24), "DEV-C1", "upi_app_event",
          "UPI payment authorised in app: ₹4,85,000 to raju.m@demobank (device-local time).", ("P-C", "P-B"))  # device 21:21
    b.txn("tx_c_raju", T(21, 24), 482377, "ACC-C", "UPI-RAJU", 485000, "UPI",
          "Payment to raju.m@demobank", ("P-C", "P-B"))
    b.wa("wa_b2_2126", T(21, 26), "DEV-B2", "PH-10003", PHONES["PH-10004"][0], "1:1",
         "Mil gaya. Shukriya. Aage ka kaam kal dekhenge.", ("P-B", "P-C"))
    b.cdr("cdr_b2_9_2247", T(22, 47), "PH-10003", "PH-10009", 74, "TWR-HW", ("P-B",))
    b.txn("tx_d_raju", T(22, 5), 482590, "ACC-D", "UPI-RAJU", 135000, "UPI",
          "Payment to raju.m@demobank", ("P-D", "P-B"))
    b.log("b2_debit", T(22, 31), "DEV-B2", "bank_notification",
          "Debit alert: ₹4,50,000 transferred to a/c ****9917. (Bank statement for the source account not obtained.)", ("P-B",))
    b.gps("gps_a_2235", T(22, 35), "DEV-A1", "LOC-PC", persons=("P-A",))
    b.gps("gps_d_2100", T(21, 0), "DEV-D1", "LOC-HW", persons=("P-D",))
    b.gps("gps_d_2200", T(22, 0), "DEV-D1", "LOC-HW", persons=("P-D",))

    # statements (event time carried in content.claimed_time)
    b.stmt("stmt_chitra", "Chitra Nair", "suspect",
           "I reached home around 7:30 PM and did not go out again that night. At 9:20 PM I was at home watching TV. "
           "I did not meet anyone and I do not know why my phone would show another location.",
           T(21, 20), "Greenview Residency (home)", ("P-C",))
    b.stmt("stmt_arjun", "Arjun Mehra", "suspect",
           "I stayed at the Sector 18 office until about 9:15 PM and then went home. I did not meet Rajesh that evening.",
           T(21, 15), "Orion Business Park, Sector 18 office", ("P-A", "P-B"))
    b.stmt("stmt_esha", "Esha Verma", "witness",
           "I saw Arjun sir leave the building around 8:45 PM. I locked the reception at 9:00 PM and left. "
           "I did not see Chitra madam or Rajesh sir that evening.",
           T(20, 45), "Orion Business Park lobby / reception", ("P-E", "P-A"))
    b.stmt("stmt_deepak", "Deepak Sharma", "suspect",
           "The ₹6.2 lakh was a repayment of a personal loan. I was near the toll plaza around 9 PM and 10 PM.",
           T(21, 0), "Mile-42 Toll Plaza", ("P-D",))

    # ---------------------------------------------------------- filler: CCTV frames (gap 21:08-21:31)
    cctv_times = [(20, 0), (20, 10), (20, 20), (20, 30), (20, 50), (21, 0),
                  (21, 40), (21, 50), (22, 0), (22, 10), (22, 20), (22, 30)]
    descs = ["Lobby: reception occupied, no visitors.", "Lobby: security guard on rounds.",
             "Lobby: one visitor at lift (face not clear).", "Lobby: quiet, lights dimmed."]
    for h, m in cctv_times:
        b.cctv(f"cctv_{h}{m:02d}", T(h, m), r.choice(descs), r.randint(0, 2), f"F-{h}{m:02d}")

    # ---------------------------------------------------------- filler: victim payments (40)
    for i in range(40):
        day = r.randint(10, 14)
        hh = r.randint(9, 17)
        mm = r.randint(0, 59)
        amt = r.choice([5000, 7500, 10000, 12000, 15000, 20000, 25000, 30000, 50000])
        b.txn(f"vic_{i:02d}", T(hh, mm, day=day), 470000 + i * 7, f"INV-PAYER-{i + 1:03d}", "ACC-NEXA",
              amt, "UPI", "Investment scheme deposit", ("P-A",))

    # ---------------------------------------------------------- filler: minor transfers (5)
    for i, (frm, to, amt) in enumerate([("ACC-C", "ACC-NEXA", 82000), ("ACC-NEXA", "ACC-C", 45000),
                                        ("ACC-NEXA", "ACC-C", 60000), ("ACC-C", "ACC-NEXA", 30000),
                                        ("ACC-NEXA", "ACC-D", 150000)]):
        b.txn(f"int_{i}", T(r.randint(10, 16), r.randint(0, 59), day=r.randint(11, 13)), 476000 + i, frm, to,
              amt, "NEFT", "Internal settlement",
              tuple(x for x in (ACCOUNTS[frm][1], ACCOUNTS[to][1]) if x))

    # ---------------------------------------------------------- filler: CDR (~48) over 10-14 Mar outside the key window
    pairs = [("PH-10001", "PH-10002"), ("PH-10001", "PH-10004"), ("PH-10002", "PH-10004"),
             ("PH-10002", "PH-10007"), ("PH-10001", "PH-10007"), ("PH-10004", "PH-10005"),
             ("PH-10002", "PH-10005"), ("PH-10001", "PH-10006")]
    towers_for = {"PH-10001": ["TWR-S18", "TWR-PC"], "PH-10002": ["TWR-S18", "TWR-HW"],
                  "PH-10004": ["TWR-GV", "TWR-S18"], "PH-10005": ["TWR-LC", "TWR-HW"],
                  "PH-10007": ["TWR-HW", "TWR-LC"], "PH-10006": ["TWR-S18"]}
    for i in range(48):
        a, c = r.choice(pairs)
        day = r.randint(10, 14)
        hh = r.choice([9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 23]) if day == 14 else r.randint(8, 22)
        b.cdr(f"cdrf_{i:02d}", T(hh, r.randint(0, 59), r.randint(0, 59), day=day), a, c, r.randint(12, 420),
              r.choice(towers_for[a]),
              tuple(x for x in (PHONES[a][1], PHONES[c][1]) if x))
    # phone 2 (+ unknown) contacts overlapping phone 1's contacts, only after 20:58 on 14 Mar
    b.cdr("cdr_b2_f", T(21, 3), "PH-10003", "PH-10007", 66, "TWR-S18", ("P-B", "P-F"))
    b.cdr("cdr_b2_d", T(22, 12), "PH-10003", "PH-10005", 51, "TWR-HW", ("P-B", "P-D"))
    b.cdr("cdr_b2_a", T(22, 25), "PH-10003", "PH-10001", 88, "TWR-HW", ("P-B", "P-A"))
    b.cdr("cdr_b2_c", T(21, 27), "PH-10003", "PH-10004", 29, "TWR-S18", ("P-B", "P-C"))
    for i, (hh, mm) in enumerate([(23, 5), (23, 20), (23, 41)]):
        b.cdr(f"cdr_u_{i}", T(hh, mm), "PH-10009", "PH-10007", r.randint(30, 140), "TWR-HW", ("P-F",))
    b.cdr("cdr_u_b2", T(22, 55), "PH-10009", "PH-10003", 40, "TWR-HW", ("P-B",))

    # ---------------------------------------------------------- filler: WhatsApp (~50)
    for i in range(24):
        pid, text = r.choice(HINGLISH_GROUP)
        dev = {"P-A": "DEV-A1", "P-B": "DEV-B1", "P-C": "DEV-C1", "P-F": "DEV-F1"}[pid]
        ph = {"P-A": "PH-10001", "P-B": "PH-10002", "P-C": "PH-10004", "P-F": "PH-10007"}[pid]
        day = r.randint(10, 14)
        hh = r.randint(9, 18) if day == 14 else r.randint(9, 22)
        b.wa(f"waf_g{i:02d}", T(hh, r.randint(0, 59), day=day), dev, ph, TEAM_CHAT, TEAM_CHAT, text, (pid,))
    one_to_one = [("P-A", "DEV-A1", "PH-10001", "PH-10002"), ("P-B", "DEV-B1", "PH-10002", "PH-10001"),
                  ("P-C", "DEV-C1", "PH-10004", "PH-10001"), ("P-B", "DEV-B1", "PH-10002", "PH-10007"),
                  ("P-F", "DEV-F1", "PH-10007", "PH-10002"), ("P-A", "DEV-A1", "PH-10001", "PH-10004")]
    for i in range(26):
        pid, dev, ph, to = r.choice(one_to_one)
        day = r.randint(10, 14)
        hh = r.randint(9, 18) if day == 14 else r.randint(9, 22)
        b.wa(f"waf_p{i:02d}", T(hh, r.randint(0, 59), day=day), dev, ph, PHONES[to][0], "1:1",
             r.choice(HINGLISH_1TO1), (pid,))
    # a few messages addressing "Raju" so alias usage can be computed from the data
    for i, (hh, mm, pid, dev, ph, to, txt) in enumerate([
            (11, 15, "P-A", "DEV-A1", "PH-10001", "PH-10002", "Raju, client ka paisa aaya kya?"),
            (15, 40, "P-C", "DEV-C1", "PH-10004", "PH-10002", "Raju bhai, receipt bhej do please."),
            (10, 5, "P-F", "DEV-F1", "PH-10007", "PH-10002", "Raju, kal ka parcel ready hai."),
            (17, 30, "P-A", "DEV-A1", "PH-10001", "PH-10002", "Raju, kal Sector 18 aana zaroori hai.")]):
        day = 13 if i % 2 == 0 else 12
        b.wa(f"waf_r{i}", T(hh, mm, day=day), dev, ph, PHONES[to][0], "1:1", txt, (pid, "P-B"))
    b.wa("wa_raju_d", T(21, 28), "DEV-A1", "PH-10001", PHONES["PH-10003"][0], "1:1",
         "Raju, ye naya number hai na? Save kar liya.", ("P-A", "P-B"))

    # ---------------------------------------------------------- filler: GPS (~28) other days / times
    gps_plan = {"DEV-A1": ["LOC-S18", "LOC-PC"], "DEV-C1": ["LOC-GV", "LOC-S18"], "DEV-D1": ["LOC-LC", "LOC-HW"],
                "DEV-F1": ["LOC-HW", "LOC-LC"], "DEV-E1": ["LOC-S18"]}
    owner_of = {d: v[2] for d, v in DEVICES.items()}
    for i in range(28):
        dev = r.choice(list(gps_plan))
        day = r.randint(10, 14)
        hh = r.choice([8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]) if day == 14 else r.randint(8, 22)
        b.gps(f"gpsf_{i:02d}", T(hh, r.randint(0, 59), day=day), dev, r.choice(gps_plan[dev]),
              persons=(owner_of[dev],))

    # ---------------------------------------------------------- filler: device logs (~12)
    misc_logs = [("DEV-A1", "battery", "Battery 62%, charging started.", "P-A"),
                 ("DEV-B1", "app_update", "WhatsApp updated to latest build.", "P-B"),
                 ("DEV-C1", "timezone_setting", "Automatic date & time disabled; manual clock in use.", "P-C"),
                 ("DEV-C1", "battery", "Battery 48%, unplugged.", "P-C"),
                 ("DEV-D1", "wifi_connect", "Connected to Wi-Fi 'LakeviewNet'.", "P-D"),
                 ("DEV-F1", "app_install", "Application installed: file manager.", "P-F"),
                 ("DEV-RTR-C", "wifi_connect", "Client 'Chitra smartphone' connected.", "P-C"),
                 ("DEV-TV-C", "power", "TV powered on.", "P-C"),
                 ("DEV-E1", "battery", "Battery 80%.", "P-E"),
                 ("DEV-A1", "wifi_connect", "Connected to office Wi-Fi 'OrionBP-Staff'.", "P-A"),
                 ("DEV-B1", "battery", "Battery 33%.", "P-B"),
                 ("DEV-A1", "app_update", "Calendar sync completed.", "P-A")]
    for i, (dev, typ, msg, p) in enumerate(misc_logs):
        day = r.randint(11, 14)
        hh = r.randint(8, 19)
        b.log(f"logf_{i:02d}", T(hh, r.randint(0, 59), day=day), dev, typ, msg, (p,))
    return b.rows


def case_row() -> dict:
    return {
        "id": DEMO_CASE_ID,
        "title": "Operation Silver Ledger – Synthetic Investment-Fraud Case",
        "summary": ("Fictional investigation into a pooled-funds fraud run through 'Nexa Capital'. Focus: the "
                    "evening of 14 March 2026, when funds moved between accounts while several devices were "
                    "in the Sector 18 tower region. ALL DATA IS SYNTHETIC."),
        "status": "Open – analysis in progress",
        "opened_at": datetime(2026, 3, 15, 9, 30),
        "jurisdiction": "Fictional Cyber Crime Cell",
        "lead_investigator": "Insp. R. Iyer (fictional)",
    }
