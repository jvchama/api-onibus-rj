// Navbar.jsx — barra de navegação fixa no topo
// NavLink do react-router-dom adiciona a classe "active" automaticamente
// na rota atual, o que o CSS em index.css usa para destacar o link ativo.

import { NavLink } from 'react-router-dom'

function Navbar() {
  return (
    <nav className="navbar">
      <span className="navbar-brand">Maravi</span>
      <NavLink to="/register">Cadastrar Alerta</NavLink>
      <NavLink to="/track">Rastrear Ônibus</NavLink>
    </nav>
  )
}

export default Navbar
