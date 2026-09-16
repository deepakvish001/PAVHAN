"""The regional languages an artisan may speak into PAVHAN.

The problem statement asks for voice notes in regional languages, translated
into professional English and Hindi listings. So the INPUT side has to
understand many languages while the OUTPUT side stays fixed at two.

Detection is by Unicode script first, because that is unambiguous and free:
Bengali text can only be Bengali or Assamese, Tamil text can only be Tamil.
Where one script carries several languages — Devanagari holds Hindi, Marathi
and Nepali; Bengali holds Bengali and Assamese — a small set of marker words
separates them. Romanised input (Hinglish and its cousins) falls back to
marker words alone, since the script tells us nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    code: str
    name: str
    native: str
    script: str
    speech_locale: str      # for the browser's SpeechRecognition
    tts_locale: str         # for speech synthesis
    sample: str             # shown on the language picker so it is recognisable


LANGUAGES: list[Language] = [
    Language("hi", "Hindi", "हिंदी", "Devanagari", "hi-IN", "hi-IN",
             "यह हाथ से बनी साड़ी है"),
    Language("en", "English", "English", "Latin", "en-IN", "en-IN",
             "This is a handmade saree"),
    Language("mr", "Marathi", "मराठी", "Devanagari", "mr-IN", "mr-IN",
             "ही हाताने बनवलेली साडी आहे"),
    Language("bn", "Bengali", "বাংলা", "Bengali", "bn-IN", "bn-IN",
             "এটি হাতে তৈরি শাড়ি"),
    Language("as", "Assamese", "অসমীয়া", "Bengali", "as-IN", "as-IN",
             "এইটো হাতেৰে বনোৱা"),
    Language("ta", "Tamil", "தமிழ்", "Tamil", "ta-IN", "ta-IN",
             "இது கையால் செய்த புடவை"),
    Language("te", "Telugu", "తెలుగు", "Telugu", "te-IN", "te-IN",
             "ఇది చేతితో చేసిన చీర"),
    Language("kn", "Kannada", "ಕನ್ನಡ", "Kannada", "kn-IN", "kn-IN",
             "ಇದು ಕೈಯಿಂದ ಮಾಡಿದ ಸೀರೆ"),
    Language("ml", "Malayalam", "മലയാളം", "Malayalam", "ml-IN", "ml-IN",
             "ഇത് കൈകൊണ്ട് ഉണ്ടാക്കിയ സാരി"),
    Language("gu", "Gujarati", "ગુજરાતી", "Gujarati", "gu-IN", "gu-IN",
             "આ હાથથી બનાવેલી સાડી છે"),
    Language("pa", "Punjabi", "ਪੰਜਾਬੀ", "Gurmukhi", "pa-IN", "pa-IN",
             "ਇਹ ਹੱਥ ਨਾਲ ਬਣੀ ਸਾੜੀ ਹੈ"),
    Language("or", "Odia", "ଓଡ଼ିଆ", "Odia", "or-IN", "or-IN",
             "ଏହା ହାତରେ ତିଆରି ଶାଢ଼ୀ"),
]

BY_CODE: dict[str, Language] = {lang.code: lang for lang in LANGUAGES}

# Unicode blocks. One range per script; the first match wins.
SCRIPT_RANGES: list[tuple[str, tuple[int, int]]] = [
    ("Devanagari", (0x0900, 0x097F)),
    ("Bengali", (0x0980, 0x09FF)),
    ("Gurmukhi", (0x0A00, 0x0A7F)),
    ("Gujarati", (0x0A80, 0x0AFF)),
    ("Odia", (0x0B00, 0x0B7F)),
    ("Tamil", (0x0B80, 0x0BFF)),
    ("Telugu", (0x0C00, 0x0C7F)),
    ("Kannada", (0x0C80, 0x0CFF)),
    ("Malayalam", (0x0D00, 0x0D7F)),
]

# A script shared by more than one language needs a tiebreaker. These are
# everyday function words that differ between the pair, not craft vocabulary.
SCRIPT_DEFAULT = {
    "Devanagari": "hi", "Bengali": "bn", "Gurmukhi": "pa", "Gujarati": "gu",
    "Odia": "or", "Tamil": "ta", "Telugu": "te", "Kannada": "kn",
    "Malayalam": "ml",
}

# A script shared by more than one language needs a tiebreaker, and romanised
# speech needs one for every language. Both kinds live in the same list per
# language — note that a dict literal cannot carry the same key twice, which
# is exactly the bug that made Marathi resolve to Hindi.
MARKERS: dict[str, list[str]] = {
    "hi": ["hai", "hain", "humne", "hamne", "isme", "iska", "banaya", "yeh", "aur ",
           "मैंने", "हमने", "इसमें", "बनाया"],
    "mr": ["आहे", "आहेत", "मी ", "ही ", "हे ", "माझ", "केले", "बनवले", "पासून", "साठी",
           "aahe", "ahe", "mi ", "maza", "kelay", "banavla", "pasun"],
    "as": ["আছে", "কৰা", "কৰি", "মোৰ", "হৈছে", "বনোৱা", "এইটো"],
    "bn": ["আমার", "এটি", "তৈরি", "হয়েছে", "করেছি",
           "ache", "ami ", "eta ", "korechi", "banano", "amar "],
    "ta": ["irukku", "naan ", "idhu ", "seitha", "panna"],
    "te": ["undi", "nenu ", "idi ", "chesina", "cheyyi"],
    "kn": ["ide ", "naanu ", "idu ", "madida"],
    "ml": ["aanu", "njan ", "ithu ", "undakkiya"],
    "gu": ["chhe", "hu ", "aa ", "banavelu", "maru "],
    "pa": ["main ", "eh ", "banai", "mera "],
    "or": ["achhi", "mu ", "eha ", "tiari"],
}


def script_of(text: str) -> str:
    """The dominant Indic script in a string, or 'Latin'."""
    counts: dict[str, int] = {}
    for ch in text:
        point = ord(ch)
        for script, (low, high) in SCRIPT_RANGES:
            if low <= point <= high:
                counts[script] = counts.get(script, 0) + 1
                break
    if not counts:
        return "Latin"
    return max(counts, key=lambda k: counts[k])


def _marker_hits(text: str, code: str) -> int:
    low = f" {text.lower()} "
    return sum(1 for word in MARKERS.get(code, []) if word.lower() in low)


def detect(text: str, *, hint: str | None = None) -> str:
    """Best guess at the language of a voice transcript.

    `hint` is the language the artisan picked in the app. It wins whenever the
    script is consistent with it, because a person who selected Tamil and then
    spoke Tamil should not be second-guessed by a heuristic.
    """
    text = (text or "").strip()
    if not text:
        return hint or "hi"

    script = script_of(text)

    if script == "Latin":
        # Romanised. Marker words are the only signal; English is the default
        # because an artisan typing Latin script with no regional markers is
        # most likely writing English.
        scores = {code: _marker_hits(text, code)
                  for code in ("hi", "mr", "bn", "ta", "te", "kn", "ml", "gu", "pa", "or")}
        best = max(scores, key=lambda k: scores[k])
        if scores[best] == 0:
            return "en"
        if hint and scores.get(hint, 0) == scores[best]:
            return hint          # a tie goes to what the artisan told us
        return best

    base = SCRIPT_DEFAULT.get(script, "hi")

    # Resolve the two shared scripts.
    if script == "Devanagari" and _marker_hits(text, "mr") >= 2:
        base = "mr"
    elif script == "Bengali" and _marker_hits(text, "as") >= 1:
        base = "as"

    # Honour the hint when it uses the same script — it distinguishes cases
    # the markers cannot, such as a short Marathi phrase with no marker word.
    if hint and BY_CODE.get(hint) and BY_CODE[hint].script == script:
        if base != hint and _marker_hits(text, base) == 0:
            return hint
    return base


def language_list() -> list[dict]:
    return [
        {"code": lang.code, "name": lang.name, "native": lang.native,
         "script": lang.script, "speech_locale": lang.speech_locale,
         "tts_locale": lang.tts_locale, "sample": lang.sample}
        for lang in LANGUAGES
    ]
