import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import interactionPlugin from "@fullcalendar/interaction";
import { useEffect, useState } from "react";
import { fetchEvents } from "../services/api";

export default function CalendarView() {
  const [events, setEvents] = useState([]);

  useEffect(() => {
    fetchEvents().then(data => {
      const formatted = data.map(e => ({
        id: e.id,
        title: e.summary,
        start: e.start?.dateTime || e.start?.date,
        end: e.end?.dateTime || e.end?.date
      }));
      setEvents(formatted);
    });
  }, []);

  return (
    <FullCalendar
      plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
      initialView="timeGridWeek"
      events={events}
      height="90vh"
    />
  );
}