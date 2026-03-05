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

  // Estado do campo de endereço geocodificado
  const [enderecoInput, setEnderecoInput] = useState('')   // o que o usuário digita
  const [buscando, setBuscando] = useState(false)          // loading do Nominatim
  const [resolved, setResolved] = useState(null)           // { lat, lon, display_name }

  function handleChange(e) {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
  }

  // Mensagens de validação nativa substituídas por PT-BR.
  // O browser usa o idioma do sistema por padrão; onInvalid sobrescreve isso.
  const MENSAGENS = {
    email:        'Insira um email válido (ex: voce@email.com)',
    bus_line:     'Informe a linha do ônibus (ex: 485)',
    // stop_lat e stop_lon removidos — preenchidos automaticamente pelo geocoding
    window_start: 'Informe o horário de início (ex: 07:00)',
    window_end:   'Informe o horário de fim (ex: 08:00)',
  }

  function handleInvalid(e) {
    e.target.setCustomValidity(MENSAGENS[e.target.name] ?? 'Campo inválido')
  }

  // Limpa a mensagem customizada ao primeiro input após erro —
  // sem isso o campo permanece inválido mesmo depois de corrigido.
  function handleClearValidity(e) {
    e.target.setCustomValidity('')
  }

  // Máscara em tempo real para campos de horário.
  // Extrai apenas dígitos do que o usuário digitou, limita a 4 (HHMM),
  // e insere o ":" fixo após os dois primeiros — o campo sempre exibe HH:MM.
  // Backspace funciona normalmente: apagar o "0" de "09:0" resulta em "09".
  function handleTimeChange(e) {
    const { name, value } = e.target
    const digits = value.replace(/\D/g, '').slice(0, 4)
    const formatted = digits.length > 2
      ? `${digits.slice(0, 2)}:${digits.slice(2)}`
      : digits
    setForm(prev => ({ ...prev, [name]: formatted }))
  }

  // Geocodifica o endereço digitado via Nominatim (OpenStreetMap, gratuito, sem chave).
  // Limita ao Brasil (countrycodes=br) e pega apenas o primeiro resultado.
  async function buscarEndereco() {
    setBuscando(true)
    setResolved(null)
    const url = `https://nominatim.openstreetmap.org/search?` +
      `q=${encodeURIComponent(enderecoInput)}&format=json&limit=1&countrycodes=br`
    try {
      const res = await fetch(url)
      const data = await res.json()
      if (data.length > 0) {
        const r = data[0]
        setResolved({ lat: r.lat, lon: r.lon, display_name: r.display_name })
        setForm(prev => ({ ...prev, stop_lat: r.lat, stop_lon: r.lon }))
      } else {
        setMsg({ tipo: 'error', texto: 'Endereço não encontrado. Tente ser mais específico.' })
      }
    } catch {
      setMsg({ tipo: 'error', texto: 'Falha ao buscar endereço. Verifique sua conexão.' })
    } finally {
      setBuscando(false)
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setEnviando(true)
    setMsg(null)

    // Bloqueia envio se o endereço ainda não foi geocodificado
    if (!resolved) {
      setMsg({ tipo: 'error', texto: 'Busque e confirme o endereço da parada antes de cadastrar.' })
      setEnviando(false)
      return
    }

    // Converte lat/lon de string para número antes de enviar.
    // Acrescenta ":00" nos horários para satisfazer o formato HH:MM:SS do backend.
    const toBackendTime = t => t.includes(':') && t.split(':').length === 2 ? `${t}:00` : t
    const payload = {
      ...form,
      stop_name: resolved.display_name,
      stop_lat: parseFloat(form.stop_lat),
      stop_lon: parseFloat(form.stop_lon),
      window_start: toBackendTime(form.window_start),
      window_end: toBackendTime(form.window_end),
    }

    try {
      const res = await fetch('/registrations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': import.meta.env.VITE_API_KEY ?? '',
        },
        body: JSON.stringify(payload),
      })

      if (res.ok) {
        setMsg({ tipo: 'success', texto: 'Alerta cadastrado com sucesso!' })
        setForm(FORM_INICIAL)
        setEnderecoInput('')
        setResolved(null)
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
            onInvalid={handleInvalid}
            onInput={handleClearValidity}
            placeholder="voce@email.com"
            required
          />
        </div>

        {/* Linha do ônibus */}
        <div className="form-group">
          <label htmlFor="bus_line">Linha do ônibus</label>
          <input
            id="bus_line"
            type="text"
            name="bus_line"
            value={form.bus_line}
            onChange={handleChange}
            onInvalid={handleInvalid}
            onInput={handleClearValidity}
            placeholder="485"
            required
          />
        </div>

        {/* Endereço da parada — geocodificado via Nominatim; lat/lon preenchidos automaticamente */}
        <div className="form-group">
          <label>Endereço da parada</label>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <input
              type="text"
              value={enderecoInput}
              onChange={e => setEnderecoInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), buscarEndereco())}
              placeholder="Av. das Américas, 1000, Rio de Janeiro"
            />
            <button
              type="button"
              className="btn btn-secondary"
              onClick={buscarEndereco}
              disabled={buscando || !enderecoInput.trim()}
            >
              {buscando ? '...' : 'Buscar'}
            </button>
          </div>
          {resolved && (
            <small style={{ color: '#65a30d' }}>✓ {resolved.display_name}</small>
          )}
        </div>

        {/* Janela de horário — máscara automática: o ":" é inserido após os 2 primeiros dígitos */}
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="window_start">Início da janela (HH:MM)</label>
            <input
              id="window_start"
              type="text"
              name="window_start"
              value={form.window_start}
              onChange={handleTimeChange}
              onInvalid={handleInvalid}
              onInput={handleClearValidity}
              placeholder="07:00"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="window_end">Fim da janela (HH:MM)</label>
            <input
              id="window_end"
              type="text"
              name="window_end"
              value={form.window_end}
              onChange={handleTimeChange}
              onInvalid={handleInvalid}
              onInput={handleClearValidity}
              placeholder="08:00"
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
