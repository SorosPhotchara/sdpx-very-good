import React from 'react'

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="bg-transparent">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="text-blue-600 font-semibold text-lg">University Login</div>
          <nav className="hidden sm:flex gap-6 text-slate-600">
            <a href="#" className="hover:text-slate-900">Home</a>
            <a href="#" className="hover:text-slate-900">Features</a>
            <a href="#" className="hover:text-slate-900">Contact</a>
          </nav>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-12">
        <section className="bg-white rounded-xl p-8 shadow-md">
          <h1 className="text-2xl font-semibold mb-2">Welcome to University Login</h1>
          <p className="text-slate-600 mb-6">A simple, secure authentication service for students and staff.</p>

          <div className="min-h-[10rem] border-2 border-dashed border-slate-200 rounded-md flex items-center justify-center text-slate-500">
            Main feature placeholder — login flow and dashboard will appear here.
          </div>
        </section>
      </main>

      <footer className="mt-10">
        <div className="max-w-4xl mx-auto px-6 py-6 text-slate-500 text-sm">© {new Date().getFullYear()} University Login</div>
      </footer>
    </div>
  )
}
