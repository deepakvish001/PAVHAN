/**
 * The outbox: cataloguing a piece with no signal at all.
 *
 * This is the feature the whole "rural artisan" framing stands or falls on.
 * An artisan in a Bhadohi village has a phone and, for most of the day, no
 * usable data connection. If the app can only work online, then every claim
 * about reaching that artisan is a claim about the artisans who happen to
 * live near a tower.
 *
 * Two decisions shape it.
 *
 * **The queue is visible, not a silent background sync.** The service worker
 * deliberately never replays writes — a POST that quietly succeeds an hour
 * later publishes a listing the artisan believed had failed, at a price they
 * may since have changed their mind about. So instead of hiding the retry,
 * the app shows it: "3 items waiting to send", with what each one is and when
 * it was recorded. The artisan is told the truth and keeps control.
 *
 * **What is queued is the raw capture, not a finished listing.** Offline, the
 * AI pipeline is unreachable — there is no price, no description, no craft
 * identification. So the phone keeps exactly what the artisan produced, a
 * photograph and a spoken sentence, and the whole pipeline runs on send.
 * The artisan's work is never lost; only its processing is deferred.
 *
 * IndexedDB rather than localStorage, because a photograph is a Blob and
 * localStorage holds about five megabytes of string.
 */

import { analyzeImage, createProduct, generateListing } from '../api/client'

const DB_NAME = 'pavhan-outbox'
const STORE = 'items'
const DB_VERSION = 1

// After this many failed attempts, stop retrying automatically and show the
// artisan the error. A queue that retries for ever against a genuine problem
// (a rejected field, a listing the server will never accept) burns the
// battery and never tells anyone why.
export const MAX_ATTEMPTS = 5

const listeners = new Set()

export function onOutboxChange(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

function announce() {
  listeners.forEach((fn) => { try { fn() } catch { /* a listener must not break the queue */ } })
}

function openDb() {
  return new Promise((resolve, reject) => {
    if (!('indexedDB' in window)) { reject(new Error('This browser has no offline storage')); return }
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: 'id' })
      }
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error || new Error('Could not open offline storage'))
  })
}

async function tx(mode, fn) {
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const t = db.transaction(STORE, mode)
    const store = t.objectStore(STORE)
    let result
    try { result = fn(store) } catch (err) { reject(err); return }
    t.oncomplete = () => { db.close(); resolve(result) }
    t.onerror = () => { db.close(); reject(t.error) }
  })
}

function newId() {
  // Also the server-side idempotency key, so a send that is interrupted after
  // the server committed but before the phone heard the reply cannot publish
  // the same piece twice. crypto.randomUUID is unavailable on insecure
  // origins, which is exactly where this app sometimes runs.
  const rand = () => Math.random().toString(36).slice(2, 10)
  return (window.crypto?.randomUUID?.() || `${Date.now().toString(36)}-${rand()}${rand()}`)
    .replace(/-/g, '').slice(0, 32)
}

/** Hold a capture until there is a connection. */
export async function enqueue({ photo, transcript, language, artisanId, label }) {
  const item = {
    id: newId(),
    kind: 'listing',
    photo: photo || null,          // a Blob; IndexedDB stores these natively
    transcript: transcript || '',
    language: language || 'hi',
    artisanId: artisanId || '',
    label: label || (transcript || '').slice(0, 60),
    createdAt: Date.now(),
    attempts: 0,
    lastError: '',
    status: 'waiting',
  }
  await tx('readwrite', (store) => store.put(item))
  announce()
  return item
}

export async function listItems() {
  const rows = await tx('readonly', (store) => {
    const out = []
    store.openCursor().onsuccess = (e) => {
      const cursor = e.target.result
      if (cursor) { out.push(cursor.value); cursor.continue() }
    }
    return out
  })
  return rows.sort((a, b) => a.createdAt - b.createdAt)
}

export async function removeItem(id) {
  await tx('readwrite', (store) => store.delete(id))
  announce()
}

export async function clearSent() {
  const rows = await listItems()
  await tx('readwrite', (store) => {
    rows.filter((r) => r.status === 'sent').forEach((r) => store.delete(r.id))
  })
  announce()
}

async function update(id, patch) {
  const rows = await listItems()
  const row = rows.find((r) => r.id === id)
  if (!row) return null
  const next = { ...row, ...patch }
  await tx('readwrite', (store) => store.put(next))
  announce()
  return next
}

/** Retry one item the artisan gave up on, ignoring the attempt cap. */
export async function retryItem(id) {
  await update(id, { attempts: 0, lastError: '', status: 'waiting' })
}

async function send(item) {
  // The pipeline the artisan would have run online, in the same order.
  let imageId = ''
  if (item.photo) {
    const file = item.photo instanceof File
      ? item.photo
      : new File([item.photo], 'capture.jpg', { type: item.photo.type || 'image/jpeg' })
    const vision = await analyzeImage(file)
    imageId = vision?.image_id || ''
  }
  const listing = await generateListing({
    transcript: item.transcript, image_id: imageId,
    language: item.language, use_llm: 'true',
  })

  const payload = {
    title: listing.title,
    short_description: listing.short_description,
    detailed_description: listing.detailed_description,
    story: listing.story,
    title_hi: listing.title_hi || '',
    short_description_hi: listing.short_description_hi || '',
    detailed_description_hi: listing.detailed_description_hi || '',
    story_hi: listing.story_hi || '',
    care_hi: listing.care_hi || '',
    craft_type: listing.craft_type,
    category: listing.category,
    material: listing.material,
    colour: listing.colour,
    region: listing.region,
    size: listing.size,
    weight: listing.weight,
    care: listing.care,
    technique: listing.technique,
    price: listing.price,
    price_floor: listing.price_floor,
    price_premium: listing.price_premium,
    quality_score: listing.quality_score,
    sustainability_score: listing.sustainability_score,
    gi_tagged: listing.gi_tagged,
    tags: listing.tags || [],
    keywords: listing.keywords || [],
    images: listing.images || [],
    palette: listing.palette || [],
    ai_meta: listing.ai_meta || {},
    pricing_meta: listing.pricing_meta || {},
    lead_time_days: listing.lead_time_days,
    moq: listing.moq || 1,
    stock: 5,
    artisan_id: item.artisanId || null,
    client_ref: item.id,
  }
  return createProduct(payload)
}

let flushing = false

/**
 * Send everything that is waiting.
 *
 * Serial, not parallel: these are photo uploads over the connection that just
 * came back, and firing five at once on a two-bar signal is how all five time
 * out together.
 */
export async function flush() {
  if (flushing) return { skipped: true }
  if (!navigator.onLine) return { offline: true, sent: 0, failed: 0 }
  flushing = true
  let sent = 0
  let failed = 0
  try {
    const rows = await listItems()
    for (const item of rows) {
      if (item.status === 'sent') continue
      if (item.attempts >= MAX_ATTEMPTS) continue
      await update(item.id, { status: 'sending' })
      try {
        const product = await send(item)
        await update(item.id, {
          status: 'sent', productId: product.id,
          title: product.title, lastError: '',
        })
        sent += 1
      } catch (err) {
        failed += 1
        await update(item.id, {
          status: 'waiting',
          attempts: (item.attempts || 0) + 1,
          lastError: err?.message || 'Could not send',
        })
        // A failure here is usually the connection dropping again. Stop
        // rather than grinding through the rest of the queue against a
        // network that has already gone.
        if (!navigator.onLine) break
      }
    }
  } finally {
    flushing = false
    announce()
  }
  return { sent, failed }
}

/** Start listening for the connection coming back. */
export function watchConnection() {
  const go = () => { flush() }
  window.addEventListener('online', go)
  // Also on wake: a phone that was asleep when the signal returned never
  // fires an 'online' event.
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && navigator.onLine) flush()
  })
  return () => window.removeEventListener('online', go)
}
