import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../AuthContext'
import api from '../api'

export default function LoginPage() {
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ email: '', password: '', full_name: '', role: 'patient' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const endpoint = mode === 'login' ? '/auth/login' : '/auth/register'
      const { data } = await api.post(endpoint, form)
      login(data)
      navigate(data.role === 'doctor' ? '/doctor' : '/patient')
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=Tiro+Devanagari+Hindi&display=swap');

        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        .pg {
          min-height: 100vh;
          display: flex;
          background: #f0f6ff;
          font-family: 'DM Sans', sans-serif;
        }

        /* ---- LEFT PANEL ---- */
        .left {
          width: 440px;
          flex-shrink: 0;
          background: #ffffff;
          display: flex;
          flex-direction: column;
          justify-content: center;
          padding: 52px 44px;
          border-right: 1px solid #dbeafe;
        }

        .logo-row {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 6px;
        }

        .logo-box {
          width: 36px;
          height: 36px;
          background: #1d4ed8;
          border-radius: 9px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .logo-box svg {
          width: 18px;
          height: 18px;
          stroke: #fff;
          fill: none;
          stroke-width: 2;
          stroke-linecap: round;
          stroke-linejoin: round;
        }

        .app-hindi {
          font-family: 'Tiro Devanagari Hindi', serif;
          font-size: 22px;
          color: #1e3a8a;
          line-height: 1;
        }

        .app-sub {
          font-size: 12.5px;
          color: #94a3b8;
          margin-bottom: 36px;
          letter-spacing: 0.2px;
        }

        .tabs {
          display: flex;
          background: #f1f5f9;
          border-radius: 8px;
          padding: 3px;
          margin-bottom: 24px;
        }

        .tab {
          flex: 1;
          padding: 7px 0;
          font-size: 13px;
          font-weight: 500;
          font-family: 'DM Sans', sans-serif;
          border: none;
          background: transparent;
          color: #94a3b8;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.15s;
        }

        .tab.on {
          background: #ffffff;
          color: #1e40af;
          box-shadow: 0 1px 3px rgba(0,0,0,0.07);
        }

        .lbl {
          display: block;
          font-size: 11.5px;
          font-weight: 500;
          letter-spacing: 0.5px;
          text-transform: uppercase;
          color: #64748b;
          margin-bottom: 5px;
        }

        .inp {
          width: 100%;
          border: 1.5px solid #e2e8f0;
          border-radius: 9px;
          padding: 10px 13px;
          font-size: 13.5px;
          font-family: 'DM Sans', sans-serif;
          color: #0f172a;
          background: #fafcff;
          outline: none;
          transition: border-color 0.15s, box-shadow 0.15s;
          margin-bottom: 13px;
        }

        .inp:focus {
          border-color: #3b82f6;
          background: #ffffff;
          box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
        }

        .role-row {
          display: flex;
          gap: 9px;
          margin-bottom: 13px;
        }

        .role-card {
          flex: 1;
          border: 1.5px solid #e2e8f0;
          border-radius: 9px;
          padding: 9px 13px;
          cursor: pointer;
          background: #fafcff;
          transition: all 0.15s;
        }

        .role-card.sel {
          border-color: #3b82f6;
          background: #eff6ff;
        }

        .rc-title {
          font-size: 13px;
          font-weight: 500;
          color: #334155;
        }

        .role-card.sel .rc-title { color: #1d4ed8; }

        .rc-sub {
          font-size: 11px;
          color: #94a3b8;
          margin-top: 2px;
        }

        .err {
          background: #fff1f2;
          border: 1px solid #fecdd3;
          border-radius: 8px;
          padding: 9px 12px;
          font-size: 12.5px;
          color: #e11d48;
          margin-bottom: 13px;
        }

        .btn {
          width: 100%;
          background: #1d4ed8;
          color: #fff;
          border: none;
          border-radius: 9px;
          padding: 11px;
          font-size: 13.5px;
          font-weight: 500;
          font-family: 'DM Sans', sans-serif;
          cursor: pointer;
          transition: background 0.15s;
          letter-spacing: 0.1px;
        }

        .btn:hover:not(:disabled) { background: #1e40af; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }

        .demo-block {
          margin-top: 22px;
          border: 1px solid #dbeafe;
          border-radius: 9px;
          padding: 13px 14px;
          background: #f8fbff;
        }

        .demo-head {
          font-size: 10.5px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: #94a3b8;
          margin-bottom: 8px;
        }

        .demo-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 5px 0;
          border-bottom: 1px solid #e2e8f0;
        }

        .demo-row:last-child { border-bottom: none; }

        .demo-badge {
          font-size: 10.5px;
          font-weight: 500;
          background: #dbeafe;
          color: #1d4ed8;
          padding: 2px 8px;
          border-radius: 20px;
        }

        .demo-cred {
          font-size: 11px;
          color: #64748b;
          font-family: 'Courier New', monospace;
        }

        /* ---- RIGHT PANEL ---- */
        .right {
          flex: 1;
          background: linear-gradient(150deg, #eff6ff 0%, #dbeafe 60%, #bfdbfe 100%);
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 48px;
          position: relative;
          overflow: hidden;
        }

        .circle1 {
          position: absolute;
          width: 520px;
          height: 520px;
          border-radius: 50%;
          background: rgba(147,197,253,0.2);
          top: -140px;
          right: -140px;
        }

        .circle2 {
          position: absolute;
          width: 280px;
          height: 280px;
          border-radius: 50%;
          background: rgba(96,165,250,0.12);
          bottom: -60px;
          left: 60px;
        }

        .hero-card {
          position: relative;
          z-index: 1;
          background: rgba(255,255,255,0.65);
          backdrop-filter: blur(16px);
          border: 1px solid rgba(255,255,255,0.85);
          border-radius: 20px;
          padding: 40px 44px;
          max-width: 420px;
          width: 100%;
        }

        .hero-devanagari {
          font-family: 'Tiro Devanagari Hindi', serif;
          font-size: 38px;
          color: #1e3a8a;
          line-height: 1.15;
          margin-bottom: 4px;
        }

        .hero-eng {
          font-size: 13px;
          font-weight: 500;
          color: #3b82f6;
          letter-spacing: 1.5px;
          text-transform: uppercase;
          margin-bottom: 16px;
        }

        .hero-desc {
          font-size: 13.5px;
          color: #475569;
          line-height: 1.75;
          margin-bottom: 28px;
        }

        .feat-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .feat {
          display: flex;
          align-items: flex-start;
          gap: 10px;
        }

        .feat-line {
          width: 3px;
          height: 38px;
          background: linear-gradient(180deg, #3b82f6, #93c5fd);
          border-radius: 3px;
          flex-shrink: 0;
          margin-top: 2px;
        }

        .feat-text {
          font-size: 12.5px;
          color: #334155;
          line-height: 1.6;
        }

        @media (max-width: 780px) {
          .right { display: none; }
          .left { width: 100%; border-right: none; }
        }
      `}</style>

      <div className="pg">
        <div className="left">
          <div className="logo-row">
            <div className="logo-box">
              <svg viewBox="0 0 24 24">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
              </svg>
            </div>
            <span className="app-hindi">निदान</span>
          </div>
          <p className="app-sub">Sahi waqt par, sahi doctor.</p>

          <div className="tabs">
            {['login', 'register'].map((m) => (
              <button key={m} className={`tab ${mode === m ? 'on' : ''}`} onClick={() => setMode(m)}>
                {m === 'login' ? 'Sign In' : 'Register'}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit}>
            {mode === 'register' && (
              <>
                <label className="lbl">Full Name</label>
                <input className="inp" placeholder="Your full name"
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  required />
              </>
            )}

            <label className="lbl">Email Address</label>
            <input className="inp" type="email" placeholder="you@example.com"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required />

            <label className="lbl">Password</label>
            <input className="inp" type="password" placeholder="••••••••"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required />

            {mode === 'register' && (
              <>
                <label className="lbl" style={{ display: 'block', marginBottom: 7 }}>I am a</label>
                <div className="role-row">
                  {[{ v: 'patient', t: 'Patient', s: 'Book appointments' },
                    { v: 'doctor', t: 'Doctor', s: 'Manage schedule' }].map((r) => (
                    <div key={r.v} className={`role-card ${form.role === r.v ? 'sel' : ''}`}
                      onClick={() => setForm({ ...form, role: r.v })}>
                      <div className="rc-title">{r.t}</div>
                      <div className="rc-sub">{r.s}</div>
                    </div>
                  ))}
                </div>
              </>
            )}

            {error && <div className="err">{error}</div>}

            <button type="submit" className="btn" disabled={loading}>
              {loading ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>

          <div className="demo-block">
            <div className="demo-head">Demo credentials (after seeding)</div>
            <div className="demo-row">
              <span className="demo-badge">Patient</span>
              <span className="demo-cred">patient@test.com / patient123</span>
            </div>
            <div className="demo-row">
              <span className="demo-badge">Doctor</span>
              <span className="demo-cred">priya@clinic.com / doctor123</span>
            </div>
          </div>
        </div>

        <div className="right">
          <div className="circle1" />
          <div className="circle2" />
          <div className="hero-card">
            <div className="hero-devanagari">निदान</div>
            <div className="hero-eng">NIDAN · निदान</div>
            <p className="hero-desc">
              Sahi waqt par, sahi doctor. Book appointments, check live availability,
              and manage your health — powered by AI.
            </p>
            <div className="feat-list">
              {[
                'Natural language booking — just type what you need',
                'Live doctor availability from the database',
                'Google Calendar events and email confirmations',
                'Doctor reports with Slack notifications',
              ].map((f) => (
                <div className="feat" key={f}>
                  <div className="feat-line" />
                  <span className="feat-text">{f}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
