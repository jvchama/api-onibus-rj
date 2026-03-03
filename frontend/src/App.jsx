// App.jsx — raiz da aplicação: define as rotas e inclui a Navbar
// Antes: boilerplate padrão do Vite (contador, logos)

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import RegisterPage from './pages/RegisterPage'
import TrackPage from './pages/TrackPage'

function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        {/* Redireciona raiz para /register */}
        <Route path="/" element={<Navigate to="/register" replace />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/track" element={<TrackPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
