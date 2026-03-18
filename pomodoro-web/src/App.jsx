import { useState, useEffect, useRef, useCallback } from 'react'
import './App.css'

const DEFAULT_SETTINGS = {
  focusMin: 25,
  breakMin: 5,
  autoAdvance: true,
  sound: true,
}

function loadSettings() {
  try {
    const raw = localStorage.getItem('pomodoroSettings')
    if (raw) return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) }
  } catch {}
  return { ...DEFAULT_SETTINGS }
}

function saveSettings(s) {
  try { localStorage.setItem('pomodoroSettings', JSON.stringify(s)) } catch {}
}

function fmt(sec) {
  sec = Math.max(0, sec)
  return `${String(Math.floor(sec / 60)).padStart(2, '0')}:${String(sec % 60).padStart(2, '0')}`
}

export default function App() {
  const [settings, setSettings] = useState(loadSettings)
  const [phase, setPhase] = useState('FOCUS')
  const [running, setRunning] = useState(false)
  const [remaining, setRemaining] = useState(() => loadSettings().focusMin * 60)
  const [flashing, setFlashing] = useState(false)
  const [showSettings, setShowSettings] = useState(false)

  const endTimeRef = useRef(null)
  const intervalRef = useRef(null)
  const settingsRef = useRef(settings)
  const phaseRef = useRef(phase)
  settingsRef.current = settings
  phaseRef.current = phase

  const phaseSeconds = (p, s) => (p === 'FOCUS' ? s.focusMin : s.breakMin) * 60

  const playBeep = useCallback(() => {
    if (!settingsRef.current.sound) return
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.frequency.value = 880
      osc.type = 'sine'
      gain.gain.setValueAtTime(0.3, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5)
      osc.start(ctx.currentTime)
      osc.stop(ctx.currentTime + 0.5)
    } catch {}
  }, [])

  const flash = useCallback(() => {
    setFlashing(true)
    setTimeout(() => setFlashing(false), 400)
  }, [])

  const startPhase = useCallback((p, s) => {
    const secs = phaseSeconds(p, s)
    endTimeRef.current = Date.now() + secs * 1000
    setPhase(p)
    setRemaining(secs)
    setRunning(true)
  }, [])

  // Tick
  useEffect(() => {
    if (!running) {
      clearInterval(intervalRef.current)
      return
    }
    intervalRef.current = setInterval(() => {
      const sec = Math.ceil((endTimeRef.current - Date.now()) / 1000)
      if (sec <= 0) {
        setRemaining(0)
        clearInterval(intervalRef.current)
        setRunning(false)
        playBeep()
        flash()
        const next = phaseRef.current === 'FOCUS' ? 'BREAK' : 'FOCUS'
        if (settingsRef.current.autoAdvance) {
          startPhase(next, settingsRef.current)
        } else {
          setPhase(next)
          setRemaining(phaseSeconds(next, settingsRef.current))
          endTimeRef.current = null
        }
      } else {
        setRemaining(sec)
      }
    }, 200)
    return () => clearInterval(intervalRef.current)
  }, [running, playBeep, flash, startPhase])

  useEffect(() => {
    document.title = `${fmt(remaining)} — ${phase === 'FOCUS' ? 'Focus' : 'Break'} | PomodoroMini`
  }, [remaining, phase])

  function toggleStartPause() {
    if (!running) {
      endTimeRef.current = Date.now() + remaining * 1000
      setRunning(true)
    } else {
      clearInterval(intervalRef.current)
      endTimeRef.current = null
      setRunning(false)
    }
  }

  function reset() {
    clearInterval(intervalRef.current)
    endTimeRef.current = null
    setRunning(false)
    setPhase('FOCUS')
    setRemaining(settings.focusMin * 60)
  }

  function skipPhase() {
    playBeep()
    flash()
    const next = phase === 'FOCUS' ? 'BREAK' : 'FOCUS'
    startPhase(next, settings)
  }

  function updateSettings(updates) {
    setSettings(prev => {
      const next = { ...prev, ...updates }
      saveSettings(next)
      if (!running) {
        if ('focusMin' in updates && phaseRef.current === 'FOCUS') setRemaining(next.focusMin * 60)
        if ('breakMin' in updates && phaseRef.current === 'BREAK') setRemaining(next.breakMin * 60)
      }
      return next
    })
  }

  const isFocus = phase === 'FOCUS'
  const total = phaseSeconds(phase, settings)
  const progress = total > 0 ? (total - remaining) / total : 0
  const circumference = 2 * Math.PI * 54

  return (
    <div className={`app ${isFocus ? 'focus' : 'break'} ${flashing ? 'flash' : ''}`}>
      <div className="card">
        <div className="tabs">
          <button
            className={`tab ${isFocus ? 'active' : ''}`}
            onClick={() => { if (!running) { setPhase('FOCUS'); setRemaining(settings.focusMin * 60); endTimeRef.current = null } }}
          >Focus</button>
          <button
            className={`tab ${!isFocus ? 'active' : ''}`}
            onClick={() => { if (!running) { setPhase('BREAK'); setRemaining(settings.breakMin * 60); endTimeRef.current = null } }}
          >Break</button>
        </div>

        <div className="circle-wrap">
          <svg className="circle-svg" viewBox="0 0 120 120">
            <circle className="circle-bg" cx="60" cy="60" r="54" />
            <circle
              className="circle-fg"
              cx="60" cy="60" r="54"
              strokeDasharray={circumference}
              strokeDashoffset={circumference * (1 - progress)}
            />
          </svg>
          <div className="time-display">{fmt(remaining)}</div>
        </div>

        <div className="controls">
          <button className="ctrl-btn" onClick={reset} title="Reset">⟲</button>
          <button className="ctrl-btn primary" onClick={toggleStartPause} title={running ? 'Pause' : 'Start'}>
            {running ? '⏸' : '▶'}
          </button>
          <button className="ctrl-btn" onClick={skipPhase} title="Skip">≫</button>
        </div>

        <div className="bottom-row">
          <button
            className={`icon-btn ${settings.sound ? '' : 'muted'}`}
            onClick={() => updateSettings({ sound: !settings.sound })}
            title="Toggle sound"
          >{settings.sound ? '🔊' : '🔇'}</button>
          <button
            className={`icon-btn ${settings.autoAdvance ? 'active' : ''}`}
            onClick={() => updateSettings({ autoAdvance: !settings.autoAdvance })}
            title="Auto-advance phases"
          >🔄</button>
          <button className="icon-btn" onClick={() => setShowSettings(s => !s)} title="Settings">⚙️</button>
        </div>

        {showSettings && (
          <div className="settings-panel">
            <div className="setting-row">
              <label>Focus</label>
              <input
                type="number" min="1" max="120"
                value={settings.focusMin}
                onChange={e => updateSettings({ focusMin: Math.max(1, Math.min(120, parseInt(e.target.value) || 1)) })}
              />
              <span>min</span>
            </div>
            <div className="setting-row">
              <label>Break</label>
              <input
                type="number" min="1" max="60"
                value={settings.breakMin}
                onChange={e => updateSettings({ breakMin: Math.max(1, Math.min(60, parseInt(e.target.value) || 1)) })}
              />
              <span>min</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
