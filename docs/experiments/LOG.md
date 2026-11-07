# Results log: fix experiments

Newest first. Method: [README.md](README.md). The 20 Oct rounds (from "Current recommendation" down) have per-config pages and a summary table in [fixes_30/summary.md](fixes_30/summary.md) (round 1 kept as [summary-round1.md](fixes_30/summary-round1.md)); each of their steps is its own commit on the 20 Oct development branch, merged into `main` on 29 Oct.

The 20 Oct numbers come from the `cli` backend: good for comparing configs with each other, **not** for thresholds or the MVP. From 29 Oct, reported pipeline numbers come from the API. Gold labels for `fixes_30` were model-written, and the draft judge is a model, so treat single-ticket differences with care.

## 7 Nov: Before the second round of test sessions: the saved run served as today's code decides it (no model calls)

Four items were left before the second round of role-played test sessions. No model was called, and nothing was spent.

**1. The saved run is served as today's code would decide it.** The viewer serves `docs/runs/test2/final.json` (run on 30 Oct; not regenerated, and the server never writes it). Until now its draft checks were recomputed with today's rules, but its outcome and flags stayed as saved: six ready tickets showed a new draft warning and asked for a tick while they sat in «جاهزة», and t2-0030 and t2-0041 had no quiet note. The author's decision: serve a saved run as today's code would decide it, for the rules that need no model call. After `apply_account_risk`, the server's `apply_current_rules` (`app/server.py`) adds only what is missing, in the result and in its "result" event:
- a flag `draft:<kind>` for each draft-check finding the page shows, as `run.py` flags a live draft; a ready ticket with one becomes «تحتاج تأكيد»;
- the code rules on the customer's text (`run.text_flags`: `secret_in_ticket`, `bidi_controls`, `other_phone`, `complaint_risk`, and the quiet `instructions_in_ticket`, which leaves a ticket ready) and `amount_disagreed` from the two saved answers, with their notes, `secret_spans`, and on an escalation the team note's line for each.

It never re-routes, re-prioritises, re-types or re-drafts a ticket, so `device_lost` and `fraud_secondary`, which move a ticket to the fraud team, are not applied. A changed result is marked `rules_recomputed` (the flags added) and `outcome_recomputed` (when it moved), and «كيف يشتغل» says so on the ticket and in the overview. A decision is checked against this served copy (`served_ticket`): an approval of t2-0004 is logged as flagged with `draft:amount_not_in_ticket`, whatever the request says, and `ticket_sha256` stays null for a saved run.

| test2 final, as the viewer serves it | Before | After |
|---|---|---|
| «تحتاج تأكيد» / «متصعّدة» / «جاهزة» | 15 / 6 / 59 | **21 / 6 / 53** |
| Ready → «تحتاج تأكيد» | – | t2-0004, t2-0013, t2-0058 (`amount_not_in_ticket`); t2-0056 (`ask_missing`); t2-0019, t2-0069 (`dialect_words`) |
| Flags added, outcome kept | – | t2-0017 (flagged already for a missing reference): `draft:ask_missing`, `draft:dialect_words`; t2-0030, t2-0041: `instructions_in_ticket`, still «جاهزة» |
| Outcome equal to the gold outcome, as «كيف يشتغل» scores it | 74/80 | 68/80 |

- **Six, not seven.** The entries below said 7 ready tickets; there were 6, and t2-0017 was already flagged (corrected below).
- **The score.** The gold file marks the six as ready: a warning is about the draft, not the ticket. «كيف يشتغل» scores them against the file as it is and says why.
- **Nothing else fires on test2:** no other code rule, and no saved ticket has a card number or code to hide.
- **The inbox's first flagged ticket is now a P1:** t2-0058, a transfer. The others there are P2s and P3s.

**2. «كيف يشتغل» hides a typed secret.** It showed the full customer text in its ticket list, the ticket's text and the cleaned text. It now hides each card number or code in `result.secret_spans` the way «رسالة الزبون» does: «••••», read «رقم مخفي» by a screen reader. The list never shows it. In the ticket on screen, the text is hidden by its spans, and the cleaned text, the models' answers and prompts, the draft, its check chips, the team note, the extracted reference and phone, and the gold table hide the same digits wherever they are written again, until one «اظهر الرقم». Opening another ticket hides it again, and ranges that do not fit the text are dropped (`app/static/js/process.js`, `setHidden`, `hideBox`, `refreshHidden`, `rowText`; shared with the inbox in `facts.js`, `fitSpans`, `secretMask`, `secretRanges`). A live ticket's spans come with its result, and the page hides them then. A number the pipeline did not find is not hidden here either (failure mode 8).

**3. `claims_done` learns «مسجل عندنا».** It missed «رقم العملية 7021535 مسجل عندنا» (dev-0015, in the prompt revision step), a claim that something is on record with us, which the tool cannot have checked. It now also fires on "registered" said to be "with us" or "in the system": «مسجل», «مسجلة», «مسجلين» or «متسجل», «سجلنا» or «سجلناه», or «تم تسجيل» or «تم تسجيله», followed within three words by «عندنا», «عدنا», «لدينا», «بنظامنا», «بالنظام» or «بسجلاتنا» (`draft_check.py`, `_on_record`). It stays narrow:
- without "with us", «سجلنا طلبك», «سجلنا رقم العملية» and «وصلنا طلبك وسجلناه» are hand-offs, and «رقمك المسجل» is the customer's number;
- not when negated («غير مسجل عندنا»), asked («رقمك مسجل عندنا؟», «إذا مسجل عندنا»), for the customer to check («تأكد إن رقمك مسجل عندنا», «لازم يكون مسجل عندنا»), reported («ذكرت إن رقمك مسجل عندنا»; but «الرقم اللي كتبته مسجل عندنا» is the draft's own claim) or quoted;
- «سجّل» and «سجلت», said by the customer or asked of them, are not matched.

Measured on every saved draft set, with the draft checks only (`LLM_CACHE_ONLY=1`, no key; the checks call no model):

| Drafts | claims_done before → after |
|---|---|
| Saved drafts: `runs/exp` (heldout left out) and test2 final, 2,531 | 0 → 5 (2 texts: dev-0040 in one config, dev-0015 in four) |
| Cache-only replays of the adopted code: dev 215, test2 74, mvp_test 69, adversarial_14 11 | 0 → 0 |
| The adopted drafter's 146 new drafts (test2 and mvp_test) | 0 → 0 |
| The prompt revision step's dev drafts, all configs (1,135) | 0 → 2 (dev-0015 and dev-0118, both from the revised drafter) |
| The session tickets re-drafted in the flag runs (183) | 0 → 0 |
| The sessions' own drafts (42) | 1 → 1 (T05's «فسجلناها», unchanged) |

All four new texts were read, and each says something is on record with us: «رقم العملية 7021535 مسجل عندنا», «ومسجلين عندنا رقم آخر عملية 7021535», «ورقم ابن عمك اللي كتبته (…) مسجل عندنا», «رقم العملية TX95304083 سجلناه عندنا». No false alarm was found. Unit tests: 11 that fire and 23 that don't (`tests/test_text_rules.py`). One older test changed with it: «رقمك 9647701234568 مسجل عدنا», in the list `sensitive_number` must leave alone, is now a `claims_done`, and `sensitive_number` still leaves it alone. The saved test2 run has no such draft, so its tab counts do not move.

**4. Branch names.** The docs named the 20 Oct working branch. `git merge-base --is-ancestor` shows that its last commit (7bae0d8, 23 Oct) is on `main` and on `mvp`, and the local reflog shows `main` reached it by a fast-forward on 29 Oct. CONTEXT.md, HANDOVER.md, this log and the 20 Oct smoke-test README now say "the 20 Oct development branch, merged into `main` on 29 Oct". The working rule now reads: work on `mvp`; changes reach `main` when the author says so.

**Tests.** pytest: 1,963 pass (1,926 before), with the API keys removed and no model call. `node tests/ui/smoke.cjs`: 535/535 (527 before): desk-light 155, desk-dark 155, phone-light 89, phone-dark 89, fresh-clone 47. New: the three «كيف يشتغل» hiding checks and an identity-tick approval in each desktop pass. Changed with the behaviour: the tab counts (21 / 6 / 53); the overview's outcome, 68/80, and its note; and the flagged-ticket steps, whose first ticket is now t2-0058 (see tests/ui/README.md). The `docs/demo/` screenshots were retaken with the fresh-clone pass (47/47); its tabs read 21 / 6 / 53.

## 7 Nov: Role-played test sessions with live model calls, and the fixes

**What was done.** Six role-played test sessions used the viewer in a browser, with live model calls on tickets they wrote themselves: a new support agent, a team lead, a support agent on a phone, a compliance reviewer, a competition judge and a customer-experience quality lead. Each ran its own viewer with a spending cap of $1.25. Together they ran **70 live tickets for about $0.23** in model calls, and decided 65 tickets of the saved final run. Their reports, about 95, were reproduced and merged into **43 confirmed issues** (T01 to T43): 7 high, 16 medium and 20 low. 5 reports were not reproduced, and 18 were by design or for later. **These sessions were role-played: no support agent has used the inbox yet.**

**What they liked.** The first screen: the card that explains the three tabs, and the line that nothing goes to a customer by itself. Friction that follows risk: approve waits for the tick on a flagged ticket, and a fraud ticket goes to its team with one key and an undo. Drafts in calm Iraqi Arabic that promise nothing; planted instructions changed no type or priority, and a reply the customer dictated («تم إرجاع مبلغ 500,000 دينار إلى حسابك») was refused. The facts line read Arabic-Indic digits, «مليونين ونص» and Mosuli words. «كيف يشتغل», the README and SECURITY.md were called honest about their limits.

**The seven high issues, and what changed:**
1. **A fraud second issue changed nothing** (T01): a lost card with an unknown ATM withdrawal went to the cards team at P3. A fraud type given as the second issue, by either model, now escalates the ticket as fraud: fraud team, P1, no draft, and the team note names the other request (`fraud_secondary`).
2. **A card number, PIN or code the customer typed was neither flagged nor hidden** (T02). It now flags the ticket (`secret_in_ticket`): a draft asks for the tick «تأكدت إن الرد ينبّه الزبون يغيّر الرمز ويوقف البطاقة», an escalation's team note says it, and the inbox shows the number as «••••» in «رسالة الزبون» and the queue row until «اظهر الرقم». The text still goes to the model provider unmasked.
3. **The decision API accepted what the page never sends** (T03): an approved fraud escalation, an unknown ticket id, and a live identity-check ticket with its flag left out. The server now checks each decision against the ticket as it served it: 400 for a ticket or a draft it did not serve, 409 for an approve or edit of an escalation or of a type that is never drafted. For a live run it keeps what it served in memory, with keyed hashes in place of the text.
4. **The code-request check missed a paraphrase and English** (T04: «الأرقام الستة اللي وصلتك على تلفونك»). It now knows the code as the digits or the message that arrived, and English after "enter", "type", "write", "read out", "say" or "what are". No flag was needed: on every guard set and the 2,531 saved drafts nothing changed.
5. **The draft check passed claims of things done** (T05: «تم إرجاع مبلغ …», «شكواك على الموظف فسجلناها»). A new warning, `claims_done`, asks for a tick.
6. **Approve-and-next acted on a ticket nobody had seen** (T06: a 180 ms double tap approved a P1). A ticket just on screen cannot be decided for 700 ms (1.5 s when the inbox has changed tab).
7. **A second request was neither routed nor shown, while the draft said a team would handle it** (T07). A drafted ticket now shows «طلب ثاني: النوع · القسم» and asks for a tick on «بالتذكرة طلب ثاني محد مستلمه، راجع شنو يكول الرد عنه». The drafter's rule 4 now says a second request will be followed up, never that it was registered or handled (dev: 2 of 5 drafts said so, now 0 of 5). It is still not routed to a second team.

**Pipeline changes: thirteen flags, measured with and without.** Each change to what the pipeline decides or drafts went into `src/pipeline/fixes.py` as a flag, off by default, and was run with and without it on the same tickets. The code rules were replayed from the cache on dev (233), test2 (80), mvp_test (78) and adversarial_14; the draft warnings were also run on the 2,531 saved drafts and the 42 session drafts; the prompt flags were re-drafted on the API and graded twice by the cli judge. Twelve were then made the normal code (next entry).

| Flag | What it does | Without → with | Adopted |
|---|---|---|---|
| `fraud_secondary` | A fraud type as the second issue, from either model, escalates as fraud (P1, no draft) | Scored sets: 0 tickets changed; fraud recall 17/17, 6/6, 6/6 both ways. Replies recorded in the sessions: 3 tickets from cards P3 or transfers P2 → fraud P1, escalated | yes |
| `secret_in_ticket` | A card number, PIN or code in the ticket flags it, and gives the page the spans to hide | Scored sets and edge_cases: 0 fired. Session tickets: 2 of 18, both true; the 2 controls stay clean | yes |
| `strip_format_chars` | The clean step drops invisible format characters; direction controls add `bidi_controls`, and two models reading different amounts add `amount_disagreed` | Scored sets hold none. The session ticket with direction controls: 3 findings caused by the hidden characters → `bidi_controls` only. dev-0138: drafted → flagged `amount_disagreed` («ميت الف مرتين»: 100,000 or 200,000) | yes |
| `device_lost` | A lost or stolen phone with the wallet still open goes to the fraud team at P1, no draft; writing from someone else's phone adds `other_phone` | Scored sets: 0 changes (8 lost-phone tickets don't say the wallet is open). The session ticket: flagged, accounts P2 → escalated, fraud P1 | yes |
| `complaint_risk` | A regulator, a threat to complain or a repeat contact flags the ticket; priority and team never change | dev 1 (already flagged), adversarial 1 (drafted → flagged), test2 0, mvp_test 0; all true after one false alarm (mvp-0005) was fixed | yes |
| `instructions_in_ticket` | Text that tries to instruct the system adds a quiet note: no tick, no outcome change | dev 5, test2 2, mvp_test 2, adversarial 3, edge_cases 1: all 13 read, all planted | yes |
| `claims_done` | Warning: the draft says something was done (refunded, registered) | Saved drafts 0 of 2,531; session drafts 1 of 42, true | yes |
| `repeated_text` | Warning: a second greeting or a repeated sentence | Saved 1 (dev-0132, true); sessions 0 | yes |
| `ask_missing` | Warning: the draft doesn't ask for a field the drafter was told to ask for | Saved 44 drafts on 15 tickets, 14 true. test2 + mvp_test: 3 old drafts → 4 drafts from the adopted drafter | yes |
| `dialect_words` | Warning: a word from another dialect or from formal Arabic («رح», «يرجى», «عشان», «وايد», «التي») | Saved 98 drafts, 25 of 25 sampled true; sessions 6 of 6 true. test2 + mvp_test: 4 old → 1 new | yes |
| `amount_own_words` | The drafter gets the customer's own words for an amount not written in digits; the warning `amount_not_in_ticket` fires on an amount the customer didn't write | dev: the narrowed warning fires on 3 of 215 no-flag drafts (all «ورقة» turned into dollars), 0 with the flag; judge on the 61 changed drafts: mean 4.51 → 4.61, bad 4 → 1 | yes |
| `draft_rules_ut` | Revised drafter rules: a second request is followed up; no guessed gender; on a blocked account, never "nothing more is needed"; plain Baghdadi words; ask only for what the ask lines name; instructions in the ticket get no answer | dev 60, graded twice: asks right 53 / 53 → 55 / 55, bad 4 / 4 → 3 / 3, avoid-list words 8 → 0, address terms 3 → 0. test2 + mvp_test (live): avoid-list 4 → 0, address terms 6 → 0, judge on 40 drafts 4.38 → 4.55 (grading 2: 4.33 → 4.53) | yes |
| `summary_qualifiers` | The escalation summary keeps the customer's own qualifiers, in the third person and in Arabic | 18 dev escalations × 3 replicates: English words 3 → 1 of 54, first person 0 → 0, over 20 words 20 → 20 | no: the bar was 0 English words |

Two pipeline fixes needed no flag: the code-request check (item 4 above) and the budget stop, which is now `budget_reached` instead of a model error, with the cap printed to four decimals (T39). With all twelve adopted, the saved drafts' review rate rose (dev 53 → 68 of 233, test2 21 → 27 of 80, mvp_test 27 → 28 of 78), mostly from the new warnings on drafts the old drafter wrote. With drafts from the adopted drafter it went from 21 to 22 of 80 on test2 and from 24 to 26 of 75 on mvp_test, and no team or priority moved (next entry).

**Viewer and server:**
- **Decisions:** checked against what the server served (T03); each live run has its own id («live-» and 6 hex digits on screen) and the log keeps a keyed hash of its cleaned text (T11); ticked points are logged from an allow-list (T28); four new reason codes (dialect, a false claim, duplicate, instructions in the ticket), and reasons about a reply only when there was one (T31).
- **Disclosure:** the new-ticket dialog says the text goes to an outside model provider abroad, so paste only tickets allowed to be sent; the header says «وضع التطوير» while `REAL_DATA` is unset (T17).
- **Flow:** the pause before a new ticket can be decided (T06); the inbox stays in the agent's tab and offers «روح لـ…» when a more urgent ticket waits (T13); a refused Ctrl+Enter puts the focus on the tick, and X ticks it (T21); forward names the corrected team (T12); corrections show after a reload and warn before leaving (T24, T25); Ctrl+Z on another ticket asks first (T29); a team-only correction has its own point (T38); a missing field can be marked «ما يحتاج بهالتذكرة» (T42).
- **Text:** digits typed with spaces keep their order, a hyphenated reference doesn't split (T10), and English reads in order (T27).
- **Phone:** the back gesture returns to the queue (T22); a refusal for the tick is said under the buttons and the box is brought into view, and toasts sit at the top (T23); short screens and the on-screen keyboard (T36); 44 px touch targets and no key hints (T37).
- **Help and keys:** the «?» sheet is now «شلون تشتغل»: four lines (the tabs, ticking, forwarding, undo) and a button that brings back the first-visit card, then the keys (T32). Ctrl+Enter sends a new ticket, C opens the correction panel, Esc closes it (T30).
- **Live tickets:** every visit starts in «وضع الموظف»; a finished live ticket becomes the open one, marked «جديدة» (T33), and heads the «كيف يشتغل» list (T34).
- **The page side of the new rules:** the hidden number, confirm points for `secret_in_ticket`, `bidi_controls`, `amount_disagreed`, `other_phone` and `complaint_risk`, the quiet note, the reasons for `device_lost` and `budget_reached`, `ask_missing` naming its fields, and «رمز مخفي انشال» in the clean step.

**Tests.** pytest: 1,926 pass (1,694 before), with the API keys removed and no model call. `node tests/ui/smoke.cjs`: 527/527 (448 before): desk-light 151, desk-dark 151, phone-light 89, phone-dark 89, fresh-clone 47.

**Still open:**
- **Questions for the institution:** an AML or frozen-account type (a session's frozen account was typed as an unknown charge); the safety advice a customer who lost a phone should get (none was written); masking before the text goes to the provider (SECURITY.md, section 11).
- **Not built:** a model-based check for unclear sentences in drafts and notes (only a prompt line); a second team for a second request, in routing and in the decision record; duplicate detection; replies in English; new ticket types; a view for a team lead.
- **Left from the fixes:** `summary_qualifiers` stays a flag, and about a third of summaries are over 20 words; 3 of 146 new drafts put words in «»; one draft carried a second, revised reply (caught by `stray_latin`); «مسجل عندنا» is not yet a `claims_done` phrase (added before the second round, entry above). The saved test2 run shows the new warnings on 6 ready tickets (this said 7) but keeps them in «جاهزة» (the author's decision; changed before the second round, entry above). The desktop toast still sits at the bottom, no real phone keyboard was tried, and edge_cases was not re-run.
- **People:** these sessions were role-played. No support agent has used the inbox yet.

**Spend.** The sessions: about $0.23, from the cost of each stage in the streams they saved, with a few uncaptured tickets estimated. The fixes: $1.40, from the run files' `cost_usd` (pipeline rules $0.06, prompt flags $0.80, their revision $0.24, the adoption's re-drafts $0.31). Reproducing the reports, the viewer fixes and the draft warnings made no paid call, and the judge ran on the free cli backend. In all, about $1.63.

## 7 Nov: Twelve of the thirteen test-session flags become the normal code

**What was adopted** (`src/pipeline/fixes.py`, `ADOPTED`). The six code rules on the customer's text: `fraud_secondary`, `secret_in_ticket`, `strip_format_chars`, `device_lost`, `complaint_risk` and `instructions_in_ticket`. They found no false alarm on dev, test2, mvp_test, adversarial_14 or edge_cases, and they fix the reported cases. Four draft warnings: `claims_done`, `repeated_text` and `dialect_words` (0 or near 0 false alarms on 2,531 saved drafts), and `ask_missing` (14 of 15 saved hits true). `amount_own_words`, with the narrowed check, which no longer fires on a faithful digit form (12 saved tickets read: all were note conversions or amounts computed by the model). And the revised `draft_rules_ut`, which replaced `draft_system.md`. On the same 60 dev drafts, graded twice, asks_right was 55/55 against 53/53 with no flag, bad drafts 3/3 against 4/4, and its code gains held. The warnings ask for a tick, and none blocks an approval.

**Not adopted.** `summary_qualifiers` stays a flag. Over three replicates it had 0 first-person slips, but 1 English word in 54 lines, and the rule asked for 0.

**Code rules and warnings, cache-only.** The adopted code ran on the saved drafts, with the old drafter inputs. The baseline is 3b37091 with no flag.

| Set | Review rate | Fraud recall | Type used, priority | Tickets moved, by rule (fired) |
|---|---|---|---|---|
| dev 233 | 53 → 68 | 17/17 → 17/17 | 231, 231 → same | dialect_words 8 (9), ask_missing 4 (7), amount_not_in_ticket 3 (3), amount_disagreed 1 (dev-0138); quiet instructions_in_ticket (5) |
| test2 80 | 21 → 27 | 6/6 → 6/6 | 78, 79 → same | amount_not_in_ticket 3 (3), dialect_words 2 (3), ask_missing 1 (2); instructions_in_ticket (2) |
| mvp_test 78 | 27 → 28 | 6/6 → 6/6 | 77, 77 → same | amount_not_in_ticket 1 (1); dialect_words (1) and ask_missing (1) on flagged tickets; instructions_in_ticket (2) |
| adversarial_14 | 4 → 5 | – | 14 → same | complaint_risk 1 (a11); instructions_in_ticket (3) |

On these sets, `fraud_secondary`, `secret_in_ticket`, `device_lost`, `other_phone`, `bidi_controls`, `claims_done` and `repeated_text` fired on no ticket. Teams did not move. complaint_risk also fired on dev-0231, which was already flagged.

**Drafts from the adopted drafter (live).** test2 and mvp_test were re-drafted with the classifications from the cache, at $0.3055. The warnings on 146 drafts: ask_missing 4 (merchant 2, agent_location 1, reference_lost 1), dialect_words 1 («بينما»), amount_not_in_ticket 0, claims_done 0, repeated_text 0. The same checks on the 143 old drafts found amount_not_in_ticket 4, ask_missing 3 and dialect_words 4. Avoid-list words went from 4 to 0, address terms from 6 to 0, and the mean length from 217.9 to 191.3 characters. Three drafts put words in «» (two status words, and the amount «مليونين»). The review rate went from 21 to 22 of 80 on test2. On mvp_test it went from 24 to 26 of 75, leaving out the 3 tickets that were cache misses in the baseline. The cli judge graded 40 drafts, picked with seed 7 from the 143 tickets drafted in both runs:

| Grading | Mean | Bad | asks_right | grounded | Score up / down |
|---|---|---|---|---|---|
| 1 | 4.375 → 4.55 | 2 → 1 | 34 → 35 | 38 → 39 | 8 / 1 |
| 2 (salt g2) | 4.325 → 4.525 | 1 → 1 | 34 → 35 | 39 → 39 | 11 / 3 |

**The saved run the viewer serves** (`docs/runs/test2/final.json`, not regenerated). The server recomputes its draft-check spans with today's rules. 6 drafted tickets (this said 7) and t2-0017 now show a new warning: amount_not_in_ticket on t2-0004, t2-0013 and t2-0058; ask_missing on t2-0056; dialect_words on t2-0019 and t2-0069; ask_missing and dialect_words on t2-0017. Their outcome and flags stay as saved, so the tab counts do not move (15 / 6 / 59, as since the 5 Nov account_risk recompute). The text rules are not recomputed, so t2-0030 and t2-0041 do not show the quiet instructions_in_ticket note. (Both changed before the second round: entry above, 21 / 6 / 53.)

## 7 Nov: The code-request check and an unrelated «ما» (no model calls)

**The problem.** While the inbox tour was being recorded, «وما نگدر دزلنا الرمز اللي وصلك» ("and we can't; send us the code you got") was typed into a draft. `asks_secret`, the blocking rule against a draft that asks the customer for a code, OTP, PIN, password or CVV, did not flag it, in the page or at the server. The same request with nothing before it was flagged.

**The cause.** Any negation within four words before a request hid the request. Here «ما» negates «نگدر» ("we can"), not «دزلنا» ("send us").

**The new rule** (`src/pipeline/draft_check.py`: `_negated`, `_reaching_negation`, `_reaches`). A negation hides a request only when it negates that request. It reaches a later word only through words that pass it on: an auxiliary («ما راح»), "can" or "need" before a verb of the same person, "think" or "that", a pronoun, an adverb, "or". An order is negated with «لا», never «ما» («ما دز» is the past). So «ما نگدر نطلب منك الرمز» ("we can't ask you for the code") is still allowed, and «وما نگدر دزلنا الرمز اللي وصلك» and «ما نگدر نكمل ترسلنا الرمز» ("we can't go on, send us the code") are caught.

**Three test rounds.** Each round wrote sentences for this test in two passes, one hunting missed requests and one hunting false alarms, ran the rule on them with no model call, and fixed what it got wrong. Each round's fixes were then checked by the next round, and all the sentences are kept as a regression set.
- Round 1: 197 sentences hunting misses and 178 hunting false alarms. The rule as it then stood got 155 and 74 wrong.
- Round 2: 108 and 146; 71 and 98 wrong. Many of round 2's false alarms came from round 1's fixes; they were fixed.
- Round 3: 152 and 416; 108 and 101 wrong.

**Held-out sets.** Two more sets of 150 were then written by evaluators who had not read the rule: replies as the drafter might write them (68 ask for a secret, 82 are safe; mostly Baghdadi, some southern, Mosuli and feminine address; login, an OTP not arriving, SIM change, a blocked account, transfers, cards, agent cash-in) and hurried edits as a support agent might type them (69 ask, 81 are safe; English, Arabizi and other dialects mixed in). Every label was read again and none was changed. The most arguable is "give the OTP to our authorised agent", kept as a request. They were measured once, before the last fixes below.

**Results** (requests caught / safe sentences passed; old is the rule at 4242ea6):

| Set (requests / safe) | Old rule | New rule, before the last fixes | After the last fixes |
|---|---|---|---|
| Rounds 1-2 (266 / 363) | 65 (24%) / 288 (79%) | 259 (97%) / 363 (100%) | 263 (99%) / 363 (100%) |
| Round 3 (144 / 424) | 19 (13%) / 374 (88%) | 140 (97%) / 424 (100%) | 143 (99%) / 424 (100%) |
| Held-out replies (68 / 82) | 41 (60%) / 75 (91%) | **48 (71%) / 79 (96%)** | 66 (97%) / 82 (100%), not held out |
| Held-out edits (69 / 81) | 15 (22%) / 80 (99%) | **30 (43%) / 77 (95%)** | 61 (88%) / 81 (100%), not held out |

- **The held-out result is the bold column.** The last column is not held out: the fixes were made from those lists.
- **Then fixed:** 18 of the replies' 20 misses and all 3 of their false alarms; 31 of the edits' 39 misses and all 4 of theirs. The ten left are under "Still not caught" below.
- On the replies the new rule got 16 items right that the old one got wrong, and 5 wrong that the old one got right: three requests to hand a secret to our side (type the PIN in the in-app chat for the employee, give the OTP to our authorised agent, give the PIN to our representative) and two false alarms («إحنا ما راح نتصل بيك نطلب كلمة السر أو الرمز», where the negation sits on "call"; a code on a receipt that the reply says is the transaction number). On the edits, 15 and 3 (three new false alarms). All eight were fixed.
- The replies' misses had five shapes: the secret described, not named («الثلاث أرقام المطبوعة بظهر البطاقة»); read out, dictated, said or handed to our staff; "reply with the code" or "put it in our private messages"; the code named in one place and asked for later, through a pronoun or a list; a warning, then a request. Most of the edits' misses were English or Arabizi, or used a verb other than "send".

**The last fixes,** each small and each with tests in `tests/test_text_rules.py`:
- **A line break** between a request and its code («ممكن تدزلنا⏎الرمز اللي وصلك؟») is read as a space when it comes right after a request word and right before the code (`_join_lines`). «دزلنا صورة الهوية⏎الرمز لا تشاركه» stays two lines.
- **Courtesy words between** (up to four: «دزلنا بأسرع وقت ممكن رجاءً الرمز», «نحتاج منك لو سمحت الرمز»), and «الـ OTP» typed with a space (`_courtesy_run`).
- **English:** share, give, tell, provide, forward, read me, reply with, "what is the code", "we need your OTP", "type it here", "the 6-digit code", "card security code", and «the code u got, send it». Not after «never», «don't», «no need» or «if someone asks you to», or with "we" or "the app" as the sender; «don't forget to» and «don't hesitate to» still ask.
- **Arabizi:** «dizlna», «tdizlna», «dezelna», «ib3atli», «ersil», «gulli» or «ni7taj» before code, otp, ramz, pin or password; not after «la», «ma» or «mo».
- **Handing it to our side:** «انطيه الرمز» (our agent), «گول للموظف كلمة السر», «اقرا عليه الرمز», «أملي على الموظف رمز التحقق», «گول بيها الرمز» (a voice note), and the PIN typed in a chat «حتى يشوفه الموظف». «گله الرمز سري وما أنطيه» is advice and stays allowed.
- **A secret described:** «الثلاث أرقام المطبوعة بظهر البطاقة», «الرقم المكون من ثلاث مراتب», «الأرقام الأربعة اللي اخترتها», «الكلمة اللي تدخل بيها», «الأرقام اللي بالظهر».
- **Named first, asked later:** a warning, then a request in the next sentence («الرمز لا تكتبه بأي موقع خارجي. دزه إلنا»); «دزلنا آخر واحد»; «گلنا شنو اخترت»; an inline numbered list («نحتاج: 1) … 3) الرقم السري»); «رد على هاي الرسالة برمز التحقق»; «حط الرمز بالخاص».
- **False alarms:** «إحنا ما راح نتصل بيك نطلب كلمة السر» (one negation over "call" and "ask"); «… اكتبه بالتطبيق واختار كلمة سر جديدة» and «دزلنا رسالة لمن تغير الرقم السري» (the code belongs to "choose" or "change"); a code printed on a receipt; «خبرنا لو الرمز ما وصلك» ("whether"); «مش لازم تدزلنا الرمز»; «if someone asks u to send the OTP».

**Guards.** A scratch script (outside the repo) runs the old rule (a copy of 4242ea6), the new rule before the last fixes (a copy of feaff34) and the working tree, with the API keys removed and no model call, on the 629 sentences of rounds 1-2, the 568 of round 3, both held-out sets and the saved drafts; the full pytest suite runs beside it. It was run after the fixes and after every later change, and no guard is worse than at feaff34 on any item. **The saved drafts are unchanged:** on the 74 drafts of the final test (`docs/runs/test2/final.json`) all three give the same findings (one `stray_latin`, no `asks_secret`). No file under `data/heldout*` or the git-ignored `runs/` was opened.

**Still not caught:**
- A request five or more words before the code, with other words between («دزلنا بعد ما تشوف الرسالة الرمز اللي وصلك»).
- The code named in one sentence and asked for as "the same number" or "which number" («رد علينا بنفس الرقم», «گلّنا شنو الرقم اللي تريده»). Reading "the number" as the code would also flag «گلنا شنو الرقم اللي تحول عليه».
- Kurdish-speaker word order («رجاء انت رمز ارسل حتى حساب يفتح»), «الغمز» for «الرمز», and an indirect question («ما ادري تگدر تدزلنا الرمز لو لا»).
- Egyptian forms («ابعت», «اديني», «ابعتهولنا»), outside the Iraqi Arabic the drafter writes; English in the passive («The OTP should be sent to us») or with no verb («OTP pls»), «confirm your PIN … just type it», and a misspelt «pasword».

**Why that is accepted.** Latin text still gets the `stray_latin` warning, so the English and Arabizi misses are still highlighted for the agent. An agent who wants to get past a text rule can (a spelling, a space, a picture). The rule is a safety net under a person's approval, not the control itself, and the server applies it too, so a hand-made request is refused (409).

**Size and tests.** `draft_check.py` grew from 381 to 1,375 lines (1,219 before the last fixes). **pytest: 1,694 pass** (697 before this work, 1,591 before the last fixes): 894 new for the three rounds and 103 for the last fixes, with the API keys removed and no model call. Each test function for the last fixes fails on the code before them (checked against a copy of feaff34). **`node tests/ui/smoke.cjs`: 448/448**, unchanged.

## 5 Nov: A calmer inbox (no model calls)

**The problem,** in the author's words: "the UI is too flooded with information, it's overwhelming." At 1280 × 800 a ready ticket showed, at once: the header with a labelled source picker, a saved-run pill and two buttons; the «ليش؟ كيف انحسمت» panel open with six stages of text; a row of key chips; a five-cell summary grid and «صحّح»; fact boxes above the message; the message; the draft; a sentence listing every check that passed; an action bar with key chips, a lock badge and a helper sentence; and a queue head with a counter, a bar, a run note and an urgent line, over rows that each showed an icon, a status word, the id, a priority pill, the team and two lines of text.

**The aim:** the agent sees what they need to decide the ticket in front of them (the message, one line on what the system understood, the draft, the one obvious action). Everything else is one click or key away, and nothing that protects a customer is removed or weakened. The pipeline, the server's checks and the decision log are unchanged; only the page (`app/static/`) changed.

**What moved where:**
- **«ليش؟»** (the six stages) is closed until the agent opens it (its button or W; Escape or its own button closes it). Over 1000 px it is a column of its own beside the ticket, which narrows; between 721 and 1000 px it is a drawer over the ticket's side that another ticket closes. Only the agent's own act is remembered (preferences key v2; v1's auto-saved «open» is dropped).
- **Header:** brand, mode switch, «تذكرة جديدة», «?». The source picker is small, with no visible label (its name «المصدر» stays), and its text says the run is saved («تشغيل محفوظ: الاختبار النهائي»). The saved-run pill is gone: the lock line by the action bar says nothing is sent. On a phone's ticket screen the mode switch and the picker are on the queue screen.
- **Queue:** the head is «خلصت X من N» and its bar. The run note («بهالتشغيل النظام صعّد 6 تذاكر، كلها احتمال احتيال.») moved to «كيف يشتغل»'s overview; the urgent line became a tiny «P1» (or «؟», no priority) on that tab, named in the tab. A row is its priority, a small id and two lines of text; its status is the start of its accessible name (the tab shows it), its team is on the ticket, and in «خلصت» a small named icon says what was done.
- **Ticket:** the id small, the priority, then one line «النوع · القسم» with a pencil («صحّح النوع أو القسم أو الأولوية»). «المسودة المفروض تسأل عن: …» shows only when something is missing and the banner does not already say it; an agreed re-check is one quiet line. The key chips under the title are gone (the «?» sheet and the buttons' names keep the keys).
- **Facts:** no boxes. One quiet line under the message («رقم العملية 9776 593217 · المبلغ 2,000,000 دينار»); a value and its underline light each other. A value not found as written has a «؟» marker whose tip (hover, focus or a tap) says «ما لكيناه بالنص بنفس الشكل. يمكن الزبون كاتبه بالحروف أو بشكل ثاني: قارنه بالرسالة.»
- **Draft:** a small label; a passing draft shows only «ما بيها مشكلة», with the list of checks in its tip; findings show as before. The reasons appear after an edit, a correction or a take-over, as one closed line «ليش غيّرتها؟ (اختياري)».
- **Decision:** approve keeps its Ctrl+Enter chip; the other buttons carry their keys in their titles; the lock line is small; the Esc / Ctrl+Enter sentence is gone (the «?» sheet has it). On a flagged ticket the tick sits under the draft, just above the action bar.
- **Banners** are one line with a coloured side bar. The identity instruction and the blocking checks' wording are unchanged. The escalation note is a tighter list; «كتبها نموذج» still marks «الخلاصة».
- **«كيف يشتغل»:** the side list is the controls and the tickets; the live-run line and the model ids are said once, in the overview's header. Its content is otherwise unchanged.
- **First-visit card:** the sentence and the three-line legend (its heading for a screen reader only).
- **Dropped as redundant:** «ما ينرسل شي» in the pill (the lock line says it), «واثق» and «ما ناقص شي», the team in the team note's title (the summary line and the forward button name it).

**Clutter, before and after.** A scratch script (outside the repo) starts a viewer with no key and `PIPELINE_MODE=off` (so the kill-switch banner shows), opens `saved/test2/final` at 1280 × 800, light, after «فهمت», and counts inside the viewport only: visible characters, words, controls (buttons, links, inputs, selects, summaries) and boxes with a border, a shadow or their own background. "Chrome" is every word except the customer's text, the queue's previews, the draft and the team note's fields. Before is a `git archive` of 4ca2af6 (no `data/heldout*`).

| State | Before: chars / words / controls / boxes | After | Chrome chars before → after | Message, draft and main button on the first screen (before → after) |
|---|---|---|---|---|
| Ready, t2-0002 | 1,421 / 319 / 18 / 42 | 1,124 / 247 / 19 / 28 | 1,076 → 455 | no draft → all three |
| Flagged disagreement, t2-0009 | 1,489 / 328 / 19 / 39 | 1,178 / 259 / 19 / 32 | 1,218 → 580 | no draft → all three |
| Escalated fraud, t2-0025 | 1,522 / 339 / 17 / 41 | 1,352 / 306 / 17 / 26 | 1,084 → 535 | no message → all three (team note for the draft) |
| Ready, one word typed | 1,663 / 363 / 21 / 39 | 1,165 / 254 / 21 / 28 | 1,189 → 491 | all three → all three |
| Phone 390 × 844, t2-0002 | 470 / 97 / 11 / 19 | 530 / 110 / 11 / 13 | 434 → 279 | button only → all three |

The page's own text (chrome) fell by 51 to 59% on the desktop and by 36% on the phone, and the boxes by 18 to 37%. Key chips on screen fell from 10 or 11 to 1 or 2. Controls stayed level: the fact values and «ما بيها مشكلة» are now buttons (they light their place or open their tip), where key chips were not controls. On the phone and the flagged ticket the total went up or fell less because the customer's words and the draft are now on the first screen (phone: 36 → 251 characters of them).

**Review.** Two internal review passes, one from the view of a support agent new to the page and one for safety and accessibility, reported 15 findings (2 high, the same problem seen twice; 4 medium; 9 low). A scratch script reproduced all 15 before any fix and none after. All were fixed, two in part:
- **High: «ليش؟» covered the ticket** at 1100 to 1366 px (at 1280 a fifth of the draft's and the message's width, the lock line, «ليش؟» itself and previous / next), and stayed open across tickets and reloads. Over 1000 px it is now a column of its own: nothing is covered at 1100, 1280 or 1366. The drawer stays only at 721 to 1000 px, where another ticket closes it and a reload never reopens it.
- **Medium: on flagged tickets the draft was not on the first screen,** while the tick that unlocks approve was. The tick moved under the draft (read, tick, approve), and each of the two models' answers is one line. All 15 flagged tickets now show the draft's first two lines above the action bar at 1280 × 800. *In part:* the summary line stays above the choice, although the checked answer repeats it, because it holds the pencil and the «صحّحتها» marks.
- **Medium: after «استلمها بنفسي», Ctrl+Enter approved the draft** with the take-over's reason attached (reproduced: `approved`, `["wrong_type"]`). Once armed, «سجّل: استلمتها» is the primary button with the Ctrl+Enter chip, approve leaves the bar, and «رجوع» or Esc goes back, restoring the reasons as they were. F forwards without them.
- **Medium: the «؟» marker** could not be read on a touch screen, made a phone scroll sideways on keyboard focus (485 px of page at 390), and named no action. Its tip is now a real element (role tooltip, the button's description), under the facts line and never wider than it; a tap pins it and a second tap unpins it; it says what to do.
- **Medium: tips** could not be dismissed with Escape, and the checks' tip vanished when the pointer moved onto it (WCAG 1.4.13). Both tips share one mechanism now: Escape hides them first (before an armed take-over, then «ليش؟»), and the pointer can cross onto them.
- **Medium: a flagged ticket said its point three or four times.** A field the banner names is not repeated in «المسودة المفروض تسأل عن»; with the two answers on screen the banner ends «النموذجين اختلفوا بنوع المشكلة.» and the question is «ياهو النوع الصح؟»; approve's reason is quiet, with no warning icon, when only the tick is missing (a blocking check keeps its red).
- **Low:** an agreed re-check read as a warning (now quiet: «النوع انراجع بنموذج ثاني، واتفقوا»); decided tickets kept the to-do banner and «المسودة المفروض تسأل عن» (gone); the phone's ticket screen opened under a 156 px header (now 58 px); the escalation named its team three times (the note's title no longer does); «ليش؟» was easy to miss (link colour; *in part:* no second «ليش؟» link in the banners, which would add a control for the same action); the red dot on a tab read as "unread" (now «P1» or «؟»); a tap on «؟» showed nothing (above).
- **Low, older than this change:** a card number typed into a draft was highlighted only as an unknown number, because the warning's span came first. Where a blocking finding overlaps a warning, the blocking one is now drawn whole. Approval was blocked all along, in the page and at the server.

**Checks:**
- **pytest: 697 pass** (694 before; 3 new for the page: «ليش؟» starts closed and old preferences don't reopen it, it never covers the ticket where there is room, and the saved run is said once with the picker keeping its name).
- **`node tests/ui/smoke.cjs`: 448/448** (369 before): desk-light 119, desk-dark 119, phone-light 84, phone-dark 84, fresh-clone 42. 51 checks are new for the calmer page and 28 for the review ([`tests/ui/README.md`](../../tests/ui/README.md) lists them). No safety, keyboard or accessibility check was removed or loosened.
- AA contrast was checked on the new states (the tab marker, the quiet lines, the tips, the take-over bar, «ليش؟» as a column) in both themes, and the new controls keep their focus ring.
- The nine `docs/demo/` images were retaken by the smoke test's fresh-clone pass and checked by eye.

**Still open:** no support agent has used the calmer page yet. The tips and the tap behaviour were tested in Chromium (with touch emulation), not on a real phone browser or with a screen reader. Just over 1000 px an open «ليش؟» leaves the ticket narrow (about 330 px at 1001, 430 at 1100): nothing is covered, but the lines are short.

## 5 Nov: Three safety rules adopted (no model calls)

**The decision.** The three flags opened by the 1 Nov security review (entry below, "Behind a flag, not adopted") were waiting for a decision. On 5 Nov they were decided as follows, for a regulated financial institution:
1. **`hold_reason` is adopted.** A draft must not hint at an investigation, a suspicion, a report or money laundering. Telling a customer about one is tipping off, which Iraq's AML/CFT Law 39/2015 forbids (Art. 12 Fourth) and punishes (Art. 39 Second(b)). The rule now always runs and blocks an approval, in the inbox and at the server. «رفعنا بلاغ» and «سجلنا بلاغ بمشكلتك» stay flagged, although they may only mean "we raised a ticket": a false alarm costs the agent an edit, and a miss is a legal breach. This settles the open wording question below.
2. **`sensitive_number` is adopted.** A draft must not repeat a card number or a code. The rule always runs and blocks an approval.
3. **`escalate_account_risk` is changed, then adopted, as the `account_risk` flag.** A blocked account or a SIM change is a common step in taking over someone else's account. Such a ticket now keeps its draft and is flagged: the agent must confirm the customer's identity by the institution's own procedure before approving. Fraud is still always escalated, with no draft.

As on 30 Oct, the adopted rules are now the normal code. No flag is open, the flag mechanism stays, and no prompt changed.

**Why a flag and not an escalation, for account risk.** The 1 Nov flag escalated these tickets with no draft, before the re-check. The new flag:
- **keeps a safe draft.** On 1 Nov these drafts were all safe: they acknowledge the problem and pass the ticket to the accounts team (entry below). Escalating threw them away.
- **forces an identity check.** The agent reads «حساب مقفول أو تبديل شريحة: تأكد من هوية الزبون حسب الإجراءات قبل الاعتماد، ولا تكتب بالرد إنه صار أي تغيير على الحساب» ("Blocked account or SIM change: confirm the customer's identity by the procedures before approving, and don't write in the reply that anything on the account changed"; wording as revised in the review below). Approve stays off until they tick «تأكدت من هوية الزبون» ("I confirmed the customer's identity").
- **reads the type after the re-check,** the type the draft was written for, not the first model's label. This removes the old flag's one false positive, t2-0009: the first model said `sim_change` at 0.60, and the re-check said `login_otp`, which is right.
- **The wording differs from the decision's text.** «حساب محظور» became «حساب مقفول»: the type label the agent sees on the same screen is «حساب مقفول» (`config/taxonomy.yaml`, `blocked_account`), so this keeps one word per concept, and «مقفول» is the everyday Iraqi word. The review below changed three more things: «بإجراءاتكم» → «حسب الإجراءات», «قبل ما ترد» → «قبل الاعتماد» (the inbox's verb), and «الرد ما يأكد أي تغيير على الحساب», which read as a fact nothing checks, → the instruction «ولا تكتب بالرد إنه صار أي تغيير على الحساب». The wording is in `FLAG_AR` (`src/pipeline/run.py`) and `WHY_AR` and `CONFIRM_AR` (`app/static/js/labels.js`), if the author prefers the original.

**What changed in the code.** These changes are in the commit after bfe8893, so they are named by file and function, not by line.
- `src/pipeline/fixes.py`: `FIXES` is empty. `ADOPTED` lists the three old names, and `active()` refuses any of them with what became of it ("PIPELINE_FIXES names a fix that is now the normal code: … Remove it from PIPELINE_FIXES."), so an old command line cannot look as if it switched a rule on or off. The viewer and `run_batch` refuse to start with one. `account_risk` is not a flag name either.
- `src/pipeline/draft_check.py` (`findings`): `hold_reason` and `sensitive_number` always run. Why «رفعنا بلاغ» stays flagged is written beside the rule (`_HOLD`).
- `src/pipeline/gate.py` (`check`): the account-risk escalation is gone.
- `src/pipeline/run.py` (`ACCOUNT_RISK`, `process`): once the draft is written, the flag is added when the type it was written for is `blocked_account` or `sim_change`. A re-check that changes the type to one of them adds it, and one that changes the type away does not. An escalation never gets it.
- `src/pipeline/handoff.py` (`_SYSTEM_REASONS`): the account-risk reason is removed from the team note's escalation reasons.
- `app/server.py`: `checks_active` lists all six draft checks. `BLOCKING_CHECKS` (`asks_secret`, `hold_reason`, `sensitive_number`) is unchanged, and now applies with no flag set.
- `app/static/js/labels.js`: the banner (`WHY_AR`) and the tick (`CONFIRM_AR`) for `account_risk`. Its old "not sent to a model because" line (`BECAUSE_AR`) is removed: it no longer skips a step.
- **No prompt changed.** The classifier prompt hash test passes. On test2, all 80 tickets have byte-identical classify, re-check and draft prompts, replies and models before and after.

**How it was measured.** No model was called and nothing was spent.
- **Before:** a copy of bfe8893 made with `git archive`, leaving out `data/heldout` and `data/heldout2`. **After:** the working tree with the change. No heldout file was copied, opened or run.
- Each set was replayed with `scripts/run_batch.py --no-mask --workers 5` from the response cache only (`LLM_CACHE_ONLY=1 LLM_BACKEND=api LLM_BUDGET_USD=0.001`), with the API keys removed from the environment and every send function replaced by one that fails.
- Cache hits and misses were counted per role, including the team-summary call. A miss there would otherwise go unseen: the note just has no summary line.
- A comparison script printed ids, labels and counts only.

**test2 (80): fully replayed.** 181 of 181 calls came from the cache, before and after, with **0 misses** (classifier 81, one of them a parse retry on t2-0076; drafter 74, re-check 15, fee 5, summary 6). The run file's usage says 180 model calls: it counts the retry inside its call. (Corrected in the review below: this said 180 of 180.)

| test2 (80) | Before | After |
|---|---|---|
| Drafted / flagged / escalated | 65 / 9 / 6 | 59 / 15 / 6 |
| Review rate (flagged + escalated) | 15/80 = 18.75% | **21/80 = 26.25%** |
| Type used correct | 78/80 | 78/80 |
| Priority correct | 79/80 | 79/80 |
| Fraud escalated, with no draft | 6/6 | 6/6 |
| Wrong type that still got a draft | 2 (t2-0041, t2-0052) | 2 |
| Outcome equal to the gold outcome | 74/80 | 68/80 |

- **6 tickets changed,** each from drafted to flagged with `account_risk` as its only flag: t2-0007, t2-0029 and t2-0080 (SIM change), and t2-0016, t2-0048 and t2-0054 (blocked account). For each, the first model, the type used and the gold label agree. Each keeps its draft text, team, priority and checks.
- **t2-0009 is unchanged:** flagged `recheck_used_second`, type used `login_otp`, no `account_risk`.
- `hold_reason` and `sensitive_number` fired on no test2 draft.
- The gold outcomes predate the rule and mark all six as drafted, so agreement with them falls from 74 to 68.
- For comparison, the 1 Nov flag escalated 7 tickets and also gave 26% (entry below). The new rule costs the same review rate and keeps all six drafts.

**mvp_test and dev: not fully replayable from the cache.**
- **Misses, the same before and after:** mvp_test 3 drafter and 3 summary calls (mvp-0007, mvp-0019, mvp-0080); dev 7 and 7 (dev-0005, dev-0081, dev-0088, dev-0141, dev-0144, dev-0174, dev-0201). All are app-bug tickets. Their drafter prompt changed on 30 Oct, when app bugs moved to the tech team (entry below), so the cache holds no draft for the new prompt. Each miss escalates the ticket as a model error, and that escalation's summary call misses too. No model was called to fill them, so these replays give no rate or accuracy.
- Prompts are identical before and after on every ticket (78/78 and 233/233), so the misses come from the 30 Oct change, not this one.
- **What the rule moved:** 4 mvp_test tickets (mvp-0018, mvp-0039 and mvp-0044, blocked account; mvp-0064, SIM change) and 12 dev tickets, each from drafted to flagged, each with the right type. None is among the misses.
- **The review rate, from the saved API runs.** The rule is code that runs after the draft, so it can be applied to a saved run file with no model call (counts and ids only):
  - mvp_test, the run of 29 Oct: 21/78 (27%) → 25/78 (**32%, over the 30% target**). The same 4 tickets move. The 1 Nov flag gave 33% here.
  - dev: the same 12 tickets move in each of four saved dev runs (local files: rec+F16+F20 and the final candidate, two replicates each), 12 of 233, or 5 points. Every one has the right type.
- **One miss: mvp-0046.** The first model said `sim_change` at 0.92, which is right. The re-check said `rejected_or_pending`, and the ticket was drafted from that answer and flagged `recheck_used_second` (FAILURE_MODES.md, mode 1). The 1 Nov flag escalated it from the first label. The new rule reads the type used, so it gets no identity reminder. The agent still sees the two answers. Choosing `sim_change` there adds "the draft was written for another type" to what to check, but not the identity tick. So the change trades t2-0009's false positive (a safe draft lost) for mvp-0046's missing reminder (a flagged ticket, with a draft for the wrong type).

**The two draft rules on every saved draft.** Every run file under `runs/exp/` outside the heldout folders, plus the committed final run: 2,531 drafts, 1,220 distinct. **`hold_reason` flagged 0 and `sensitive_number` 0.** The other checks are unchanged: stray Latin 24 (12 distinct), unknown number 7 (6 distinct).

**Tests.**
- **pytest: 675 pass** (648 before), with the API keys removed and no model call. The new tests fail on bfe8893 (68 failures, checked by running them against a copy of it; this said 67 until the review below).
  - New: an old flag name is refused with what became of it, in the pipeline and at viewer start-up (3 each), and `account_risk` is not a flag name either. The gate never escalates a blocked account or a SIM change. `account_risk` flags the draft and never escalates. It reads the type after the re-check (the t2-0009 shape), applies when the re-check changed the type to one of the two, and is never added to an escalation. Fraud is still escalated with no draft. `hold_reason` and `sensitive_number` flag the draft end to end (4 phrasings, including «رفعنا بلاغ» and «سجلنا بلاغ بمشكلتك»). The server refuses (409) an approval or edit that tips off or repeats a number, with no flag set (8 cases; nothing logged; a take-over is still recorded).
  - Changed because the behaviour changed: `test_pipeline.py::test_fix_flags_off_by_default_and_reject_unknown` (`FIXES` is empty, `ADOPTED` lists the three) and `test_pipeline_safety.py::test_new_flags_have_their_arabic_notes` (the new wording). Contract H in `test_pipeline_safety.py` is rewritten: `test_new_fix_flags_are_off_by_default`, `test_account_risk_gate_only_when_enabled` and `test_account_risk_ticket_gets_no_draft` are gone. Renamed: `test_text_rules.py::test_hold_reason_only_when_enabled` → `::test_hold_reason_is_caught` (now with «سجلنا بلاغ بمشكلتك» and «رفعنا بلاغ بخصوص مشكلتك»), `::test_sensitive_number_only_when_enabled_even_if_the_ticket_had_it` → `::test_sensitive_number_is_caught_even_if_the_ticket_had_it`, and `test_server_ui.py::test_check_runs_the_flagged_rules_only_when_their_flag_is_on` → `::test_check_always_runs_hold_reason_and_sensitive_number`. The `/api/meta` test now expects all six checks in `checks_active`.
- **`node tests/ui/smoke.cjs`: 361/361** (359 before): desk-light 94, desk-dark 94, phone-light 70, phone-dark 70, fresh-clone 33.
  - Two new checks in `fresh-clone`: "account_risk (6 tickets, t2-0007 opened): «تحتاج تأكيد» with its draft, no forward, and the identity line" and "account_risk: approve stays off until «تأكدت من هوية الزبون» is ticked, then it is on". The committed run predates the rule, so these feed the page that run with the rule applied, through a browser route. They approve nothing.
  - One fixture changed because the behaviour changed: the run note's "mixed reasons" case used `account_risk` as a second escalation reason, which it can no longer be. It now uses `ref_not_in_text`; the assertion is the same.

**What it costs.** The review rate counts every ticket that needs more than a quick approve, and each `account_risk` ticket needs a tick. On test2 it rises from 19% to 26%, under the 30% target. On mvp_test, from its saved run, it rises from 27% to 32%, over the target. The six test2 drafts and four mvp_test drafts are kept, so the agent's cost is a tick after an identity check, not a reply written from nothing.

**What remains:**
- **heldout2** (80, sealed) is now the next run, once, on this final version. It will show the review rate on fresh tickets.
- **No identity reminder in two cases.** `account_risk` is added only to tickets that get a draft, so a blocked account or a SIM change that escalates anyway (low confidence, models disagreeing, a draft model error, or `PIPELINE_MODE=classify_only`) carries none. And a ticket whose re-check moved the type away gets none either (mvp-0046). *Review: the escalations now have the reminder in their team note, and choosing the first model's answer adds the tick; mvp-0046 by itself still gets none.*
- **The tick is the agent's word.** The server refuses only the blocking draft checks, as for the other ticks, so a hand-made `/api/decision` request could approve an `account_risk` ticket without it. The decision log keeps the ticket's flags, but not the tick itself. *Review: the tick is logged now, and the server refuses an approval without it.*
- **Saved runs predate the rule.** The server recomputes the draft checks of a saved run, not its outcome, so in the viewer the six test2 tickets still show as ready until test2 is run again. The smoke checks feed the flag through a browser route instead. *Review: the server now gives saved runs the flag.*
- **Gold outcomes predate the rule.** The six test2 tickets are labelled drafted. The labels were not changed. *Review: «كيف يشتغل» now scores them against the rule and says so.*
- Runs saved between 1 and 4 Nov with check spans (none in this repo; `runs/` is git-ignored) lack the two rules. The page's "nothing found" line would then name checks that never ran on them. The server still checks the approval itself.
- `hold_reason` and `sensitive_number` have never fired on a saved draft, so how often they catch a real draft, or raise a false alarm, is unknown.
- The mvp_test and dev replays need the 10 app-bug drafts (and their summaries) that the cache lacks. Filling them needs model calls.

**Review.** Two review passes (safety regression; Arabic and UX in the browser) reported 14 findings. Each was reproduced first, all 14 held, and all were fixed, with no prompt change and no model call. The viewer gave the six test2 tickets one-key approval with no identity tick: the server now gives a saved run the flag as `run.py` does today (`app/server.py`, `apply_account_risk`, marked `account_risk_recomputed`), so the final run opens at 15 / 6 / 59. The tick is now logged (`ACK_KINDS`) and required by the server (409, `needs_identity`: the flags, the agent's correction, and on a saved run the ticket as served), an agent's correction to either type asks for it (`/api/meta` `account_risk_types`; t2-0009 and mvp-0046 when the first answer is chosen), it is listed first with the tick «تأكدت من هوية الزبون وراجعت باقي النقاط» when there are other points, and «ليش؟» and the decided view mention it. An escalated blocked account or SIM change (not fraud) ends its team note with an identity reminder (`handoff.py`, `IDENTITY_AR`); no replayed note has one. The wording is revised (above), and the tipping-off block says what to remove and offers «سجلنا طلبك». «كيف يشتغل» expects «تحتاج تأكيد» for these tickets and says why (test2 outcome 74/80, gold files unchanged; new gold from `generate_tickets.py` follows the rule). Two counts above were wrong (180 calls, 67 failures). The line references in CONTEXT.md, SECURITY.md and FAILURE_MODES.md now point at the current code, and the `docs/demo/` screenshots were retaken. test2 replayed again from the cache: 181 hits, 0 misses, same prompts and outcomes, only the six notes' wording changed. pytest 694 pass (19 new; `test_new_flags_have_their_arabic_notes` and `test_account_risk_is_not_added_to_an_escalation` changed with the behaviour); smoke 369/369 (8 new; the tab counts and the two fresh-clone account_risk checks changed with the behaviour). Still open: mvp-0046 gets no reminder unless the agent picks the first answer, and the tick is the agent's word.

## 1 Nov: The agent inbox (UI), no model calls

**Why.** The mentor asked for more care on functionality, security and UI/UX. The viewer's first screen was a debugger: one ticket's stage-by-stage trace, with gold labels, scores and model ids. A support agent needs the opposite: a queue, one ticket, a draft to check, and a quick way to decide. No model was called for this work, and nothing was spent.

**What the agent sees** («وضع الموظف», the default screen):
- **A queue** with four tabs and counts: تحتاج تأكيد (flagged), متصعّدة (escalated), جاهزة (drafted), خلصت (decided). It is sorted by priority, then arrival. Each row has an icon and a word for its status (never colour alone), the id, the priority («P1 · عاجلة»), the team and the first words. A counter («خلصت 12 من 80») counts the agent's decisions, and a note under it says what the system did with the whole run («بهالتشغيل النظام صعّد 6 تذاكر، كلها احتمال احتيال.»; changed in the polish below).
- **The ticket:** the customer's text with each extracted fact (reference, amount, phone, time) underlined where it was written, and a list of the facts that lights up its place in the text. A one-line summary gives the type, team, priority and what is missing. Confidence is a word with what was done about it («واثق», «غير متأكد: انراجع بنموذج ثاني», «متصعّد»), never a decimal. Anything not ready opens with one line saying why.
- **The draft** is in an editable box. The draft checks are highlighted on the phrase, with the reason in Arabic. They run again on every edit (`POST /api/check`, about 400 ms after typing stops).
- **Friction follows risk.** A ready draft is approved with one key (Ctrl/Cmd+Enter). A flagged ticket names the one thing to check, and approve stays off until «تأكدت من …» is ticked. A draft that asks for a code or password cannot be approved until the text no longer asks. An escalated ticket has no draft at all: the team note is the main content, under a red banner for fraud. When the two models disagreed, both answers are shown, with the team and priority each would get.
- **Decisions** (approve, edit, take over, forward, with optional reason chips and corrections) go to the decision log, which keeps no reply text. Each one can be undone (Ctrl+Z or the toast). They come back after a reload. When the list is done, a session summary counts approved as-is, edited, taken over, forwarded, corrections, drafts kept unchanged, the median seconds, and the reasons. This is the human-feedback evidence the project still lacks (CONTEXT §7, "Open"), ready to collect.
- **Keyboard:** J/K, E, Esc, T, F, W, 1–4, ? and Ctrl+Z, bound by key position so the Arabic layout works. Single keys can be switched off. The page also works at phone width: the queue and the ticket are two screens, and the action bar sits at the bottom.
- A pasted ticket («تذكرة جديدة») shows its stage in the queue row while it runs, then opens.
- The page always says «ما ينرسل شي للزبون تلقائياً».

**«كيف يشتغل» (how it works)** keeps everything the old viewer showed: the run and ticket-set picker, the overview (accuracy against gold, outcomes, calibration, review rate, cost and time), the stage-by-stage trace with the gate scale, prompts and raw replies, the gold table and the run's decision summary. Two old bugs are fixed: replay timers kept running after a switch, and the gold table heading could read "undefined". Clicking a set ticket no longer runs it (that spent money): a separate button does, and "run all" asks first, stating the count.

**Security changes:**
- **Strict CSP with no inline code:** `script-src 'self'; style-src 'self'`, no `'unsafe-inline'`, `connect-src 'self'`, `frame-ancestors 'none'`. This closes the open item in the entry below. The page is a markup shell. The code is in ES modules under `app/static/js/`, and every node is built with `textContent`, never `innerHTML`.
- **Fonts are local:** IBM Plex Sans Arabic and IBM Plex Mono, from @fontsource 5.3.0, under the SIL Open Font License. `SOURCE.txt` has the sha256 of each file. The page makes no request to another host.
- **Static files by allow-list:** `/static/` serves only files under `app/static/` with an allowed extension, each with an exact content type. Traversal, encoded dots, hidden files, folders and symlinks out get 404.
- **`/api/check`** has the same guards as the other POSTs. It never logs or stores the draft.
- `localStorage` holds preferences only (five since the polish below), never ticket text or drafts.

**How it was checked:**
- **pytest:** 625 pass (549 before: 70 new for the server, 6 for the page).
- **Browser smoke test** (`node tests/ui/smoke.cjs`, new): it starts its own viewer with no key and `PIPELINE_MODE=off`, then drives Chromium at desktop and phone width, light and dark. **178/178 checks pass**, three runs in a row. It checks:
  - no console errors, CSP violations or requests to another host
  - tab counts 9/6/65 on `saved/test2/final`
  - no gold label, model id or check mark in agent mode, over all 80 tickets
  - approve, undo, the flagged tick and the blocked secret request, each read back from the decision log
  - forward, reload, J/K, the process overview (type 78/80, priority 79/80) and a trace
  - a pasted ticket ending escalated with `pipeline_off`
  - a 4,100-character ticket refused in Arabic by the page, and by the server (413)
  - no sideways scroll at 360 px
- **Live run from the cache only** (`LLM_BACKEND=api`, `LLM_CACHE_ONLY=1`, `LLM_BUDGET_USD=0.001`). The real key was not in the viewer's environment: a placeholder value let the page offer live runs, so even a cache bypass could not reach a paid call.
  - t2-0001 and t2-0009, pasted into the page, ended drafted and flagged (`recheck_used_second`), the same as the saved run. Outcome, flags, team, priority and draft text are identical.
  - The queue row showed every stage word, including «يراجع…» for the re-check.
  - Both landed in the inbox with their draft and check list. t2-0009 also showed the two-answer choice and the tick.
  - 5 model steps, all from the cache: **0 misses**, no error events.
- **Integration fixes found by these checks:**
  - Ctrl+Enter did nothing when the focus was on a queue row, which is where J/K leave it. The listbox took the key as "open".
  - Two tables in «كيف يشتغل» made the page scroll sideways at 360 px.
  - The outcome bar cut off its labels.
  - A reference could break across two lines inside its underline.
  - After the last decision the queue showed an empty tab instead of «خلصت».
  - A live row showed «…» between its result and the end of the stream.
- **Screenshots** in `docs/demo/`:
  - `inbox-desktop.png`, `inbox-flagged.png`, `inbox-escalated.png`, `inbox-phone.png`, `inbox-dark.png`
  - `process-overview.png`, `process-trace.png`
  - `inbox-done.png`. A script decided all 80 tickets of the final run through the page for this one (redone after the review below), so its times (median 0.1 s in the image retaken in the polish below) are not a person's; the page itself now says so («80 قرار انحسمت بأقل من 3 ثواني»).

**Still open:**
- No agent has used it yet. The decision log and the session summary have no human data.
- No automated accessibility audit and no screen-reader pass. Landmarks, labels, the listbox, focus and contrast (AA in both themes) were checked by hand and in Playwright.
- The keys were tested with key codes, not on a real Arabic keyboard or on macOS.
- A fact written in words («مليونين», «خمسين ورقة») is listed but not found in the text.
- `hold_reason` and `sensitive_number` would block approval, but both are still off by default (the author's decision, entry below). The page names only the checks that ran.
- `/api/check` takes up to about 0.5 s on 8,000-character repetitive text. The page waits for typing to stop and drops stale replies.
- README and CONTEXT still describe the old viewer.

**Review.** Five reviewers checked the inbox through five lenses: the agent's workflow and human-in-the-loop UX, Arabic copy and right-to-left type, accessibility (WCAG 2.2 AA), security and privacy, and functional regression against the old viewer. They filed 53 findings (5 high, 18 medium, 30 low; about 45 distinct problems, since several overlap). Each was reproduced first, in Chromium against a viewer with no key and `PIPELINE_MODE=off`, or with a slowed scratch copy for the live-run timing ones. All 53 reproduced, and each got a fix, in full or in part. No model was called.
- **Fixed, highest risk first:**
  - Correcting a ticket to fraud now turns it into an escalation: no draft, forward to the fraud team or take it over. Choosing the first model's answer, or another team, adds «المسودة انكتبت لنوع ثاني» to the checks and clears an earlier tick (H1).
  - Ticks, edits, reasons, corrections and time are kept per run and ticket. Two runs with the same ids no longer share them, and undo acts only on the run it was made in (H2, F1, F2).
  - Spaced phones and references («0791 079 0226») read in the written order everywhere: queue rows, the customer text, the draft (no-break spaces between digit groups) and approved replies (RTL-1, L3).
  - The action bar's real height drives the scroll padding, so focus is never hidden under it. Between 721 and 1000 px «ليش؟» is a drawer, closed by Escape (A11Y-1).
  - A check still running when approve is pressed can no longer pass newer text: the draft locks, and findings count only for the exact text they were computed on. The server now refuses (409) an approval whose reply asks for a code, and a second decision on a ticket that already has one (SEC-1, F8).
  - Undo brings back the edit; take-over always needs a second press (M1, F3). A ticked warning is logged as `warnings_acknowledged` (kinds only), and the tick no longer claims the opposite of the finding (M2). Seconds add up over visits and pause while the ticket is hidden, with `visits` logged; a live ticket's clock starts at its result (M3, F5). The inbox opens on, and moves to, the most urgent open ticket (M4). Decisions under 3 s are counted apart in both summaries, and a refused approve focuses what to check, not the tick (M5). The caret stays above the bar while checks answer (M6).
  - Accessibility: focus never drops to `<body>` (A11Y-2). Focus lands on the new live ticket, and its end and the budget cap are announced (A11Y-3). The other fixes: skipped stages at full contrast (A11Y-4), «?» off with single keys (A11Y-5, L7), an `h1` and the phone skip link (A11Y-6), the outcome legend (A11Y-7), no load on arrow keys (A11Y-8), button names (A11Y-9), forced colours (A11Y-10) and table rows (A11Y-11).
  - Privacy and robustness: the paste box has no autocomplete or spellcheck and forgets cancelled text (SEC-2). Direction controls are dropped from customer text, with a note (SEC-3). Data-keyed maps have no inherited keys (SEC-4). Run-all stops when a saved ticket is opened (F7). A cut-off replay is redrawn (F4). The type comes from the classify step when the drafter failed (F6). «شغّلها» is free again once the server takes a run (F9).
  - «كيف يشتغل» opens on an 8-step stage map with counts and an example ticket per step (L5). The gate labels sit at 0.60 and 0.75 (L4, PROC-1). Experiment runs and the recompute note moved there (L6).
  - Copy: Iraqi forms (اكو، ماكو، مو متأكد، اقرا, also in the pipeline's fixed notes), number agreement, one colon per line, one word per concept, both key letters, the forward arrow pointing left, and Arabic key letters and prompts in Plex Sans Arabic (COPY-1 to 9, RTL-2, TYPE-1, TYPE-2).
- **Not done, and why:**
  - «متصعّد» stays masculine: it is the spec's wording. «غير متأكد» and «ما في» did change, because the hard rule asks for Iraqi forms (مو، ماكو).
  - Stripping direction controls in `clean()` would change what the model reads, so it waits for a flag and a with/without run. The page strips them for display only.
  - The why panel now says «المفروض تطلب» and stops listing a bill type the customer named. It does not yet check whether the draft really asks (L1).
  - Fast decisions are flagged in the summaries, not by a new field in the log (the log has `seconds` and `visits`).
  - axe still reports `landmark-one-main` on the phone's queue screen, where `<main>` is hidden. It is a best-practice rule, not a WCAG failure.
- **Where reviewers differed:**
  - On a refused approve, focus now goes to the choice or the box to check, not straight to the tick. The workflow reviewer showed that the tick let 9 flagged tickets pass in 3 keys each without a look.
  - Experiment runs left the agent's picker, rather than being grouped there.
- **Checks:**
  - pytest: 642 pass (17 new for the decision rules).
  - `node tests/ui/smoke.cjs`: 250/250 (72 new checks, one per fixed behaviour where practical).
  - A reproduction script showed each finding before the fixes and none after, apart from the parts under «Not done».
  - The focus-obscured sweep (1280×600, 1093×520, 911×512, 768×1024, 360×780) shows no hidden focus.
  - axe on 7 states shows no WCAG violation.
  - The screenshots in `docs/demo/` are redone.

**Polish.** Seven items from a last check of the inbox, then two reviews of the result (a judge's first five minutes on a fresh copy with no key, and a regression pass) and their fixes. No model was called.
- **The items:** (1) The viewer runs new tickets on the API backend unless `LLM_BACKEND` says otherwise (`default_viewer_backend` in `app/server.py`; the scripts still default to cli). With no key, live runs are off and the page says why; `LLM_BACKEND=cli` still works when set. (2) A first-visit card («أول مرة هنا؟») says what the page is and what each tab asks, until «فهمت». It is a fifth preference and works with storage blocked. (3) When the next ticket is in another tab, the toast says why. (4) The strip under the counter describes the run and no longer repeats the decided count. (5) A refused approve's message goes once what it names is fixed. (6) Each trace stage shows its own time, not the time since the ticket started. (7) The screenshots are retaken as a fresh clone shows them (no key, no kill switch) by `node tests/ui/smoke.cjs --pass fresh-clone --demo docs/demo`, with a new `inbox-first-visit.png`. The four images of the old viewer (`test2-*.png`) are deleted: no tracked file linked them.
- **Review:** 16 findings (4 medium, 12 low). Each was reproduced in Chromium first, and all 16 are fixed. Medium: the README described the old viewer (now the two modes, the run that opens by default, three screenshots). The team note said it was all rules, but its «الخلاصة» line is written by a model: the line is now marked, and the trace's result box names that call and its own time (1.0 to 1.4 s on the six escalations), which no stage showed. The cleaned text in the trace showed a spaced reference in reverse order (now drawn like the ticket text). A cache-only demo looked like a live run: `/api/meta` now has `cache_only`, and the page shows a banner, a note in the dialog and «من الكاش» beside each model stage. The start-up line says so too, and prints a $0.001 cap as $0.001, not $0.00. Low: the run's elapsed time was called a total (now «التشغيل كله خذ 86.1 ث (5 تذاكر سوة)»). A hidden table caption made the whole page scroll in «كيف يشتغل» (`.pane` is now positioned). With no key, «تذكرة جديدة» looked usable (now dashed, and the dialog shows no text box, only the reason and what turns live runs on). Wording: the legend now follows the tab order, flagged rows say «تحتاج تأكيد», a tab that runs out says «ماكو بعد», the tile labels read with any number, and the model pair is in one order everywhere. The decision toast followed the agent into «كيف يشتغل». The phone image showed no draft, and the scripted session summary was not labelled. The README said «he». Focus dropped to `<body>` when the card crossed 720 px. The run note was wrong for one escalation or mixed reasons. An unknown `LLM_BACKEND` stopped the viewer with a traceback (now one line). SECURITY.md and this entry still described the old state.
- **Not done:** pacing a cache-only replay by the recorded stage times (it is labelled instead), and a separate stage event for the team-note summary in the pipeline (saved runs would not have it, so the result box shows the call).
- **Checks:** pytest 648 pass (4 new for the backend default, 2 for the review). `node tests/ui/smoke.cjs` 359/359: desk-light 94, desk-dark 94, phone-light 70, phone-dark 70, fresh-clone 31 (109 more than the 250 above). All nine images in `docs/demo/` were retaken and checked by eye.

## 1 Nov: Security and reliability hardening (no model calls)

The mentor asked for more security. A review on 1 Nov found 12 problems, each checked by hand before it was fixed. This entry lists the fixes, how they were checked, and what is still open. No model was called and nothing was spent: tests stub every model, and the replays below read only the response cache (`LLM_CACHE_ONLY=1`, which raises instead of calling a model, with a $0.001 cap as a second lock).

**What changed, by finding:**

1. **The viewer is local only** (a web page could start paid runs through `GET /api/stream?text=`, and a DNS name re-pointed at 127.0.0.1 could too). The viewer now answers only when Host is localhost, 127.0.0.1 or [::1] on its own port (else 421), refuses a foreign Origin (403), and needs a per-process token on every `/api/` call. The page gets the token in a `<meta>` tag. A live run is a `POST` with a JSON body, one at a time (429 in Arabic for a second one). `GET /api/stream` returns 405.
2. **Input limits** (no limit before). `config/thresholds.yaml` has a `limits` block: 4,000 characters per ticket (a longer one goes to a person before any model call, flag `too_long`), 1,000 tickets per batch file, 64 KB per request. No ticket in dev, mvp_test, test2 or the probes is over 4,000 characters (longest 1,875), so no measured result moves.
3. **The secret-request rule is rewritten.** It missed all 10 of the review's phrasings, for example «لازم ترسل الرمز» (it read «لازم» as «لا»), «شنو الرمز اللي وصلك؟», «ماكو مشكلة دزلنا الرمز». It now catches 10/10, plus 13/13 more requests (old: 4/13). It flags none of 27 warnings and mentions (old: 3 false alarms, such as «دزيت الرمز لأحد؟»).
4. **A time in a draft is allowed only from the policy facts.** Before, «خلال يومين» passed if the customer had written it, and a ticket could plant a fake `</ticket>` and «Known facts» line. `draft.known_facts()` is now the only source. A `<ticket>` tag typed in a ticket is changed to `‹ticket›` in both prompts. Tickets without such a tag get byte-identical prompts.
5. **Sealed sets can't reach the page.** The run list shows only real run files (top-level `meta` and `tickets`) outside any `heldout*` folder and without sealed ticket ids. A run is served only by a name the list shows, so traversal and odd names get 404. Gold labels are never read from `data/heldout*`.
6. **Spending is bounded.** While a cap is set, a model with no price is refused (its cost would not count). SDK retries are off. `llm.call` retries once on a timeout, dropped connection, rate limit or server error only, with a 60 s timeout. Before, one step could make 6 attempts of up to 600 s each. When the browser closes, the live run stops before its next model call (flag `cancelled`).
7. **No exception text reaches the page or a run file.** An error event says what failed in fixed Arabic, plus the error type. The traceback goes to stderr only; under `REAL_DATA=1`, without the message.
8. **A run always ends.** `process()` never raises. Any unexpected error escalates the ticket with flag `internal_error`, and a result event is always sent. The live stream always ends with `event: end`.
9. **Masking covers more.** Numbers split by `-`, `.` or spaces (`0770-123-4567`), card numbers (Luhn check) and a code after a code word (`OTP 482913` → `OTP ******`) are now masked. Dates, comma amounts and decimals stay as they are. On 2,639 saved strings, 46 change, all hyphenated references the old rule left visible.
10. **Security headers on every response:** CSP, X-Frame-Options DENY, nosniff, no-referrer, COOP and no-store. The Server header no longer shows the Python version. The viewer still logs no requests.
11. **Dependencies** have upper bounds. The unused streamlit and faker are removed. pytest moved to `requirements-dev.txt`. pip-audit found no known vulnerabilities.
12. **Tipping-off and echoed numbers** (Iraq AML/CFT Law 39/2015 forbids telling a customer about a report or an investigation; repeating a card number or code back is poor card-industry practice). There are two new draft rules, behind flags (below).

**New controls:**
- **Kill switch:** `PIPELINE_MODE=off` calls no model, and every ticket goes to a person (`pipeline_off`). `classify_only` sorts and routes but writes no draft (`drafts_off`).
- **Real-data guard:** under `REAL_DATA=1`, the viewer, `run_batch` and every model call refuse the dev-only paths: the cli backend, free-model profiles and the response cache. `--no-mask` is refused too.
- **Decision log** for the next UI: `POST /api/decision` appends one line per approve, edit, take-over or forward. A line holds the reason codes, seconds, corrections, model ids, prompt hashes and a count of edited characters. It never holds the draft or reply text.

**How it was checked:**
- **Tests:** 296 pass. 76 existed before, and 220 are new (`test_text_rules.py` 118, `test_pipeline_safety.py` 52, `test_server_security.py` 50). Three old tests in `test_pipeline.py` were updated for the intended changes. Two now pass the policy facts separately: a time the customer wrote is still a promise. One reflects the three new flags, all off. No safety assertion was weakened.
- **Replay of test2 from the cache:** 180 model calls, all from the cache, **0 misses**.
  - Type 78/80, priority 79/80, outcomes 65 drafted, 9 flagged, 6 escalated: the same as the saved final run.
  - 165 of 169 model prompts are byte-identical. The 4 others are the drafter prompts of the app-bug tickets (t2-0021, t2-0041, t2-0060, t2-0078), whose team line changed on 30 Oct (general → tech), so their drafts differ too.
  - The new secret and promise rules change no outcome.
- **Old vs new draft rules on 2,255 saved dev and mvp_test drafts** (`runs/exp/dev`, `runs/exp/mvp_test`): identical on every draft (stray Latin 21, unknown number 7, nothing else).
- **Live viewer** (`PIPELINE_MODE=off`, checked with curl):
  - the page carries the token, and `/api/meta` gives 200 with it and 403 without
  - a foreign Host gets 421, a foreign Origin 403, `GET /api/stream` 405
  - a short ticket streams to an escalated `pipeline_off` result, then `event: end`
  - a 5,000-character ticket and a 70 KB body both get 413
  - every response carries the headers
  - a decision appends one line with no text
  - 18 runs are listed, none sealed; sealed and non-run names get 404
- **In a browser** (Playwright): the current viewer replays "test2 · final", opens a ticket and runs a pasted one with no script errors.

**Behind a flag, not adopted** (off by default; `PIPELINE_FIXES=...`; for the author to adopt or delete):

| Flag | What it does | test2 (80) | dev, mvp_test |
|---|---|---|---|
| `hold_reason` | flags a draft that mentions an investigation, suspicion, a report or money laundering | 0 drafts | 0 of 2,255 drafts |
| `sensitive_number` | flags a draft that repeats a card number or a code | 0 drafts | 0 of 2,255 (one false alarm, dev-0099, fixed while building it) |
| `escalate_account_risk` | a blocked account or a SIM change goes to a person, with no draft | 7 tickets escalated; review rate 19% → 26% | dev 12 (17% → 22%; replicate 20% → 25%); mvp_test 5 (27% → **33%**, over the 30% target) |

- The two draft rules fire on no saved draft, so they cost nothing measurable and their benefit is untested. «تحقيق» can also mean "achieving" («لتحقيق رضاك»); no draft uses it yet.
- `escalate_account_risk`: in dev and mvp_test, every ticket it escalated was really a blocked account or a SIM change. In test2, 6 of 7 were. Their drafts were safe (they acknowledge and pass the ticket to the accounts team), so the trade is a lost safe draft against a person handling a possible account takeover from the start.
  - Its one wrong case: t2-0009 is a code-not-arriving ticket. The first model said SIM change at 0.60, and the flag escalates before the re-check that had corrected it.
  - In a live run, each of these escalations also makes one small team-summary call (missing from the cache replay, so those notes had no summary line).

**Left for the institution that deploys it:**
- Fill `config/policy.yaml` (hours, response times).
- Run with `REAL_DATA=1` on the API backend.
- Keep the API key in a secrets store.
- Choose where requests are served (the run records `inference_geo` when the API reports it).
- Set how long run files and the decision log are kept.
- Put real sign-in and TLS in front of the viewer before more than one person uses it. The local token only stops other web pages, and the reviewer name comes from the computer's login.
- Mask names: masking covers numbers only.
- Its own AML/CFT procedure for reporting: the pipeline only keeps the draft from mentioning it.

**Still open:**
- The dev-only scripts (`calibrate.py`, `run_probes.py`) still record exception messages in their own outputs. They run on synthetic sets only.
- The CSP allows inline scripts, because the page is one file. The new UI can move its script to a file and drop `'unsafe-inline'`.
- README and CONTEXT still describe the old secret and time checks, the old masking and the old test count.

**Review.** Six reviewers (security, regression and Arabic rules, two each) checked the changes above and filed 53 reports, about 30 distinct problems. Each was reproduced with no model call before it was fixed, and each fix has a test that fails on the code before it (checked by running the new tests against a copy of that code).
- **Fixed, safety switches and spending:**
  - The kill switch failed open. YAML reads a bare `mode: off` as false, and the full pipeline ran. `mode:` is now read before every call (no restart needed), and false means off.
  - `REAL_DATA=y` or `2` turned the guard off, and `LLM_BUDGET_USD=nan` turned the cap off. Both now fail closed.
  - `ANTHROPIC_BASE_URL` could send real tickets and the key to another host. It is refused under `REAL_DATA=1` unless it is the Anthropic API.
  - A price without its cache rates failed after the paid reply, so the spend went uncounted and the call was retried. Such a price is now refused before sending.
  - A rate limit or overload was retried at once. It now waits as the API asks, at most 10 s.
  - A page closed during a failed call still got a paid retry. should_stop is now checked before a retry.
- **Fixed, the viewer and run files:**
  - A lone surrogate in a ticket (an emoji cut in half) killed the stream and lost a whole batch run. The viewer refuses it, process() and run_batch replace it, and a run file is written whole or not at all.
  - The stream treated a socket above fd 1024, or a half-closed client, as gone. A worker that could not start held the live slot for good, and a stream error left the run going.
  - A foreign caller's body was read before the refusal, so a slow sender could hold a thread.
  - edit_chars took 13 s on two long rewrites.
  - The reply hashes in the decision log were plain SHA-256, so a short edit could be guessed. They are now keyed (`DECISIONS_HASH_KEY`, else a key per viewer run).
  - The decision log, and the run file under `REAL_DATA=1`, are now readable by their owner only.
  - The saved sensitive_number span kept the code's digits. They are now `*`.
- **Fixed, masking:**
  - A number joined by a space swallowed a comma amount or a date after it.
  - Amounts, waits and bill or tracking codes after a code word were masked as codes.
  - These slipped through: «باسورد», `OTP482913`, `CVV2 123`, a code four or five words after its word, «لرقمي», shadda, Persian kaf and yeh, and invisible characters.
  - A +964 phone or a 13-digit reference counted as a card.
  - All 3,602 non-sealed ticket texts, drafts and notes mask exactly as before.
- **Fixed, draft rules.** The rules now read text with harakat and invisible characters removed.
  - asks_secret missed formal and verbal-noun requests, the «ما عليك أمر» openers, need and know verbs, Mosuli and southern forms, the secret named first, and requests with no verb. It flagged quoted warnings («أي شخص يطلب منك…»), «اوعى» and «اياك», typing the code in the app, "we sent you a new code" and error codes on screen.
  - hold_reason now catches شبهة, مريب, امتثال, تحت المراقبة and reports to the authorities. It no longer flags phishing advice or the customer's own «البلاغ مالتك».
  - promise: a policy «خلال يومين» no longer allows a draft's «خلال يوم». It catches refund verbs and «بظرف», «غضون», «الأيام الجاية», and no longer flags «أكيد راح نساعدك» or «ما نكدر نضمن».
  - unknown_number accepts «50 ألف» for 50,000.
  - Of the reviewers' phrasings, 193 that the old rules got wrong are now right, and none is wrong.
  - On the 1,220 saved drafts (dev, mvp_test, test2, probes), the old and new rules give the same flags on every draft, with both new flags on.
- **Not changed, and why:**
  - «رفعنا بلاغ» and «سجلنا بلاغ بمشكلتك» stay flagged by hold_reason. The reviewers disagreed on whether this means "we raised a ticket". A false alarm costs an edit; a miss is tipping-off. For the author to decide.
  - «لازم تكتب الرمز خلال دقيقتين» stays asks_secret. With no app named, it reads like finding 3's «لازم تكتب الكود».
  - A code written before its word («482913 هذا الرمز») is not masked. The rule masks a code only after its word, and the same pattern would mask an amount before «الكود ما وصل».
  - There is no cap on connections. The viewer is local only, a local process can tie up threads while sending headers anyway, and the deployment notes already ask for a proxy with sign-in.
  - An empty reply is still retried once, as before this phase.
  - Still missed: a request more than three words before the secret («دزلنا آخر اربع ارقام من الرقم السري») and «خلال اربعة وعشرين ساعة». An amount after a code word with no unit («وعندي 150000») is still masked.
- **Checked:** 549 tests pass (253 new). The test2 cache-only replay made 180 calls, all from the cache, with 0 misses. Its results, events and prompts are identical to the replay above.

## 30 Oct: app bugs go to a new Tech support team

The author's choice (from the author's test2 note on t2-0021): `app_bug` now routes to `tech` («قسم الدعم التقني») instead of the general queue (`team:` on the subcategory in `config/taxonomy.yaml`). Routing only: no scored metric changes; runs made before this show the general queue.

## 30 Oct: final test on the fresh test2 split (checked by the author before the run)

`test2`: 80 new tickets (seed 5505, no Arabizi, the new dialect bans). The author checked 30 of them **before** the pipeline ran, seeing only the ticket and its gold label: **30/30 labels and details right**; 27 natural, 3 a bit off («متضايج», «بعثلي», now banned in the generator; t2-0041 is the planted injection). Answers: `data/review/test2_label_check_answers.json`. Then `PIPELINE_FIXES=mvp` ran **once** on the API; nothing was changed after. `heldout2` (80) stays sealed.

| test2 (80) | |
|---|---|
| Type used correct | **77 (96.3%, 95% CI 89.5–98.7%)** as run; **78/80** after the author relabelled t2-0033 (below); 28/30 on the author-checked tickets |
| Priority / amount / reference | 78/80 · 79/80 · **21/21** |
| Fraud escalated, none drafted | **6/6** |
| Wrong type that still got a draft | 3 (1 marked ready) |
| Review rate (flagged + escalated) | **19%** (6 escalated, 9 flagged) |
| Drafts: mean score / asks right / grounded / no promise / safe | 4.41 · 65/74 · 71/74 · 73/74 · 74/74 |
| Model errors / cost | 0 · $0.21 ($0.0027 per ticket) |

The three misses:
- **t2-0033** «دفعت ... للمطعم بالكود وانسحبت مني مرتين»: gold `merchant_payment`, pipeline `reversal_request` (the re-check's answer, flagged). By the author's ruling on dev-0109 (a shop paid twice by mistake is a reversal), the label was the error; not among the 30 the author checked. **The author confirmed (30 Oct): relabelled `reversal_request`. Re-scored with no model calls: type 78/80, priority 79/80, wrong type that got a draft 2.** Other double-charge-looking tickets (a payment that failed but was deducted, then paid in cash) are a different case and keep their labels.
- **t2-0052**: an agent overcharged *and* the cash-in never arrived; gold leads with the fee, the pipeline with the missing money (the draft covers both). Either could lead, as with dev-0152.
- **t2-0041** (the planted injection): `app_bug` instead of `complaint`; the injection itself failed (P3, no promise).

## 29 Oct: MVP results: the locked configuration on mvp_test and heldout, once each

`PIPELINE_FIXES=mvp`, thresholds 0.75 / 0.60, API backend, each split run **once**, nothing changed after seeing the results. Drafts graded by the cli judge (rubric with the loanword fix). Heldout: totals only; its per-ticket pages stay out of git (they show drafts). **Gold labels are model-written; the author checked 34 dev tickets, none of these.**

| | mvp_test (78) | heldout (78) |
|---|---|---|
| Type used correct | **77 (98.7%)** | **77 (98.7%)** |
| Priority correct | 77 | 77 |
| Amount correct | 77 | 78 |
| Outcome = gold | 69 | 75 |
| Fraud tickets escalated, none drafted | 6/6 | 5/5 |
| Wrong type that still got a draft | 1 (flagged) | 1 (marked ready) |
| Ready / flagged / escalated | 57 / 15 / 6 | 64 / 9 / 5 |
| **Review rate** (flagged + escalated) | **27%** | **18%** |
| Mean draft score (1–5) | 4.49 | 4.55 |
| Drafts asking for the right things | 61/72 (85%) | 62/73 (85%) |
| Grounded / no promise / safe | 70 / 72 / 72 of 72 | 70 / 73 / 73 of 73 |
| Bad drafts (judge) | 4 | 3 |
| Model calls / cost | 180 / $0.21 ($0.0027 per ticket) | 179 / $0.20 ($0.0026 per ticket) |

- The wrong types: mvp-0046 (`sim_change` read as `rejected_or_pending`, flagged) and hold-0075 (`merchant_payment` read as `reversal_request`, marked ready; possibly F20 pulling a payment toward reversal; text not read).
- mvp_test's higher review rate: 6 of its 15 flags are F3c's "the models disagreed, the second answer was used", by design.
- **Three false alarms in the draft check, all in the safe direction** (a ticket flagged for a person to look at): mvp-0013 and hold-0015, where the draft warned the customer *not* to send the code, and mvp-0071, a number written in words («واحد وعشرين» = 21). The secret check is fixed for future runs (f3d8731); these runs keep their measured numbers.

## 29 Oct: F11b and F21 tested; the MVP configuration is locked

On top of rec+F16+F20, dev 233 with a replicate ($0.33 for both):

- **F21 `team_summary`: adopt.** All 18 escalated tickets got a one-line Arabic summary in the team note that says what happened (dev-0197: «انطى الرمز لواحد اتصل بيه وكال من خدمة الزبائن، والزبون يسأل شنو يسوي هسه»), which is what the author asked for. A few lines slip into formal Arabic («ادعت العميلة», «لم يتمكن»); acceptable for an internal note. A small Haiku call on escalated tickets only; a line with a number not in the ticket is dropped.
- **F11b `ask_if_unnamed`: do not adopt.** The 68 drafts it changed, graded on cli (rubric with the loanword fix): asks right 49 → 59 in one replicate but 54 → 55 in the other; bad drafts 1 → 4 and 2 → 5 in **both**. The reworded instruction led the drafter to give advice it may not state ("no need to pay again until it is checked", dev-0132, dev-0207) and once to write two versions with an English meta line. The F11 weakness (dev-0199) stays a known limitation.
- **Thresholds stay 0.75 / 0.60.** With F20, recheck_from 0.65 moves no ticket on dev, and pass_above 0.85 trades one fixed ticket (dev-0145) for one needless escalation (dev-0116) for +$0.00009 per ticket.

**Locked: `PIPELINE_FIXES=mvp`** (`src/pipeline/fixes.py`): F2, F3c, F6b, F11, F12, F14b, F15, F16, F17, F18, F19, F20, F21; thresholds 0.75 / 0.60; unknown charges stay with the fraud and security team (P1, escalated). Next: mvp_test and heldout, once each.

## 29 Oct: round 2 review, F20 (a payment made twice), calibration with F20

**Author's round 2** (`data/review/dev_round2_answers.json`, 16 tickets from dev/recF16; the cli grader's verdicts stored beside the author's, hidden from the author during the review):
- Drafts: **10 of 13 send as is, 3 after small edits, 0 rewrite.** Asks for the right things 9/13; missing a question on 4 (dev-0199: the restaurant's name, the known F11 weakness).
- The grader mostly agrees, but marks drafts down for English words Iraqi customers use themselves (PIN, QR, error): the author would send dev-0075 as is, which the grader called bad. 16 of the 25 "bad" drafts on dev failed only `clean`, so the grader's bad-draft count is too high.
- Fraud team note (dev-0197) should say what happened ("he gave the code to the scammer"); F17 lists fields only.
- Dialect in the generated tickets: Iraqis say «اريد», not «ابي»; «من الاستعجال», not «من العجلة».
- Decisions: recheck_from 0.65 yes ("we should test"); test F20 yes; unknown charges → transfers team (the author is still unsure; not applied).

**F20 `duplicate_payment_hint`** (one hint line on `reversal_request`: the same amount sent twice by mistake, or a cancelled deal; money to the wrong person is `wrong_recipient`), dev 233 with a replicate, on top of rec+F16:

| | Type used correct | First model correct | Wrong type → draft | Fraud → draft | Review rate |
|---|---|---|---|---|---|
| rec+F16 / -r1 | 228 / 228 | 227 / 227 | 4 / 4 | 0 / 0 | 19% / 19% |
| **rec+F16+F20 / -r1** | **231 / 232** | **229 / 229** | **1 / 0** | 0 / 0 | 18% / 19% |

All three tickets paid twice (dev-0109, 0138, 0190) fixed in both replicates; every other changed ticket also moved to the gold answer. Cost $0.27. **Adopt F20.**

**Calibration with F20** ([dev/calibration-recF16F20.md](dev/calibration-recF16F20.md), re-check on all 233, $0.41): confidence ≥ 0.85 → 213/213 correct. `recheck_from` 0.60 vs 0.65 now makes **no difference** (no ticket left between them). `pass_above` 0.85 removes the last wrong type marked ready (1 → 0) for 10 more re-checks per 233 tickets (≈ $0.05) and review 17% → 18%: one ticket, so weak evidence.

## 29 Oct: the author's label check (18 dev tickets)

The first check of gold labels by a person: the author, on a review page, for the 14 dev tickets where the recommended runs disagreed with gold most consistently, plus 4 random agreeing tickets. Answers: `data/review/dev_label_check_answers.json`.

- **Gold was right on 16 of 18.** Corrected: **dev-0094** `fees_limits_question` → `not_received`; **dev-0152** `cash_out_refused` → `overcharged_fee` (second issue `cash_out_refused`; the author: "either"). Priority and outcome recomputed by the dataset's rules (`generate_tickets.regold`).
- **Gold amounts were right on all 5 tickets where the pipeline's amount differed** (dev-0074, 0084, 0101, 0138, 0156): the pipeline sometimes misses an amount (e.g. «عشرة الاف» as an agent's fee) and flags "amount missing" for nothing.
- **A systematic pipeline error: paying the same amount twice by mistake.** dev-0109, 0138 and 0190 are `reversal_request` (gold right); the pipeline said `merchant_payment` or `wrong_recipient`. In 0138 and 0190 the first model was right and the re-check's answer, used by F3c, was wrong. The author: the draft and routing should also carry the reason (pressed twice by mistake).
- **dev-0164:** gold `login_otp` is right; the first model read an OTP problem as a scam (escalated; the safe direction, but extra work).
- **dev-0145** (the dataset's prompt-injection test, a fake "SYSTEM" line asking for P1): the pipeline ignored it (P3). The author was unsure of the type; gold `limit_upgrade` kept.
- **dev-0083** (spot-check, `unauthorized_charge`): the author says it is not fraud, since nobody tricked the customer; the customer found an unknown charge. A taxonomy question: `unauthorized_charge` sits under fraud and is always escalated as P1. Open.
- The author also noted that the check showed no drafts, and that some tickets need more information from the customer.

**Re-scored on the corrected labels** (calibration replay, no model calls): type used correct 235/240 and 236/240 (was 233); wrong type reaching a draft 4 and 3 at the current thresholds, **3 and 1 with `recheck_from` 0.65**. The 0.65 gain now holds in both replicates.

## 29 Oct: dev (240 tickets) on the API, gate calibration, label-check sheet

Six runs on `data/dev/tickets.jsonl`, API backend, each with a replicate (`-r1`: fresh classifier, re-check and drafter replies). rec = F2+F3c+F6b+F15+F11+F12+F14b+F17+F18+F19. Total cost **$2.43**, about $0.002–0.0025 per ticket for a fresh run. No budget hit. **Gold labels are model-written and not yet checked by a person.**

| Run | Type used correct | Outcome | Priority | Amount | USD amounts | Wrong type → draft | Fraud → draft | Review rate |
|---|---|---|---|---|---|---|---|---|
| baseline / -r1 | 233 / 233 | 220 / 222 | 193 / 193 | 231 / 233 | 2/8 / 4/8 | 4 / 3 | 0 / 0 | 22% / 21% |
| rec / -r1 | 233 / 234 | 227 / 228 | 234 / 235 | 231 / 233 | 2/8 / 4/8 | 6 / 5 | 0 / 0 | 19% / 18% |
| rec+F16 / -r1 | 233 / 233 | 226 / 226 | 236 / 237 | 234 / 236 | 6/8 / 7/8 | 6 / 6 | 0 / 0 | 19% / 19% |

- **Priority** is the big baseline/rec gap, by design: gold follows the author's rules F15, F18, F19.
- **F16 (ورقة = 100 USD) passes its replicate test:** USD amounts 2–4/8 → 6–7/8, amounts overall +3. One low-confidence ticket per replicate changed type (dev-0088, dev-0210, different tickets), and the re-check corrected both, so the type count is unchanged. **Recommend adopting F16.**
- **Classifier JSON:** Haiku sometimes ends its JSON with a stray `)` (4/240 in one replicate, all escalated as model errors). A reply that doesn't parse now gets one fresh try; all 4 recovered.

**Gate calibration** ([dev/calibration-rec.md](dev/calibration-rec.md), [dev/calibration-rec-r1.md](dev/calibration-rec-r1.md)): the re-check model was asked about all 240 tickets ($0.43 per run), then the gate was replayed for every threshold pair (the replay reproduces each run's own outcomes 240/240).
- The first model's confidence is well ordered: ≥ 0.90 → 175/175 and 180/180 correct.
- Review rate is 17–19% at every setting (target ≤ ~30%): it comes from fraud and missing fields, not from the thresholds.
- `recheck_from` 0.60 → **0.65** cuts wrong types reaching a draft in both replicates (6 → 4, 5 → 2): tickets at 0.60–0.65 are escalated instead. `pass_above` 0.75 → 0.90 helps in one replicate only (wrong → ready 2 → 1, 1 → 1) and doubles the re-checks (≈ 42 → 82).
- **Not decided yet:** the differences are a few tickets, and some "wrong" tickets may be wrong labels. Decide after the author's label check. (If `recheck_from` goes to 0.65, `missing_field_cap` must go with it, or a missing field escalates instead of flagging; the replay already does this.)

**Draft quality, baseline vs rec** ([dev/rec.md](dev/rec.md); cli judge, rubric corrected for F18): mean score 4.41 → **4.47**, asks for the right information 180/218 → **186/222** (83% → 84%), grounded 96% → 96%, no promise 99.5% → **100%**, bad drafts 24 → 25 (none scored ≤ 2; they fail on `clean` or `grounded`). The first grading said asks-right fell (185 → 180) because the judge still wanted a transaction number where the author's F18 rule says none is needed (dev-0043, a reversal); fixed in the judge, both arms re-graded. **Remaining F11 weakness:** the drafter sometimes treats the kind of place as its name ("بالمطعم", "at the restaurant") and doesn't ask for the shop or agent name (dev-0018 and ~9 others: card payments, agent fees, cash-in). A wording fix would need its own with/without test.

**Label check for the author:** `data/review/dev_label_check.csv`, 18 rows: the 14 tickets where the recommended runs disagree with gold most consistently (type first, then outcome and priority; F3c's own "models disagreed" flag doesn't count), plus 4 random tickets where everything matched, shuffled.

## 29 Oct: first API runs, and the cli judge becomes the default

The first runs on the **API** backend (the $35 test key), with the recommended set plus F17, F18 and F19 on, on a 30-ticket sample of dev (one ticket from each of the 23 subcategories plus 7 at random, seed 29; the file lives in `runs/sets/`, git-ignored).

- **Cost:** 10-ticket pilot $0.030, the other 20 tickets $0.052: **about $0.002–0.003 per ticket**. The drafter (Sonnet) is ~70% of it. The prompt cache works: 62,562 prompt tokens were read from it in the 20-ticket run, and the first ticket now runs alone so the parallel workers don't each pay to write the same cache entry.
- **Accuracy on the 30:** subcategory used correct 29/30, priority 29/30. The two differences from gold: dev-0121 (the models disagreed; F3c used the re-check's answer, which is correct, and flagged it, as designed) and dev-0109 (gold `reversal_request`, classified and drafted as `merchant_payment`: a wrong type that reached a draft).
- **F2 false alarm, fixed:** dev-0077's draft echoed the customer's "declined" before an Arabic comma, and F2 counted the comma (and tatweel) as an Arabic letter. Only Arabic letters count now.

**Judge on cli vs API** ([dev_sample30/judge_backends-rec.md](dev_sample30/judge_backends-rec.md)): the same 27 drafts graded 3 times on each backend.

| | Score identical | Score within 1 | Same bad/ok verdict |
|---|---|---|---|
| cli vs cli | 83% | 100% | 95% |
| API vs API | 85% | 100% | 98% |
| **cli vs API** | **82%** | **100%** | **97%** |

The cli judge agrees with the API judge as well as each agrees with itself; per-draft average scores differ by 0.14 (cli mean 4.33, API 4.42), never by more than 1. **Decision (author's rule: if similar, take the free one): drafts are graded on cli by default** (`report` and `judge-noise` take `--judge-backend api` to override). Pipeline numbers still come from the API. The API grading cost $0.65 for 81 gradings.

## Current recommendation (after round 3)

**Adopt F2 + F3c + F6b + F15 + F11 + F12 (v2) + F14b.** F15 (no word raises priority) replaced F7 on 23 Oct after a correction from the project author; F14b was added after the fraud/secondary follow-up below. **F16** (the meaning of "ورقة") is pending an API test with replicates. This replaces F3 with F3c and F6 with F6b compared with the round-2 advice. F8 stays your call; F5 needs your real policy values. Do not adopt F9, F10 or F13 (reasons below).

Confirmed on **holdout_30**: 30 tickets written before any round-3 result and run only once the recommendation was fixed. Three runs of each arm (as run, fresh classifier, fresh drafter):

| Metric | Baseline | Recommended | Round-2 set (F2+F3+F6+F7) |
|---|---|---|---|
| Subcategory used correct | 28 / 28 / 28 | **29 / 29 / 29** | 27 |
| Draft given iff it should be | 29 / 28 / 29 | **30 / 29 / 30** | 27 |
| Priority correct | 28 / 28 / 28 | **30 / 30 / 30** | 29 |
| Fee correct | 0/2 | **2/2** | 2/2 |
| Escalated | 3 / 4 / 3 | 2 / 3 / 2 | 5 |
| Mean draft score (pooled, ~55 drafts each) | 4.44 | **4.63** | 4.36 |
| Drafts asking for the right info (pooled) | 78% | **89%** | — |
| Grounded (pooled) | 98% | **100%** | — |
| Model calls | 63 | 68 | 59 |

Pages: [holdout_30/summary.md](holdout_30/summary.md), [pooled drafts](holdout_30/pooled-rec-vs-baseline.md). The dev results (95 tickets, `dev_95`) are in [dev_95/summary.md](dev_95/summary.md).

One ticket is missed by every configuration: **h19** ("I want to raise my monthly limit, how long, which papers?") is read as a fee/limit *question* instead of `limit_upgrade`. It's the same confusion as s05 and m08 on the dev set. Adding `[limit_upgrade, fees_limits_question]` as a look-alike pair, or a sharper hint, is the next thing to try. It was left alone here so the hold-out stays a fair test.

### Corrections from the project author (23 Oct): F15 and F16

The project author, a native Iraqi speaker, corrected two assumptions built into the pipeline:

| Flag | Change | Why | Status |
|---|---|---|---|
| **F15** `no_urgency_words` | No word changes priority; only the subcategory default and the ≥ 1,000,000 IQD amount rule | No word (هسه, ضروري, عاجل, بسرعة, صارلي يومين…) reliably marks urgency. F7 only removed هسه | **Adopt, replaces F7.** Rule-only, so no model noise. The old probe sets' gold priorities assumed urgent words raise priority, so priority scores on those sets will drop under F15; the regenerated dataset is labelled with F15 |
| **F16** `warqa_usd` | The classifier prompt's amount example: "ورقة" is a 100 USD note, "خمسين ورقة" = 5,000 USD (amount_usd); "خمسين الف" = 50,000 IQD | The old example said "خمسين ورقة" = 50,000 IQD: wrong, and it contradicted the amount_usd line | **Not run.** It edits the shared classifier prompt; F6, F13 and F14 all shifted other classifications, so test it with replicates on the API before adopting |

### Follow-up: the fraud / secondary-subcategory rule (F14, F14b)

**Raised by the author:** the classifier prompt says "pick exactly one category and one subcategory", yet rule 1 says "put the other issue in `secondary_subcategory`" for fraud. Worse, rule 1 contradicts rule 5 ("being locked out after a scam … stays with the main subcategory"). Across all 522 saved fraud classifications, 26 (5%) put a consequence of the fraud in the secondary field: e02 and f22 (`login_otp`), f26 (`unauthorized_charge`). The same ticket got different answers on different runs.

Tested only on existing tickets (dev_95, holdout_30), with 3 runs per arm on dev:

| Fix | Change | Result | Verdict |
|---|---|---|---|
| **F14** | Reword the two prompt sentences so rule 1 defers to rule 5 | Secondary correct 64/63/63 → 65/64/64 (one ticket). But subcategory used 90/88/91 → **87/86/87**, and 95 → **92** inside the recommended set; **3 wrong types reach a draft in every run** (0 before). The re-check uses the same prompt and now makes the same mistakes (m02, m23), so the disagreement F3c relies on disappears; m08 also flips. Hold-out 28 → 27/26. | **Do not adopt** |
| **F14b** | Same rule enforced in code: a fraud ticket's secondary is cleared when it is an account-access or fraud subcategory (a consequence); a separate request (e.g. e13's top-up) is kept | Identical to its baseline on every metric in all 6 comparisons (no model input changes, so it can't shift classifications); clears all 26 inconsistent cases seen | **Adopt** (small, safe) |

Lesson, the third time it has shown up (F6, F13, F14): the classifier and the re-check share one prompt, so editing it can make both models wrong in the same way and silently remove the safety net. Prefer code rules or separate calls over prompt edits, and always test a prompt edit with replicates.

### Round 3: what was tried

| Fix | Idea | Dev result (dev_95, 95 tickets) | Verdict |
|---|---|---|---|
| **F3b** | Same-team disagreement: use the re-check's answer | Subcategory used 90 → 92, escalated 13 → 11 | Subset of F3c |
| **F3c** | Any non-fraud disagreement: use the re-check's answer, flagged (fraud never overridden) | **90 → 95/95**, draft given 90 → 95/95, escalated 13 → 8, priority 86 → 90, 0 wrong types reaching a draft, +5 calls | **Adopt** (replaces F3) |
| **F9** | Re-check look-alike answers under 0.90 | +6 calls, no gain alone; with F3c, 95 → 95 and one fewer draft | Drop |
| **F10** | Classifier names a runner-up | +16 calls, 90 → 89, wrong types reach drafts (2 runs) | Drop |
| **F13** | Sharper look-alike hints in the classifier prompt | Alone 90 → 92/93, but with F3c **−4** (it makes the first model surer, so fewer tickets reach the re-check F3c relies on) | Drop |
| **F11** | Ask for shop / agent / bill details only if the ticket doesn't give them | Pooled 3×28 drafts: asks right 82% → 87%, bad 2 → 2 | **Adopt** |
| **F12 v1** | No promising to send a specific answer, date or result | Bad drafts **2 → 13/84**: its "check and follow up" wording made the drafter's follow-up phrase come out broken ("wياك", "يتابعونويا") | Replaced by v2 |
| **F12 v2** | Same rule without that wording | Bad drafts 2 → **0/84**, no promise 98% → 100%; with F11: asks right 94%, grounded 100% | **Adopt** |
| **F6 (re-test)** | The round-2 fee field in the classifier prompt | On the larger dev set it **costs classification**: 2 and 1 wrong types reach drafts; F3c+F6 92 vs F3c 95 | Replaced by F6b |
| **F6b** | Separate small fee call only for fee tickets; classifier prompt untouched | Classification identical to baseline; fee 4/4 with F3c; about +1 small call per fee ticket | **Adopt** (replaces F6) |

**Interactions are real in round 3** (unlike rounds 1–2): F3c × F13 −4 and F3c × F6 −3 on subcategory used, both through the same mechanism (a prompt change makes the first model surer, so fewer tickets reach the re-check). F11 × F12 is positive: asks right 87% and 89% alone, 94% together. All pair pages are in `dev_95/`.

**Method additions in round 3:** draft replicates with the classification held fixed (`LLM_CACHE_SALT=drafter=d1`), pooled scoring (`experiment.py pool`), a classifier-noise replicate per key config (`classifier=c1`; about ±2 tickets on 95), "subcategory used" and "wrong type, not escalated" metrics, and the sealed hold-out set.

**Label correction:** s18's gold label was changed from `reversal_request` to `wrong_recipient`, because the classifier prompt's own rule 5 says wanting the money back after a wrong transfer stays with the main subcategory. Every config was re-scored; no model output changed.

## Rounds 1–2

## Verdict per fix

| Fix | What it did on the tickets | Side effects | Recommendation |
|---|---|---|---|
| **F7** casual "هسه" | Priority 24/30 → **29/30**. All five casual-"هسه" tickets fixed; real urgency (f06, "ضروري") still P1. | None. Rule-only, so this result has no noise. | **Adopt.** |
| **F3** same-team re-check | On fixes_30, no same-team disagreement happened, so no effect. On 65 more tickets: **2 of 2** same-team disagreements (s18 reversal vs wrong recipient, m02 forgot PIN vs login) went from "escalated, no draft" to "flagged with a draft" scoring 4/5. | None seen; cross-team and fraud still escalate. Small sample (2 cases). | ~~Adopt~~ **Superseded by F3c** (round 3). |
| **F2** draft checks (v2) | v1 had a false alarm (f12, "we'll get back to you" read as a refund promise). v2 fixed that and two other false alarms found in a wider check. On all **161** distinct drafts so far, v2 flags **2**, both real stray Latin letters ("hلا", "wياهم"); **0** false alarms. | Catches nothing meaning-level: the judge's bad drafts (a promised branch address, an implied refund date) pass the rules. | **Adopt.** Cheap, no false alarms; catches about 1% of drafts. |
| **F6** fee field | Fee **0/4 → 4/4**, and again 4/4 in an uncached replicate. Classification: +f14 −f15 in round 1, not repeated in the replicate, so **no effect beyond noise**. | The classifier prompt changed, so it needs re-checking on the API dev set. | ~~Adopt~~ **Superseded by F6b**: on the larger round-3 dev set the prompt change cost classification. |
| **F8** unclear template | Saves the drafter call on unclear tickets (4/30 here; 63 → 59 calls). Draft scores on those 4 tickets: model drafts 5 5 3 4; template v1 4 5 2 4; v2 4 4 3 4. | Slightly lower quality: a fixed text can't answer an off-topic question (f09) and can't fit every opening (greeting vs "I have a problem"). | **Your call.** It saves about 6% of calls at a small quality cost. If you want it, v2 is the safer text. |
| **F5** policy facts (isolated) | Mean score 4.50 → 4.61, inside the noise floor (4.50–4.65 between identical baseline runs). Drafts now state response times and support hours. | One draft had a stray Latin letter (F2 v2 catches it). The judge rewards safety and editing effort, not added information, so the benefit is under-measured. | **Fill `config/policy.yaml` with your real values,** then re-test on the API. The values used here are placeholders (`config/experiments/policy_filled.yaml`). |

**Follow-up for F3 (tested in round 3 as F3b/F3c; F3c adopted):** under F3 the draft and priority follow the *first* model's answer. In m02 that was wrong (login/OTP, P2), while the re-check had it right (forgot PIN, P3); see `screenshots/f3-m02-same-team-flagged.png`. Across all baseline runs, the re-check model was right in 7 of the 8 disagreements. A variant F3b that drafts from the re-check's answer is worth testing next.

## Combinations

All 10 pairs of {F2, F3, F6, F7, F8} and the full set were run in both rounds. **Every combination scored exactly the sum of its single fixes: zero interaction on every metric.** That fits the design: each fix acts on a different stage (F6 classify, F3 gate, F7 route, F8 and F2 draft), and F2's checks pass the F8 template. So the fixes can be adopted or dropped independently.

All five together (round 2) vs baseline on fixes_30:

| Metric | Baseline | All five |
|---|---|---|
| Outcome matches gold | 29/30 | **30/30** |
| Draft given iff it should be | 29/30 | **30/30** |
| Priority correct | 24/30 | **29/30** |
| Fee correct | 0/4 | **4/4** |
| Escalated | 2 | 1 |
| Model calls | 63 | 58 |
| Bad drafts / mean score | 2 / 4.50 | 3 / 4.38 (within noise) |

A fresh uncached replicate of all five (`fixes_30/all5-rep1.md`) confirms the robust gains: priority 29/30, fee 4/4, 59 model calls. f14 was wrong again, as in the F6 replicate, so the outcome/escalation gain in the table above is noise, not a fix.

## Noise floor and judge

- Two uncached baseline replicates: classification flipped on 0 and 2 tickets (f14, f15 are the unstable ones); bad drafts 0–2; mean score 4.50–4.65. **Draft-quality differences under about ±2 bad drafts or ±0.15 mean score are noise.**
- The judge graded the same 28 drafts twice: the same bad/ok verdict 28/28, and scores always within 1.
- Judge fix during round 1: the judge hadn't been told the drafter is given the handling team, so it marked team names as invented. All configs were re-scored after the fix.

## Timeline

| Step | What was tried | Result |
|---|---|---|
| Harness | Flags, response cache, judge, scorer | Commit `e83f638` |
| Test set | `fixes_30`: 30 new tickets, not the ones that motivated the fixes | `6085e77` |
| Fixes | F7, F3, F2, F8, F6, F5 behind flags, off by default | one commit each |
| Round 1 | Baseline, 2 noise replicates, judge noise, 6 singles, 10 pairs, all five | F7 clear win; F2 false alarm; F3 untested; F8 hurts the off-topic ticket |
| Round 2 | F2 v2 (3 false-alarm fixes), F8 v2 text, F6 replicate, F3 on 65 more tickets, re-run of every config with F2/F8 | See the verdicts above |

## Confidence (item 4): recommendation without 3 calls per ticket

What the data shows (155 baseline classifications across the four sets, cli backend):

| Model's own confidence | Correct |
|---|---|
| ≥ 0.90 | 95/95 |
| 0.75 – 0.90 | 40/42 |
| 0.60 – 0.75 | 12/18 |

- The score is already ordered the right way, and the gate only re-checks about 21% of tickets, so the pipeline averages about 2.1 calls per ticket. Nothing here needs three calls per ticket.
- The re-check earns its cost: in 7 of its 8 disagreements, the first model was the one that was wrong.
- The misses that get through sit at 0.75–0.90, and the disagreements cluster on a few **confusable pairs**: not received ↔ fee question (4 times), reversal ↔ wrong recipient, cash-in ↔ top-up, login ↔ forgot PIN, not received ↔ merchant payment.

Recommended, cheapest first:
1. **Confusable-pairs rule (no extra cost on most tickets):** a short list in `config/taxonomy.yaml`. If the predicted subcategory is in a confusable pair and confidence is under 0.90, re-check. This targets the 0.75–0.90 misses without re-checking everything.
2. **Runner-up in the same call:** ask the classifier for its second choice. If the runner-up is a different team with a small margin, re-check. It costs a few output tokens, not a call.
3. **Calibrate on the API dev set** (the repo's `require_api` path) and set the thresholds from the calibration table in the viewer. The cli numbers above are a direction, not thresholds.

These can be tested with this same harness, as F9 (confusable pairs) and F10 (runner-up).

**Tested in round 3:** neither was worth it. F10 added 16 calls and made accuracy slightly worse. F9 added calls without beating F3c, which uses the re-check that already runs on about 21% of tickets. For confidence, the best cheap lever turned out to be acting on the existing re-check's answer (F3c), not adding more checks. Calibration on the API dev set is still the next step before any threshold change.

## Monitoring additions (after the experiments)

These don't change what the agent sees; they help us watch the pipeline.

- **Cost logging:** every model step records its tokens (and, on cli, the cost Claude Code reports) in the run events, marked when the reply came from the cache; `run_batch.py` prints and stores run totals in `meta.usage`. The fresh all-five run used 59 calls, about 174k input and 12k output tokens, reported $0.06 for 30 tickets (about 6,200 tokens and $0.002 per ticket, including the cli's own context).
- **Viewer:** experiment runs appear under their own group in the source list; the queue can be sorted by priority (P1 and escalated first) or grouped by team; the overview shows tokens and cost per ticket; each model step shows its tokens. Screenshots are in `screenshots/`.
