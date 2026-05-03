// src/App.jsx
import { useEffect, useRef, useState } from "react";
import { BrowserRouter, Routes, Route, Link, Navigate } from "react-router-dom";
import axios from "axios";
import "./index.css";

import CalendarView from "./components/CalendarView";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Profile from "./pages/Profile";
import ProtectedRoute from "./components/ProtectedRoute";

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [events, setEvents] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [theme, setTheme] = useState("dark");
  const [lang, setLang] = useState("en");

  const [newEvent, setNewEvent] = useState({
    title: "",
    start: "",
    end: "",
  });

  const calendarRef = useRef(null);

  const translations = {
    en: {
      today: "Today",
      week: "Week",
      month: "Month",
      calendar: "Calendar",
      createEvent: "Create Event",
      title: "Title",
      create: "Create",
      cancel: "Cancel",
    },
    uk: {
      today: "Сьогодні",
      week: "Тиждень",
      month: "Місяць",
      calendar: "Календар",
      createEvent: "Створити подію",
      title: "Назва",
      create: "Створити",
      cancel: "Скасувати",
    },
  };

  const t = translations[lang];

  // ====== THEME ======
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  // ====== CHECK AUTH ======
  useEffect(() => {
    axios
      .get("/api/user/me", { withCredentials: true })
      .then((res) => setUser(res.data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  // ====== LOAD EVENTS (only if user is logged in) ======
  const loadEvents = () => {
    if (!user) return;
    axios
      .get("/api/events", { withCredentials: true })
      .then((res) => {
        const formatted = res.data.map((event) => ({
          id: event.id,
          title: event.title,
          start: new Date(event.start),
          end: new Date(event.end),
        }));
        setEvents(formatted);
      })
      .catch((err) => console.error("Error loading events:", err));
  };

  useEffect(() => {
    if (user) {
      loadEvents();
    }
  }, [user]);

  // ====== NAVIGATION ======
  const changeView = (view) => {
    calendarRef.current?.getApi().changeView(view);
  };

  const goPrev = () => calendarRef.current?.getApi().prev();
  const goNext = () => calendarRef.current?.getApi().next();
  const goToday = () => calendarRef.current?.getApi().today();

  // ====== CREATE EVENT ======
  const handleDateSelect = (info) => {
    setNewEvent({
      title: "",
      start: info.startStr,
      end: info.endStr,
    });
    setModalOpen(true);
  };

  const handleCreateEvent = async () => {
    if (!newEvent.title) return;
    try {
      await axios.post("/api/events", newEvent, { withCredentials: true });
      setModalOpen(false);
      loadEvents();
    } catch (error) {
      console.error(error);
      alert("Error creating event");
    }
  };

  // ====== DRAG & DROP ======
  const handleEventDrop = (info) => {
    axios.put(
      `/api/events/${info.event.id}`,
      {
        start: info.event.start.toISOString(),
        end: info.event.end.toISOString(),
      },
      { withCredentials: true }
    );
  };

  const handleEventResize = (info) => {
    axios.put(
      `/api/events/${info.event.id}`,
      {
        start: info.event.start.toISOString(),
        end: info.event.end.toISOString(),
      },
      { withCredentials: true }
    );
  };

  const logout = async () => {
    await axios.post("/auth/logout", {}, { withCredentials: true });
    setUser(null);
    setEvents([]);
  };

  if (loading) return <div>Loading...</div>;

  return (
    <BrowserRouter>
      <div className="app-wrapper">
        <div className="topbar">
          <div className="left-controls">
            {user && (
              <>
                <button onClick={goPrev}>‹</button>
                <button onClick={goToday}>{t.today}</button>
                <button onClick={goNext}>›</button>
              </>
            )}
          </div>

          <div className="center-title">
            <h2>{t.calendar}</h2>
          </div>

          <div className="right-controls">
            {user && (
              <>
                <button onClick={() => changeView("timeGridWeek")}>
                  {t.week}
                </button>
                <button onClick={() => changeView("dayGridMonth")}>
                  {t.month}
                </button>
              </>
            )}
            <button onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
              {theme === "dark" ? "☀ Light" : "🌙 Dark"}
            </button>
            <button onClick={() => setLang(lang === "en" ? "uk" : "en")}>
              {lang === "en" ? "🇺🇦" : "🇬🇧"}
            </button>
            {user && (
              <>
                <Link to="/profile">Profile</Link>
                <button onClick={logout}>Logout</button>
              </>
            )}
            {!user && (
              <>
                <Link to="/login">Login</Link>
                <Link to="/register">Register</Link>
              </>
            )}
          </div>
        </div>

        <Routes>
          <Route
            path="/login"
            element={<Login setUser={setUser} />}
          />
          <Route
            path="/register"
            element={<Register setUser={setUser} />}
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute user={user}>
                <Profile user={user} />
              </ProtectedRoute>
            }
          />
          <Route
            path="/"
            element={
              <ProtectedRoute user={user}>
                <CalendarView
                  events={events}
                  lang={lang}
                  handleDateSelect={handleDateSelect}
                  handleEventDrop={handleEventDrop}
                  handleEventResize={handleEventResize}
                  calendarRef={calendarRef}
                  modalOpen={modalOpen}
                  newEvent={newEvent}
                  setNewEvent={setNewEvent}
                  handleCreateEvent={handleCreateEvent}
                  t={t}
                />
              </ProtectedRoute>
            }
          />
        </Routes>
      </div>
    </BrowserRouter>
  );
}