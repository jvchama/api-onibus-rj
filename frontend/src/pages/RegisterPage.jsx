// RegisterPage.jsx — formulário para cadastrar alertas de proximidade.
// Após POST bem-sucedido, incrementa `refreshKey` para forçar o
// RegistrationList a rebuscar a lista atualizada.

import { useState } from 'react'
import RegistrationList from '../components/RegistrationList'

// Estado inicial do formulário — centralizado para facilitar o reset
const FORM_INICIAL = {
  email: '',
  bus_line: '',
  stop_lat: '',
  stop_lon: '',
  window_start: '',
  window_end: '',
}

function RegisterPage() {
  const [form, setForm] = useState(FORM_INICIAL)
  const [enviando, setEnviando] = useState(false)
  const [msg, setMsg] = useState(null) // { tipo: 'success'|'error', texto: '...' }
  const [refreshKey, setRefreshKey] = useState(0)

  function handleChange(e) {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setEnviando(true)
    setMsg(null)

    // Converte lat/lon de string para número antes de enviar
    const payload = {
      ...form,
      stop_lat: parseFloat(form.stop_lat),
      stop_lon: parseFloat(form.stop_lon),
    }

    try {
      const res = await fetch('/registrations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (res.ok) {
        setMsg({ tipo: 'success', texto: 'Alerta cadastrado com sucesso!' })
        setForm(FORM_INICIAL)
        // Incrementar a chave faz o useEffect do RegistrationList disparar de novo
        setRefreshKey(k => k + 1)
      } else {
        const err = await res.json()
        setMsg({ tipo: 'error', texto: `Erro ${res.status}: ${JSON.stringify(err.detail)}` })
      }
    } catch {
      setMsg({ tipo: 'error', texto: 'Falha de rede. Verifique se o backend está rodando.' })
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="page">
      <h1>Cadastrar Alerta</h1>

      <form className="form" onSubmit={handleSubmit}>
        {/* Email ocupa a linha inteira */}
        <div className="form-group">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            name="email"
            value={form.email}
            onChange={handleChange}
            placeholder="voce@email.com"
            required
          />
        </div>

        {/* Linha + coordenadas na mesma row */}
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="bus_line">Linha do ônibus</label>
            <input
              id="bus_line"
              type="text"
              name="bus_line"
              value={form.bus_line}
              onChange={handleChange}
              placeholder="485"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="stop_lat">Latitude da parada</label>
            <input
              id="stop_lat"
              type="number"
              step="any"
              name="stop_lat"
              value={form.stop_lat}
              onChange={handleChange}
              placeholder="-22.9068"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="stop_lon">Longitude da parada</label>
            <input
              id="stop_lon"
              type="number"
              step="any"
              name="stop_lon"
              value={form.stop_lon}
              onChange={handleChange}
              placeholder="-43.1729"
              required
            />
          </div>
        </div>

        {/* Janela de horário */}
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="window_start">Início da janela (HH:MM:SS)</label>
            <input
              id="window_start"
              type="text"
              name="window_start"
              value={form.window_start}
              onChange={handleChange}
              placeholder="07:00:00"
              pattern="\d{2}:\d{2}:\d{2}"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="window_end">Fim da janela (HH:MM:SS)</label>
            <input
              id="window_end"
              type="text"
              name="window_end"
              value={form.window_end}
              onChange={handleChange}
              placeholder="08:00:00"
              pattern="\d{2}:\d{2}:\d{2}"
              required
            />
          </div>
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={enviando}
        >
          {enviando ? 'Cadastrando...' : 'Cadastrar'}
        </button>

        {msg && (
          <p className={`msg msg-${msg.tipo}`}>{msg.texto}</p>
        )}
      </form>

      <h2>Alertas cadastrados</h2>
      <RegistrationList onRefresh={refreshKey} />
    </main>
  )
}

export default RegisterPage
