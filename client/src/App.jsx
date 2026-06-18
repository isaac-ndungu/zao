import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import Solutions from './pages/Solutions'
import ForFarmers from './pages/ForFarmers'
import About from './pages/About'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/solutions" element={<Solutions />} />
        <Route path="/farmers" element={<ForFarmers />} />
        <Route path="/about" element={<About />} />
      </Routes>
    </BrowserRouter>
  )
}
