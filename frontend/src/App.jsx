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

/** Screens behind the role gate — visiting them without a role sends you to
 *  the front door, which is where the app asks who you are. */
function RequireRole({ children }) {
  const { role } = useApp()
  const location = useLocation()
  if (!role) return <Navigate to="/" replace state={{ from: location.pathname }} />
  return children
}

export default function App() {
  const { assistant } = useApp()
  const { pathname } = useLocation()

  // Stop the guide mid-sentence when the user navigates away — nothing feels
  // more broken than a voice describing the previous screen.
  useEffect(() => { assistant.cancel() }, [pathname]) // eslint-disable-line

  return (
    <div className="app-frame">
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
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  )
}
