export default function Sidebar({ theme, setTheme }) {
  return (
    <div className="sidebar">

      <h2>Calendar</h2>

      <button onClick={() =>
        setTheme(theme === "dark" ? "light" : "dark")
      }>
        {theme === "dark" ? "☀ Light" : "🌙 Dark"}
      </button>

      <div className="calendar-list">
        <div className="calendar-item">📚 Study</div>
        <div className="calendar-item">🏫 University</div>
        <div className="calendar-item">🏋 Gym</div>
      </div>

    </div>
  )
}