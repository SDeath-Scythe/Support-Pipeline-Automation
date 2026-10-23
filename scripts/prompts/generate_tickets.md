You write synthetic customer support tickets for a dataset. The company is a fictional mobile-money wallet in Iraq: customers send transfers, top up phone credit, pay bills and merchants, use agents for cash-in and cash-out, and have a payment card. Tickets are written by customers in Iraqi Arabic, in a chat or app support form.

You get a list of specs. Write exactly one ticket per spec and return them all in one JSON array.

## Each spec tells you
- `issue`: the problem the customer has (its key, label and a short description). The ticket must be clearly about this issue as an Iraqi customer would describe it. Never write the label or key itself.
- `second_issue` (optional): a second, separate request in the same ticket.
- `dialect`:
  - `baghdadi`: شكو، شلون، هسه، اكو / ماكو، كلش، ديروح، اريد، شنو، چان
  - `southern` (Basra, Nasiriyah, Amarah): شنهو / شنو، يمعود، هواي، ﭽ for ك in some words (چان، ﭽا)، ابد، ليش هيج، اكو
  - `mosuli`: ق kept (قلتُ), غ for ر in some words (اغيد، مغتين), ايش for شنو, كتيغ for very, هوني for here
  Use the dialect naturally; don't overdo it.
- `style`:
  - `short`: one sentence, under about 15 words.
  - `long`: 3 to 6 sentences with background and some frustration or detail.
  - `typos`: realistic phone-typing mistakes (missing hamza, swapped or dropped letters, ه/ة, ي/ى), still readable.
  - `mixed_english`: some English words mixed in (transfer, app, card, OTP, balance, error), Arabic otherwise.
  - `voice_note_style`: like speech typed out: run-on, almost no punctuation, fillers (يعني، شوف، اي، والله).
  - `arabizi`: Arabic written in Latin letters and numbers (3=ع, 7=ح, 2=ء, 5=خ, 6=ط, 9=ص), as Iraqis type it.
- `difficulty`: `easy` = one clear problem; `medium` = needs some reading (slang, indirect wording); `hard` = genuinely easy to misread, while the intended issue stays the right answer.
- `edge_case` (optional) with an instruction: follow it exactly.
- `amount_iqd` or `amount_usd` (optional): the ticket MUST state exactly this amount, written the way a customer would (digits, Arabic-Indic digits, words, or dropping the thousand: خمسين = 50,000, ربع مليون = 250,000, مليون ونص = 1,500,000). If neither is given, write no amount.
- `include_reference`: if true, write the placeholder {REF} exactly once where the customer gives the transaction / operation number (رقم العملية، رقم الحوالة، ref). If false, do not write {REF} and do not invent any reference number.
- `include_phone`: if true, write the placeholder {PHONE} exactly once where the customer gives a phone number (the number money or credit was sent to). If false, do not write {PHONE} and do not invent any phone number.
- `urgency`: if true, the customer sounds urgent with a word like ضروري or عاجل or بسرعة.
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
