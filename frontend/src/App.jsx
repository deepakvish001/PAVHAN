import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import { useApp } from './context/AppContext'

import Welcome from './pages/Welcome'
import ArtisanHome from './pages/ArtisanHome'
import AddProduct from './pages/AddProduct'
import MyProducts from './pages/MyProducts'
import BuyerMatching from './pages/BuyerMatching'
import Marketplace from './pages/Marketplace'
import SearchPage from './pages/SearchPage'
import ProductDetail from './pages/ProductDetail'
import B2BHome from './pages/B2BHome'
import Profile from './pages/Profile'
import Login from './pages/Login'
import Assistant from './pages/Assistant'
import MarketplaceExport from './pages/MarketplaceExport'
import Impact from './pages/Impact'
import FairMode from './pages/FairMode'
import Storefront from './pages/Storefront'
import Orders from './pages/Orders'
import Requirements from './pages/Requirements'
import Outbox from './pages/Outbox'
import Earnings from './pages/Earnings'
import OrderPayment from './pages/OrderPayment'
import Shipping from './pages/Shipping'
import Pooling from './pages/Pooling'

/** Screens behind the role gate — visiting them without a role sends you to
 *  the front door, which is where the app asks who you are. */
function RequireRole({ children }) {
  const { role } = useApp()
  const location = useLocation()
  if (!role) return <Navigate to="/" replace state={{ from: location.pathname }} />
  return children
}

export default function App() {
  const { cancelUnlessProtected } = useApp()
  const { pathname } = useLocation()

  // Stop the guide when the user navigates away — nothing feels more broken
  // than a voice describing the previous screen. The one exception is a
  // greeting that was deliberately started alongside a navigation.
  useEffect(() => { cancelUnlessProtected() }, [pathname]) // eslint-disable-line

  return (
    <div className="app-frame">
      <a className="skip-link" href="#main">Skip to content</a>
      <div className="app-shell">
        <Routes>
          <Route path="/" element={<Welcome />} />
          <Route path="/artisan" element={<RequireRole><ArtisanHome /></RequireRole>} />
          <Route path="/artisan/products" element={<RequireRole><MyProducts /></RequireRole>} />
          <Route path="/artisan/buyers" element={<RequireRole><BuyerMatching /></RequireRole>} />
          <Route path="/add" element={<RequireRole><AddProduct /></RequireRole>} />
          <Route path="/shop" element={<Marketplace />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/product/:id" element={<ProductDetail />} />
          <Route path="/b2b" element={<B2BHome />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/login" element={<Login />} />
          <Route path="/assistant" element={<Assistant />} />
          <Route path="/export/:id" element={<MarketplaceExport />} />
          <Route path="/impact" element={<Impact />} />
          <Route path="/fairs" element={<RequireRole><FairMode /></RequireRole>} />
          <Route path="/orders" element={<RequireRole><Orders /></RequireRole>} />
          <Route path="/requirements" element={<RequireRole><Requirements /></RequireRole>} />
          <Route path="/outbox" element={<RequireRole><Outbox /></RequireRole>} />
          <Route path="/earnings" element={<RequireRole><Earnings /></RequireRole>} />
          <Route path="/pooling" element={<RequireRole><Pooling /></RequireRole>} />
          <Route path="/orders/:orderId/pay" element={<RequireRole><OrderPayment /></RequireRole>} />
          <Route path="/orders/:orderId/ship" element={<RequireRole><Shipping /></RequireRole>} />
          {/* A stall QR must open for anyone, with no role and no sign-in. */}
          <Route path="/s/:code" element={<Storefront />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  )
}
