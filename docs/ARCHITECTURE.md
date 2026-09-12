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
- **No authentication.** The demo opens into a seeded artisan account so the
  dashboard has data from second one. Auth is the obvious next commit, not an
  oversight.
