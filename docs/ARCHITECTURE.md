# PAVHAN — engineering notes

Notes on the decisions that are not obvious from reading the code.

## Why the AI runs on-device by default

A hackathon demo that dies when the venue Wi-Fi drops, or when an API key runs
out of credit, is not a demo. So every intelligent behaviour in PAVHAN has a real
local implementation, and the Claude API is a quality upgrade layered on top —
never a dependency.

That constraint turned out to be a design benefit. Because the local engines had
to be genuinely good, they are explainable in a way a single LLM call is not: the
pricing engine can show its arithmetic, the matching engine can show its per-
factor scores, and the craft identifier can show its evidence. An artisan
negotiating with a trader needs the arithmetic, not a confident sentence.

## The three things that had to be fixed first

The prototype this replaces failed in three specific ways, and the architecture
is shaped around not repeating them.

### 1. Every upload returned the same Banarasi saree

The fix is that craft identification is a *scored inference over three
independent evidence streams* (`services/listing.py:infer_craft`), not a lookup.
Keyword evidence from the transcript carries 0.60, palette affinity from the
photograph 0.22, and silhouette plus surface 0.18, with corroboration bonuses for
a named material or region. Change the photo and the score moves; change the
words and it moves more.

Below ~55% confidence the app declines to guess and asks the artisan to confirm.
Saying "I am not sure" is a feature — a confidently wrong craft type means the
listing never appears in the right search.

`tests/smoke_test.py` asserts this directly: two different photos must produce
different palettes, silhouettes and intricacy values, and two different voice
notes must produce different crafts, titles and prices.

### 2. The microphone did nothing

Four separate causes, all handled explicitly in
`frontend/src/hooks/useSpeechRecognition.js`:

- **Insecure context.** `getUserMedia` and the Web Speech API are disabled
  outside `https://` and `localhost`, silently. We detect it and say so.
- **The permission prompt never appeared.** Calling `recognition.start()` alone
  does not reliably raise it. We call `getUserMedia` first — which does — and
  keep the stream for a live input-level meter, so the artisan can *see* that
  the mic is hearing them. That visible feedback matters more than it sounds:
  without it, a user who is being heard perfectly still thinks it is broken.
- **Chrome ends the session after a few seconds of silence.** An artisan pauses
  to think, `onend` fires, and recording stops. We restart while the user still
  intends to be recording.
- **Every error was swallowed.** Each `SpeechRecognition` error code now maps to
  a sentence in the artisan's own language, with the next thing to try.

When speech recognition is genuinely unavailable, `MediaRecorder` plus server
transcription takes over, and typing always works. The app states which path is
active rather than appearing broken.

### 3. Buyer matching showed "select a product" and then nothing

`services/matching.py` scores every buyer against one concrete product on seven
weighted signals and returns a per-factor explanation for each. The screen
auto-selects the artisan's first product so it is never empty.

One subtlety worth recording: the first implementation averaged category overlap
across all of a product's tags, which buried exact matches — a buyer who
literally sources "Pottery & Ceramics" scored 0.2 on a pottery listing because
the product also carried nine tags they had never mentioned. `_category_fit`
now checks the primary category first and falls back to progressively weaker
evidence. Strong matches went from 0 to 6 on the same data.

## Two bugs that only showed up on someone else's laptop

**The steps were declared inside the page component.** `PhotoStep`, `VoiceStep`
and the rest lived inside `AddProduct`, so every parent render produced a new
component *type*, React unmounted the old one, and the step's state went with
it. Switching language halfway through the flow silently threw away the photo
and the transcript the artisan had just recorded. They are module-level
components now, and the flow's state lives in the parent. A React lesson worth
keeping: defining a component inside another component is never a cosmetic
choice.

**The voice guide talked over itself.** Picking a role greets the artisan and
navigates at the same time, and the screen it lands on immediately spoke its own
script — which calls `speechSynthesis.cancel()` first, cutting the greeting off
about a second in. The fix has two halves: a greeting started through
`sayProtected` holds the floor for roughly as long as it takes to read, and
screen scripts queue behind it instead of interrupting. The hold is released
early when the utterance genuinely ends, so nothing waits out an estimate.

Testing that second one needed a fake speech engine. Headless Chromium ships no
voices, so every utterance "ends" instantly and the overlap cannot be
reproduced; the regression test installs a `speechSynthesis` stub whose
utterances take a realistic reading time, which is the only way the bug is
visible outside a real laptop.

## Hindi is a first-class language, not a translation layer

Three things follow from taking this seriously:

**Extraction accepts all three scripts.** Artisans speak Hinglish — "Yeh
Banarasi silk saree hai, saade paanch metre" — mixing Devanagari, Roman Hindi
and English in one sentence. Every extractor in `services/nlp.py` accepts all
three, including number words: `बारह`, `barah` and `twelve` all resolve to 12,
`saade paanch` to 5.5, and `chaar sau gram` to 400g.

**Vocabulary matches are returned in sentence order.** In "red aur golden
design", red is the main colour and gold is the accent. Returning them in
dictionary order produced "Golden Red Banarasi Saree", which reads wrong to
anyone who knows the craft.

**The reasoning is translated, not just the labels.** The pricing breakdown
notes, season labels, comparables, match explanations, photo coaching and gap
warnings all carry a `_hi` variant. An explanation the artisan cannot read is
not an explanation.

**The data is translated too.** Translating the UI chrome while leaving
"Pottery & Ceramics · Varanasi · Pure Silk" in English produces a half-Hindi
screen that reads worse than either language alone. `taxonomy.label_pack()`
serves Hindi names for craft types, categories, materials, regions, colours,
techniques and buyer types; the app pulls them once per language change and
`L(value)` renders any API token in the current language, falling through
unchanged when there is no Hindi name. Product titles are deliberately left
alone — those are the artisan's own words, not ours to rewrite.

## Pricing for dignity, then for the market

The engine is deliberately cost-plus first and market-adjusted second, because
the failure it is fixing is an artisan accepting a piece rate that values their
time at ₹20/hour. Wages start at ₹55/hour for an apprentice and reach ₹180 for
heritage-craft masters, and the screen reports the effective hourly wage the
artisan actually ends up with — warning them when it is still under ₹60.

Two guards worth noting:

- The **floor** is cost + 4%. The engine will not recommend a loss.
- The seed catalogue uses *focused working days of six hours*, not elapsed
  calendar days. An early version treated a 21-day calendar span as 126 paid
  hours and priced a saree at ₹44,000. Anything that turns time into money has
  to be precise about which kind of time it means.

## Search

BM25 over a weighted field concatenation (title 4.0 … story 0.5), with a synonym
layer that collapses `साड़ी`, `saree`, `sari` and `sadi` into one concept before
anything is scored, and a `difflib` pass for typos. Coverage is folded into the
final score so a document matching every query term outranks one that matched a
single common term many times. Facets are computed from live data, so adding a
craft cluster needs no UI change.

## Training a model with no dataset to train on

The honest problem: nobody publishes what Indian artisan craft sells for. The
absence of that number is the whole reason a weaver accepts ₹14,000 for a
₹35,000 saree. So a scraped dataset was not an option, and inventing one
quietly would have been worse.

What `app/ml/dataset.py` does instead is write the market model down. Every
effect is stated and auditable: how labour saturates, how each category's
ceiling compresses the top end, how a GI tag is worth more where export demand
already exists, how presentation is a threshold rather than a slope, how
textiles and decor peak in different months. A reviewer can disagree with a
coefficient and change it; they cannot be misled about where the number came
from.

The important design constraint was that the simulation must **not** be the
rules engine with noise added. If it were, the model would only rediscover the
rules and add nothing. Every effect listed above is one the rules engine does
not express, which is why the two engines disagree on unusual inputs — and
that disagreement is information worth showing rather than a bug to smooth
over.

Training on `log1p(price)` rather than price matters more than it looks. Craft
prices span three orders of magnitude; optimising raw rupee error would let
the model ignore everything under a few thousand rupees, which is most of what
a bamboo weaver makes. In log space the model optimises proportional error,
which is what "10% off" means to the person being paid.

## Local explanations, not a global chart

Feature importance says the same thing for every product, which is useless to
the artisan looking at one piece. `pricing_ml._explain` pushes each feature
back to a typical value one at a time and re-queries the model, so the number
on screen — "GI certification +₹6,714" — is that feature's contribution for
*this* piece. It costs fourteen extra predictions and turns a model into an
explanation.

## Making a ministry statistic you could defend in a review meeting

The impact report was the first feature where being *wrong* was worse than
being absent. Its first run produced a mean uplift of **2,653%** and a monthly
income of ₹1.79 lakh for a rural artisan. Both were arithmetically correct and
completely fake, and a panel would have stopped reading there.

Three defects, all of the same shape — a number divided by the wrong
denominator:

1. **Tenure came from `User.created_at`.** Seeded and imported artisans are
   created *now* while their order history spans months, so a year of sales was
   being divided by a two-week-old account. Fixed by taking the earliest of the
   account, its first listing and its first order:

   ```python
   candidates = [_aware(artisan.created_at)]
   candidates += [_aware(p.created_at) for p in products]
   candidates += [_aware(o.created_at) for o in orders]
   started = min((c for c in candidates if c), default=now)
   ```

2. **A single mis-stated baseline dominated the mean.** An artisan who declares
   ₹300/month produces a four-figure uplift percentage that swamps every honest
   row. `IMPLAUSIBLE_UPLIFT = 400.0` excludes those from the published average,
   and the response reports `uplift_sample_size`,
   `uplift_excluded_implausible` and `uplift_excluded` so the exclusion is
   visible rather than quiet.

3. **The headline and the breakdown disagreed.** The exclusion was applied when
   computing the ministry headline but not when grouping by corporation, so the
   page showed a mean of +83.5% above a corporation row reading +486.2%. A
   report that contradicts itself on the same screen is worse than no report.
   The filter now runs once, before both.

Artisans with negative outcomes are kept in the table. The demo report shows
two (−3% and −60.1%) and that is the point: a tool that only ever reports
success is not measuring anything.

## Why a fair needs a QR and not a listing

Fair mode looks like a small feature and is the one that maps most directly
onto the problem statement's diagnosis — "a temporary boost in sales" versus
"continuous, year-round access". The mechanism is deliberately minimal: a code,
a printed square, a storefront, a follow button.

The QR is **SVG, not PNG**, because it is printed on A4 and taped to a stall
frame, and a raster QR scaled to the wrong size is a QR that will not scan. It
uses `ERROR_CORRECT_H` because that sheet will be creased and partly obscured
by whatever is hanging in front of it. Dark modules are emitted as run-length
`<rect>` runs rather than one per module, which keeps the SVG small enough to
inline in a JSON response. Stall codes omit `0`/`O` and `1`/`I`/`L`, because
sometimes a visitor types the code by hand when a camera will not focus.

The measurement is the reason the feature exists: `stall/{code}/performance`
splits sales into during-fair and after-fair. Two fairs with identical takings
on the day are not the same fair, and nothing before this could tell them
apart.

## Requirements, quotes and orders share the pricing engine's numbers

The buyer matcher answers "who wants what I already made". A requirement board
answers the other direction, and the ranking reuses the same scoring rather
than a second, subtly different one — an artisan who sees two screens disagree
about which buyers suit them stops trusting both.

The quote sheet shows unit price × quantity, the pricing engine's cost, and the
resulting margin, because the failure mode for a first bulk order is accepting
it at a loss because the total looked large. Accepting a quote writes an
`Order` — the same rows the impact report counts, which is what makes those
figures transaction-derived instead of declared.

## Test isolation

The suite publishes listings, sends quotes and advances orders, so it mutates
the state it asserts against. It passed once and failed on the second run — the
worst kind of test, because the failure looks like a regression in whatever you
touched most recently. Two fixes: `main()` calls `POST /api/admin/reseed`
before anything else, and the sign-in check uses a random phone number per run
so "a new user is sent to onboarding" stays true. 118 checks now pass twice in
a row against the same running server, which is the property that actually
matters the morning of a demo.

## Why the payment rail is a URL scheme and not a gateway

`upi://pay?pa=…&am=…&tr=…` is the whole integration. It opens the payer's own
UPI app with the destination and amount filled in, needs no merchant account,
no settlement account and no PCI surface, and works from a four-year-old
Android phone on a village connection.

The details that took a second pass:

* **Every parameter is percent-encoded.** Artisan names carry spaces and the
  transaction note carries punctuation; an unencoded parameter silently
  truncates the *amount* on some apps, which is the single worst failure this
  feature could have.
* **An unrecognised bank handle is accepted.** `KNOWN_HANDLES` exists so the
  app can reassure the artisan ("looks like a PhonePe ID"), not to gate them.
  New PSP and bank handles appear constantly, and a validator that refused one
  would lock out precisely the person this app is for.
* **A payment cannot be raised without a destination.** Creating a UPI intent
  for an artisan with no VPA on file is a 400, not an empty link. Money
  collected into nowhere is discovered last by the person it belonged to.

The escrow is enforced in the API rather than described in the UI:
`TRANSITIONS` allows `awaiting_payment → held → released`, `release` before
`held` is a 409, and `release` before the *order* is delivered is a second,
differently-worded 409. Both are tested, because a guarantee nobody tests is a
guarantee that quietly stops holding.

## The pincode table is three digits, and that is not a detail

The obvious implementation keys on the first two digits of a PIN, and it is
wrong twice over in ways that matter: `81`–`83` is Jharkhand *inside* Bihar's
`80`–`85`, and `403` is Goa *inside* Maharashtra's `40`–`44`. Both come out as
the wrong state, which puts them in the wrong rate zone, which quotes the wrong
price — and the error is invisible until a parcel is refused at a counter.

`PIN_RANGES` is therefore three-digit ranges with the narrow ones listed first
and first match winning. Goa, Puducherry, Sikkim, the Andamans, Uttarakhand and
Jharkhand are all listed above the neighbour they sit inside. Both cases are in
the smoke suite by name.

The serviceability model is data, not commentary. `REMOTE_STATES` is the set
where private couriers thin out, and their rate cards carry a zero base for
that zone — so Varanasi → Aizawl returns two India Post options and *names*
Delhivery and DTDC as refusing. Showing an artisan a cheap rate from a carrier
that will not come is worse than showing them nothing.

## Largest-remainder, and why the lead does not get the leftovers

Splitting four hundred pieces across six artisans in proportion to capacity
produces six fractions, and something has to be done with the remainder. The
tempting answer — give them to the lead — is the one that ends the pool. A
self-help group that watches the organiser's share round up every time does not
form a second one.

So `allocate()` gives everyone the integer part of their proportional share and
then hands the leftover pieces to whoever was rounded down hardest, capped at
what each said they can make. It is the method used to allot seats from vote
shares, and it has the property that matters here: the parts always sum to the
whole, and nobody is systematically shortchanged. The screen states the rule in
Hindi before anyone agrees to anything, and the suite asserts that the payouts
add up to the net *to the rupee*.

Capacity is measured inside the buyer's window and rounded **down**
(`int(monthly * days / 30)`). A pool that promises the ceiling of everyone's
capacity delivers late. The lead's coordination share is 3%, paid for real work
— collecting, checking and despatching the consignment — and is shown as its
own line to every member rather than folded into the split.

When capacity does not reach the quantity, `plan()` reports the shortfall and
`create_pool` refuses with a 409. Quoting short without saying so loses the
buyer permanently, and it is the failure mode a well-meaning implementation
falls into by default.

## The outbox exists because the service worker refuses to replay writes

Those two decisions are the same decision seen from both ends.

The service worker never queues a POST, for a reason recorded when it was
written: a write that quietly succeeds an hour later publishes a listing the
artisan believed had failed, at a price they may since have changed. That is
correct, and on its own it leaves an artisan with no signal unable to do
anything at all.

So the retry is not hidden, it is a screen. `lib/outbox.js` holds captures in
IndexedDB — IndexedDB and not localStorage, because a photograph is a Blob and
localStorage holds about five megabytes of string — and the app shows how many
are waiting, what each is, and why anything stuck is stuck.

What is stored is the **raw capture**: the photo and the transcript, not a
finished listing. Offline there is no price, no description and no craft
identification to be had, so deferring the processing rather than the work is
the only honest option. On send, the full pipeline runs in the order the
artisan would have run it: `analyzeImage` → `generateListing` → `createProduct`.

Three details earn their keep:

* **The queue id is the server's idempotency key.** `Product.client_ref` is
  unique-by-lookup, and a create carrying a `client_ref` that already exists
  returns the existing row. A send interrupted after the server committed but
  before the phone heard the reply — routine on two bars — retries safely.
  Without this the artisan wakes up to two of the same piece.
* **`crypto.randomUUID` is not available on insecure origins**, which is
  exactly where this app sometimes runs, so the id falls back to a timestamp
  plus two random strings.
* **The flush is serial.** These are photo uploads over the connection that
  just came back; firing five at once on a weak signal is how all five time
  out together. It also stops as soon as `navigator.onLine` goes false again
  rather than grinding through the rest against a network that has gone.

`watchConnection()` is mounted once in `AppContext`, which is what makes the
promise true app-wide: a listing recorded in a field sends itself the moment
the phone finds a tower, with nobody pressing anything.

## A reset button that did not reset

`POST /api/admin/reseed` deleted orders, products, buyers and users — and not
requirements, quotes, enquiries, stalls or fairs. Those accumulated across
every reset, and the smoke suite eventually found itself ranking **seventy-nine
"open" requirements** against a catalogue of sixteen listings.

The bug was invisible for as long as nobody counted, and the screen it
corrupts is the one being demonstrated. The teardown now covers every table the
demo writes to, deleted children-first so no foreign key is left dangling.

## The 404 that was hiding real failures

`GET /api/logistics/order/{id}/shipment` returned 404 when nothing had been
despatched yet. Defensible REST, and wrong here: the despatch screen asks this
question every time it opens, so the caller was written as
`orderShipment(id).catch(() => null)` — which swallows a genuine network
failure exactly as happily as the expected miss, and fills the console with red
that hides the errors that matter.

It now answers `{"shipment": null}`, and the caller catches only real errors and
tells the artisan about them. The browser drive asserts zero console errors,
which is how this was found at all.

## The Hindi was written, stored, and never shown

The report was "the Hindi description is not working", and it turned out to be
three separate bugs wearing one coat.

**The app never rendered the Hindi at all.** `ProductDetail`, `ProductCard`,
`MyProducts`, `ArtisanHome`, `BuyerMatching` and `Orders` all read
`product.title` and `product.short_description` — the English columns — no
matter what language the interface was set to. The generator had been
producing good Hindi for months, the database had been storing it, and every
screen showed the English. Fixed with one helper, `P(product, field)`, in
`AppContext`: it returns the `_hi` column in Hindi and falls back to English
when that column is empty, because a blank title is worse than a foreign one
and listings made before the Hindi generator existed still have to render.

**The seed catalogue had no Hindi to show.** `seed.py` hand-wrote English
strings and left every `_hi` column blank, so even after the screens were
fixed the demo catalogue stayed English. It now calls `hindi_listing()` — a
new entry point that packs known facts into the same `TranscriptFacts` the
voice flow builds and runs the same builders. One set of Hindi, one place to
improve it. The same function now also runs in `POST /api/products`, so the
outbox's replay, the smoke suite and any future bulk import get Hindi without
each having to remember to.

**What Hindi there was, was mixed.** This is the part the artisan actually
sees, and it had four sources:

* `craft.unit` is an English word — "painting", "figurine", "piece" — and it
  was the fallback when an artisan's noun was unrecognised. It produced
  `पीला मधुबनी चित्रकला painting`. Now `UNIT_HI` maps every unit.
* The noun lookup was exact-match only, so "Wall Painting", "Dinner Plate Set"
  and "Meenakari Jhumka" all missed. `_noun_hi()` now tries the phrase, then
  its last word, then any known noun inside it, longest first.
* `_hi()` falls back to the English token, and nine regions, six materials and
  twenty-four technique names had no entry — each one a Latin word dropped
  into the middle of a Hindi sentence. The tables are now complete for
  everything the taxonomy can produce.
* `_measure_hi()` translated units but not qualifiers, so "9 inch tall" became
  "9 इंच tall". `UNITS_HI` now carries tall, wide, long, each, drop, chest and
  the rest, matched longest-first and case-insensitively.

Behind all four sits one rule: `LATIN = re.compile(r"[A-Za-z]")`, and any part
that still matches after every lookup is **dropped rather than shown**. A
slightly shorter Hindi title reads as Hindi; one English word in the middle of
it reads as a bug.

**And the voice was reading English out loud in a Hindi accent.** Two places
built a Hindi sentence around raw English data — `ProductDetail`'s arrival
line interpolated `p.region` ("यह Madhubani में हाथ से बनाई गई है") and its
`VoiceOrb` read the English title and description inside a Hindi frame. Both
now speak what the screen shows. This was invisible to any DOM assertion, so
the browser test installs a fake `speechSynthesis` that records utterances
instead of playing them, and asserts the recorded text is Devanagari. Note the
stub must be installed with `Object.defineProperty` — `window.speechSynthesis`
is a prototype accessor and a plain assignment is silently ignored.

While stubbing it, one production fix fell out: `utter.voice = voice` is now
wrapped in a try/catch, because a voice handle taken before a `voiceschanged`
event can be rejected as stale, and an exception there silences the assistant
for the rest of the session.

The suite now asserts, over the whole catalogue and over freshly generated
listings, that every Hindi field exists, that none contains a Latin word, and
— the constraint the artisan set explicitly — that the English is untouched.

## Dead code that had been copied, not written

`nlp.py` contained `TranscriptFacts` and `PRODUCT_NOUNS` **twice**, byte for
byte, 49 lines apart. Python silently keeps the second, so nothing
misbehaved — which is precisely why it survived. It is the same failure mode
as the duplicate `"mr"` key that once made Marathi resolve to Hindi, and the
same remedy applies: an AST walk over the module now asserts no top-level name
is defined more than once.

## "The Hindi voice is not working" was the operating system

Reported immediately after the Hindi *text* was fixed, and with a decisive
clue attached: the English assistant worked fine on the same page. That
asymmetry rules out almost everything in the app — the queueing, the autoplay
unlock, the utterance plumbing are shared — and points at the one thing that
is not shared, which is the voice.

`speechSynthesis` speaks only scripts its installed voices know. Android ships
`hi-IN`; Windows does not without the Hindi language pack, and a demo laptop
or a cloud VM never has one. `pickVoice(voices, 'hi')` found no Hindi voice,
fell through to its English fallback, and the app then handed an English voice
a string of Devanagari. Nothing came out.

Worse, the previous commit had made this *more* likely to be silent, not less:
before it, the Hindi strings still had English words scattered through them,
so an English voice at least said something. Cleaning the Hindi to pure
Devanagari removed the last thing that voice could pronounce. A correct fix
made the symptom complete.

The remedy is `lib/devanagari.js`: when no Indic voice is present, transliterate
to Roman and let an Indian-English voice read it. Four details matter.

* **Schwa deletion.** Hindi writes an `a` after every bare consonant and then
  declines to say most of them. The word-final one always goes — राम is
  "raam", never "raama" — and that rule has no exceptions worth worrying
  about. A second rule drops the middle vowel in three-syllable words (अपने →
  "apne") and stops there: at four syllables the same rule starts mangling
  compounds (चित्रकला is "chitrakala", not "chitraklaa"), and distinguishing a
  compound from a verb form needs morphology this does not have. Both rules
  err towards keeping the vowel, because an extra syllable is understood and a
  missing one is not.
* **The danda is inside the Devanagari block.** U+0964 is a punctuation mark
  that a naive "is this Devanagari?" test keeps glued to the word, so "रुपये।"
  never matched the entry for "रुपये" and came out "rupye" two words after the
  same word had come out "rupaye" correctly.
* **The utterance language must be `en-IN`, not `hi-IN`.** Telling an English
  voice the text is Hindi makes it apply Hindi phonology to Roman letters,
  which is worse than not telling it anything. `transliterated` decides.
* **Numbers, currency and Latin words pass through.** An artisan who hears the
  wrong price is worse off than one who hears none.

`Profile` now reports which of the four states this device is in — a real
Hindi voice, another Indic voice, romanised fallback, or no voices at all —
names the voice, and offers a button to hear it. The commonest support
question about this app now has an answer on the screen.

Tested by installing a fake `speechSynthesis` with each machine's voice list
and asserting what the app *would say*: Devanagari where a Hindi voice exists,
Roman where it does not, `en-IN` on the utterance either way. The
transliterator itself has its own test, run by `./run.sh test` before the
API suite, because on most machines it is the only reason the artisan hears
anything at all.

## Three things between "it speaks Hindi" and "it sounds good"

Getting Hindi *audible* was the previous fix. Getting it pleasant is a
different set of problems, and none of them is in the text.

**`getVoices()` is an unordered pile, and the first match is a coin toss.**
A Chrome Android device commonly carries both "Google हिन्दी" — neural, sounds
like a person — and an eSpeak Hindi voice that sounds like a 1998 answering
machine. Both match `hi-IN`. The old `pickVoice` returned whichever came
first, so quality was decided by array order.

`lib/voices.js` scores instead. Language dominates (a 1000-point base, so a
great engine on the wrong language still loses to a poor one on the right
one), then engine reputation: Google, Microsoft "Natural"/"Online", Apple
"Premium"/"Enhanced" at the top; eSpeak at −80; `localService: false` worth a
bonus because on every engine that reports it, remote means neural. Named
voices known to be good — Swara, Madhur, Neerja, Prabhat — get their own
bonus. For the romanised path `en-IN` beats `en-GB` beats `en-US`, because an
Indian-English voice says "kaareegar" and "rupaye" close to right and an
American one does not.

`chooseVoice` returns the voice *and* whether to romanise, deliberately
together: a device with no Devanagari-capable voice needs both an English
voice and Roman text, and letting those be decided separately is how they
drift apart.

**An English voice reads "4249" in English.** On the romanised path that
lands English digits in the middle of a Hindi sentence, and lands them exactly
where it matters, because the numbers in this app are the artisan's money.
`lib/hindiNumbers.js` converts them: "chaar hazaar do sau unachaas". Hindi
numerals below a hundred are irregular the whole way — 52 is "baavan", not
derivable from 50 and 2 — so the table is the implementation, and grouping is
Indian (laakh, karod), never thousands.

The hard part is deciding *what not to convert*. A pincode read as a quantity
sends a parcel to the wrong state. The rule: comma-grouped numbers are money,
four digits or fewer is a count or a small price, and a longer bare digit run
— pincode, AWB, phone number, order id — is left alone, because reading those
digit-by-digit is correct. A leading zero marks an identifier too.

**Chrome stops speaking after about fifteen seconds and fires no `onend`.**
The guide goes quiet mid-sentence and never recovers. It is a decade-old bug
with two halves to the workaround, and both are needed: split the text into
short utterances (`lib/speech.js`, 170 characters, broken at sentence ends,
then clause commas, and only then a word boundary — a break mid-clause is
audible and a break mid-word is a different word), and run a
pause-and-resume keep-alive while anything is in flight.

The chunking pays twice: the gaps between pieces — 240ms after a full stop,
120ms after a comma — are the pauses that stop a long passage sounding like it
is being read off a card.

Chunked playback needs one guard. A passage is a chain of utterances, each
queueing the next from its `onend`, so a cancelled greeting could otherwise
resume over the screen the user has already navigated to. `runRef` increments
on every new passage and on `cancel()`; a chunk whose run id no longer matches
stops instead of continuing.

`chunkForSpeech` lives in `lib/` rather than in the hook so plain node can
test it — importing the hook would drag React in — and because the rule it
encodes, "where does a person pause?", is about language rather than
components.

## Three "improvements" that made the voice worse

Reported as "the chatbot does not speak Hindi clearly — at the starting point
it was better". That last clause is the whole bug report: something shipped
later had made it worse, and it was the commit immediately before, the one
whose message claimed to make the voice sound like a person.

The text was not at fault. The assistant's Hindi answers contain no English at
all; every regression was in the delivery.

* **A pause/resume keep-alive running every nine seconds, from the first
  second.** In Chrome, `pause()` followed by `resume()` on a voice that is
  mid-word produces an audible click and on some engines a small stutter. It
  exists to rescue passages that run past Chrome's fifteen-second cut-off — so
  running it on every utterance in the app damaged hundreds of two-second
  lines in order to save the handful that needed it. It now waits twelve
  seconds before starting, by which point anything still speaking is genuinely
  at risk, and it is armed only when the passage was long enough to be
  chunked at all.

* **A chunk size of 170 characters.** Ordinary two-sentence answers were being
  split into separate utterances that would have been spoken perfectly as one.
  Every split is a seam: the voice stops, restarts, and ramps up again.
  Chrome's real ceiling is about fifteen seconds, which at a Hindi voice's
  twenty-odd characters per second is ~300 — so the limit is now 260, and the
  chatbot answer, the product line and the entire welcome greeting each come
  out as a single unbroken utterance. The committed test now asserts exactly
  that, having previously asserted the opposite.

* **A 240ms pause inserted between pieces, and pitch raised to 1.05.** Both
  were added to "sound natural" and both did the reverse. The synthesiser
  already leaves its own pause at a full stop; a second one on top is what
  made a flowing passage sound like it was being read one line at a time. And
  a neural voice is tuned by its vendor at pitch 1 — raising it made a warm
  voice sound thin. The rate of 0.88 on the romanised path dragged, too.

The lesson is narrow and worth writing down: every one of these was a
plausible-sounding adjustment made without listening to the result, and
together they turned a good voice into a stuttering one. The defaults a voice
ships with are a considered choice by the people who trained it, and the bar
for overriding them is higher than "this seems like it would help".

## Accent is the listener's call, not the scoring table's

The other half of the same report asked for a good Indian Hindi accent. The
ranking in `lib/voices.js` gets the *quality* ordering right — neural over
local, `hi-IN` over everything, eSpeak last — but which of two good Indian
voices sounds better is taste, and which voices exist at all differs on every
machine.

So `chooseVoice` now takes a preferred voice name that wins outright when that
voice is still installed, `offerableVoices` returns everything worth offering
(Devanagari-capable voices plus Indian and British English, never American),
and Profile lists them with a sample button beside each. The label says what
each will actually do — "speaks Hindi" or "speaks romanised", and natural /
standard / basic — because nobody can pick a voice from a name. The choice
persists, and can be handed back to the automatic pick.

The preference also carries the romanise decision with it: choosing an
Indian-English voice on a device that *has* a Hindi voice switches the text to
Roman, because the two decisions are one decision and letting them be made
separately is how they drift apart.

## The brand was being announced as the word for "wind"

While listening to the recorded utterances, the greeting turned out to say
**पवन** — *pavan*, wind — rather than **पावहन**. It was in the welcome line
for all four roles, the assistant's answers, the fee explanation and the
impact report: the first sentence anyone hears, naming the wrong product. The
only place the old spelling survives is the regex that matches what a user
*types*, which now accepts both, because someone asking about the app may well
spell it either way.

## Things a reviewer should know are deliberate

- **SQLite, not Postgres.** One file, no service to start, trivially resettable
  before a demo. The SQLAlchemy layer moves to Postgres by changing one URL.
- **The search index is in memory and rebuilt on write.** At 16 listings this is
  free; past a few thousand it should move to SQLite FTS5 or Meilisearch. The
  `SearchIndex` class is the seam.
- **No CSS framework and no component library.** The design system is ~360 lines
  in `theme.css`. A craft marketplace that looks like every other Tailwind demo
  undersells the crafts.
- **Uploaded images are kept in a process-level cache plus disk.** Fine for a
  single-process demo; a multi-worker deployment needs object storage. The cache
  is confined to `routers/ai.py`.
- **Mobile-number sign-in has no SMS gateway.** The OTP is returned in the
  response and labelled on screen as a demo affordance. Wiring a provider is
  one function, `auth._deliver`. Pretending an SMS had been sent would have
  been the dishonest choice.
- **Government marketplace submission stops before the push.** Field mapping,
  HSN classification and the statutory declarations are complete; the POST
  needs a seller account granted to an organisation. The app states this
  rather than implying an integration.
- **The regional vocabulary is narrow on purpose.** Ten languages times a full
  dictionary would be unmaintainable and mostly unused. Ten languages times
  "the forty words that appear in a product description" is small, auditable
  and sufficient — and Indic scripts never collide, so the tables merge into
  one flat lookup with no ambiguity.
- **Accessibility is a scale factor, not a second stylesheet.** The in-app
  text-size control sets one `--font-scale` custom property on the root. The
  first version scaled only `html { font-size }`, which is the usual advice and
  was wrong here: this interface declares most of its type in explicit pixels,
  and a pixel does not care what the root font-size is — body copy grew while
  every button, label, chip and nav item stayed exactly where it was, so the
  control looked like it half-worked. Every declared size now carries the
  multiplier itself, `calc(Npx * var(--font-scale))`, in `theme.css` and in all
  329 inline sizes across the screens. Measured in a browser at 145%: root
  16→23.2px, buttons 15→21.75px, section titles 18→26.1px, with no horizontal
  overflow at 412px wide. High contrast is a `data-contrast` attribute that
  redefines the palette tokens, for the same reason — one switch, whole theme.
- **Payments stop before real settlement.** The UPI intent link is real and
  opens a real payment app; confirmation is recorded from the UTR the payer
  reads out of it. Replacing `payments.confirm()` with a provider webhook
  changes nothing else, because the states, the split and the ledger are
  already the ones a settlement provider reports. Claiming a settled payment
  would have been the dishonest version of this.
- **Carrier booking stops before the carrier's API.** Rates, zones, packing and
  AWB format are real; handing the despatch to India Post's or Delhivery's own
  system needs their credentials, and the screen says so — the same line drawn
  at the same place as with GeM and ONDC.
- **A stated capacity always beats an inferred one.** `_capacity` falls back to
  inferring from an artisan's own listed lead times, and marks the result as
  inferred so the screen can ask them to confirm it rather than quietly
  promising a buyer something nobody agreed to.
- **The service worker never caches writes.** A queued POST replaying later
  would publish a listing the artisan believed had failed. Reads fall back to
  the last good response and are tagged so the app can say "saved data"
  instead of presenting a stale price as live.
