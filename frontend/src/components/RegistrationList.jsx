// RegistrationList.jsx — lista os alertas cadastrados e permite deletar cada um.
// Recebe `onRefresh` como prop: o RegisterPage chama isso após um POST bem-sucedido
// para que a lista atualize sem o usuário precisar recarregar a página.

import { useState, useEffect } from 'react'

function RegistrationList({ onRefresh }) {
  const [registrations, setRegistrations] = useState([])
  const [loading, setLoading] = useState(true)
  const [deletingId, setDeletingId] = useState(null)

  // Busca a lista ao montar o componente
  useEffect(() => {
    fetchRegistrations()
  }, [onRefresh]) // re-executa toda vez que o pai sinalizar um novo cadastro

  async function fetchRegistrations() {
    setLoading(true)
    try {
      const res = await fetch('/registrations')
      const data = await res.json()
      setRegistrations(data)
    } catch {
      // Silencia o erro de rede — a tabela simplesmente fica vazia
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(id) {
    setDeletingId(id)
    try {
      await fetch(`/registrations/${id}`, {
        method: 'DELETE',
        headers: { 'X-API-Key': import.meta.env.VITE_API_KEY ?? '' },
      })
      // Remove da lista local sem precisar de outro GET
      setRegistrations(prev => prev.filter(r => r.id !== id))
    } catch {
      alert('Erro ao deletar. Tente novamente.')
    } finally {
      setDeletingId(null)
    }
  }

  if (loading) {
    return (
      <div className="loading-row">
        <span className="spinner" />
        Carregando alertas...
      </div>
    )
  }

  if (registrations.length === 0) {
    return <p className="empty-state">Nenhum alerta cadastrado ainda.</p>
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Email</th>
            <th>Linha</th>
            <th>Parada</th>
            <th>Janela</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {registrations.map(r => (
            <tr key={r.id}>
              <td>{r.id}</td>
              <td>{r.email}</td>
              <td>{r.bus_line}</td>
              {/* stop_name exibido quando disponível; fallback para coordenadas em registros antigos */}
              <td>{r.stop_name ?? `${r.stop_lat}, ${r.stop_lon}`}</td>
              <td>{r.window_start} – {r.window_end}</td>
              <td>
                <button
                  className="btn btn-danger"
                  onClick={() => handleDelete(r.id)}
                  disabled={deletingId === r.id}
                >
                  {deletingId === r.id ? '...' : 'Deletar'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default RegistrationList
