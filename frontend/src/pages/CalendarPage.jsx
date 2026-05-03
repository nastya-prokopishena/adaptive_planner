import { useState, useEffect } from "react"

export default function CalendarPage() {
  const [theme, setTheme] = useState("dark")

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme)
  }, [theme])

  return (
    <>
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        padding: "20px 40px"
      }}>
        <h2>March 2026</h2>

        <button
          onClick={() =>
            setTheme(theme === "dark" ? "light" : "dark")
          }
          style={{
            background: "none",
            border: "1px solid var(--border-color)",
            padding: "6px 12px",
            borderRadius: "8px",
            cursor: "pointer"
          }}
        >
          {theme === "dark" ? "☀ Light" : "🌙 Dark"}
        </button>
      </div>

      <FullCalendar
        headerToolbar={false}
        initialView="timeGridWeek"
        plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
        events={events}
      />
    </>
  )
}