import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../AuthContext'
import ChatWindow from '../components/ChatWindow'
import api from '../api'

const QUICK_PROMPTS = [
  'How many patients do I have today?',
  'Show appointments for tomorrow',
  'How many patients with fever this week?',
  "Give me yesterday's summary",
]

const REPORT_BTNS = [
  { label: "Today's Report",  query: "How many appointments do I have today? Give me a full summary." },
  { label: 'Tomorrow',        query: 'How many appointments do I have tomorrow?' },
  { label: 'This Week',       query: 'Give me a summary of appointments this week.' },
  { label: 'Fever Cases',     query: 'How many patients have fever this week?' },
]

export default function DoctorPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [appointments, setAppointments] = useState([])
  const [summaryLoading, setSummaryLoading] = useState(null)
  const [notif, setNotif] = useState('')

  useEffect(() => {
    if (!user || user.role !== 'doctor') { navigate('/login'); return }
    fetchAppointments()
  }, [])

  const fetchAppointments = async () => {
    try {
      const { data } = await api.get('/doctor/appointments')
      setAppointments(data)
    } catch {}
  }

  const showNotif = (msg) => {
    setNotif(msg)
    setTimeout(() => setNotif(''), 4000)
  }

  const handleSend = async (message) => {
    setMessages((p) => [...p, { role: 'user', content: message }])
    setLoading(true)
    try {
      const { data } = await api.post('/chat/doctor', { message, session_id: sessionId })
      setSessionId(data.session_id)
      setMessages((p) => [...p, {
        role: 'assistant',
        content: data.reply,
        tool_calls_made: data.tool_calls_made,
      }])
      if (data.tool_calls_made?.includes('get_doctor_summary')) {
        showNotif('Summary sent to Slack')
      }
    } catch {
      setMessages((p) => [...p, { role: 'assistant', content: 'Error. Please try again.' }])
    } finally {
      setLoading(false)
    }
  }

  const triggerReport = async (label, query) => {
    setSummaryLoading(label)
    try {
      const { data } = await api.post('/doctor/summary', { query })
      setMessages([
        { role: 'user', content: query },
        { role: 'assistant', content: data.summary },
      ])
      setSessionId(null)
      if (data.notification_sent) showNotif('Report sent to Slack')
    } catch {
    } finally {
      setSummaryLoading(null)
    }
  }

  const clearChat = () => {
    if (sessionId) api.delete(`/chat/session?session_id=${sessionId}`).catch(() => {})
    setMessages([])
    setSessionId(null)
  }

  const todayStr = new Date().toISOString().slice(0, 10)
  const todayCount = appointments.filter((a) => a.scheduled_at?.startsWith(todayStr)).length

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=Tiro+Devanagari+Hindi&display=swap');

        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        .dr-root {
          min-height: 100vh;
          background: #f0f6ff;
          font-family: 'DM Sans', sans-serif;
          display: flex;
          flex-direction: column;
        }

        /* NAV */
        .dr-nav {
          height: 52px;
          background: #ffffff;
          border-bottom: 1px solid #dbeafe;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 24px;
          flex-shrink: 0;
          position: relative;
        }

        .dr-nav-left { display: flex; align-items: center; gap: 10px; }

        .dr-logo {
          width: 30px;
          height: 30px;
          background: #1d4ed8;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .dr-logo svg {
          width: 15px;
          height: 15px;
          stroke: #fff;
          fill: none;
          stroke-width: 2;
          stroke-linecap: round;
          stroke-linejoin: round;
        }

        .dr-brand {
          font-family: 'Tiro Devanagari Hindi', serif;
          font-size: 17px;
          color: #1e3a8a;
        }

        .dr-badge {
          font-size: 10.5px;
          font-weight: 500;
          background: #eff6ff;
          color: #1d4ed8;
          border: 1px solid #bfdbfe;
          border-radius: 20px;
          padding: 2px 9px;
          margin-left: 4px;
        }

        .dr-nav-right { display: flex; align-items: center; gap: 14px; }

        .dr-notif {
          background: #f0fdf4;
          border: 1px solid #bbf7d0;
          color: #15803d;
          font-size: 12px;
          font-weight: 500;
          padding: 4px 12px;
          border-radius: 20px;
          transition: opacity 0.3s;
        }

        .dr-user-label { font-size: 13px; color: #64748b; }

        .dr-logout {
          background: none;
          border: 1px solid #dbeafe;
          border-radius: 7px;
          padding: 5px 12px;
          font-size: 12.5px;
          font-family: 'DM Sans', sans-serif;
          color: #1d4ed8;
          cursor: pointer;
          transition: background 0.15s;
        }

        .dr-logout:hover { background: #eff6ff; }

        /* BODY */
        .dr-body {
          flex: 1;
          display: flex;
          gap: 18px;
          padding: 18px 24px;
          min-height: 0;
        }

        /* CHAT PANEL */
        .dr-chat-panel {
          flex: 1;
          background: #ffffff;
          border: 1px solid #dbeafe;
          border-radius: 14px;
          display: flex;
          flex-direction: column;
          overflow: hidden;
          min-height: 0;
        }

        .dr-chat-header {
          padding: 13px 18px;
          border-bottom: 1px solid #f1f5f9;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .dr-chat-title { font-size: 13.5px; font-weight: 600; color: #1e293b; }
        .dr-chat-sub { font-size: 11.5px; color: #94a3b8; margin-top: 1px; }

        .dr-new-btn {
          background: none;
          border: 1px solid #dbeafe;
          border-radius: 7px;
          padding: 4px 11px;
          font-size: 12px;
          font-family: 'DM Sans', sans-serif;
          color: #3b82f6;
          cursor: pointer;
          transition: background 0.15s;
        }

        .dr-new-btn:hover { background: #eff6ff; }

        /* SIDEBAR */
        .dr-sidebar {
          width: 260px;
          flex-shrink: 0;
          display: flex;
          flex-direction: column;
          gap: 14px;
        }

        /* STAT CARDS */
        .dr-stats {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
        }

        .dr-stat {
          background: #ffffff;
          border: 1px solid #dbeafe;
          border-radius: 12px;
          padding: 14px;
        }

        .dr-stat-label { font-size: 11px; color: #94a3b8; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.4px; }
        .dr-stat-num { font-size: 26px; font-weight: 600; color: #1e3a8a; line-height: 1; }
        .dr-stat-sub { font-size: 10.5px; color: #94a3b8; margin-top: 2px; }

        /* REPORTS CARD */
        .dr-card {
          background: #ffffff;
          border: 1px solid #dbeafe;
          border-radius: 14px;
          padding: 16px;
        }

        .dr-card-title {
          font-size: 12.5px;
          font-weight: 600;
          color: #1e3a8a;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 10px;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .dr-refresh {
          background: none;
          border: none;
          cursor: pointer;
          color: #94a3b8;
          display: flex;
          align-items: center;
          transition: color 0.15s;
        }

        .dr-refresh:hover { color: #3b82f6; }
        .dr-refresh svg {
          width: 13px; height: 13px;
          stroke: currentColor; fill: none;
          stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
        }

        .dr-report-btns {
          display: flex;
          flex-direction: column;
          gap: 7px;
        }

        .dr-report-btn {
          background: #f8fbff;
          border: 1px solid #dbeafe;
          border-radius: 8px;
          padding: 8px 12px;
          font-size: 12.5px;
          font-family: 'DM Sans', sans-serif;
          color: #1e40af;
          text-align: left;
          cursor: pointer;
          transition: background 0.15s, border-color 0.15s;
          font-weight: 400;
        }

        .dr-report-btn:hover:not(:disabled) {
          background: #eff6ff;
          border-color: #93c5fd;
        }

        .dr-report-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .dr-report-btn.active { background: #dbeafe; border-color: #3b82f6; }

        .dr-report-hint {
          font-size: 11px;
          color: #94a3b8;
          margin-top: 8px;
          text-align: center;
        }

        /* UPCOMING LIST */
        .dr-appt-list {
          display: flex;
          flex-direction: column;
          gap: 7px;
          max-height: 240px;
          overflow-y: auto;
          scrollbar-width: thin;
          scrollbar-color: #dbeafe transparent;
        }

        .dr-appt-item {
          border: 1px solid #f1f5f9;
          border-radius: 9px;
          padding: 9px 11px;
        }

        .dr-appt-top {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 3px;
        }

        .dr-appt-name { font-size: 12.5px; font-weight: 500; color: #1e293b; }

        .dr-appt-status {
          font-size: 10px;
          font-weight: 500;
          padding: 2px 7px;
          border-radius: 20px;
        }

        .status-scheduled { background: #eff6ff; color: #1d4ed8; }
        .status-completed  { background: #f0fdf4; color: #15803d; }
        .status-cancelled  { background: #fff1f2; color: #be123c; }

        .dr-appt-time { font-size: 11px; color: #64748b; }
        .dr-appt-reason { font-size: 11px; color: #94a3b8; margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

        .dr-empty { font-size: 12.5px; color: #94a3b8; text-align: center; padding: 14px 0; }
      `}</style>

      <div className="dr-root">
        <nav className="dr-nav">
          <div className="dr-nav-left">
            <div className="dr-logo">
              <svg viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>
            </div>
            <span className="dr-brand">निदान</span>
            <span className="dr-badge">Doctor</span>
          </div>
          <div className="dr-nav-right">
            {notif && <div className="dr-notif">{notif}</div>}
            <span className="dr-user-label">{user?.full_name}</span>
            <button className="dr-logout" onClick={logout}>Sign out</button>
          </div>
        </nav>

        <div className="dr-body">
          <div className="dr-chat-panel">
            <div className="dr-chat-header">
              <div>
                <div className="dr-chat-title">Summary Assistant</div>
                <div className="dr-chat-sub">GPT-4o · Slack notifications on summary</div>
              </div>
              <button className="dr-new-btn" onClick={clearChat}>Clear</button>
            </div>
            <ChatWindow
              onSend={handleSend}
              loading={loading}
              messages={messages}
              placeholder="e.g. How many patients do I have today?"
              quickPrompts={QUICK_PROMPTS}
            />
          </div>

          <div className="dr-sidebar">
            <div className="dr-stats">
              <div className="dr-stat">
                <div className="dr-stat-label">Today</div>
                <div className="dr-stat-num">{todayCount}</div>
                <div className="dr-stat-sub">appointments</div>
              </div>
              <div className="dr-stat">
                <div className="dr-stat-label">Upcoming</div>
                <div className="dr-stat-num">{appointments.length}</div>
                <div className="dr-stat-sub">total</div>
              </div>
            </div>

            <div className="dr-card">
              <div className="dr-card-title">Quick Reports</div>
              <div className="dr-report-btns">
                {REPORT_BTNS.map(({ label, query }) => (
                  <button
                    key={label}
                    className={`dr-report-btn ${summaryLoading === label ? 'active' : ''}`}
                    disabled={!!summaryLoading}
                    onClick={() => triggerReport(label, query)}
                  >
                    {summaryLoading === label ? 'Generating...' : label}
                  </button>
                ))}
              </div>
              <div className="dr-report-hint">Sends Slack notification automatically</div>
            </div>

            <div className="dr-card" style={{ flex: 1 }}>
              <div className="dr-card-title">
                Upcoming
                <button className="dr-refresh" onClick={fetchAppointments}>
                  <svg viewBox="0 0 24 24"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                </button>
              </div>

              {appointments.length === 0 ? (
                <p className="dr-empty">No upcoming appointments.</p>
              ) : (
                <div className="dr-appt-list">
                  {appointments.slice(0, 10).map((a) => (
                    <div key={a.appointment_id} className="dr-appt-item">
                      <div className="dr-appt-top">
                        <span className="dr-appt-name">{a.patient_name}</span>
                        <span className={`dr-appt-status status-${a.status}`}>{a.status}</span>
                      </div>
                      <div className="dr-appt-time">{a.scheduled_at}</div>
                      {a.reason && <div className="dr-appt-reason">{a.reason}</div>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
