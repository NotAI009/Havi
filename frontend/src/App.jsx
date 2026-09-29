import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './index.css';

const API = 'http://localhost:8000/api';

// ─── Icons (inline SVG to avoid dependency issues) ──────
const icons = {
  shield: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
  ),
  mic: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>
    </svg>
  ),
  upload: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>
    </svg>
  ),
  grid: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
    </svg>
  ),
  file: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
    </svg>
  ),
  list: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>
    </svg>
  ),
  users: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
    </svg>
  ),
  lock: (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>
  ),
  check: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  ),
  alert: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  ),
  x: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  ),
};

// ─── App Component ──────────────────────────────────────
export default function App() {
  const [page, setPage] = useState('dashboard');

  const pages = {
    dashboard: { label: 'Dashboard', icon: icons.grid, component: Dashboard },
    verify: { label: 'Verify Voice', icon: icons.mic, component: VerifyVoice },
    registry: { label: 'Consent Registry', icon: icons.file, component: ConsentRegistry },
    speakers: { label: 'Speakers', icon: icons.users, component: Speakers },
    audit: { label: 'Audit Trail', icon: icons.list, component: AuditTrail },
  };

  const Page = pages[page]?.component || Dashboard;

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-icon">{icons.shield}</div>
          <h1>HAVI</h1>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section-title">Overview</div>
          <button className={`nav-item ${page === 'dashboard' ? 'active' : ''}`} onClick={() => setPage('dashboard')}>
            {icons.grid} Dashboard
          </button>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section-title">Analysis</div>
          <button className={`nav-item ${page === 'verify' ? 'active' : ''}`} onClick={() => setPage('verify')}>
            {icons.mic} Verify Voice
          </button>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section-title">Management</div>
          <button className={`nav-item ${page === 'registry' ? 'active' : ''}`} onClick={() => setPage('registry')}>
            {icons.file} Consent Registry
          </button>
          <button className={`nav-item ${page === 'speakers' ? 'active' : ''}`} onClick={() => setPage('speakers')}>
            {icons.users} Speakers
          </button>
          <button className={`nav-item ${page === 'audit' ? 'active' : ''}`} onClick={() => setPage('audit')}>
            {icons.list} Audit Trail
          </button>
        </div>

        <div className="sidebar-footer">
          <div className="chain-status">
            <span className="chain-dot"></span>
            Audit chain verified
          </div>
        </div>
      </aside>

      <main className="main-content">
        <AnimatePresence mode="wait">
          <motion.div
            key={page}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <Page />
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}

// ─── Dashboard ──────────────────────────────────────────
function Dashboard() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API}/dashboard`).then(r => r.json()).then(setData).catch(() => {});
  }, []);

  if (!data) return <LoadingState />;

  return (
    <div>
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>System overview and recent verification activity</p>
      </div>

      <div className="stats-grid">
        <StatCard label="Protected Voices" value={data.protected_voices} accent="var(--accent)" />
        <StatCard label="Verified Recordings" value={data.verified_recordings} accent="var(--cyan)" />
        <StatCard label="Suspicious Attempts" value={data.suspicious_attempts} accent="var(--danger)" />
        <StatCard label="Active Consents" value={data.active_consents} accent="var(--success)" />
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{icons.list} Recent Verifications</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Avg risk: {data.avg_risk_score}
          </span>
        </div>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>File</th>
                <th>Speaker</th>
                <th>Identity</th>
                <th>Synthetic</th>
                <th>Consent</th>
                <th>Risk</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_verifications.map((v, i) => (
                <motion.tr
                  key={v.report_id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <td style={{ fontWeight: 600 }}>{v.filename}</td>
                  <td>{v.matched_speaker_name || '—'}</td>
                  <td>
                    <span style={{ color: v.speaker_similarity > 0.7 ? 'var(--success)' : 'var(--warning)', fontWeight: 600 }}>
                      {(v.speaker_similarity * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td>
                    <span style={{ color: v.synthetic_probability > 0.5 ? 'var(--danger)' : 'var(--success)', fontWeight: 600 }}>
                      {(v.synthetic_probability * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td>
                    <span className={`status-pill ${v.consent_status === 'ACTIVE' ? 'ACTIVE' : v.consent_status === 'NOT_FOUND' ? 'REVOKED' : v.consent_status}`}>
                      {v.consent_status || 'N/A'}
                    </span>
                  </td>
                  <td><span className={`risk-pill ${v.risk_level}`}>{v.risk_level}</span></td>
                  <td className="mono">{v.created_at ? new Date(v.created_at).toLocaleTimeString() : '—'}</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
          {data.recent_verifications.length === 0 && (
            <div className="empty-state">No verification records yet.</div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, accent }) {
  return (
    <motion.div
      className="stat-card"
      style={{ '--stat-accent': accent }}
      whileHover={{ y: -3 }}
      transition={{ type: 'spring', stiffness: 400 }}
    >
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ color: accent }}>{value}</div>
    </motion.div>
  );
}

// ─── Verify Voice ───────────────────────────────────────
function VerifyVoice() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [purpose, setPurpose] = useState('');
  const [speakerId, setSpeakerId] = useState('');
  const [speakers, setSpeakers] = useState([]);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef(null);

  useEffect(() => {
    fetch(`${API}/speakers`).then(r => r.json()).then(d => setSpeakers(d.speakers || [])).catch(() => {});
  }, []);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  };

  const handleSubmit = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);
    const fd = new FormData();
    fd.append('audio', file);
    if (purpose) fd.append('claimed_purpose', purpose);
    if (speakerId) fd.append('claimed_speaker_id', speakerId);
    try {
      const res = await fetch(`${API}/verify`, { method: 'POST', body: fd });
      setResult(await res.json());
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  return (
    <div>
      <div className="page-header">
        <h2>Voice Authentication</h2>
        <p>Upload an audio sample to run identity, authenticity, and consent verification</p>
      </div>

      <div className="verify-grid">
        <div className="card">
          <div className="card-header">
            <span className="card-title">{icons.upload} Audio Analysis</span>
          </div>

          <div className="form-group">
            <label className="form-label">Claimed Speaker (Optional)</label>
            <select className="form-select" value={speakerId} onChange={e => setSpeakerId(e.target.value)}>
              <option value="">— Auto-detect —</option>
              {speakers.map(s => (
                <option key={s.speaker_id} value={s.speaker_id}>{s.name} ({s.speaker_id})</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Claimed Purpose (Optional)</label>
            <select className="form-select" value={purpose} onChange={e => setPurpose(e.target.value)}>
              <option value="">— None specified —</option>
              <option value="AI Assistant">AI Assistant</option>
              <option value="Authentication">Authentication</option>
              <option value="Advertisement">Advertisement</option>
              <option value="Education">Education</option>
              <option value="Research">Research</option>
            </select>
          </div>

          <div
            className={`upload-zone ${dragOver ? 'drag-over' : ''} ${file ? 'has-file' : ''}`}
            onClick={() => fileRef.current?.click()}
            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
          >
            <div className="upload-icon">{file ? icons.check : icons.upload}</div>
            <div className="upload-title">{file ? file.name : 'Upload Audio Sample'}</div>
            <div className="upload-hint">
              {file ? `${(file.size / 1024).toFixed(1)} KB` : 'Drag & drop or click — WAV, MP3, FLAC'}
            </div>
            <input ref={fileRef} type="file" accept="audio/*" style={{ display: 'none' }} onChange={e => setFile(e.target.files[0])} />
          </div>

          <div style={{ marginTop: '1.25rem' }}>
            <button className="btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={!file || loading} onClick={handleSubmit}>
              {loading ? <><div className="spinner"></div> Analyzing...</> : <>{icons.shield} Analyze Voice</>}
            </button>
          </div>
        </div>

        <div>
          <AnimatePresence>
            {result && (
              <motion.div
                initial={{ opacity: 0, scale: 0.97, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ type: 'spring', stiffness: 300, damping: 25 }}
              >
                <ResultPanel result={result} />
              </motion.div>
            )}
            {!result && (
              <div className="card" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
                <div style={{ opacity: 0.15, marginBottom: '1rem' }}>{icons.shield}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  Upload an audio file to begin verification
                </div>
              </div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

function ResultPanel({ result }) {
  const r = result.risk_assessment;
  const s = result.speaker_verification;
  const d = result.deepfake_detection;
  const c = result.consent_verification;

  const barColor = (val, invert = false) => {
    const v = invert ? 1 - val : val;
    if (v > 0.7) return 'var(--success)';
    if (v > 0.4) return 'var(--warning)';
    return 'var(--danger)';
  };

  return (
    <div className={`card result-panel risk-${r.risk_level}`}>
      <div className={`result-risk-header ${r.risk_level}`}>
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, opacity: 0.7, marginBottom: '0.25rem' }}>RISK ASSESSMENT</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>{r.risk_score.toFixed(1)} / 100</div>
        </div>
        <span className={`risk-pill ${r.risk_level}`}>
          {r.risk_level === 'LOW' ? icons.check : r.risk_level === 'HIGH' ? icons.alert : icons.alert}
          {r.risk_level} RISK
        </span>
      </div>

      <div className="result-body">
        <div className="result-metric">
          <span className="metric-label">Identity Match</span>
          <div className="metric-value-row">
            <span className="metric-value" style={{ color: barColor(s.similarity_score) }}>
              {(s.similarity_score * 100).toFixed(1)}%
            </span>
            <div className="metric-bar">
              <div className="metric-bar-fill" style={{ width: `${s.similarity_score * 100}%`, background: barColor(s.similarity_score) }}></div>
            </div>
          </div>
        </div>

        {s.matched_speaker_name && (
          <div className="result-metric">
            <span className="metric-label">Matched Speaker</span>
            <span className="metric-value" style={{ color: 'var(--success)' }}>{s.matched_speaker_name}</span>
          </div>
        )}

        <div className="result-metric">
          <span className="metric-label">Synthetic Probability</span>
          <div className="metric-value-row">
            <span className="metric-value" style={{ color: barColor(d.synthetic_probability, true) }}>
              {(d.synthetic_probability * 100).toFixed(1)}%
            </span>
            <div className="metric-bar">
              <div className="metric-bar-fill" style={{ width: `${d.synthetic_probability * 100}%`, background: barColor(d.synthetic_probability, true) }}></div>
            </div>
          </div>
        </div>

        <div className="result-metric">
          <span className="metric-label">Consent Record</span>
          <span className={`status-pill ${c.consent_status === 'ACTIVE' ? 'ACTIVE' : c.consent_status === 'NOT_FOUND' ? 'REVOKED' : c.consent_status}`}>
            {c.consent_status}
          </span>
        </div>

        <div className="result-metric">
          <span className="metric-label">Usage Authorized</span>
          <span className="metric-value" style={{ color: c.usage_authorized ? 'var(--success)' : 'var(--danger)' }}>
            {c.usage_authorized ? 'AUTHORIZED' : 'UNAUTHORIZED'}
          </span>
        </div>

        {r.reasons.length > 0 && (
          <div className="reasons-section">
            <div style={{ fontSize: '0.75rem', fontWeight: 700, marginBottom: '0.5rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Assessment Details</div>
            {r.reasons.map((reason, i) => (
              <div key={i} className="reason-item">
                <span className="reason-bullet">→</span> {reason}
              </div>
            ))}
          </div>
        )}

        <div className="hash-footer">
          {icons.lock} SHA-256: {result.report_hash?.substring(0, 24)}...
        </div>
      </div>
    </div>
  );
}

// ─── Consent Registry ───────────────────────────────────
function ConsentRegistry() {
  const [consents, setConsents] = useState([]);
  useEffect(() => {
    fetch(`${API}/consent`).then(r => r.json()).then(d => setConsents(d.consents || [])).catch(() => {});
  }, []);

  return (
    <div>
      <div className="page-header">
        <h2>Consent Registry</h2>
        <p>Cryptographically signed voice usage consent records</p>
      </div>
      <div className="card">
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Person</th>
                <th>Consent ID</th>
                <th>Voice ID</th>
                <th>Purpose</th>
                <th>Expires</th>
                <th>Status</th>
                <th>Hash</th>
              </tr>
            </thead>
            <tbody>
              {consents.map((c, i) => (
                <motion.tr
                  key={c.consent_id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.04 }}
                >
                  <td style={{ fontWeight: 600 }}>{c.person_name}</td>
                  <td className="mono">{c.consent_id}</td>
                  <td className="mono">{c.voice_id}</td>
                  <td>{c.purpose}</td>
                  <td className="mono">{c.expires_at ? new Date(c.expires_at).toLocaleDateString() : '—'}</td>
                  <td><span className={`status-pill ${c.status}`}>{c.status}</span></td>
                  <td className="mono" style={{ fontSize: '0.7rem' }}>{c.record_hash?.substring(0, 12)}...</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
          {consents.length === 0 && <div className="empty-state">No consent records found.</div>}
        </div>
      </div>
    </div>
  );
}

// ─── Speakers ───────────────────────────────────────────
function Speakers() {
  const [speakers, setSpeakers] = useState([]);
  const [showRegister, setShowRegister] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [audio, setAudio] = useState(null);
  const [registering, setRegistering] = useState(false);

  const load = () => fetch(`${API}/speakers`).then(r => r.json()).then(d => setSpeakers(d.speakers || [])).catch(() => {});
  useEffect(() => { load(); }, []);

  const handleRegister = async () => {
    if (!name || !audio) return;
    setRegistering(true);
    const fd = new FormData();
    fd.append('name', name);
    fd.append('audio', audio);
    if (email) fd.append('email', email);
    try {
      await fetch(`${API}/speakers/register`, { method: 'POST', body: fd });
      setName(''); setEmail(''); setAudio(null); setShowRegister(false);
      load();
    } catch (err) { console.error(err); }
    setRegistering(false);
  };

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>Registered Speakers</h2>
          <p>Voice biometric profiles for identity verification</p>
        </div>
        <button className="btn-primary" onClick={() => setShowRegister(!showRegister)}>
          + Register Speaker
        </button>
      </div>

      <AnimatePresence>
        {showRegister && (
          <motion.div
            className="card"
            style={{ marginBottom: '1.5rem' }}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            <div className="card-header">
              <span className="card-title">{icons.users} New Speaker Registration</span>
              <button className="btn-ghost" onClick={() => setShowRegister(false)}>{icons.x}</button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Full Name *</label>
                <input className="form-input" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Rahul Sharma" />
              </div>
              <div className="form-group">
                <label className="form-label">Email</label>
                <input className="form-input" value={email} onChange={e => setEmail(e.target.value)} placeholder="email@example.com" />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Voice Sample *</label>
              <input type="file" accept="audio/*" className="form-input" onChange={e => setAudio(e.target.files[0])} />
            </div>
            <button className="btn-primary" disabled={!name || !audio || registering} onClick={handleRegister}>
              {registering ? 'Registering...' : 'Register Speaker'}
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="card">
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Speaker ID</th>
                <th>Voice ID</th>
                <th>Samples</th>
                <th>Registered</th>
              </tr>
            </thead>
            <tbody>
              {speakers.map((s, i) => (
                <motion.tr key={s.speaker_id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.04 }}>
                  <td style={{ fontWeight: 600 }}>{s.name}</td>
                  <td className="mono">{s.speaker_id}</td>
                  <td className="mono">{s.voice_id}</td>
                  <td>{s.samples_count}</td>
                  <td className="mono">{s.created_at ? new Date(s.created_at).toLocaleDateString() : '—'}</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
          {speakers.length === 0 && <div className="empty-state">No speakers registered.</div>}
        </div>
      </div>
    </div>
  );
}

// ─── Audit Trail ────────────────────────────────────────
function AuditTrail() {
  const [data, setData] = useState(null);
  const [chainValid, setChainValid] = useState(null);

  useEffect(() => {
    fetch(`${API}/audit?limit=50`).then(r => r.json()).then(setData).catch(() => {});
    fetch(`${API}/audit/verify`).then(r => r.json()).then(d => setChainValid(d.chain_valid)).catch(() => {});
  }, []);

  const dotClass = (type) => {
    if (type === 'ALERT_GENERATED') return 'alert';
    if (type === 'SPEAKER_VERIFIED' || type === 'CONSENT_CREATED') return 'success';
    return '';
  };

  if (!data) return <LoadingState />;

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>Audit Trail</h2>
          <p>Tamper-evident SHA-256 hash-chained event log</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span className="chain-dot" style={chainValid === false ? { background: 'var(--danger)', boxShadow: '0 0 8px var(--danger)' } : {}}></span>
          <span style={{ fontSize: '0.8rem', color: chainValid ? 'var(--success)' : 'var(--danger)', fontWeight: 600 }}>
            Chain {chainValid ? 'Verified' : 'COMPROMISED'}
          </span>
        </div>
      </div>

      <div className="card">
        <div className="timeline">
          {data.entries.map((e, i) => (
            <motion.div
              key={e.event_id}
              className="timeline-item"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.03 }}
            >
              <div className={`timeline-dot ${dotClass(e.event_type)}`}></div>
              <div className="timeline-content">
                <div className="timeline-type">{e.event_type}</div>
                <div className="timeline-detail">
                  {Object.entries(e.details || {}).map(([k, v]) => (
                    <span key={k} style={{ marginRight: '1rem' }}>
                      <span style={{ color: 'var(--text-muted)' }}>{k}:</span>{' '}
                      <span style={{ fontWeight: 500 }}>{typeof v === 'number' ? (Number.isInteger(v) ? v : v.toFixed(2)) : String(v)}</span>
                    </span>
                  ))}
                </div>
                <div className="timeline-time">
                  {e.timestamp ? new Date(e.timestamp).toLocaleString() : '—'}
                  {' • '}
                  <span className="mono" style={{ fontSize: '0.65rem' }}>{e.entry_hash?.substring(0, 16)}...</span>
                </div>
              </div>
            </motion.div>
          ))}
          {data.entries.length === 0 && (
            <div className="empty-state">No audit events recorded.</div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Loading State ──────────────────────────────────────
function LoadingState() {
  return (
    <div>
      <div className="page-header">
        <div className="skeleton" style={{ width: '200px', height: '28px', marginBottom: '0.5rem' }}></div>
        <div className="skeleton" style={{ width: '300px', height: '18px' }}></div>
      </div>
      <div className="stats-grid">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="skeleton" style={{ height: '100px', borderRadius: 'var(--radius-md)' }}></div>
        ))}
      </div>
      <div className="skeleton" style={{ height: '300px', borderRadius: 'var(--radius-lg)' }}></div>
    </div>
  );
}
