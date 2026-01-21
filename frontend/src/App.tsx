import { useEffect, useState } from 'react'

interface Land {
  id: string
  name: string
}

function App() {
  const [lands, setLands] = useState<Land[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/v1/lands/')
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then(data => {
        setLands(data.results || data)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  if (loading) return <p>Loading...</p>
  if (error) return <p>Error: {error}</p>

  return (
    <div>
      <h1>Kapok - Indigenous Lands</h1>
      {lands.length === 0 ? (
        <p>No lands found.</p>
      ) : (
        <ul>
          {lands.map(land => (
            <li key={land.id}>{land.name}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default App
