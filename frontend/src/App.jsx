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

axios.defaults.withCredentials = true;

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [events, setEvents] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [theme, setTheme] = useState("dark");
  const [lang, setLang] = useState("uk");

  const [newEvent, setNewEvent] = useState({
    title: "",
    start: "",
    end: "",
  });

  const calendarRef = useRef(null);

  const translations = {
    en: {
      appName: "Adaptive Planner",
      today: "Today",
      week: "Week",
      month: "Month",
      calendar: "Calendar",
      createEvent: "Create Event",
      title: "Title",
      create: "Create",
      cancel: "Cancel",
      profile: "Profile",
      logout: "Logout",
      login: "Login",
      register: "Register",
      loading: "Loading...",
    },
    uk: {
      appName: "Adaptive Planner",
      today: "Сьогодні",
      week: "Тиждень",
      month: "Місяць",
      calendar: "Календар",
      createEvent: "Створити подію",
      title: "Назва",
      create: "Створити",
      cancel: "Скасувати",
      profile: "Профіль",
      logout: "Вийти",
      login: "Увійти",
      register: "Реєстрація",
      loading: "Завантаження...",
    },
  };

  const t = translations[lang];

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

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

  const normalizeEvent = (event) => {
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
      source: event.source || "local",
    };
  };

    const loadEvents = () => {
      if (!user) return;

      axios
        .get("/api/events")
        .then((res) => {
          const formatted = Array.isArray(res.data)
            ? res.data
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

          setEvents(formatted);
        })
        .catch((err) => {
          console.error("Error loading events:", err);
          setEvents([]);
        });
    };

  useEffect(() => {
    if (user) {
      loadEvents();
    }
  }, [user]);

  const changeView = (view) => {
    calendarRef.current?.getApi().changeView(view);
  };

  const goPrev = () => {
    calendarRef.current?.getApi().prev();
  };

  const goNext = () => {
    calendarRef.current?.getApi().next();
  };

  const goToday = () => {
    calendarRef.current?.getApi().today();
  };

  const handleDateSelect = (info) => {
    setNewEvent({
      title: "",
      start: info.startStr,
      end: info.endStr,
    });

    setModalOpen(true);
  };

  const handleCreateEvent = async () => {
    if (!newEvent.title.trim()) {
      alert("Введи назву події");
      return;
    }

    try {
      await axios.post("/api/events", newEvent);
      setModalOpen(false);
      setNewEvent({
        title: "",
        start: "",
        end: "",
      });
      loadEvents();
    } catch (error) {
      console.error(error);
      alert("Помилка при створенні події");
    }
  };

  const handleEventDrop = async (info) => {
    try {
      await axios.put(`/api/events/${info.event.id}`, {
        start: info.event.start?.toISOString(),
        end: info.event.end?.toISOString(),
      });

      loadEvents();
    } catch (error) {
      console.error(error);
      info.revert();
      alert("Помилка при оновленні події");
    }
  };

  const handleEventResize = async (info) => {
    try {
      await axios.put(`/api/events/${info.event.id}`, {
        start: info.event.start?.toISOString(),
        end: info.event.end?.toISOString(),
      });

      loadEvents();
    } catch (error) {
      console.error(error);
      info.revert();
      alert("Помилка при оновленні події");
    }
  };

  const logout = async () => {
    try {
      await axios.post("/auth/logout");
    } catch (error) {
      console.error(error);
    } finally {
      setUser(null);
      setEvents([]);
    }
  };

  if (loading) {
    return <div className="loading">{t.loading}</div>;
  }

  return (
    <BrowserRouter>
      <div className="app-wrapper">
        <div className="topbar">
          <div className="left-controls">
            {user && (
              <>
                <button type="button" onClick={goPrev}>
                  ‹
                </button>

                <button type="button" onClick={goToday}>
                  {t.today}
                </button>

                <button type="button" onClick={goNext}>
                  ›
                </button>
              </>
            )}
          </div>

          <div className="center-title">
            <Link to="/" className="logo-link">
              <h2>{t.appName}</h2>
            </Link>
          </div>

          <div className="right-controls">
            {user && (
              <>
                <button type="button" onClick={() => changeView("timeGridWeek")}>
                  {t.week}
                </button>

                <button type="button" onClick={() => changeView("dayGridMonth")}>
                  {t.month}
                </button>
              </>
            )}

            <button
              type="button"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            >
              {theme === "dark" ? "☀ Light" : "🌙 Dark"}
            </button>

            <button
              type="button"
              onClick={() => setLang(lang === "en" ? "uk" : "en")}
            >
              {lang === "en" ? "🇺🇦" : "🇬🇧"}
            </button>

            {user ? (
              <>
                <Link to="/profile">{t.profile}</Link>
                <button type="button" onClick={logout}>
                  {t.logout}
                </button>
              </>
            ) : (
              <>
                <Link to="/login">{t.login}</Link>
                <Link to="/register">{t.register}</Link>
              </>
            )}
          </div>
        </div>

        <Routes>
          <Route
            path="/"
            element={
              user ? (
                <CalendarView
                  events={events}
                  handleDateSelect={handleDateSelect}
                  handleEventDrop={handleEventDrop}
                  handleEventResize={handleEventResize}
                  calendarRef={calendarRef}
                  modalOpen={modalOpen}
                  setModalOpen={setModalOpen}
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

          <Route path="/login" element={<Login setUser={setUser} />} />
          <Route path="/register" element={<Register setUser={setUser} />} />

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