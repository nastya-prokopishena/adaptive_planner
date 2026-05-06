import { useEffect, useRef, useState } from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import axios from "axios";
import "./index.css";

import CalendarView from "./components/CalendarView";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Profile from "./pages/Profile";
import ProtectedRoute from "./components/ProtectedRoute";
import WelcomePage from "./pages/WelcomePage";

// 🔥 ОБОВʼЯЗКОВО
axios.defaults.withCredentials = true;

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

  // ====== AUTH CHECK (ВИПРАВЛЕНО) ======
  useEffect(() => {
    axios
      .get("/api/user/me")
      .then((res) => {
        if (res.data.authenticated) {
          setUser(res.data);
        } else {
          setUser(null);
        }
      })
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  // ====== LOAD EVENTS ======
  const loadEvents = () => {
    if (!user) return;

    axios
      .get("/api/events")
      .then((res) => {
        const formatted = res.data.map((event) => ({
          id: String(event.id),
          title:
            typeof event.title === "string"
              ? event.title
              : JSON.stringify(event.title || "No title"),
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
      await axios.post("/api/events", newEvent);
      setModalOpen(false);
      loadEvents();
    } catch (error) {
      console.error(error);
      alert("Error creating event");
    }
  };

  // ====== DRAG & DROP ======
  const handleEventDrop = (info) => {
    axios.put(`/api/events/${info.event.id}`, {
      start: info.event.start.toISOString(),
      end: info.event.end.toISOString(),
    });
  };

  const handleEventResize = (info) => {
    axios.put(`/api/events/${info.event.id}`, {
      start: info.event.start.toISOString(),
      end: info.event.end.toISOString(),
    });
  };

  const logout = async () => {
    await axios.post("/auth/logout");
    setUser(null);
    setEvents([]);
  };

  if (loading) return <div>Loading...</div>;

  return (
    <BrowserRouter>
      <div className="app-wrapper">

        {/* 🔝 HEADER */}
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

            {user ? (
              <>
                <Link to="/profile">Profile</Link>
                <button onClick={logout}>Logout</button>
              </>
            ) : (
              <>
                <Link to="/login">Login</Link>
                <Link to="/register">Register</Link>
              </>
            )}
          </div>
        </div>

        {/* 🔥 ROUTES */}
        <Routes>

          {/* 👇 ГОЛОВНЕ: Welcome або Calendar */}
          <Route
            path="/"
            element={
              user ? (
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
              ) : (
                <WelcomePage />
              )
            }
          />

          {/* LOGIN / REGISTER */}
          <Route path="/login" element={<Login setUser={setUser} />} />
          <Route path="/register" element={<Register setUser={setUser} />} />

          {/* PROFILE */}
          <Route
            path="/profile"
            element={
              <ProtectedRoute user={user}>
                <Profile user={user} />
              </ProtectedRoute>
            }
          />

        </Routes>
      </div>
    </BrowserRouter>
  );
}