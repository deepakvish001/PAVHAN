/**
 * Numbers as a Hindi speaker says them.
 *
 * On a device with no Hindi voice the app reads romanised Hindi through an
 * Indian-English voice, and that voice reads "4249" as "four thousand two
 * hundred forty-nine" — English digits dropped into the middle of a Hindi
 * sentence, and dropped in exactly where they matter most, because the
 * numbers in this app are what the artisan is being paid.
 *
 * "chaar hazaar do sau unachaas rupaye" is what they would actually say.
 *
 * Hindi numerals below a hundred are irregular the whole way — 52 is
 * "baavan", not "paanch-do" or "pachaas-do" — so there is no generating them
 * from rules. The table is the implementation.
 *
 * Spellings are chosen for how an Indian-English synthesiser pronounces them.
 */

const ONES = [
  'shoonya', 'ek', 'do', 'teen', 'chaar', 'paanch', 'chhah', 'saat', 'aath',
  'nau', 'das', 'gyaarah', 'baarah', 'terah', 'chaudah', 'pandrah', 'solah',
  'satrah', 'atthaarah', 'unnees', 'bees', 'ikkees', 'baaees', 'teees',
  'chaubees', 'pachchees', 'chhabbees', 'sattaaees', 'atthaaees', 'untees',
  'tees', 'ikattees', 'battees', 'taintees', 'chauntees', 'paintees',
  'chhattees', 'saintees', 'adtees', 'untaalees', 'chaalees', 'iktaalees',
  'bayaalees', 'taintaalees', 'chavaalees', 'paintaalees', 'chhiyaalees',
  'saintaalees', 'adtaalees', 'unchaas', 'pachaas', 'ikyaavan', 'baavan',
  'tirpan', 'chauvan', 'pachpan', 'chhappan', 'sattaavan', 'atthaavan',
  'unsath', 'saath', 'iksath', 'baasath', 'tirsath', 'chausath', 'painsath',
  'chhiyaasath', 'sarsath', 'adsath', 'unhattar', 'sattar', 'ikhattar',
  'bahattar', 'tihattar', 'chauhattar', 'pachhattar', 'chhihattar',
  'sathattar', 'athhattar', 'unaasee', 'assee', 'ikyaasee', 'bayaasee',
  'tiraasee', 'chauraasee', 'pachaasee', 'chhiyaasee', 'sattaasee',
  'atthaasee', 'navaasee', 'nabbe', 'ikyaanave', 'baanave', 'tiraanave',
  'chauraanave', 'pachaanave', 'chhiyaanave', 'sattaanave', 'atthaanave',
  'ninyaanave',
]

/** A whole number, 0 to 99,99,99,999, in Hindi words. */
export function toHindiWords(value) {
  let n = Math.floor(Math.abs(Number(value) || 0))
  if (n === 0) return ONES[0]
  if (n > 999999999) return null          // beyond what this app ever says

  const parts = []
  // Indian grouping, largest first: crore, lakh, thousand, hundred, rest.
  const groups = [
    [10000000, 'karod'],
    [100000, 'laakh'],
    [1000, 'hazaar'],
    [100, 'sau'],
  ]
  for (const [size, word] of groups) {
    const count = Math.floor(n / size)
    if (count) {
      parts.push(`${ONES[count] || toHindiWords(count)} ${word}`)
      n -= count * size
    }
  }
  if (n) parts.push(ONES[n])
  return parts.join(' ')
}

// A run of digits that is a *quantity*, not an identity. Comma grouping is a
// strong signal of money; four digits or fewer is a count or a small price.
// Longer bare runs — a pincode, an AWB, a phone number, an order id — are
// deliberately left alone, because "do do ek zero zero ek" is how a pincode
// should be read and "do laakh ikkees hazaar ek" is not.
const QUANTITY = /(?<![\d.,])(\d{1,3}(?:,\d{2,3})+|\d{1,4})(?![\d.,])/g

/**
 * Replace the quantities in a string with Hindi words.
 *
 * Only for the romanised path: a real Hindi voice reads digits in Hindi by
 * itself, and rewriting them would take a good reading and make it wordier.
 */
export function speakNumbersInHindi(text) {
  if (!text) return text
  return text.replace(QUANTITY, (match) => {
    const plain = match.replace(/,/g, '')
    if (plain.length > 9) return match
    // A leading zero means it is an identifier, not a count.
    if (plain.length > 1 && plain.startsWith('0')) return match
    const words = toHindiWords(plain)
    return words || match
  })
}
