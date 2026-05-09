import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../AuthContext'
import ChatWindow from '../components/ChatWindow'
import api from '../api'

const QUICK_PROMPTS = [
  'Show all available doctors',
  'Book appointment with Dr. Ahuja tomorrow morning',
  'Check Dr. Sharma availability this Friday',
  'What appointments do I have?',
]

export default function PatientPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [appointments, setAppointments] = useState([])

  useEffect(() => {
    if (!user || user.role !== 'patient') { navigate('/login'); return }
    fetchAppointments()
  }, [])

  const fetchAppointments = async () => {
    try {
      const { data } = await api.get('/appointments/mine')
      setAppointments(data)
    } catch {}
  }

  const handleSend = async (message) => {
    setMessages((p) => [...p, { role: 'user', content: message }])
    setLoading(true)
    try {
      const { data } = await api.post('/chat/patient', { message, session_id: sessionId })
      setSessionId(data.session_id)
      setMessages((p) => [...p, {
        role: 'assistant',
        content: data.reply,
        tool_calls_made: data.tool_calls_made,
        appointment_booked: data.appointment_booked,
      }])
      if (data.appointment_booked) fetchAppointments()
    } catch {
      setMessages((p) => [...p, { role: 'assistant', content: 'Something went wrong. Please try again.' }])
    } finally {
      setLoading(false)
    }
  }

  const clearChat = () => {
    if (sessionId) api.delete(`/chat/session?session_id=${sessionId}`).catch(() => {})
    setMessages([])
    setSessionId(null)
  }

  const STATUS_STYLE = {
    scheduled:   { bg: '#eff6ff', color: '#1d4ed8' },
    completed:   { bg: '#f0fdf4', color: '#15803d' },
    cancelled:   { bg: '#fff1f2', color: '#be123c' },
    rescheduled: { bg: '#fffbeb', color: '#b45309' },
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=Tiro+Devanagari+Hindi&display=swap');

        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        .pt-root {
          min-height: 100vh;
          background: #f0f6ff;
          font-family: 'DM Sans', sans-serif;
          display: flex;
          flex-direction: column;
        }

        /* NAV */
        .pt-nav {
          height: 52px;
          background: #ffffff;
          border-bottom: 1px solid #dbeafe;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 24px;
          flex-shrink: 0;
        }

        .pt-nav-left {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .pt-logo {
          width: 30px;
          height: 30px;
          background: #1d4ed8;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .pt-logo svg {
          width: 15px;
          height: 15px;
          stroke: #fff;
          fill: none;
          stroke-width: 2;
          stroke-linecap: round;
          stroke-linejoin: round;
        }

        .pt-brand {
          font-family: 'Tiro Devanagari Hindi', serif;
          font-size: 17px;
          color: #1e3a8a;
        }

        .pt-nav-right {
          display: flex;
          align-items: center;
          gap: 16px;
        }

        .pt-user-label {
          font-size: 13px;
          color: #64748b;
        }

        .pt-logout {
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

        .pt-logout:hover { background: #eff6ff; }

        /* BODY */
        .pt-body {
          flex: 1;
          display: flex;
          gap: 18px;
          padding: 18px 24px;
          min-height: 0;
        }

        /* CHAT PANEL */
        .pt-chat-panel {
          flex: 1;
          background: #ffffff;
          border: 1px solid #dbeafe;
          border-radius: 14px;
          display: flex;
          flex-direction: column;
          overflow: hidden;
          min-height: 0;
        }

        .pt-chat-header {
          padding: 13px 18px;
          border-bottom: 1px solid #f1f5f9;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .pt-chat-title {
          font-size: 13.5px;
          font-weight: 600;
          color: #1e293b;
        }

        .pt-chat-sub {
          font-size: 11.5px;
          color: #94a3b8;
          margin-top: 1px;
        }

        .pt-new-btn {
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

        .pt-new-btn:hover { background: #eff6ff; }

        /* SIDEBAR */
        .pt-sidebar {
          width: 260px;
          flex-shrink: 0;
          display: flex;
          flex-direction: column;
          gap: 14px;
        }

        .pt-card {
          background: #ffffff;
          border: 1px solid #dbeafe;
          border-radius: 14px;
          padding: 16px;
        }

        .pt-card-title {
          font-size: 12.5px;
          font-weight: 600;
          color: #1e3a8a;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 12px;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .pt-refresh {
          background: none;
          border: none;
          cursor: pointer;
          color: #94a3b8;
          display: flex;
          align-items: center;
          transition: color 0.15s;
        }

        .pt-refresh:hover { color: #3b82f6; }

        .pt-refresh svg {
          width: 13px;
          height: 13px;
          stroke: currentColor;
          fill: none;
          stroke-width: 2;
          stroke-linecap: round;
          stroke-linejoin: round;
        }

        .pt-appt-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
          max-height: 420px;
          overflow-y: auto;
          scrollbar-width: thin;
          scrollbar-color: #dbeafe transparent;
        }

        .pt-appt-item {
          border: 1px solid #f1f5f9;
          border-radius: 9px;
          padding: 10px 11px;
        }

        .pt-appt-top {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 6px;
          margin-bottom: 4px;
        }

        .pt-appt-doc {
          font-size: 12.5px;
          font-weight: 500;
          color: #1e293b;
        }

        .pt-appt-spec {
          font-size: 11px;
          color: #94a3b8;
          margin-top: 1px;
        }

        .pt-status {
          font-size: 10.5px;
          font-weight: 500;
          padding: 2px 8px;
          border-radius: 20px;
          white-space: nowrap;
        }

        .pt-appt-time {
          font-size: 11px;
          color: #64748b;
        }

        .pt-empty-text {
          font-size: 12.5px;
          color: #94a3b8;
          text-align: center;
          padding: 16px 0;
        }
      `}</style>

      <div className="pt-root">
        <nav className="pt-nav">
          <div className="pt-nav-left">
            <div className="pt-logo">
              <svg viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>
            </div>
            <span className="pt-brand">निदान</span>
          </div>
          <div className="pt-nav-right">
            <span className="pt-user-label">Hello, {user?.full_name}</span>
            <button className="pt-logout" onClick={logout}>Sign out</button>
          </div>
        </nav>

        <div className="pt-body">
          <div className="pt-chat-panel">
            <div className="pt-chat-header">
              <div>
                <div className="pt-chat-title">Appointment Assistant</div>
                <div className="pt-chat-sub">GPT-4o · multi-turn conversation</div>
              </div>
              <button className="pt-new-btn" onClick={clearChat}>New chat</button>
            </div>
            <ChatWindow
              onSend={handleSend}
              loading={loading}
              messages={messages}
              placeholder="e.g. Book an appointment with Dr. Ahuja tomorrow morning..."
              quickPrompts={QUICK_PROMPTS}
            />
          </div>

          <div className="pt-sidebar">
            <div className="pt-card">
              <div className="pt-card-title">
                My Appointments
                <button className="pt-refresh" onClick={fetchAppointments}>
                  <svg viewBox="0 0 24 24"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                </button>
              </div>

              {appointments.length === 0 ? (
                <p className="pt-empty-text">No appointments yet.</p>
              ) : (
                <div className="pt-appt-list">
                  {appointments.map((a) => {
                    const s = STATUS_STYLE[a.status] || { bg: '#f1f5f9', color: '#64748b' }
                    return (
                      <div key={a.appointment_id} className="pt-appt-item">
                        <div className="pt-appt-top">
                          <div>
                            <div className="pt-appt-doc">{a.doctor_name}</div>
                            <div className="pt-appt-spec">{a.specialization}</div>
                          </div>
                          <span className="pt-status" style={{ background: s.bg, color: s.color }}>
                            {a.status}
                          </span>
                        </div>
                        <div className="pt-appt-time">{a.scheduled_at}</div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
