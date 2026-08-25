import React, { useEffect, useState } from 'react'
import { createClassroom, getClassrooms, getHealth } from './api'

export default function App() {
  const [health, setHealth] = useState<string>('loading...')
  const [classrooms, setClassrooms] = useState<any[]>([])
  const [newClassroom, setNewClassroom] = useState('')

  useEffect(() => {
    async function load() {
      const healthData = await getHealth()
      setHealth(healthData?.status ?? 'offline')
      setClassrooms(await getClassrooms())
    }
    load()
  }, [])

  async function handleCreateClassroom() {
    if (!newClassroom.trim()) return
    const classroom = await createClassroom(newClassroom.trim())
    setClassrooms((current) => [...current, classroom])
    setNewClassroom('')
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-6 py-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-blue-700 font-semibold text-xl">PairEval</div>
            <div className="text-slate-500 text-sm">Pairwise evaluation for fair student scoring</div>
          </div>
          <nav className="flex flex-wrap gap-4 text-slate-600">
            <a href="#features" className="hover:text-slate-900">Features</a>
            <a href="#values" className="hover:text-slate-900">Why PairEval</a>
            <a href="#cta" className="hover:text-slate-900">Get Started</a>
          </nav>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-12">
        <section className="rounded-3xl bg-white p-8 shadow-sm">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-3xl font-semibold text-slate-900">Backend prototype connected</h1>
              <p className="mt-3 text-slate-600">This frontend can now call the PairEval backend prototype for classroom creation and health checks.</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-slate-600">
              Backend status: <span className="font-semibold text-slate-900">{health}</span>
            </div>
          </div>

          <div className="mt-8 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="space-y-4">
              <div className="rounded-3xl border border-slate-200 bg-slate-50 p-6">
                <h2 className="text-xl font-semibold text-slate-900">Create a classroom</h2>
                <div className="mt-4 flex gap-3">
                  <input
                    value={newClassroom}
                    onChange={(event) => setNewClassroom(event.target.value)}
                    placeholder="Classroom name"
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-slate-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  />
                  <button
                    onClick={handleCreateClassroom}
                    className="rounded-2xl bg-blue-600 px-5 py-3 text-white hover:bg-blue-700"
                  >
                    Create
                  </button>
                </div>
              </div>

              <div className="rounded-3xl border border-slate-200 bg-slate-50 p-6">
                <h2 className="text-xl font-semibold text-slate-900">Classrooms</h2>
                <div className="mt-4 space-y-3">
                  {classrooms.length ? (
                    classrooms.map((classroom) => (
                      <div key={classroom.id} className="rounded-2xl border border-slate-200 bg-white p-4">
                        <div className="font-medium text-slate-900">{classroom.name}</div>
                        <div className="text-slate-500 text-sm">ID: {classroom.id}</div>
                      </div>
                    ))
                  ) : (
                    <div className="text-slate-500">No classrooms yet.</div>
                  )}
                </div>
              </div>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-gradient-to-b from-slate-950 to-blue-900 p-6 text-white shadow-xl">
              <h2 className="text-xl font-semibold">PairEval backend prototype</h2>
              <p className="mt-4 text-slate-300">The frontend now includes a lightweight API client and a classroom create flow that hits the FastAPI backend at <code className="rounded bg-slate-800 px-2 py-1 text-sm">http://localhost:8000</code>.</p>
              <p className="mt-4 text-slate-300">Next steps are implementing student import, group pairing, and evaluation pages.</p>
            </div>
          </div>
        </section>

        <section id="features" className="mt-16 grid gap-8 sm:grid-cols-2">
          <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">Classroom & assignment workflow</h2>
            <p className="mt-3 text-slate-600">Create classrooms, import students by CSV, assign instructors, and define group/individual evaluation criteria.</p>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">Pair generation engine</h2>
            <p className="mt-3 text-slate-600">Generate balanced pairwise comparisons with coverage targets, self-evaluation exclusion, and reassign support.</p>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">Rolling & final scoring</h2>
            <p className="mt-3 text-slate-600">Compute normalized pairwise scores, partial credit, and instructor-weighted votes for group and individual evaluations.</p>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-900">Reports & export</h2>
            <p className="mt-3 text-slate-600">View coverage reports, pairwise evaluations, and export results to CSV/Excel for instructors.</p>
          </div>
        </section>

        <section id="values" className="mt-16 rounded-3xl border border-slate-200 bg-slate-800 p-10 text-white">
          <div className="grid gap-6 sm:grid-cols-3">
            <div>
              <p className="text-sm uppercase tracking-[0.24em] text-slate-400">Fairness</p>
              <p className="mt-3 text-lg font-semibold">Reduce bias with pairwise comparisons, not direct numeric grading.</p>
            </div>
            <div>
              <p className="text-sm uppercase tracking-[0.24em] text-slate-400">Visibility</p>
              <p className="mt-3 text-lg font-semibold">Students see rolling scores while anonymity and raw reports remain instructor-only.</p>
            </div>
            <div>
              <p className="text-sm uppercase tracking-[0.24em] text-slate-400">Control</p>
              <p className="mt-3 text-lg font-semibold">Instructor-defined weighting, deadlines, and reassignments keep workflows manageable.</p>
            </div>
          </div>
        </section>

        <section id="cta" className="mt-16 rounded-3xl border border-slate-200 bg-white p-10 shadow-sm">
          <h2 className="text-2xl font-semibold text-slate-900">Build a better student evaluation experience</h2>
          <p className="mt-4 text-slate-600">This project is a platform starter for PairEval: login + classroom creation, pairwise assessment, and reporting.</p>
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
              <h3 className="font-semibold text-slate-900">Instructor</h3>
              <p className="mt-2 text-slate-600">Create assignments, import students, manage weights, and review reports.</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
              <h3 className="font-semibold text-slate-900">Student</h3>
              <p className="mt-2 text-slate-600">Complete pairwise evaluations, save drafts, and track rolling scores.</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
              <h3 className="font-semibold text-slate-900">Admin</h3>
              <p className="mt-2 text-slate-600">Manage classrooms, reassign groups, and regenerate pairs.</p>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-slate-50 py-8">
        <div className="max-w-5xl mx-auto px-6 text-slate-500 text-sm">© {new Date().getFullYear()} PairEval — A fair student pairwise evaluation system.</div>
      </footer>
    </div>
  )
}
