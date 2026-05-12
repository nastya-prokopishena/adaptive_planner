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

  const upcomingEvents = events.filter((event) => {
    if (!event.start) return false;
    return new Date(event.start) >= now;
  });

  const todayEvents = events.filter((event) => {
    if (!event.start) return false;

    const date = new Date(event.start);

    return (
      date.getFullYear() === now.getFullYear() &&
      date.getMonth() === now.getMonth() &&
      date.getDate() === now.getDate()
    );
  });

  const googleEvents = events.filter((event) => event.source === "google");
  const localEvents = events.filter((event) => event.source !== "google");

  return (
    <main className="dashboard-page">
      <section className="dashboard-header">
        <div>
          <p className="eyebrow">{t.personalPlanner}</p>
          <h1>Dashboard</h1>
          <p>{t.dashboardSubtitle}</p>
        </div>

        <button
          type="button"
          className="primary-button"
          onClick={openCreateModal}
        >
          + {t.createEvent}
        </button>
      </section>

      <section className="compact-stats">
        <div>
          <span>{t.todayStat}</span>
          <strong>{todayEvents.length}</strong>
        </div>

        <div>
          <span>{t.upcomingStat}</span>
          <strong>{upcomingEvents.length}</strong>
        </div>

        <div>
          <span>{t.googleStat}</span>
          <strong>{googleEvents.length}</strong>
        </div>

        <div>
          <span>{t.localStat}</span>
          <strong>{localEvents.length}</strong>
        </div>
      </section>

      <section className="workspace-grid">
        <aside className="workspace-sidebar">
          <EventList events={events} limit={5} lang={lang} t={t} />

          <div className="planner-tools">
            <h3>{t.quickActions}</h3>

            <button type="button" onClick={openCreateModal}>
              + {t.addEvent}
            </button>

            <Link to="/schedule-import" className="planner-tool-link">
              {t.uploadSchedule}
            </Link>

            <button type="button" onClick={openAutoPlanModal}>
              ✨ {t.autoPlanning}
            </button>

            <button type="button" onClick={openDeleteManagerModal}>
              🗑 {t.manageDeletion}
            </button>

            <p>{t.toolsDescription}</p>
          </div>
        </aside>

        <section className="calendar-panel">
          <div className="calendar-panel-header">
            <div>
              <p className="eyebrow">{t.calendarSection}</p>
              <h2>{calendarTitle || t.schedule}</h2>
            </div>

            <div className="calendar-controls">
              <button type="button" onClick={goPrev}>
                ‹
              </button>

              <button type="button" onClick={goToday}>
                {t.today}
              </button>

              <button type="button" onClick={goNext}>
                ›
              </button>

              <div className="view-switcher">
                <button type="button" onClick={() => changeView("adaptiveWeek")}>
                  {t.week}
                </button>

                <button type="button" onClick={() => changeView("dayGridMonth")}>
                  {t.month}
                </button>
              </div>
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