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
      console.log("EVENTS FROM BACKEND:", data); // 🔥 DEBUG
      setEvents(data); // ✅ БЕЗ map
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