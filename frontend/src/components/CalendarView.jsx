import { useRef } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import interactionPlugin from "@fullcalendar/interaction";
import ukLocale from "@fullcalendar/core/locales/uk";
import enLocale from "@fullcalendar/core/locales/en-gb";

export default function CalendarView({
  events = [],
  handleDateSelect,
  handleEventClick,
  handleEventDrop,
  handleEventResize,
  calendarRef,
  modalOpen,
  closeModal,
  newEvent,
  setNewEvent,
  selectedEvent,
  isEditMode,
  selectedColor,
  setSelectedColor,
  eventPalette = [],
  handleCreateEvent,
  handleUpdateEvent,
  handleDeleteEvent,
  lang = "uk",
  t,
  onCalendarTitleChange,
}) {
  const wheelLockRef = useRef(false);

  const toDatetimeLocal = (value) => {
    if (!value) return "";

    const date = new Date(value);

    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    const hours = String(date.getHours()).padStart(2, "0");
    const minutes = String(date.getMinutes()).padStart(2, "0");

    return `${year}-${month}-${day}T${hours}:${minutes}`;
  };

  const fromDatetimeLocal = (value) => {
    if (!value) return "";
    return `${value}:00`;
  };

  const getDurationMs = () => {
    const start = new Date(newEvent.start);
    const end = new Date(newEvent.end);

    if (!newEvent.start || !newEvent.end || end <= start) {
      return 30 * 60 * 1000;
    }

    return end.getTime() - start.getTime();
  };

  const handleStartChange = (value) => {
    const duration = getDurationMs();
    const start = new Date(value);
    const end = new Date(start.getTime() + duration);

    setNewEvent({
      ...newEvent,
      start: fromDatetimeLocal(value),
      end: fromDatetimeLocal(toDatetimeLocal(end)),
    });
  };

  const handleEndChange = (value) => {
    setNewEvent({
      ...newEvent,
      end: fromDatetimeLocal(value),
    });
  };

  const setDuration = (minutes) => {
    if (!newEvent.start) return;

    const start = new Date(newEvent.start);
    const end = new Date(start.getTime() + minutes * 60 * 1000);

    setNewEvent({
      ...newEvent,
      end: fromDatetimeLocal(toDatetimeLocal(end)),
    });
  };

  const formatCalendarTitle = (date) => {
    return new Intl.DateTimeFormat(lang === "uk" ? "uk-UA" : "en-US", {
      month: "long",
      year: "numeric",
    }).format(date);
  };

  const handleHorizontalWheel = (event) => {
    const isHorizontalSwipe = Math.abs(event.deltaX) > Math.abs(event.deltaY);

    if (!isHorizontalSwipe) return;
    if (Math.abs(event.deltaX) < 35) return;
    if (wheelLockRef.current) return;

    wheelLockRef.current = true;

    const calendarApi = calendarRef.current?.getApi();

    if (event.deltaX > 0) {
      calendarApi?.next();
    } else {
      calendarApi?.prev();
    }

    setTimeout(() => {
      wheelLockRef.current = false;
    }, 420);
  };

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

          const color = event.color || {
            bg: "#2563eb",
            bg2: "#38bdf8",
          };

          return {
            id: String(event.id),
            title:
              typeof event.title === "string"
                ? event.title
                : lang === "uk"
                ? "Без назви"
                : "Untitled",
            start,
            end,
            backgroundColor: color.bg,
            borderColor: color.bg,
            textColor: "#ffffff",
            extendedProps: {
              source: event.source,
              google_event_id: event.google_event_id,
              bg: color.bg,
              bg2: color.bg2,
            },
          };
        })
        .filter((event) => event.start && event.end)
    : [];

  const renderEventContent = (eventInfo) => {
    const bg = eventInfo.event.extendedProps.bg || "#2563eb";
    const bg2 = eventInfo.event.extendedProps.bg2 || "#38bdf8";

    return (
      <div
        className="custom-calendar-event"
        style={{
          background: `linear-gradient(135deg, ${bg}, ${bg2})`,
        }}
      >
        <span className="custom-event-time">{eventInfo.timeText}</span>
        <span className="custom-event-title">{eventInfo.event.title}</span>
      </div>
    );
  };

  return (
    <div className="calendar-page">
      <div className="calendar-scroll-shell" onWheel={handleHorizontalWheel}>
        <FullCalendar
          ref={calendarRef}
          plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
          locales={[ukLocale, enLocale]}
          locale={lang === "uk" ? "uk" : "en-gb"}
          initialView="adaptiveWeek"
          views={{
            adaptiveWeek: {
              type: "timeGrid",
              duration: { days: 7 },
              dateIncrement: { days: 1 },
            },
          }}
          headerToolbar={false}
          events={safeEvents}
          selectable={true}
          editable={true}
          selectMirror={true}
          select={handleDateSelect}
          eventClick={handleEventClick}
          eventDrop={handleEventDrop}
          eventResize={handleEventResize}
          eventContent={renderEventContent}
          allDaySlot={false}
          expandRows={false}
          height="78vh"
          slotMinTime="06:00:00"
          slotMaxTime="23:00:00"
          slotDuration="01:00:00"
          slotLabelInterval="01:00:00"
          snapDuration="00:30:00"
          nowIndicator={true}
          stickyHeaderDates={true}
          dayHeaderFormat={{
            weekday: "short",
            day: "numeric",
          }}
          datesSet={(dateInfo) => {
            const titleDate = dateInfo.view.currentStart || dateInfo.start;
            onCalendarTitleChange?.(formatCalendarTitle(titleDate));
          }}
        />
      </div>

      {modalOpen && (
        <div className="modal-overlay">
          <div className="modal modern-modal">
            <div className="modal-header">
              <div>
                <p className="eyebrow">{t.event}</p>
                <h3>{isEditMode ? t.editEvent : t.createEvent}</h3>
              </div>

              <button type="button" className="icon-button" onClick={closeModal}>
                ×
              </button>
            </div>

            {isEditMode && selectedEvent && (
              <div className="event-edit-meta">
                <span
                  className={`event-source ${
                    selectedEvent.source === "google" ? "google" : "local"
                  }`}
                >
                  {selectedEvent.source === "google" ? "Google" : t.local}
                </span>

                {selectedEvent.google_event_id && (
                  <span className="event-sync-label">Google Calendar sync</span>
                )}
              </div>
            )}

            <label>
              {t.title}
              <input
                type="text"
                placeholder={t.title}
                value={newEvent.title}
                onChange={(e) =>
                  setNewEvent({
                    ...newEvent,
                    title: e.target.value,
                  })
                }
              />
            </label>

            <div className="datetime-grid">
              <label>
                {t.start}
                <input
                  type="datetime-local"
                  value={toDatetimeLocal(newEvent.start)}
                  onChange={(e) => handleStartChange(e.target.value)}
                />
              </label>

              <label>
                {t.end}
                <input
                  type="datetime-local"
                  value={toDatetimeLocal(newEvent.end)}
                  onChange={(e) => handleEndChange(e.target.value)}
                />
              </label>
            </div>

            <div className="color-picker-block">
              <p>{t.color}</p>

              <div className="color-picker-grid">
                {eventPalette.map((color) => (
                  <button
                    key={color.id}
                    type="button"
                    className={`color-dot ${
                      selectedColor?.id === color.id ? "active" : ""
                    }`}
                    style={{
                      background: `linear-gradient(135deg, ${color.bg}, ${color.bg2})`,
                    }}
                    onClick={() => setSelectedColor(color)}
                    aria-label={color.name}
                    title={color.name}
                  />
                ))}
              </div>
            </div>

            <div className="duration-row">
              <button type="button" onClick={() => setDuration(30)}>
                {t.duration30}
              </button>

              <button type="button" onClick={() => setDuration(60)}>
                {t.duration60}
              </button>

              <button type="button" onClick={() => setDuration(90)}>
                {t.duration90}
              </button>

              <button type="button" onClick={() => setDuration(120)}>
                {t.duration120}
              </button>
            </div>

            <div className="modal-buttons">
              {isEditMode && (
                <button
                  type="button"
                  className="danger-button"
                  onClick={handleDeleteEvent}
                >
                  {t.delete}
                </button>
              )}

              <button type="button" onClick={closeModal}>
                {t.cancel}
              </button>

              <button
                type="button"
                className="primary-button"
                onClick={isEditMode ? handleUpdateEvent : handleCreateEvent}
              >
                {isEditMode ? t.save : t.create}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}