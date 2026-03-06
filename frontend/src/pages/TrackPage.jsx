// TrackPage.jsx — layout split: mapa à esquerda (60%), painel à direita (40%).
// O mapa fica sempre visível. Após o primeiro submit, marcadores dos ônibus
// e o marcador da parada do usuário aparecem sobre ele.

import 'leaflet/dist/leaflet.css'

import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'

import iconUrl from 'leaflet/dist/images/marker-icon.png'
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png'
import shadowUrl from 'leaflet/dist/images/marker-shadow.png'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({ iconUrl, iconRetinaUrl, shadowUrl })

const CENTRO_RIO = [-22.9068, -43.1729]
const FORM_INICIAL = { line: '' }

const MENSAGENS = {
  line: 'Informe a linha do ônibus (ex: 485)',
}

const stopIcon = L.divIcon({
  className: '',
  html: `<div style="
    width: 16px; height: 16px;
    background: #ef4444;
    border: 3px solid #fff;
    border-radius: 50%;
    box-shadow: 0 2px 6px rgba(0,0,0,0.45);
  "></div>`,
  iconSize: [16, 16],
  iconAnchor: [8, 8],
})

// Componente interno que reage a flyTarget — chama map.flyTo() quando o alvo muda.
function MapController({ flyTarget }) {
  const map = useMap()
  useEffect(() => {
    if (flyTarget) map.flyTo(flyTarget, 16)
  }, [flyTarget])
  return null
}

function TrackPage() {
  const [form, setForm] = useState(FORM_INICIAL)
  const [searchParams, setSearchParams] = useState(null)
  const [buses, setBuses] = useState([])
  const [loading, setLoading] = useState(false)
  const [flyTarget, setFlyTarget] = useState(null)

  // Estado do campo de endereço geocodificado
  const [enderecoInput, setEnderecoInput] = useState('')   // o que o usuário digita
  const [buscando, setBuscando] = useState(false)          // loading do Nominatim
  const [resolved, setResolved] = useState(null)           // { lat, lon, display_name }
  const [enderecoErro, setEnderecoErro] = useState('')     // feedback de erro inline

  function handleChange(e) {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
  }

  function handleInvalid(e) {
    e.target.setCustomValidity(MENSAGENS[e.target.name] ?? 'Campo inválido')
  }

  function handleClearValidity(e) {
    e.target.setCustomValidity('')
  }

  // Geocodifica o endereço digitado via Nominatim 
  async function buscarEndereco() {
    setBuscando(true)
    setResolved(null)
    setEnderecoErro('')
    const url = `https://nominatim.openstreetmap.org/search?` +
      `q=${encodeURIComponent(enderecoInput)}&format=json&limit=1&countrycodes=br`
    try {
      const res = await fetch(url)
      const data = await res.json()
      if (data.length > 0) {
        const r = data[0]
        setResolved({ lat: r.lat, lon: r.lon, display_name: r.display_name })
      } else {
        setEnderecoErro('Endereço não encontrado. Tente ser mais específico.')
      }
    } catch {
      setEnderecoErro('Falha ao buscar endereço. Verifique sua conexão.')
    } finally {
      setBuscando(false)
    }
  }

  async function fetchBuses(params) {
    setLoading(true)
    try {
      const { line, stop_lat, stop_lon } = params
      const res = await fetch(`/buses/${line}?stop_lat=${stop_lat}&stop_lon=${stop_lon}`)
      const data = await res.json()
      setBuses(data.buses ?? [])
    } catch {
      // Silencia erro de rede — tabela mantém o último resultado
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(e) {
    e.preventDefault()
    setSearchParams({
      line: form.line,
      stop_lat: parseFloat(resolved.lat),
      stop_lon: parseFloat(resolved.lon),
    })
  }

  // Busca imediata + auto-refresh de 60s. Cancela o intervalo anterior
  // sempre que searchParams mudar ou o componente desmontar.
  useEffect(() => {
    if (!searchParams) return
    fetchBuses(searchParams)
    const id = setInterval(() => fetchBuses(searchParams), 60_000)
    return () => clearInterval(id)
  }, [searchParams])

  return (
    <div className="track-layout">

      {/* ── Lado esquerdo: mapa sempre visível ── */}
      <div className="track-map">
        <MapContainer center={CENTRO_RIO} zoom={13}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapController flyTarget={flyTarget} />

          {/* Marcador da parada do usuário */}
          {searchParams && (
            <Marker
              position={[searchParams.stop_lat, searchParams.stop_lon]}
              icon={stopIcon}
            >
              <Popup>📍 Sua parada</Popup>
            </Marker>
          )}

          {/* Marcadores dos ônibus */}
          {buses.map(bus =>
            bus.latitude && bus.longitude ? (
              <Marker key={bus.ordem} position={[bus.latitude, bus.longitude]}>
                <Popup>
                  <strong>{bus.ordem}</strong><br />
                  Velocidade: {bus.velocidade ?? '—'} km/h<br />
                  ETA: {bus.eta_minutes ?? '—'} min
                </Popup>
              </Marker>
            ) : null
          )}
        </MapContainer>
      </div>

      {/* ── Lado direito: busca + tabela ── */}
      <div className="track-panel">
        <h1>Rastrear Ônibus</h1>

        <form className="form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="line">Linha</label>
            <input
              id="line"
              type="text"
              name="line"
              value={form.line}
              onChange={handleChange}
              onInvalid={handleInvalid}
              onInput={handleClearValidity}
              placeholder="485"
              required
            />
          </div>
          {/* Endereço da parada — geocodificado via Nominatim; lat/lon resolvidos automaticamente */}
          <div className="form-group">
            <label>Endereço da parada</label>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="text"
                value={enderecoInput}
                onChange={e => { setEnderecoInput(e.target.value); setResolved(null) }}
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
            {enderecoErro && (
              <small style={{ color: '#b91c1c' }}>{enderecoErro}</small>
            )}
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading || !resolved}>
            {loading ? 'Buscando...' : 'Buscar ônibus'}
          </button>
        </form>

        {searchParams && (
          <>
            <h2>
              Linha {searchParams.line}
              {loading && <span className="spinner" style={{ marginLeft: '0.75rem' }} />}
            </h2>

            {!loading && buses.length === 0 ? (
              <p className="empty-state">Nenhum ônibus encontrado para essa linha.</p>
            ) : (
              <>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Ordem</th>
                        <th>Dist. (km)</th>
                        <th>Vel. (km/h)</th>
                        <th>ETA (min)</th>
                        <th>Atualizado em</th>
                      </tr>
                    </thead>
                    <tbody>
                      {buses.map(bus => (
                        <tr
                          key={bus.ordem}
                          style={{ cursor: bus.latitude ? 'pointer' : 'default' }}
                          onClick={() => bus.latitude && bus.longitude && setFlyTarget([bus.latitude, bus.longitude])}
                        >
                          <td>{bus.ordem}</td>
                          <td>{bus.distance_km ?? '—'}</td>
                          <td>{bus.velocidade ?? '—'}</td>
                          <td>{bus.eta_minutes ?? '—'}</td>
                          <td>{bus.datahora}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <small style={{ color: '#94a3b8' }}>
                  Ônibus ordenados por distância. ETA calculado via rota real (ORS) para os {3} mais próximos; demais exibem —.
                </small>
              </>
            )}
          </>
        )}
      </div>

    </div>
  )
}

export default TrackPage
