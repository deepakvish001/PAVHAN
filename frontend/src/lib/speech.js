/**
 * Breaking speech into pieces a synthesiser will actually finish.
 *
 * Kept out of the React hook so it can be tested with plain node — and
 * because the rule it encodes ("where does a person pause?") is about
 * language, not about components.
 */

// Chrome stops speaking after roughly fifteen seconds and does not fire
// `onend`. It is a decade-old bug and the only reliable workaround is to
// break the text into short utterances and keep nudging the queue. Both are
// done below; this is the length each piece is kept under.
// Chrome cuts speech off at roughly fifteen seconds. A Hindi voice at 0.95
// covers about twenty characters a second, so ~300 characters is the real
// ceiling and 260 leaves room for a slow voice.
//
// The previous value of 170 was cautious to the point of being a bug: it
// split ordinary two-sentence answers that would have been spoken perfectly
// as one, and every split is an audible seam. Splitting is a repair, not an
// improvement — it should happen as rarely as the limit allows.
export const MAX_CHUNK = 260

/**
 * Split speech into utterance-sized pieces, at the places a person pauses.
 *
 * Sentence ends first, then clause commas, and only then a hard cut — a break
 * mid-clause is audible, and a break mid-word is a different word. The pieces
 * also give the synthesiser a natural pause at each boundary, which makes a
 * long passage sound less like it is being read off a card.
 */
export function chunkForSpeech(text, limit = MAX_CHUNK) {
  const clean = String(text || '').replace(/\s+/g, ' ').trim()
  if (!clean) return []
  if (clean.length <= limit) return [clean]

  const sentences = clean.match(/[^।.!?]+[।.!?]*\s*/g) || [clean]
  const out = []
  let buffer = ''

  const flush = () => { if (buffer.trim()) out.push(buffer.trim()); buffer = '' }

  for (const sentence of sentences) {
    if ((buffer + sentence).length <= limit) { buffer += sentence; continue }
    flush()
    if (sentence.length <= limit) { buffer = sentence; continue }

    // One very long sentence: break it on clause commas instead.
    let clause = ''
    for (const piece of sentence.split(/(?<=[,;—])\s*/)) {
      if ((clause + piece).length <= limit) { clause += piece; continue }
      if (clause.trim()) out.push(clause.trim())
      clause = piece
      // Still too long even as one clause — cut on a word boundary.
      while (clause.length > limit) {
        const cut = clause.lastIndexOf(' ', limit)
        out.push(clause.slice(0, cut > 40 ? cut : limit).trim())
        clause = clause.slice(cut > 40 ? cut : limit)
      }
    }
    buffer = clause
  }
  flush()
  return out.filter(Boolean)
}
