export default function EventList({ events = [], limit = 5, lang = "uk", t }) {
  const now = new Date();

  const upcomingEvents = events
    .filter((event) => {
      if (!event.start) return false;
      return new Date(event.start) >= now;
    })
    .sort((a, b) => new Date(a.start) - new Date(b.start))
    .slice(0, limit);

  const formatDate = (value) => {
    if (!value) return "";

    const date = new Date(value);

    return date.toLocaleString(lang === "uk" ? "uk-UA" : "en-US", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (!upcomingEvents.length) {
    return (
      <div className="event-list empty">
        <h3>{t.upcomingEvents}</h3>
        <p>{t.noUpcomingEvents}</p>
      </div>
    );
  }

  return (
    <div className="event-list">
      <div className="section-heading">
        <div>
          <h3>{t.upcomingEvents}</h3>
          <p>
            {t.shownEvents} {upcomingEvents.length}
          </p>
        </div>
      </div>

      <div className="event-list-items">
        {upcomingEvents.map((event) => (
          <div className="event-card" key={event.id}>
            <div className="event-card-header">
              <strong>{event.title || (lang === "uk" ? "Без назви" : "Untitled")}</strong>

              <span className={`event-source ${event.source || "local"}`}>
                {event.source === "google" ? "Google" : t.local}
              </span>
            </div>

            <p>
              {formatDate(event.start)} — {formatDate(event.end)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}