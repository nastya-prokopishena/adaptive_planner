import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import interactionPlugin from "@fullcalendar/interaction";

export default function CalendarView({
  events = [],
  handleDateSelect,
  handleEventDrop,
  handleEventResize,
  calendarRef,
  modalOpen,
  setModalOpen,
  newEvent,
  setNewEvent,
  handleCreateEvent,
  t,
}) {
  const safeEvents = Array.isArray(events)
    ? events
        .map((event) => {
          const start =
            typeof event.start === "object"
              ? event.start?.dateTime || event.start?.date
              : event.start;

          const end =
            typeof event.end === "object"
              ? event.end?.dateTime || event.end?.date
              : event.end;

          return {
            id: String(event.id),
            title:
              typeof event.title === "string"
                ? event.title
                : typeof event.summary === "string"
                ? event.summary
                : "Без назви",
            start,
            end,
          };
        })
        .filter((event) => event.start && event.end)
    : [];

  return (
    <div className="calendar-page">
      <FullCalendar
        ref={calendarRef}
        plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
        initialView="timeGridWeek"
        headerToolbar={false}
        events={safeEvents}
        selectable={true}
        editable={true}
        select={handleDateSelect}
        eventDrop={handleEventDrop}
        eventResize={handleEventResize}
        height="90vh"
      />

      {modalOpen && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>{t?.createEvent || "Створити подію"}</h3>

            <input
              type="text"
              placeholder={t?.title || "Назва"}
              value={newEvent.title}
              onChange={(e) =>
                setNewEvent({
                  ...newEvent,
                  title: e.target.value,
                })
              }
            />

            <div className="modal-buttons">
              <button type="button" onClick={() => setModalOpen(false)}>
                {t?.cancel || "Скасувати"}
              </button>

              <button type="button" onClick={handleCreateEvent}>
                {t?.create || "Створити"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}