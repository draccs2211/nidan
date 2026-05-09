import { useState, useRef, useEffect } from 'react'

export default function ChatWindow({ onSend, loading, messages, placeholder, quickPrompts = [] }) {
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = () => {
    const text = input.trim()
    if (!text || loading) return
    onSend(text)
    setInput('')
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&display=swap');

        .cw-wrap {
          display: flex;
          flex-direction: column;
          height: 100%;
          font-family: 'DM Sans', sans-serif;
        }

        .cw-messages {
          flex: 1;
          overflow-y: auto;
          padding: 20px 20px 8px;
          display: flex;
          flex-direction: column;
          gap: 14px;
          scrollbar-width: thin;
          scrollbar-color: #dbeafe transparent;
        }

        .cw-messages::-webkit-scrollbar { width: 4px; }
        .cw-messages::-webkit-scrollbar-thumb { background: #bfdbfe; border-radius: 4px; }

        .cw-empty {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 40px 24px;
          gap: 20px;
        }

        .cw-empty-icon {
          width: 48px;
          height: 48px;
          background: #eff6ff;
          border-radius: 14px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .cw-empty-icon svg {
          width: 22px;
          height: 22px;
          stroke: #3b82f6;
          fill: none;
          stroke-width: 1.8;
          stroke-linecap: round;
          stroke-linejoin: round;
        }

        .cw-empty-text {
          font-size: 13px;
          color: #94a3b8;
          text-align: center;
          line-height: 1.6;
        }

        .cw-quick {
          display: flex;
          flex-wrap: wrap;
          gap: 7px;
          justify-content: center;
        }

        .cw-quick-btn {
          background: #f0f6ff;
          border: 1px solid #bfdbfe;
          color: #1d4ed8;
          font-size: 12px;
          font-family: 'DM Sans', sans-serif;
          border-radius: 20px;
          padding: 6px 13px;
          cursor: pointer;
          transition: background 0.15s;
        }

        .cw-quick-btn:hover { background: #dbeafe; }

        .cw-row {
          display: flex;
        }

        .cw-row.user { justify-content: flex-end; }
        .cw-row.assistant { justify-content: flex-start; }

        .cw-bubble-wrap { max-width: 78%; display: flex; flex-direction: column; gap: 4px; }

        .cw-sender {
          font-size: 11px;
          font-weight: 500;
          color: #94a3b8;
          margin-bottom: 2px;
          padding-left: 2px;
        }

        .cw-bubble {
          padding: 10px 14px;
          border-radius: 14px;
          font-size: 13.5px;
          line-height: 1.65;
          white-space: pre-wrap;
          word-break: break-word;
        }

        .cw-row.user .cw-bubble {
          background: #1d4ed8;
          color: #ffffff;
          border-bottom-right-radius: 4px;
        }

        .cw-row.assistant .cw-bubble {
          background: #ffffff;
          color: #1e293b;
          border: 1px solid #e2e8f0;
          border-bottom-left-radius: 4px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }

        .cw-tools {
          display: flex;
          flex-wrap: wrap;
          gap: 5px;
          margin-top: 2px;
        }

        .cw-tool-tag {
          font-size: 10.5px;
          background: #f0f6ff;
          color: #2563eb;
          border: 1px solid #bfdbfe;
          border-radius: 20px;
          padding: 2px 9px;
          font-weight: 500;
        }

        .cw-booked {
          margin-top: 6px;
          background: #f0fdf4;
          border: 1px solid #bbf7d0;
          border-radius: 10px;
          padding: 10px 12px;
          display: flex;
          gap: 10px;
          align-items: flex-start;
        }

        .cw-booked-line {
          width: 3px;
          background: #22c55e;
          border-radius: 3px;
          align-self: stretch;
          flex-shrink: 0;
        }

        .cw-booked-title {
          font-size: 12px;
          font-weight: 600;
          color: #15803d;
          margin-bottom: 2px;
        }

        .cw-booked-detail {
          font-size: 11.5px;
          color: #166534;
        }

        .cw-typing {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 10px 14px;
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 14px;
          border-bottom-left-radius: 4px;
          width: fit-content;
          box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }

        .cw-dot {
          width: 6px;
          height: 6px;
          background: #93c5fd;
          border-radius: 50%;
          animation: bounce 1.2s infinite;
        }

        .cw-dot:nth-child(2) { animation-delay: 0.2s; }
        .cw-dot:nth-child(3) { animation-delay: 0.4s; }

        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-5px); }
        }

        /* quick prompts above input */
        .cw-quick-bottom {
          padding: 8px 20px 4px;
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }

        /* Input area */
        .cw-input-area {
          border-top: 1px solid #e2e8f0;
          padding: 12px 16px;
          display: flex;
          gap: 10px;
          align-items: flex-end;
          background: #ffffff;
        }

        .cw-textarea {
          flex: 1;
          border: 1.5px solid #e2e8f0;
          border-radius: 10px;
          padding: 9px 13px;
          font-size: 13.5px;
          font-family: 'DM Sans', sans-serif;
          color: #0f172a;
          background: #fafcff;
          resize: none;
          outline: none;
          max-height: 120px;
          transition: border-color 0.15s, box-shadow 0.15s;
          line-height: 1.5;
        }

        .cw-textarea:focus {
          border-color: #3b82f6;
          background: #fff;
          box-shadow: 0 0 0 3px rgba(59,130,246,0.09);
        }

        .cw-send {
          width: 38px;
          height: 38px;
          background: #1d4ed8;
          border: none;
          border-radius: 9px;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          flex-shrink: 0;
          transition: background 0.15s;
        }

        .cw-send:hover:not(:disabled) { background: #1e40af; }
        .cw-send:disabled { opacity: 0.4; cursor: not-allowed; }

        .cw-send svg {
          width: 16px;
          height: 16px;
          stroke: #ffffff;
          fill: none;
          stroke-width: 2;
          stroke-linecap: round;
          stroke-linejoin: round;
        }
      `}</style>

      <div className="cw-wrap">
        <div className="cw-messages">
          {messages.length === 0 ? (
            <div className="cw-empty">
              <div className="cw-empty-icon">
                <svg viewBox="0 0 24 24">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
              </div>
              <p className="cw-empty-text">Type a message to get started.<br />The AI will use live data to help you.</p>
              {quickPrompts.length > 0 && (
                <div className="cw-quick">
                  {quickPrompts.map((p) => (
                    <button key={p} className="cw-quick-btn" onClick={() => onSend(p)}>{p}</button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <>
              {messages.map((msg, i) => (
                <div key={i} className={`cw-row ${msg.role}`}>
                  <div className="cw-bubble-wrap">
                    {msg.role === 'assistant' && <div className="cw-sender">Nidan AI</div>}
                    <div className="cw-bubble">{msg.content}</div>

                    {msg.tool_calls_made?.length > 0 && (
                      <div className="cw-tools">
                        {msg.tool_calls_made.map((t) => (
                          <span key={t} className="cw-tool-tag">{t}</span>
                        ))}
                      </div>
                    )}

                    {msg.appointment_booked && (
                      <div className="cw-booked">
                        <div className="cw-booked-line" />
                        <div>
                          <div className="cw-booked-title">Appointment Confirmed</div>
                          <div className="cw-booked-detail">
                            {msg.appointment_booked.scheduled_at} &nbsp;&middot;&nbsp; ID #{msg.appointment_booked.id}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="cw-row assistant">
                  <div className="cw-typing">
                    <div className="cw-dot" />
                    <div className="cw-dot" />
                    <div className="cw-dot" />
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={bottomRef} />
        </div>

        {messages.length > 0 && quickPrompts.length > 0 && (
          <div className="cw-quick-bottom">
            {quickPrompts.slice(0, 3).map((p) => (
              <button key={p} className="cw-quick-btn" onClick={() => onSend(p)}>{p}</button>
            ))}
          </div>
        )}

        <div className="cw-input-area">
          <textarea
            className="cw-textarea"
            placeholder={placeholder}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
            }}
          />
          <button className="cw-send" onClick={handleSend} disabled={loading || !input.trim()}>
            <svg viewBox="0 0 24 24">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </div>
    </>
  )
}
