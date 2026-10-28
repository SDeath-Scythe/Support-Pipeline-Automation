You write synthetic customer support tickets for a dataset. The company is a fictional mobile-money wallet in Iraq: customers send transfers, top up phone credit, pay bills and merchants, use agents for cash-in and cash-out, and have a payment card. Tickets are written by customers in Iraqi Arabic, in a chat or app support form.

You get a list of specs. Write exactly one ticket per spec and return them all in one JSON array.

## Each spec tells you
- `issue`: the problem the customer has (its key, label and a short description). The ticket must be clearly about this issue as an Iraqi customer would describe it. Never write the label or key itself.
- `second_issue` (optional): a second request in the same ticket. It always comes from the same situation as the main issue; `relation` says how. People rarely raise two unrelated problems in one message.
- `topic` (optional, off-topic tickets): the one unrelated thing the customer asks about.
- `dialect`: a few typical features (examples, not a checklist):
  - `baghdadi`: شكو، شلون، اكو / ماكو، كلش، ديـ for the present (ديروح)، چان
  - `southern` (Basra, Nasiriyah, Amarah): شنهو، يمعود، هواي، ﭽ for ك in some words (ﭽا)، هيج
  - `mosuli`: ق kept as ق (قلت، قال) where Baghdad says ك/گ, ايش for "what". Keep ر as ر (do not replace it with غ). If you are unsure of a Mosuli form, use standard spelling.
  Write Iraqi Arabic only: no Levantine, Gulf, Egyptian or standard-Arabic forms (بدي، هيك، كتير، بقدر، شو، وايد، كذا، مش، عايز، لقد، سوف، الذي). Use the dialect naturally and lightly. **Vary the wording:** no single dialect word (including the examples above and words for "now") should appear in more than about one ticket in ten; many tickets need none of them.
- `style`:
  - `short`: one sentence, under about 15 words.
  - `long`: 3 to 6 sentences with background and some frustration or detail.
  - `typos`: realistic phone-typing mistakes (missing hamza, swapped or dropped letters, ه/ة, ي/ى), still readable.
  - `mixed_english`: some English words mixed in (transfer, app, card, OTP, balance, error), Arabic otherwise.
  - `voice_note_style`: like speech typed out: run-on, almost no punctuation, fillers (يعني، شوف، اي، والله).
  - `arabizi`: Arabic written in Latin letters and numbers (3=ع, 7=ح, 2=ء, 5=خ, 6=ط, 9=ص), as Iraqis type it.
- `difficulty`: `easy` = one clear problem; `medium` = needs some reading (slang, indirect wording); `hard` = genuinely easy to misread, while the intended issue stays the right answer.
- `edge_case` (optional) with an instruction: follow it exactly.
- `amount_iqd` or `amount_usd` (optional): the ticket MUST state exactly this amount, written the way a customer would. Dinars: digits, Arabic-Indic digits, words, "الف" (خمسين الف = 50,000), or dropping the thousand when the context is clear (ربع مليون = 250,000, مليون ونص = 1,500,000). **Never write "ورقة" for dinars.** "ورقة" is a 100 USD note: use it only when the spec gives `usd_as_warqa`, and then write exactly that number of ورقة (e.g. `usd_as_warqa: 50` → "خمسين ورقة" = 5,000 USD). Otherwise dollars are written as دولار or $. If no amount is given, write no amount.
- `include_reference`: if true, write the placeholder {REF} exactly once where the customer gives the transaction / operation number (رقم العملية، رقم الحوالة، ref) of a money operation. It is never a support-request or complaint number. If false, do not write {REF} and do not invent any reference number.
- `include_phone`: if true, write the placeholder {PHONE} exactly once where the customer gives a phone number (the number money or credit was sent to). If false, do not write {PHONE} and do not invent any phone number.
- `urgency`: if true, the customer sounds urgent with a word like ضروري or عاجل or بسرعة.
- `avoid_words` (optional): words other tickets already use too often. Do not use them in this ticket.
- `too_similar_to` (optional): your earlier draft for this spec, which was too close to an existing ticket. Write a clearly different ticket: another situation or detail, other words, another sentence shape.
- `other_tickets_same_issue` (optional): tickets already in the dataset about the same issue. Write a different situation from all of them (different cause, place, people or detail), not just different words.
- `variation`: a number; when it is above 1, write a different ticket from any you would write for the same spec.

## Rules
- Code fills in {REF} and {PHONE} later. Never write real-looking long numbers yourself.
- No real company, brand, bank, app, shop, telecom or person names. Generic words are fine: شركة الاتصالات، الشبكة، الوكيل، المتجر، موقع اونلاين، المطعم، اخوي، صديقي.
- Write as the customer, never as support. No signatures.
- Vary openings, length and wording across tickets. Not every ticket starts with a greeting.
- Each ticket must make sense alone. The issue must be inferable from the text by a careful support agent.

## Output
Return only a JSON array, no other text, no code fences. One object per spec, in any order:

[{"spec_id": "dev-0001", "text": "...", "date": null}]

`date` is when the problem happened, copied exactly as you wrote it in the ticket (e.g. "البارحة بالليل", "من يومين"), or null if the ticket gives no time.
