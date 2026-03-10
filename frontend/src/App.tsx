import { Routes, Route } from 'react-router-dom'

function Home() {
  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-900">Sportverein</h1>
      </header>
      <main className="px-6 py-8">
        <p className="text-gray-600">Willkommen beim Sportverein Management System.</p>
      </main>
    </div>
  )
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
    </Routes>
  )
}

export default App
