/** Thin API client. Every call returns parsed JSON or throws an Error whose
 *  message is safe to show a user. */

const BASE = import.meta.env.VITE_API_BASE || ''

async function handle(res) {
  if (res.status === 204) return null
  let body = null
  try { body = await res.json() } catch { /* empty or non-JSON body */ }
  if (!res.ok) {
    const detail = body?.detail
    throw new Error(
      typeof detail === 'string' ? detail
        : Array.isArray(detail) ? detail.map((d) => d.msg).join(', ')
        : `Request failed (${res.status})`,
    )
  }
  return body
}

export function qsPublic(params) {
  return qs(params)
}

function qs(params = {}) {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null && v !== '' && v !== false,
  )
  return entries.length ? `?${new URLSearchParams(entries)}` : ''
}

export const api = {
  get: (path, params) => fetch(`${BASE}${path}${qs(params)}`).then(handle),

  post: (path, body) => fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(handle),

  patch: (path, body) => fetch(`${BASE}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(handle),

  form: (path, fields) => {
    const data = new FormData()
    Object.entries(fields).forEach(([k, v]) => {
      if (v !== undefined && v !== null) data.append(k, v)
    })
    return fetch(`${BASE}${path}`, { method: 'POST', body: data }).then(handle)
  },
}

// --- domain helpers ------------------------------------------------------
export const health = () => api.get('/api/health')
export const aiStatus = () => api.get('/api/ai/status')

export const analyzeImage = (file) => api.form('/api/ai/analyze-image', { file })
export const coach = (transcript, language) => api.form('/api/ai/coach', { transcript, language })
export const generateListing = (payload) => api.form('/api/ai/generate-listing', payload)
export const transcribeAudio = (file, language) =>
  api.form('/api/ai/transcribe', { file, language })

export const listProducts = (params) => api.get('/api/products', params)
export const featuredProducts = (limit = 8) => api.get('/api/products/featured', { limit })
export const getProduct = (id) => api.get(`/api/products/${id}`)
export const similarProducts = (id, limit = 6) => api.get(`/api/products/${id}/similar`, { limit })
export const createProduct = (payload) => api.post('/api/products', payload)
export const updateProduct = (id, payload) => api.patch(`/api/products/${id}`, payload)

export const search = (params) => api.get('/api/search', params)
export const suggest = (q) => api.get('/api/search/suggest', { q })
export const facets = () => api.get('/api/search/facets')
export const trending = () => api.get('/api/search/trending')

export const recommendPrice = (payload) => api.post('/api/pricing/recommend', payload)
export const priceForProduct = (id, params) => api.get(`/api/pricing/product/${id}`, params)
export const marketContext = () => api.get('/api/pricing/market-context')
export const craftList = () => api.get('/api/pricing/crafts')

export const listBuyers = (params) => api.get('/api/buyers', params)
export const matchBuyers = (productId, params) => api.get(`/api/buyers/match/${productId}`, params)
export const buyerRecommendations = (buyerId) =>
  api.get(`/api/buyers/${buyerId}/recommended-products`)
export const sendEnquiry = (payload) => api.post('/api/buyers/enquiries', payload)
export const artisanEnquiries = (id) => api.get(`/api/buyers/enquiries/for-artisan/${id}`)

export const listUsers = (role) => api.get('/api/users', { role })
export const dashboard = (id) => api.get(`/api/artisans/${id}/dashboard`)
export const placeOrder = (payload) => api.post('/api/orders', payload)
export const platformStats = () => api.get('/api/stats/platform')

export const voiceWelcome = (role, lang) => api.get('/api/voice/welcome', { role, lang })
export const voiceScripts = (lang) => api.get('/api/voice/scripts', { lang })
export const voiceRoles = (lang) => api.get('/api/voice/roles', { lang })
export const voiceLabels = (lang) => api.get('/api/voice/labels', { lang })
export const voiceLanguages = () => api.get('/api/voice/languages')

// --- pricing model -------------------------------------------------------
export const priceModelCard = () => api.get('/api/pricing/model')

// --- government e-marketplace -------------------------------------------
export const exportFormats = () => api.get('/api/export/formats')
export const exportReadiness = (id) => api.get(`/api/export/readiness/${id}`)
export const exportPackage = (id, format = 'json') =>
  api.get(`/api/export/${id}`, { format })
export const exportDownloadUrl = (id, format) =>
  `/api/export/${id}?format=${format}&download=true`
export const bulkCatalogueUrl = (artisanId) => `/api/export/bulk/artisan/${artisanId}`

// --- MoSJE scheme impact -------------------------------------------------
export const schemeList = () => api.get('/api/impact/schemes')
export const linkScheme = (artisanId, payload) =>
  api.post(`/api/impact/artisan/${artisanId}/link`, payload)
export const artisanImpact = (artisanId) => api.get(`/api/impact/artisan/${artisanId}`)
export const ministryReport = () => api.get('/api/impact/ministry')
export const ministryCsvUrl = () => '/api/impact/ministry.csv'

// --- physical fairs ------------------------------------------------------
export const listFairs = () => api.get('/api/fairs')
export const createStall = (payload) => api.post('/api/fairs/stall', payload)
export const artisanStalls = (artisanId) => api.get(`/api/fairs/artisan/${artisanId}/stalls`)
export const stallStorefront = (code, follow = false) =>
  api.get(`/api/fairs/stall/${code}`, { follow })
export const stallPerformance = (code) => api.get(`/api/fairs/stall/${code}/performance`)

// --- two-way B2B ---------------------------------------------------------
export const listRequirements = (artisanId) =>
  api.get('/api/trade/requirements', { artisan_id: artisanId })
export const getRequirement = (id) => api.get(`/api/trade/requirements/${id}`)
export const createRequirement = (payload) => api.post('/api/trade/requirements', payload)
export const sendQuote = (payload) => api.post('/api/trade/quotes', payload)
export const artisanQuotes = (id) => api.get(`/api/trade/quotes/artisan/${id}`)
export const acceptQuote = (id) => api.post(`/api/trade/quotes/${id}/accept`)

// --- orders --------------------------------------------------------------
export const artisanOrders = (id) => api.get(`/api/trade/orders/artisan/${id}`)
export const advanceOrder = (id, to) =>
  api.post(`/api/trade/orders/${id}/advance${qsPublic({ to })}`)

// --- AI Product Studio ---------------------------------------------------
export const studioStatus = () => api.get('/api/studio/status')
export const enhancePhoto = (file, background = 'white') =>
  api.form('/api/studio/enhance', { file, background })

// --- assistant -----------------------------------------------------------
export const askAssistant = (message, lang, artisanId) =>
  api.post(`/api/assistant/ask${qsPublic({ message, lang, artisan_id: artisanId })}`)
export const assistantSuggestions = (lang) => api.get('/api/assistant/suggestions', { lang })

// --- auth ----------------------------------------------------------------
export const requestOtp = (phone) => api.post('/api/auth/request-otp', { phone })
export const verifyOtp = (payload) => api.post('/api/auth/verify-otp', payload)
export const completeProfile = (payload) => api.post('/api/auth/complete-profile', payload)
export const whoAmI = (token) => api.get('/api/auth/me', { token })

// --- profile -------------------------------------------------------------
export const updateUser = (id, payload) => api.patch(`/api/users/${id}`, payload)

// --- payments ------------------------------------------------------------
export const checkVpa = (vpa) => api.get('/api/payments/check-vpa', { vpa })
export const saveVpa = (artisanId, payload) =>
  api.post(`/api/payments/artisan/${artisanId}/vpa`, payload)
export const orderPayment = (orderId) => api.get(`/api/payments/order/${orderId}`)
export const raisePayment = (orderId, payload) =>
  api.post(`/api/payments/order/${orderId}/intent`, payload)
export const confirmPayment = (paymentId, payload) =>
  api.post(`/api/payments/${paymentId}/confirm`, payload)
export const releasePayment = (paymentId) => api.post(`/api/payments/${paymentId}/release`)
export const refundPayment = (paymentId) => api.post(`/api/payments/${paymentId}/refund`)
export const paymentStatement = (artisanId) => api.get(`/api/payments/artisan/${artisanId}`)

// --- logistics -----------------------------------------------------------
export const lookupPincode = (pin) => api.get(`/api/logistics/pincode/${pin}`)
export const shippingOptions = (orderId, toPincode) =>
  api.get(`/api/logistics/order/${orderId}/options`, { to_pincode: toPincode })
export const bookShipment = (orderId, payload) =>
  api.post(`/api/logistics/order/${orderId}/book`, payload)
export const orderShipment = (orderId) => api.get(`/api/logistics/order/${orderId}/shipment`)
export const trackShipment = (awb) => api.get(`/api/logistics/track/${awb}`)
export const advanceShipment = (id, to) =>
  api.post(`/api/logistics/shipment/${id}/advance${qsPublic({ to })}`)

// --- self-help group pooling --------------------------------------------
export const poolCluster = (artisanId, deliveryDays) =>
  api.get(`/api/collective/cluster/${artisanId}`, { delivery_days: deliveryDays })
export const previewPool = (payload) => api.post('/api/collective/plan', payload)
export const createPool = (payload) => api.post('/api/collective/pools', payload)
export const getPool = (id) => api.get(`/api/collective/pools/${id}`)
export const respondToPool = (poolId, memberId, payload) =>
  api.post(`/api/collective/pools/${poolId}/members/${memberId}/respond`, payload)
export const submitPoolQuote = (poolId) => api.post(`/api/collective/pools/${poolId}/quote`)
export const artisanPools = (artisanId) => api.get(`/api/collective/artisan/${artisanId}/pools`)

// --- share ---------------------------------------------------------------
export const shareProduct = (id, lang, phone) =>
  api.get(`/api/share/product/${id}`, { lang, phone })
export const shareOrder = (id, lang) => api.get(`/api/share/order/${id}`, { lang })
export const shareStall = (code, lang) => api.get(`/api/share/stall/${code}`, { lang })
