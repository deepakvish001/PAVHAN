/* PAVHAN service worker.
 *
 * Rural connectivity drops mid-task, and the worst moment for that is after an
 * artisan has spent two minutes photographing and describing a piece. So:
 *
 *   app shell   -> cache first, network in the background. The app always opens.
 *   API reads   -> network first, fall back to the last good response. Stale
 *                  prices beat a blank screen.
 *   API writes  -> never cached. A queued POST that silently replays later
 *                  would publish a listing the artisan thought had failed.
 *
 * Media is cached separately and capped, because studio output is large and an
 * unbounded cache on a cheap phone is its own kind of failure.
 */

const VERSION = 'pavhan-v1'
const SHELL = `${VERSION}-shell`
const DATA = `${VERSION}-data`
const MEDIA = `${VERSION}-media`
const MEDIA_LIMIT = 60

const SHELL_URLS = ['/', '/manifest.webmanifest', '/icon.svg']

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL)
      .then((cache) => cache.addAll(SHELL_URLS))
      .then(() => self.skipWaiting())
      .catch(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k)),
      ))
      .then(() => self.clients.claim()),
  )
})

async function trim(cacheName, limit) {
  const cache = await caches.open(cacheName)
  const keys = await cache.keys()
  if (keys.length <= limit) return
  await Promise.all(keys.slice(0, keys.length - limit).map((k) => cache.delete(k)))
}

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return          // writes are never intercepted

  const url = new URL(request.url)
  if (url.origin !== self.location.origin) return

  // Media: cache first, and keep the cache bounded.
  if (url.pathname.startsWith('/media/') || url.pathname.startsWith('/seed/')) {
    event.respondWith((async () => {
      const cached = await caches.match(request)
      if (cached) return cached
      try {
        const response = await fetch(request)
        if (response.ok) {
          const cache = await caches.open(MEDIA)
          cache.put(request, response.clone())
          trim(MEDIA, MEDIA_LIMIT)
        }
        return response
      } catch {
        return new Response('', { status: 504 })
      }
    })())
    return
  }

  // API reads: fresh if possible, last known good if not.
  if (url.pathname.startsWith('/api/')) {
    event.respondWith((async () => {
      try {
        const response = await fetch(request)
        if (response.ok) {
          const cache = await caches.open(DATA)
          cache.put(request, response.clone())
        }
        return response
      } catch {
        const cached = await caches.match(request)
        if (cached) {
          // Mark it so the app can say "showing saved data" rather than
          // presenting a stale price as if it were live.
          const body = await cached.text()
          return new Response(body, {
            status: 200,
            headers: { 'Content-Type': 'application/json', 'X-PAVHAN-Offline': '1' },
          })
        }
        return new Response(JSON.stringify({ detail: 'You are offline.' }), {
          status: 503, headers: { 'Content-Type': 'application/json' },
        })
      }
    })())
    return
  }

  // App shell and assets: serve instantly, refresh in the background.
  event.respondWith((async () => {
    const cached = await caches.match(request)
    const network = fetch(request).then((response) => {
      if (response.ok) caches.open(SHELL).then((c) => c.put(request, response.clone()))
      return response
    }).catch(() => null)
    if (cached) return cached
    const fresh = await network
    if (fresh) return fresh
    // A navigation with nothing cached still has to render something.
    return (await caches.match('/')) || new Response('', { status: 504 })
  })())
})
