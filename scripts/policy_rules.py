"""Keyword screen for Meta and Malaysian advertising rules (see skills/dtc-reels-editor/references/meta-policy.md).

Every finding is REVIEW (a person decides), never BLOCK: these notes are not legal advice, and some rules are still to be verified.
Brand guideline BLOCK terms stay in brands/<slug>/brand.json. Each rule: (id, applies_to, regex, why).
applies_to: "all", "service" (brand type == service, e.g. a clinic) or "product".
"""
import re

RULES = [
    ("personal-attribute", "all",
     r"\b(anda|awak|kamu|you|your)\b.{0,30}\b(ada masalah|mengalami|menghidap|alami|lemah|suffer\w*|struggl\w*|have (ed|erectile|low)|disfungsi)\b"
     r"|\b(adakah|are) (anda|awak|you)\b.{0,30}\b(masalah|lemah|suffer\w*)\b",
     "Meta personal attributes: copy must not state or imply the viewer has a medical condition. Describe the offer, or 'people who want X'."),
    ("sexual-function", "all",
     r"\b(tahan lama|stamina|tenaga batin|prestasi (seks|seksual|batin)|sexual performance|performance|enhance\w*|enlarge\w*|besar(kan)?|panjang(kan)?|memanjangkan|kepuasan|pleasure|ereksi|erection|kekerasan)\b",
     "Sexual function or performance wording. Malaysia Act 290 s.3(1)(c) bars promoting an article as a remedy for improving sexual function or performance; Meta bars pleasure/enhancement focus. A brand owner decision on file may allow it (see brand.json), but a person must confirm."),
    ("impotence-treatment", "all",
     r"\b(impoten\w*|mati pucuk|lemah (syahwat|tenaga batin)|disfungsi erekt\w*|erectile dysfunction|ejakulasi pramatang|premature ejaculation|frigid\w*)\b",
     "Condition named in the Act 290 Schedule (impotency, frigidity) or a treatment claim. Meta allows ED/PE health products with 18+ targeting only; Malaysia restricts advertising for them. Human and adviser decide."),
    ("explicit-anatomy", "all",
     r"\b(zakar|penis|kemaluan|batang|alat sulit|genital\w*)\b",
     "Explicit anatomy word. Fruit metaphors only; Meta adult content review risk. A person decides if the doctor's real words can be used."),
    ("cure-guarantee", "all",
     r"\b(sembuh\w*|pulih sepenuhnya|cure\w*|heal\w*|dijamin|jaminan|guarantee\w*|pasti (berjaya|berkesan)|kekal selamanya|dalam (masa )?\d+ (hari|minggu|days|weeks))\b|100 ?%",
     "Meta unrealistic outcomes: no cure/heal claims for incurable conditions, no guarantees, and specific results or timeframes need an approved disclaimer."),
    ("before-after", "all",
     r"\b(sebelum( dan)? selepas|before( and|/|&)? ?after)\b",
     "Before/after: restricted by Meta; treat as not allowed for men's or sexual health."),
    ("superlative", "service",
     r"\b(terbaik|paling \w+|nombor (satu|1)|no\.? ?1|number one|the best|best|state[- ]of[- ]the[- ]art|termurah|terhebat)\b",
     "MAB services guideline 5.2: no superlatives such as 'the best' or 'state-of-the-art' for services or facilities."),
    ("inducement", "service",
     r"\b(diskaun|discount|promosi|promo|percuma|free|tawaran|offer|jimat|last slots?|slot terakhir|terhad|limited)\b|\d ?% ?(off|diskaun)",
     "MAB services guideline 7.0: no financial inducements, sales promotions or fee discounts for clinic services. Brand guideline also bars countdowns and 'last slots'."),
    ("testimonial", "service",
     r"\b(testimoni\w*|testimonial\w*|ulasan (pelanggan|pesakit)|review (pelanggan|pesakit)|pesakit (kata|cakap|berkata)|patient (said|says))\b",
     "MAB services guideline 5.3: patient testimonials may not be published for clinic services. Needs written clearance."),
    ("testimonial", "product",
     r"\b(testimoni\w*|testimonial\w*|ulasan (pelanggan|pembeli)|pelanggan (kata|cakap|berkata)|customer (said|says))\b",
     "Testimonial: real text only, names blurred, no health result claims inside it. A person confirms the source."),
    ("promo-credentials", "service",
     r"\b(pakar|specialist|berpengalaman|experienced|\d+ tahun pengalaman|years of experience|doktor terbaik)\b",
     "MAB services guideline 4.2 / MMC: naming the doctor's qualification is allowed, promoting individual skill or experience is not."),
]


def scan(text, brand_type="product"):
    """Return list of (rule_id, why, matched_text) for one line."""
    out = []
    for rid, scope, rx, why in RULES:
        if scope != "all" and scope != brand_type:
            continue
        m = re.search(rx, text, re.IGNORECASE)
        if m:
            out.append((rid, why, m.group(0)))
    return out
