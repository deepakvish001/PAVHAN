/**
 * Devanagari → Roman, so Hindi can be *spoken* on a machine with no Hindi voice.
 *
 * This exists because of a failure that looks exactly like "the Hindi is
 * broken" and is nothing of the sort. `speechSynthesis` can only speak a
 * script its installed voices know. Android usually ships a `hi-IN` voice;
 * Windows does not unless someone has added the Hindi language pack, and a
 * cloud VM or a borrowed demo laptop almost never has one. On those machines
 * `getVoices()` returns English voices only, the app hands one of them a
 * string of Devanagari, and the result is silence — while the English
 * assistant on the very same page works perfectly.
 *
 * That asymmetry is the whole bug: English worked, Hindi was mute, and the
 * text on screen was correct the entire time.
 *
 * The fix is to give the English voice something it *can* pronounce. An
 * Indian-English voice reading "yah madhubani mein haath se banaee gaee hai"
 * is understood by a Hindi speaker immediately — it is how Hindi is typed on
 * a phone every day. It is not as good as a real Hindi voice, so a real Hindi
 * voice is always preferred; this is what happens when there is not one.
 *
 * The spellings below are chosen for how an en-IN synthesiser pronounces
 * them, not for scholarly correctness. "ee" rather than "ī" because a TTS
 * engine says "ee" right and "ī" not at all.
 */

// Independent vowels.
const VOWELS = {
  'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo',
  'ऋ': 'ri', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
  'ऑ': 'o', 'ऍ': 'e',
}

// Dependent vowel signs (matras) that follow a consonant.
const MATRAS = {
  'ा': 'aa', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo',
  'ृ': 'ri', 'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au',
  'ॉ': 'o', 'ॅ': 'e',
}

const CONSONANTS = {
  'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
  'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
  'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
  'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
  'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
  'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'ळ': 'l',
  'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
  // Nukta forms, written as single code points. Urdu-origin sounds are
  // everywhere in spoken Hindi — ज़री, क़ीमत, फ़ोटो — and getting them wrong
  // is immediately audible.
  'क़': 'q', 'ख़': 'kh', 'ग़': 'gh', 'ज़': 'z', 'ड़': 'r', 'ढ़': 'rh', 'फ़': 'f',
}

const DIGITS = {
  '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
  '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
}

const VIRAMA = '्'      // suppresses the inherent 'a'
const NUKTA = '़'
const ANUSVARA = 'ं'
const CHANDRABINDU = 'ँ'
const VISARGA = 'ः'

// A handful of words a letter-by-letter pass gets audibly wrong, either
// because Hindi spelling is conservative or because the word is a loan the
// listener expects to hear in its English form.
const WORD_FIXES = {
  'है': 'hai', 'हैं': 'hain', 'हूँ': 'hoon', 'हो': 'ho',
  'और': 'aur', 'में': 'mein', 'से': 'se', 'को': 'ko', 'का': 'ka',
  'की': 'kee', 'के': 'ke', 'यह': 'yeh', 'ये': 'ye', 'वह': 'voh',
  'नहीं': 'nahin', 'क्या': 'kya', 'कर': 'kar', 'रुपये': 'rupaye',
  'रुपए': 'rupaye', 'दिन': 'din', 'आपको': 'aapko', 'आपका': 'aapka',
  'आपकी': 'aapki', 'हाथ': 'haath', 'बनी': 'banee', 'बना': 'bana',
  'गई': 'gayee', 'गया': 'gaya', 'कीमत': 'keemat', 'सीधे': 'seedhe',
  'कारीगर': 'kaareegar', 'जाते': 'jaate', 'जिसमें': 'jismein',
  'नमस्ते': 'namaste', 'स्वागत': 'swaagat', 'धन्यवाद': 'dhanyavaad',
  'पावहन': 'pavhan', 'सामान': 'saamaan', 'फोटो': 'photo', 'बोलिए': 'boliye',
  'लीजिए': 'leejiye', 'दीजिए': 'deejiye', 'कीजिए': 'keejiye',
  'भेज': 'bhej', 'मिला': 'mila', 'दिया': 'diya', 'रंग': 'rang',
  'खरीदार': 'khareedaar', 'पैसा': 'paisa', 'पैसे': 'paise',
  'ऑर्डर': 'order', 'डिलीवरी': 'delivery', 'व्हाट्सऐप': 'WhatsApp',
}

function isDevanagari(ch) {
  const code = ch.codePointAt(0)
  return code >= 0x0900 && code <= 0x097F
}

export function hasDevanagari(text) {
  return /[ऀ-ॿ]/.test(text || '')
}

/**
 * One Devanagari word to Roman, as a list of syllables.
 *
 * Syllables rather than a running string, because the schwa rules below need
 * to look at neighbours: whether the inherent 'a' of a syllable is spoken
 * depends on what comes after it.
 */
function syllabify(word) {
  const parts = []            // {text, vowel, inherent}
  let i = 0

  const push = (text, vowel, inherent = false) => parts.push({ text, vowel, inherent })

  while (i < word.length) {
    const ch = word[i]
    const next = word[i + 1]

    // A consonant may carry a nukta as a separate code point.
    let cons = CONSONANTS[ch]
    let consumed = 1
    if (cons && next === NUKTA) {
      cons = CONSONANTS[ch + NUKTA] || cons
      consumed = 2
    }

    if (cons) {
      i += consumed
      const after = word[i]
      if (after === VIRAMA) {
        push(cons, '', false)            // conjunct — no vowel at all
        i += 1
      } else if (MATRAS[after]) {
        push(cons + MATRAS[after], MATRAS[after], false)
        i += 1
      } else {
        push(cons, 'a', true)            // inherent 'a', kept or dropped later
      }
      continue
    }

    if (VOWELS[ch]) { push(VOWELS[ch], VOWELS[ch]); i += 1; continue }
    if (MATRAS[ch]) { push(MATRAS[ch], MATRAS[ch]); i += 1; continue }
    if (DIGITS[ch]) { push(DIGITS[ch], ''); i += 1; continue }
    if (ch === ANUSVARA || ch === CHANDRABINDU) { push('n', ''); i += 1; continue }
    if (ch === VISARGA) { push('h', ''); i += 1; continue }
    if (ch === VIRAMA || ch === NUKTA) { i += 1; continue }
    if (ch === '।' || ch === '॥') { push('.', ''); i += 1; continue }

    push(ch, '')                         // Latin, digits, punctuation
    i += 1
  }
  return parts
}

/** Does this syllable carry an actual letter, as opposed to punctuation? */
function isLetter(part) {
  return /[a-z0-9]/i.test(part.text)
}

// Punctuation that clings to a word and hid it from the fix table: "रुपये,"
// missed the entry for "रुपये" and came out "rupye" two words after the same
// word had come out "rupaye" correctly.
// Note the danda (।, U+0964) is excluded explicitly: it lives *inside* the
// Devanagari block, so a naive "is this Devanagari" test keeps it glued to
// the word and "रुपये।" never matches the entry for "रुपये".
const EDGE_PUNCT = /^([^\u0900-\u0963\u0966-\u097Fa-z0-9]*)(.*?)([^\u0900-\u0963\u0966-\u097Fa-z0-9]*)$/i

/** One Devanagari word (no spaces) to Roman. */
function wordToLatin(word) {
  const [, before, core, after] = word.match(EDGE_PUNCT) || [null, '', word, '']
  if (WORD_FIXES[core]) {
    return before + WORD_FIXES[core] + after.replace(/[।॥]/g, '.')
  }

  const parts = syllabify(word)
  const letters = parts.filter(isLetter)

  // --- schwa deletion -----------------------------------------------------
  //
  // Hindi writes an 'a' after every bare consonant and then declines to say
  // most of them. Two rules cover the cases that matter, and both err towards
  // keeping the vowel: an extra syllable is understood, a missing one is not.
  //
  // 1. The word-final inherent 'a' always goes. राम is "raam", never
  //    "raama". This one has no exceptions worth worrying about. Punctuation
  //    does not count as the end of the word — "क्लीन।" was coming out as
  //    "kleena." because the danda flushed the pending vowel back in.
  const last = letters[letters.length - 1]
  if (last && last.inherent) last.inherent = false

  // 2. In a three-syllable word whose last syllable has a written vowel, the
  //    middle inherent 'a' goes too: अपने is "apne", करते is "karte".
  //    Deliberately only three syllables. The same rule at four starts
  //    mangling compounds — चित्रकला is "chitrakala", not "chitraklaa" —
  //    and telling a compound from a verb form needs morphology this does
  //    not have.
  if (letters.length === 3 && letters[1].inherent && letters[2].vowel
      && letters[2].vowel !== 'a') {
    letters[1].inherent = false
  }

  return parts
    .map((part) => (part.inherent ? part.text + 'a' : part.text))
    .join('')
}

/**
 * Transliterate a mixed string. Latin runs, digits and punctuation are left
 * exactly as they are, so "कीमत 4249 रुपये" keeps its number.
 */
export function toLatin(text) {
  if (!text) return ''
  if (!hasDevanagari(text)) return text

  return text
    .split(/(\s+)/)
    .map((token) => (token.trim() && [...token].some(isDevanagari)
      ? wordToLatin(token)
      : token))
    .join('')
}

/**
 * Is there a voice on this device that can actually read Devanagari?
 *
 * Anything Indic will do — a Marathi or Nepali voice shares the script and
 * pronounces Hindi far better than an English one does.
 */
export function hasIndicVoice(voices) {
  return (voices || []).some((v) => {
    const tag = `${v.lang || ''} ${v.name || ''}`.toLowerCase()
    return /\bhi[-_]/.test(tag) || tag.includes('hindi')
      || /\bmr[-_]/.test(tag) || tag.includes('marathi')
      || /\bne[-_]/.test(tag) || tag.includes('nepali')
      || /\bsa[-_]/.test(tag) || tag.includes('sanskrit')
  })
}
