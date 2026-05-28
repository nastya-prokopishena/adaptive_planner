import { useState } from "react";
import { Link } from "react-router-dom";
import CalendarView from "../components/CalendarView";
import EventList from "../components/EventList";
import TasksPanel from "../components/TasksPanel";

export default function Dashboard({
  events,
  calendarRef,
  modalOpen,
  closeModal,
  newEvent,
  setNewEvent,
  selectedEvent,
  isEditMode,
  selectedColor,
  setSelectedColor,
  eventPalette,
  handleCreateEvent,
  handleUpdateEvent,
  handleDeleteEvent,
  handleDateSelect,
  handleEventClick,
  handleEventDrop,
  handleEventResize,
  openCreateModal,
  openAutoPlanModal,
  openDeleteManagerModal,
  goPrev,
  goNext,
  goToday,
  changeView,
  lang,
  t,
}) {
  const [calendarTitle, setCalendarTitle] = useState("");

  const now = new Date();

  const todayEvents = events.filter((event) => {
    if (!event.start) return false;

    const date = new Date(event.start);

    return (
      date.getFullYear() === now.getFullYear() &&
      date.getMonth() === now.getMonth() &&
      date.getDate() === now.getDate()
    );
  });

  const upcomingEvents = events.filter((event) => {
    if (!event.start) return false;
    return new Date(event.start) >= now;
  });

  const googleEvents = events.filter((event) => event.source === "google");
  const localEvents = events.filter((event) => event.source !== "google");

  return (
    <main className="ap-dashboard-page">
      <section className="ap-dashboard-stats">
        <article className="ap-stat-card">
          <span>{t.todayStat}</span>
          <strong>{todayEvents.length}</strong>
        </article>

        <article className="ap-stat-card">
          <span>{t.upcomingStat}</span>
          <strong>{upcomingEvents.length}</strong>
        </article>

        <article className="ap-stat-card">
          <span>{t.googleStat}</span>
          <strong>{googleEvents.length}</strong>
        </article>

        <article className="ap-stat-card">
          <span>{t.localStat}</span>
          <strong>{localEvents.length}</strong>
        </article>
      </section>

      <section className="ap-quick-actions">
        <button type="button" onClick={openCreateModal}>
          + {t.addEvent}
        </button>

        <Link to="/analytics">
          📊 Аналітика
        </Link>

        <Link to="/schedule-import">
          {t.uploadSchedule}
        </Link>

        <Link to="/tasks/import">
          🧠 Імпортувати задачу
        </Link>

        <button type="button" onClick={openAutoPlanModal}>
          ✨ {t.autoPlanning}
        </button>

        <button type="button" onClick={openDeleteManagerModal}>
          🗑 {t.manageDeletion}
        </button>
      </section>

      <section className="ap-dashboard-main">
        <aside className="ap-events-panel">
          <EventList events={events} limit={5} lang={lang} t={t} />
        </aside>

        <section className="ap-calendar-panel">
          <div className="ap-calendar-header">
            <div>
              <p className="eyebrow">{t.calendarSection}</p>
              <h2>{calendarTitle || t.schedule}</h2>
            </div>

            <div className="ap-calendar-controls">
              <button type="button" onClick={goPrev}>
                ‹
              </button>

              <button type="button" onClick={goToday}>
                {t.today}
              </button>

              <button type="button" onClick={goNext}>
                ›
              </button>

              <button type="button" onClick={() => changeView("adaptiveWeek")}>
                {t.week}
              </button>

              <button type="button" onClick={() => changeView("dayGridMonth")}>
                {t.month}
              </button>
            </div>
          </div>

          <CalendarView
            events={events}
            handleDateSelect={handleDateSelect}
            handleEventClick={handleEventClick}
            handleEventDrop={handleEventDrop}
            handleEventResize={handleEventResize}
            calendarRef={calendarRef}
            modalOpen={modalOpen}
            closeModal={closeModal}
            newEvent={newEvent}
            setNewEvent={setNewEvent}
            selectedEvent={selectedEvent}
            isEditMode={isEditMode}
            selectedColor={selectedColor}
            setSelectedColor={setSelectedColor}
            eventPalette={eventPalette}
            handleCreateEvent={handleCreateEvent}
            handleUpdateEvent={handleUpdateEvent}
            handleDeleteEvent={handleDeleteEvent}
            lang={lang}
            t={t}
            onCalendarTitleChange={setCalendarTitle}
          />
        </section>
      </section>

      <TasksPanel events={events} lang={lang} />
    </main>
  );
}
