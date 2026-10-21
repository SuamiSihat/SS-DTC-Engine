# Meta and Malaysia ad policy notes

Researched 2026-10-21 by Claude. NOT legal advice and NOT approved yet. A person reviews and approves this file, and compliance decisions go to the human (see CLAUDE.md). Re-check before each batch: policies change and some sources below are dated.

## How reliable is this
- Meta's own Transparency Center pages for Health and wellness and Adult products could not be read by the research tool (the pages load their text with JavaScript). The Meta rules below come from dated third-party summaries that cite those pages, so verify each one on the live Meta pages before relying on it. Only Meta's "Unrealistic outcomes" page was read directly.
- The Malaysian items come from the text of the Medicines (Advertisement and Sale) Act 1956 (Act 290, read directly from the Ministry of Health site) and from MAB guidelines whose version needs confirming with the Medicine Advertisements Board.

## 1. Malaysian law and regulators (highest risk for our ads)
Our brands are men's health (SS Clinic: doctor-led clinic services; Dr MIT Ring and others: products). Malaysian rules can be stricter than Meta's, and Meta also requires ads to follow local law.

**Medicines (Advertisement and Sale) Act 1956 (Act 290)**, source: pharmacy.moh.gov.my, Act 290 text (revised 1983, amendments to 1990, check for later changes):
- s.3(1)(c): no advertisement promoting an article as a medicine, appliance or remedy for "improving the sexual function or sexual performance of human beings".
- Schedule items 17, 18, 20: frigidity; "impairment of sexual function or impotency"; "nervous debility, or other complaint or infirmity, arising from or relating to sexual intercourse".
- s.4A: no advertisement referring to a skill or service relating to the treatment, prevention or diagnosis of an ailment that invites people to seek the advertiser's advice.
- s.4B: advertisements for other medicines need Medicine Advertisements Board (MAB) approval.
- s.5 penalties: first conviction up to RM 3,000 or 1 year; later up to RM 5,000 or 2 years, or both.

**MAB guidelines for advertising healthcare services** (document reviewed at MAB meeting 27 July 2010, file titled "Amendment MAB 6/2011", so confirm the current version with MAB):
- Patient testimonials may not be published (5.3).
- No comparisons between facilities (5.1) and no superlatives such as "the best" or "state-of-the-art" (5.2).
- No celebrities, athletes, models, patients receiving treatment or professionals promoting services (5.4).
- Content must be accurate, substantiable and not exaggerated, false, misleading or deceptive (2.2).
- No financial inducements, sales promotions or fee discounts (7.0).
- Practitioner name, qualifications and specialty may be listed; promoting individual skill or experience may not (4.2).
- Not addressed in the document: before/after photos, and sexual function claims.

**Malaysian Medical Council / MMA ethics**: doctors may not advertise to obtain patients or promote themselves (MMC Guideline on Dissemination of Information by the Medical Profession 001/2006; MPS factsheet dated 22 Jan 2015). The MMC guideline is under review, so confirm the current version.

**What this means for our work (flag to the human before any batch for Malaysia):**
- Quote popups and WhatsApp proof screenshots are patient testimonials. For clinic services (SS Clinic) the MAB guideline bans them. Do not use them on clinic ads unless the human or the clinic's compliance advisor clears it in writing.
- Offer cards with discounts or promotions may count as inducements for clinic services. Prices read from `prices.json` still need the human to confirm the wording.
- Any claim that a product or service improves sexual function or performance, or treats impotence, is a legal risk under Act 290, whatever Meta allows. Hooks like "besarkan zakar?" and "morning wood = tak serius?" need human sign-off.
- Doctor-on-camera ads can read as promotion of the practitioner. Confirm with the clinic's compliance advisor.
- Whether MAB approval is needed, and for which brands (product vs service), is a decision for the brand owner. Claude does not decide it.

## 2. Meta rules (verify on the live pages)
Pages to check: transparency.meta.com/policies/ad-standards (Restricted goods and services: Health and wellness; Content-specific restrictions: Adult products or services; Deceptive content: Unrealistic outcomes; Objectionable content: Personal attributes).

**Unrealistic outcomes** (read directly from Meta, no page date shown): health ads may not claim to cure, heal or eliminate incurable diseases or terminal illnesses; specific results need qualifying or disclaimer language; sensational click-bait wording is not allowed; example of a banned claim: "Lose 5% of your body weight in a month!".

**Personal attributes** (stackmatix.com summary, page dated 2026-09-08): copy, images and video text must not state or imply that the viewer has a medical condition. Second-person "you have / are you suffering from ..." copy is the trigger. Write about the offer or about "people who want X" instead.

**Sexual health** (femtechinsider.com, dated 2022-10-18, and aimerce.ai summary dated 2026-08-24):
- Allowed: sexual health, wellness and reproductive products and services, for example erectile dysfunction products and premature ejaculation treatments, contraception, sex education.
- Not allowed: content or products that focus on sexual pleasure, arousal or sexual enhancement.
- Ads in this category must be targeted at 18+.
- Claude's note: "besarkan" (enlargement) and performance framing read as enhancement, which is a review risk.

**Health and wellness general** (adm summary dated 2026-08-27; aimerce summary dated 2026-08-24):
- No negative statements about physical appearance, and no close-ups that pinch or highlight body parts.
- Before/after images are restricted for weight loss, and allowed only for certain cosmetic procedures, for adults. For sexual or men's health, treat before/after as not allowed.
- Dietary, health, weight-loss and weight-gain products must be targeted 18+.
- Online pharmacies and telehealth need LegitScript certification.
- Accounts tied to health conditions can have restricted conversion events for optimization, and sensitive custom audiences or lookalikes can be disabled. A media buyer should check this.

**Adult nudity and sexual content**: no nudity or suggestive imagery. Our rules already say fruit metaphors only and no anatomy imagery.

## 3. Rules applied in the pipeline (from the above and earlier decisions)
- Fruit metaphors only; no anatomy imagery, no pills, no distressed people.
- No second-person condition statements in headlines, captions or hooks ("Anda ada masalah ...", "Are you suffering ...").
- No guarantees, cure claims, sensational wording, or specific results without a disclaimer the human approves.
- No before/after imagery.
- No sexual pleasure, arousal or enhancement framing.
- Testimonials and review popups: real text only, names blurred, and not on clinic-service ads until the human clears them (section 1).
- Customer names in WhatsApp proof screenshots must be blurred.
- Disclaimers keep the bottom 768 px clear on Reels (see `safe-zones.md`).
- Ads for sexual health products target 18+ (media buyer sets this).

## 4. Human review gate (before packaging)
The human confirms, per batch: each hook and headline wording; any testimonial, proof screenshot or quote popup; prices and offer wording; any sexual-function or performance wording; whether MAB approval or clinic compliance sign-off is needed; and 18+ targeting.

## 5. Open items
- Read Meta's live pages for Health and wellness, Adult products or services and Personal attributes in a browser and replace the third-party summaries with Meta's exact wording and dates.
- Get the current MAB guidelines (services and products) and MMC guideline from MAB / MMC and confirm the dates.
- Ask a Malaysian healthcare advertising adviser whether doctor-led men's health ads, testimonials and offers are allowed for each brand.
- TikTok ad policy for health and sexual health has not been researched yet.
- Consider adding these checks to `scripts/check_brand.py`: second-person condition phrases, enlargement and performance words, "terbaik" and other superlatives on service ads, guarantee words.

## Sources
- Meta, Unrealistic outcomes: https://transparency.meta.com/policies/ad-standards/deceptive-content/unrealistic-outcomes
- Meta, Health and wellness (page text not readable by the research tool): https://transparency.meta.com/policies/ad-standards/restricted-goods-services/health-wellness
- Meta, Adult products or services (not readable by the tool): https://transparency.meta.com/policies/ad-standards/content-specific-restrictions/adult-products-or-services
- Aimerce, summary of Meta Health & Wellness policy (2026-08-24): https://www.aimerce.ai/blogs/what-metas-health-wellness-ad-policy-actually-allows
- Accelerated Digital Media, health ad restrictions guide (2026-08-27): https://www.accelerateddigitalmedia.com/insights/guide-to-social-media-health-ad-restrictions-2025/
- Stackmatix, Meta personal attributes policy (2026-09-08): https://www.stackmatix.com/blog/meta-ads-personal-attributes-policy
- Femtech Insider, Meta sexual health policy (2022-10-18): https://femtechinsider.com/meta-ads-policy/
- Medicines (Advertisement and Sale) Act 1956, Act 290: https://pharmacy.moh.gov.my/sites/default/files/document-upload/medicine-advertisement-sale-act-1956-act-290_1.pdf
- MAB guidelines for advertising healthcare services: https://pharmacy.moh.gov.my/sites/default/files/document-upload/advertisement-guidelines-services-edited-mab-6-2011.pdf
- Baker McKenzie, Promoting Medical Products Globally, Malaysia chapter (2018): https://www.bakermckenzie.com/-/media/files/insight/publications/2019/05/dsc127515_malaysia_promoting-medical-products2018.pdf
- Medical Protection Society, Practice promotion factsheet (2015-01-22): https://www.medicalprotection.org/malaysia/casebook-resources/factsheets/factsheets/mal-practice-promotion
