import { useState, useEffect } from 'react'
import axios from 'axios'
import './App.css'

function App() {
  const [user, setUser] = useState(localStorage.getItem('user_name') || null)
  const [view, setView] = useState('home') // 'home', 'history'
  const [file, setFile] = useState(null)
  const [transcript, setTranscript] = useState('')
  const [summary, setSummary] = useState('')
  const [emails, setEmails] = useState([])
  const [loading, setLoading] = useState(false)
  const [step, setStep] = useState('upload') // upload, transcript, result
  const [selectedEmailIndex, setSelectedEmailIndex] = useState(0)
  const [error, setError] = useState('')
  const [filename, setFilename] = useState('')
  const [history, setHistory] = useState([])
  const [loginError, setLoginError] = useState('')

  const handleLogin = (e) => {
    e.preventDefault()
    const username = e.target.username.value
    const password = e.target.password.value

    if (username === 'admin' && password) {
      setUser(username)
      localStorage.setItem('user_name', username)
      setLoginError('')
    } else {
      setLoginError('Invalid credentials. Username must be "admin"')
    }
  }

  const handleLogout = () => {
    setUser(null)
    localStorage.removeItem('user_name')
    setStep('upload')
    setTranscript('')
    setSummary('')
    setEmails([])
    setView('home')
  }

  const fetchHistory = async () => {
    try {
      const response = await axios.get('http://localhost:8000/history')
      setHistory(response.data)
    } catch (err) {
      console.error("Failed to fetch history", err)
    }
  }

  useEffect(() => {
    if (view === 'history') {
      fetchHistory()
    }
  }, [view])

  const handleUpload = async () => {
    if (!file) return

    setLoading(true)
    setError('') // Clear any previous errors

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await axios.post('http://localhost:8000/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      setTranscript(response.data.transcript)
      setStep('transcript')
    } catch (err) {
      setError('Failed to upload file. Please try again.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleGenerate = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await axios.post('http://localhost:8000/generate', {
        transcript: transcript,
        filename: filename
      })
      setSummary(response.data.summary)
      setEmails(response.data.emails)
      setStep('result')
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Failed to generate content. Please try again.'
      setError(errorMessage)
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSendEmail = (service) => {
    const currentEmail = emails[selectedEmailIndex]
    // Simple parsing to extract subject and body
    // Assuming format "Subject: ... \n\n Body..."
    let subject = "Meeting Follow-up"
    let body = currentEmail

    const subjectMatch = currentEmail.match(/Subject: (.*?)(\n|$)/)
    if (subjectMatch) {
      subject = subjectMatch[1]
      body = currentEmail.replace(subjectMatch[0], '').trim()
    }

    const encodedSubject = encodeURIComponent(subject)
    const encodedBody = encodeURIComponent(body)

    let url = ''
    if (service === 'gmail') {
      url = `https://mail.google.com/mail/?view=cm&fs=1&su=${encodedSubject}&body=${encodedBody}`
    } else if (service === 'outlook') {
      url = `https://outlook.office.com/mail/deeplink/compose?subject=${encodedSubject}&body=${encodedBody}`
    }

    window.open(url, '_blank')
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    alert("Copied to clipboard!")
  }

  const handleViewHistoryItem = (item) => {
    setTranscript(item.transcript)
    setSummary(item.summary)
    setEmails(item.emails)
    setFilename(item.filename)
    setStep('result')
    setView('home')
  }

  // Helper to format date in system timezone
  const formatDate = (utcString) => {
    if (!utcString) return ''
    // Append 'Z' to ensure it's treated as UTC if missing
    const date = new Date(utcString.endsWith('Z') ? utcString : utcString + 'Z')
    return date.toLocaleString()
  }

  if (!user) {
    return (
      <div className="login-container">
        <div className="upload-card login-card">
          <h2>Welcome Back</h2>
          <p className="subtitle">Please log in to your account</p>
          {loginError && <div className="error-message">{loginError}</div>}
          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label>Username</label>
              <input type="text" name="username" placeholder="Enter username" required />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input type="password" name="password" placeholder="Enter password" required />
            </div>
            <button type="submit" className="primary-btn full-width">Login</button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>Meeting AI</h1>
        </div>

        <nav className="sidebar-nav">
          <button
            className={`nav-item ${view === 'home' ? 'active' : ''}`}
            onClick={() => setView('home')}
          >
            <span className="icon">➕</span> New Meeting
          </button>
          <button
            className={`nav-item ${view === 'history' ? 'active' : ''}`}
            onClick={() => setView('history')}
          >
            <span className="icon">📜</span> History
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="user-info">
            <div className="avatar">{user[0].toUpperCase()}</div>
            <span className="username">{user}</span>
          </div>
          <button onClick={handleLogout} className="logout-btn-sidebar">
            Logout
          </button>
        </div>
      </aside>

      <main className="main-content-area">
        {view === 'history' ? (
          <div className="history-view">
            <h2>Meeting History</h2>
            <div className="history-list">
              {history.map((item) => (
                <div key={item.id} className="history-item">
                  <div className="history-info">
                    <h3>{item.filename}</h3>
                    <span className="timestamp">{formatDate(item.timestamp)}</span>
                    <p className="history-preview">{item.summary.substring(0, 100)}...</p>
                  </div>
                  <button
                    className="view-btn"
                    onClick={() => handleViewHistoryItem(item)}
                    title="View Summary & Emails"
                  >
                    👁️
                  </button>
                </div>
              ))}
              {history.length === 0 && <p>No history found.</p>}
            </div>
          </div>
        ) : (
          <>
            {error && <div className="error-message">{error}</div>}

            {step === 'upload' && (
              <div className="upload-container">
                <div className="upload-card">
                  <h2>Upload Transcript</h2>
                  <p className="subtitle">Supported formats: .txt, .docx</p>

                  <div
                    className="upload-area"
                    onDragOver={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                    }}
                    onDrop={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      const droppedFile = e.dataTransfer.files[0]
                      if (droppedFile) {
                        setFile(droppedFile)
                        setFilename(droppedFile.name)
                        setError('')
                      }
                    }}
                  >
                    <input
                      type="file"
                      id="file-upload"
                      accept=".txt,.docx"
                      onChange={(e) => {
                        const selectedFile = e.target.files[0]
                        if (selectedFile) {
                          setFile(selectedFile)
                          setFilename(selectedFile.name)
                          setError('')
                        }
                      }}
                      className="hidden-input"
                    />
                    <label htmlFor="file-upload" className="upload-label">
                      <div className="icon-wrapper">
                        <span className="upload-icon">☁️</span>
                      </div>
                      <div className="text-content">
                        {file ? (
                          <div className="selected-file">
                            <span className="file-icon">📄</span>
                            <span className="file-name">{file.name}</span>
                            <span className="change-file-text">Click to change</span>
                          </div>
                        ) : (
                          <>
                            <span className="primary-text">Click to upload</span>
                            <span className="secondary-text">or drag and drop</span>
                            <span className="format-info">TXT or DOCX</span>
                          </>
                        )}
                      </div>
                    </label>
                  </div>

                  <button
                    onClick={handleUpload}
                    disabled={!file || loading}
                    className="primary-btn large-btn"
                  >
                    {loading ? 'Uploading...' : 'Upload & Continue'}
                  </button>
                </div>
              </div>
            )}

            {step === 'transcript' && (
              <div className="transcript-container">
                <div className="section-header">
                  <h2>Review Transcript</h2>
                  <div className="actions">
                    <button className="secondary-btn" onClick={() => setStep('upload')}>Back</button>
                    <button className="primary-btn" onClick={handleGenerate} disabled={loading}>
                      {loading ? 'Generating...' : 'Generate Summary & Emails'}
                    </button>
                  </div>
                </div>
                <div className="editor-wrapper">
                  <textarea
                    value={transcript}
                    onChange={(e) => setTranscript(e.target.value)}
                    className="transcript-editor"
                  />
                </div>
              </div>
            )}

            {step === 'result' && (
              <div className="dashboard-container">
                <div className="dashboard-header">
                  <button onClick={() => setStep('transcript')} className="secondary-btn">← Back to Transcript</button>
                  <h2>Generation Results</h2>
                </div>

                <div className="dashboard-grid">
                  <div className="dashboard-card summary-card">
                    <div className="card-header">
                      <h3>Meeting Summary</h3>
                      <button className="copy-btn" onClick={() => copyToClipboard(summary)}>📋 Copy</button>
                    </div>
                    <div className="card-content summary-content">
                      {summary}
                    </div>
                  </div>

                  <div className="dashboard-card email-card">
                    <div className="card-header">
                      <h3>Email Drafts</h3>
                      <div className="tabs">
                        {emails.map((_, index) => (
                          <button
                            key={index}
                            className={`tab ${selectedEmailIndex === index ? 'active' : ''}`}
                            onClick={() => setSelectedEmailIndex(index)}
                          >
                            {index === 0 ? 'Formal' : index === 1 ? 'Action-Oriented' : 'Casual'}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="card-content">
                      <div className="email-actions-top">
                        <button className="copy-btn" onClick={() => copyToClipboard(emails[selectedEmailIndex])}>📋 Copy Text</button>
                      </div>
                      <textarea
                        className="email-preview"
                        value={emails[selectedEmailIndex]}
                        onChange={(e) => {
                          const newEmails = [...emails]
                          newEmails[selectedEmailIndex] = e.target.value
                          setEmails(newEmails)
                        }}
                      />

                      <div className="email-actions">
                        <button onClick={() => handleSendEmail('gmail')} className="action-btn gmail-btn">
                          Send via Gmail
                        </button>
                        <button onClick={() => handleSendEmail('outlook')} className="action-btn outlook-btn">
                          <span className="icon">O</span> Send via Outlook
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}

export default App
