# PAVHAN — 5-minute demo script

For the SIH jury round (Problem Statement 26090). Practise the order; the
surprises land better than the slides do.

## Before you start

```bash
./run.sh          # Windows: run.bat
```

Open **http://localhost:8000** in **Chrome or Edge**, volume up, microphone
allowed. Have a real craft object and your phone ready if you can — a live photo
is far more convincing than a file upload.

**Use the localhost address exactly as printed.** Browsers disable the
microphone on any other `http://` address, silently. If you must present from
another device, put it behind HTTPS first (`ngrok http 8000`).

Sixty seconds before you present, check the Speak screen shows
*"✅ माइक तैयार है"*. If it shows a warning instead, it names the exact blocker
and the fix — read it and act on it then, not in front of the jury.

Optional reset to a clean catalogue: `curl -X POST localhost:8000/api/admin/reseed`

---

## 0:00 — The problem, in one number (30s)

> "This is a Banarasi saree. Twelve days of work. The weaver is paid about
> fourteen thousand rupees at the door. The same saree sits in a Delhi boutique
> at fifty-five thousand. The weaver is not underpaid because the market is
> cruel — they are underpaid because they are the only person in the chain who
> does not know what it is worth."

## 0:30 — Open the app, let it speak (30s)

Open PAVHAN. **Do not talk over the voice guide.** It says, in Hindi:

> *"स्वागत है आपका पवन में। यहाँ हम आपसे सिर्फ़ सामान नहीं लेंगे, आपको उसका पूरा
> दाम भी दिलाएँगे।"*

Point out the four roles. Say: "The app is different for each of them. Pick
artisan."

## 1:00 — Photograph (45s)

Take a photo of the real object.

Land these three things on the report card that appears:
- the **palette swatches** are pulled from the actual pixels
- **intricacy** (e.g. 1.37×) is measured, and it goes straight into the price
- the **photo quality score** with spoken coaching — "move near a window", "use
  a plain white cloth". Most artisan listings fail at the photo, so the app
  teaches the photo first.

> If a juror asks: this is real colour quantisation, edge-density and symmetry
> analysis running in the backend, not a placeholder.

## 1:45 — Speak (60s)

Press the mic. Speak Hindi naturally:

> *"यह बनारसी हथकरघा रेशमी साड़ी है, इसमें लाल और सुनहरी ज़री है, साढ़े पाँच मीटर
> की है, वज़न चार सौ पचास ग्राम, बनाने में बारह दिन लगे, केवल ड्राई क्लीन।"*

While you speak, point at the **live coaching card**: the chips filling in
(साड़ी ✓ रेशम ✓ 5.5 metre ✓ 450 gram ✓ 12 दिन ✓) and the completeness bar
climbing.

Then stop mid-sentence deliberately and show that it **asks you the next
question**: *"इसे बनाने में कितने दिन लगे?"* — it knows what it has not been told.

> If the venue is loud, open **"बोल नहीं पा रहे? तैयार नमूना चुनिए"** and pick
> any of the six crafts. Pick a *different* one each time you rehearse — the
> whole point is that the listing, price and buyers change with it.

## 2:45 — The listing (30s)

Scroll the generated listing. The point to make:

> "It wrote a title, a description, a story, tags and search keywords. And
> notice what it did **not** do — it did not invent a thread count or a dye name.
> Every field traces back to something I said or something the camera measured.
> The confidence score and the evidence are on screen."

## 3:15 — The price (75s) — **this is the moment**

> "Twelve days. Eighty-five... no — one hundred and eighty rupees an hour,
> because this is heritage-level work. Times the intricacy the camera measured."

Scroll to the breakdown and read one line aloud. Then scroll to the comparables
and stop on this:

| | |
|---|---|
| बिचौलिये का भाव | ₹14,399 |
| **PAVHAN की सलाह** | **₹34,099** |
| निर्यात का दाम | ₹55,239 |

> "The artisan can now show this arithmetic to the trader at the door. That is
> the whole product. Not a marketplace — a negotiating position."

Point at the warning box if it appears: the app tells the artisan when *they*
have under-priced themselves.

## 4:30 — Buyers (45s)

Publish. Watch it score 12 buyers.

Expand "यह मेल क्यों खाता है" on the top match and show the seven factors, each
with a Hindi explanation. Then the pre-written pitch.

> "Wedding Story Co. in Jaipur, 94% fit, twenty pieces, six lakh rupees. And the
> message to send them is already written, in Hindi."

**Now the proof it is real:** go to My Products, pick the **bamboo basket**, and
show that the buyers are completely different — Fabindia, Anthropologie, the
Nordic collective. Say:

> "Different product, different buyers. This is scored per item, not a static
> list."

## 5:15 — Close (20s)

Switch the language toggle to English mid-screen to show the whole reasoning
layer flips, not just labels. Then:

> "Photo and a sentence in. Listing, a price they can defend, and buyers out.
> Ninety-five paise of every rupee reaches the person who made it, and the app
> says so on every single product page."

---

## Questions you will get, and the honest answers

**"Is the AI real or is it hardcoded?"**
Run `./run.sh test` in front of them. Forty-two checks, including two that exist
purely to prove this: *two different photos must read differently* and *two
different voice notes must produce different crafts and different prices*. Then
upload something absurd — a photo of a shoe — and show it drop to low confidence
and ask the artisan to confirm, instead of confidently claiming a saree.

The fastest live proof is the sample picker: choose the bamboo basket, then the
Banarasi saree, and put the two results side by side. Different craft, different
price band, completely different buyers.

**"Does it work in Hindi, or is it just Hindi buttons?"**
Toggle the अ / A button on any screen. The categories, materials, regions, craft
names, pricing-breakdown notes, buyer-match reasons and photo coaching all flip,
not just the labels. Then open a price breakdown in Hindi and read a line of the
arithmetic aloud — that is the screen an artisan shows a trader.

**"Does it need an internet connection / an API key?"**
No key at all. The vision, NLP, pricing, matching and search engines are ours and
run locally. Setting `ANTHROPIC_API_KEY` upgrades the copywriting and image
understanding to Claude, and the Profile screen shows which is live. Browser
speech-to-text does need connectivity; there is a server-transcription fallback
and typing always works.

**"Where do the prices come from?"**
Cost-plus, built from craft-specific material rates and skill-band hourly wages,
then adjusted by measured intricacy, GI status, cluster premium and a seasonal
demand index. Every term is on screen. We are not predicting a market price from
thin air — we are computing what the work is worth and showing the arithmetic.

**"How does it scale past 18 crafts?"**
The taxonomy is a data file, not code. Each entry is a craft's vocabulary,
economics and visual signature. Adding a cluster is adding a record, and the
search index, pricing engine and matching engine pick it up with no code change.

**"What about artisans with no smartphone?"**
The same flow works from a shared phone at a common service centre or an SHG
facilitator, which is how most cluster digitisation actually happens today. The
voice-first design is what makes a shared device workable — nothing depends on
the artisan being able to type.
