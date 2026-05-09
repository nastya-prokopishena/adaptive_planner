import { useEffect, useRef, useState } from "react";
import { BrowserRouter, Routes, Route, Link, useNavigate } from "react-router-dom";
import axios from "axios";
import "./index.css";

import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Profile from "./pages/Profile";
import ProtectedRoute from "./components/ProtectedRoute";
import WelcomePage from "./pages/WelcomePage";

axios.defaults.withCredentials = true;

function AppContent() {
  const defaultRecurrence = {
    type: "none",
    interval: 1,
    unit: "week",
    days: [],
    endType: "never",
    endDate: "",
    count: 4,
  };

  const eventPalette = [
    { id: "blue", name: "Blue", bg: "#2563eb", bg2: "#38bdf8" },
    { id: "green", name: "Green", bg: "#16a34a", bg2: "#4ade80" },
    { id: "red", name: "Red", bg: "#dc2626", bg2: "#f87171" },
    { id: "purple", name: "Purple", bg: "#7c3aed", bg2: "#a78bfa" },
    { id: "orange", name: "Orange", bg: "#ea580c", bg2: "#fb923c" },
    { id: "teal", name: "Teal", bg: "#0f766e", bg2: "#2dd4bf" },
    { id: "pink", name: "Pink", bg: "#db2777", bg2: "#f472b6" },
    { id: "indigo", name: "Indigo", bg: "#4338ca", bg2: "#818cf8" },
    { id: "lime", name: "Lime", bg: "#65a30d", bg2: "#a3e635" },
    { id: "amber", name: "Amber", bg: "#d97706", bg2: "#fbbf24" },
    { id: "cyan", name: "Cyan", bg: "#0891b2", bg2: "#22d3ee" },
    { id: "rose", name: "Rose", bg: "#e11d48", bg2: "#fb7185" },
  ];

  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [events, setEvents] = useState([]);

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [isEditMode, setIsEditMode] = useState(false);

  const [autoPlanOpen, setAutoPlanOpen] = useState(false);
  const [autoPlanTask, setAutoPlanTask] = useState({
    title: "",
    duration_minutes: 60,
    date_from: "",
    date_to: "",
    day_start: "08:00",
    day_end: "22:00",
    preferred_time: "10:00",
    repeat_enabled: false,
    times_per_week: 1,
    allowed_days: [],
  });

  const [deleteManagerOpen, setDeleteManagerOpen] = useState(false);
  const [deleteSearchQuery, setDeleteSearchQuery] = useState("");
  const [deleteSearchResults, setDeleteSearchResults] = useState([]);
  const [selectedDeleteIds, setSelectedDeleteIds] = useState([]);

  const [theme, setTheme] = useState("dark");
  const [lang, setLang] = useState("uk");

  const [toast, setToast] = useState(null);
  const [confirmDialog, setConfirmDialog] = useState(null);
  const [recurringDeleteDialog, setRecurringDeleteDialog] = useState(null);

  const [newEvent, setNewEvent] = useState({
    title: "",
    start: "",
    end: "",
    recurrence: defaultRecurrence,
  });

  const [eventTitleColors, setEventTitleColors] = useState(() => {
    try {
      const saved = localStorage.getItem("eventTitleColors");
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });

  const [selectedColor, setSelectedColor] = useState(eventPalette[0]);

  const calendarRef = useRef(null);
  const navigate = useNavigate();

  const translations = {
    uk: {
      appName: "Adaptive Planner",
      today: "Сьогодні",
      week: "Тиждень",
      month: "Місяць",
      createEvent: "Створити подію",
      editEvent: "Редагувати подію",
      title: "Назва",
      create: "Створити",
      save: "Зберегти",
      delete: "Видалити",
      cancel: "Скасувати",
      profile: "Профіль",
      logout: "Вийти",
      login: "Увійти",
      register: "Реєстрація",
      loading: "Завантаження...",

      dashboardSubtitle:
        "Календар, найближчі події та швидкі дії для адаптивного планування.",
      personalPlanner: "Особистий планер",
      calendarSection: "Календар",
      schedule: "Розклад",
      todayStat: "Сьогодні",
      upcomingStat: "Найближчі",
      googleStat: "Google",
      localStat: "Локальні",
      upcomingEvents: "Найближчі події",
      shownEvents: "Показано найближчих подій:",
      noUpcomingEvents: "Найближчих подій поки немає",
      quickActions: "Швидкі дії",
      addEvent: "Додати подію",
      uploadSchedule: "Завантажити розклад",
      autoPlanning: "Автопланування",
      toolsDescription:
        "Ці дії будуть використані для імпорту розкладу, пошуку вільного часу та адаптивного планування.",

      start: "Початок",
      end: "Кінець",
      duration30: "30 хв",
      duration60: "1 год",
      duration90: "1 год 30 хв",
      duration120: "2 год",
      event: "Подія",
      color: "Колір події",

      repeat: "Повторення",
      repeatNone: "Не повторювати",
      repeatDaily: "Щодня",
      repeatWeekdays: "Кожен будній день",
      repeatWeekly: "Щотижня",
      repeatBiweekly: "Кожні 2 тижні",
      repeatMonthly: "Щомісяця",
      repeatYearly: "Щороку",
      repeatCustom: "Custom...",
      customRepeat: "Custom repeat",
      every: "Кожні",
      day: "день",
      monthUnit: "місяць",
      year: "рік",
      on: "У дні",
      ends: "Завершення",
      never: "Ніколи",
      onDate: "У дату",
      after: "Після",
      times: "разів",
      done: "Готово",

      autoPlanTitle: "Автоматичне планування",
      autoPlanDescription:
        "Система знайде вільний слот у календарі та створить подію без накладань.",
      taskTitle: "Назва задачі",
      durationMinutes: "Тривалість, хв",
      dateFrom: "Початкова дата",
      dateTo: "Кінцева дата",
      dayStart: "Планувати з",
      dayEnd: "Планувати до",
      preferredTime: "Бажаний час",
      autoPlanButton: "Запланувати автоматично",
      autoPlanSuccess: "Подію автоматично заплановано",
      autoPlanError: "Не вдалося автоматично запланувати подію",
      noFreeSlot: "Вільний слот не знайдено",
      repeatAutoPlan: "Повторювати задачу",
      timesPerWeek: "Кількість разів на тиждень",
      preferredDays: "Бажані дні",
      plannedMany: "Події автоматично заплановано",

      manageDeletion: "Керувати видаленням",
      deleteManagerTitle: "Керування видаленням",
      deleteManagerDescription:
        "Знайди події за назвою, вибери конкретні варіанти або видали всі події з однаковою назвою.",
      searchByEventName: "Пошук за назвою події",
      searchPlaceholder: "Наприклад: Gym, навчання, робота",
      searchEvents: "Знайти події",
      selectedForDelete: "Вибрано для видалення",
      deleteSelected: "Видалити вибрані",
      deleteAllWithTitle: "Видалити всі з такою назвою",
      noDeleteResults: "Подій за цим запитом не знайдено",
      deleteOnlyThis: "Тільки цю подію",
      deleteThisAndFuture: "Цю і всі наступні",
      deleteWholeSeries: "Усю серію",
      recurringDeleteTitle: "Що саме видалити?",
      recurringDeleteDescription:
        "Це повторювана подія. Можна видалити тільки цей екземпляр, усі наступні або всю серію.",
      bulkDeleteSuccess: "Події видалено",
      selectEventsFirst: "Спочатку вибери події для видалення",
      enterSearchTitle: "Введи назву події для пошуку",

      enterTitle: "Введи назву події",
      invalidEnd: "Кінець події має бути пізніше за початок",
      createError: "Помилка при створенні події",
      updateError: "Помилка при оновленні події",
      deleteError: "Помилка при видаленні події",
      conflictError: "Цей час уже зайнятий іншою подією",
      confirmDeleteTitle: "Видалити подію?",
      confirmDeleteText:
        "Цю дію не можна буде скасувати. Подія також буде видалена з Google Calendar, якщо вона синхронізована.",
      confirmDeleteAction: "Так, видалити",
      successCreate: "Подію створено",
      successUpdate: "Подію оновлено",
      successDelete: "Подію видалено",
      local: "Локальна",
      untitled: "Без назви",
    },

    en: {
      appName: "Adaptive Planner",
      today: "Today",
      week: "Week",
      month: "Month",
      createEvent: "Create event",
      editEvent: "Edit event",
      title: "Title",
      create: "Create",
      save: "Save",
      delete: "Delete",
      cancel: "Cancel",
      profile: "Profile",
      logout: "Logout",
      login: "Login",
      register: "Register",
      loading: "Loading...",

      dashboardSubtitle:
        "Calendar, upcoming events and quick actions for adaptive planning.",
      personalPlanner: "Personal planner",
      calendarSection: "Calendar",
      schedule: "Schedule",
      todayStat: "Today",
      upcomingStat: "Upcoming",
      googleStat: "Google",
      localStat: "Local",
      upcomingEvents: "Upcoming events",
      shownEvents: "Upcoming events shown:",
      noUpcomingEvents: "No upcoming events yet",
      quickActions: "Quick actions",
      addEvent: "Add event",
      uploadSchedule: "Upload schedule",
      autoPlanning: "Auto planning",
      toolsDescription:
        "These actions will be used for schedule import, free time search and adaptive planning.",

      start: "Start",
      end: "End",
      duration30: "30 min",
      duration60: "1 h",
      duration90: "1 h 30 min",
      duration120: "2 h",
      event: "Event",
      color: "Event color",

      repeat: "Repeat",
      repeatNone: "Does not repeat",
      repeatDaily: "Every day",
      repeatWeekdays: "Every weekday",
      repeatWeekly: "Every week",
      repeatBiweekly: "Every 2 weeks",
      repeatMonthly: "Every month",
      repeatYearly: "Every year",
      repeatCustom: "Custom...",
      customRepeat: "Custom repeat",
      every: "Every",
      day: "day",
      monthUnit: "month",
      year: "year",
      on: "On",
      ends: "Ends",
      never: "Never",
      onDate: "On",
      after: "After",
      times: "times",
      done: "Done",

      autoPlanTitle: "Automatic planning",
      autoPlanDescription:
        "The system will find a free calendar slot and create an event without overlaps.",
      taskTitle: "Task title",
      durationMinutes: "Duration, min",
      dateFrom: "Start date",
      dateTo: "End date",
      dayStart: "Plan from",
      dayEnd: "Plan until",
      preferredTime: "Preferred time",
      autoPlanButton: "Plan automatically",
      autoPlanSuccess: "Event was planned automatically",
      autoPlanError: "Could not automatically plan the event",
      noFreeSlot: "No free slot found",
      repeatAutoPlan: "Repeat task",
      timesPerWeek: "Times per week",
      preferredDays: "Preferred days",
      plannedMany: "Events were planned automatically",

      manageDeletion: "Manage deletion",
      deleteManagerTitle: "Deletion manager",
      deleteManagerDescription:
        "Search events by title, select exact items or delete all events with the same title.",
      searchByEventName: "Search by event name",
      searchPlaceholder: "For example: Gym, study, work",
      searchEvents: "Search events",
      selectedForDelete: "Selected for deletion",
      deleteSelected: "Delete selected",
      deleteAllWithTitle: "Delete all with this title",
      noDeleteResults: "No events found for this query",
      deleteOnlyThis: "Only this event",
      deleteThisAndFuture: "This and future events",
      deleteWholeSeries: "Whole series",
      recurringDeleteTitle: "What do you want to delete?",
      recurringDeleteDescription:
        "This is a recurring event. You can delete only this occurrence, this and future events, or the whole series.",
      bulkDeleteSuccess: "Events deleted",
      selectEventsFirst: "Select events first",
      enterSearchTitle: "Enter event title to search",

      enterTitle: "Enter event title",
      invalidEnd: "Event end must be later than start",
      createError: "Error while creating event",
      updateError: "Error while updating event",
      deleteError: "Error while deleting event",
      conflictError: "This time overlaps with another event",
      confirmDeleteTitle: "Delete event?",
      confirmDeleteText:
        "This action cannot be undone. The event will also be deleted from Google Calendar if it is synced.",
      confirmDeleteAction: "Yes, delete",
      successCreate: "Event created",
      successUpdate: "Event updated",
      successDelete: "Event deleted",
      local: "Local",
      untitled: "Untitled",
    },
  };

  const t = translations[lang];

  const normalizeTitleKey = (title) => {
    return (title || "").trim().toLowerCase();
  };

  const getSafeRecurrence = (recurrence) => {
    return {
      ...defaultRecurrence,
      ...(recurrence || {}),
      days: Array.isArray(recurrence?.days) ? recurrence.days : [],
    };
  };

  const getEventColorByTitle = (title, colorsMap = eventTitleColors) => {
    const key = normalizeTitleKey(title);

    if (key && colorsMap[key]) {
      return colorsMap[key];
    }

    if (!key) {
      return eventPalette[0];
    }

    let hash = 0;

    for (let i = 0; i < key.length; i += 1) {
      hash = key.charCodeAt(i) + ((hash << 5) - hash);
    }

    const index = Math.abs(hash) % eventPalette.length;

    return eventPalette[index];
  };

  const saveColorForTitle = (title, color) => {
    const key = normalizeTitleKey(title);

    if (!key || !color) {
      return eventTitleColors;
    }

    const updatedColors = {
      ...eventTitleColors,
      [key]: color,
    };

    setEventTitleColors(updatedColors);
    localStorage.setItem("eventTitleColors", JSON.stringify(updatedColors));

    return updatedColors;
  };

  const showToast = (type, message) => {
    setToast({ type, message });

    setTimeout(() => {
      setToast(null);
    }, 3500);
  };

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  useEffect(() => {
    axios
      .get("/api/user/me")
      .then((res) => {
        setUser(res.data.authenticated ? res.data : null);
      })
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const formatDateForApi = (date) => {
    if (!date) return "";

    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    const hours = String(d.getHours()).padStart(2, "0");
    const minutes = String(d.getMinutes()).padStart(2, "0");

    return `${year}-${month}-${day}T${hours}:${minutes}:00`;
  };

  const formatEventDate = (value) => {
    if (!value) return "";

    const date = new Date(value);

    return new Intl.DateTimeFormat(lang === "uk" ? "uk-UA" : "en-US", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  };

  const normalizeEvent = (event, colorsMap = eventTitleColors) => {
    const start =
      typeof event.start === "object"
        ? event.start?.dateTime || event.start?.date
        : event.start;

    const end =
      typeof event.end === "object"
        ? event.end?.dateTime || event.end?.date
        : event.end;

    const title =
      typeof event.title === "string"
        ? event.title
        : typeof event.summary === "string"
          ? event.summary
          : t.untitled;

    const color = getEventColorByTitle(title, colorsMap);

    return {
      id: String(event.id),
      master_id: event.master_id || event.id,
      title,
      start,
      end,
      source: event.source || "local",
      google_event_id: event.google_event_id || null,
      is_recurring: event.is_recurring || false,
      recurrence: getSafeRecurrence(event.recurrence),
      color,
    };
  };

  const loadEvents = (colorsMap = eventTitleColors) => {
    if (!user) return;

    axios
      .get("/api/events")
      .then((res) => {
        const formattedEvents = Array.isArray(res.data)
          ? res.data
              .map((event) => normalizeEvent(event, colorsMap))
              .filter((event) => event.start && event.end)
          : [];

        setEvents(formattedEvents);
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
  }, [user, lang]);

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

  const resetEventForm = () => {
    setModalOpen(false);
    setSelectedEvent(null);
    setIsEditMode(false);
    setNewEvent({
      title: "",
      start: "",
      end: "",
      recurrence: defaultRecurrence,
    });
  };

  const openCreateModal = () => {
    const now = new Date();

    const start = new Date(now);
    start.setMinutes(0, 0, 0);

    const end = new Date(start);
    end.setMinutes(end.getMinutes() + 30);

    setSelectedEvent(null);
    setIsEditMode(false);
    setSelectedColor(eventPalette[0]);

    setNewEvent({
      title: "",
      start: formatDateForApi(start),
      end: formatDateForApi(end),
      recurrence: defaultRecurrence,
    });

    setModalOpen(true);
  };

  const openAutoPlanModal = () => {
    const today = new Date();
    const nextWeek = new Date();

    nextWeek.setDate(today.getDate() + 7);

    const formatOnlyDate = (date) => {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, "0");
      const day = String(date.getDate()).padStart(2, "0");

      return `${year}-${month}-${day}`;
    };

    setAutoPlanTask({
      title: "",
      duration_minutes: 60,
      date_from: formatOnlyDate(today),
      date_to: formatOnlyDate(nextWeek),
      day_start: "08:00",
      day_end: "22:00",
      preferred_time: "10:00",
      repeat_enabled: false,
      times_per_week: 1,
      allowed_days: [],
    });

    setAutoPlanOpen(true);
  };

  const openDeleteManagerModal = () => {
    setDeleteSearchQuery("");
    setDeleteSearchResults([]);
    setSelectedDeleteIds([]);
    setDeleteManagerOpen(true);
  };

  const handleDateSelect = (info) => {
    setSelectedEvent(null);
    setIsEditMode(false);
    setSelectedColor(eventPalette[0]);

    setNewEvent({
      title: "",
      start: formatDateForApi(info.start),
      end: formatDateForApi(info.end),
      recurrence: defaultRecurrence,
    });

    setModalOpen(true);
  };

  const handleEventClick = (info) => {
    const clickedEvent = events.find(
      (event) => String(event.id) === String(info.event.id)
    );

    if (!clickedEvent) return;

    setSelectedEvent(clickedEvent);
    setIsEditMode(true);
    setSelectedColor(clickedEvent.color || getEventColorByTitle(clickedEvent.title));

    setNewEvent({
      title: clickedEvent.title || "",
      start: formatDateForApi(clickedEvent.start),
      end: formatDateForApi(clickedEvent.end),
      recurrence: getSafeRecurrence(clickedEvent.recurrence),
    });

    setModalOpen(true);
  };

  const handleApiError = (error, fallbackMessage) => {
    console.error(error);

    if (error?.response?.status === 409) {
      const conflictTitle =
        error.response.data?.conflict_event?.title || t.untitled;

      showToast("error", `${t.conflictError}: ${conflictTitle}`);
      return;
    }

    showToast("error", fallbackMessage);
  };

  const validateEventForm = () => {
    if (!newEvent.title.trim()) {
      showToast("error", t.enterTitle);
      return false;
    }

    if (!newEvent.start || !newEvent.end) {
      showToast("error", t.invalidEnd);
      return false;
    }

    const startDate = new Date(newEvent.start);
    const endDate = new Date(newEvent.end);

    if (endDate <= startDate) {
      showToast("error", t.invalidEnd);
      return false;
    }

    return true;
  };

  const handleCreateEvent = async () => {
    if (!validateEventForm()) return;

    const updatedColors = saveColorForTitle(newEvent.title, selectedColor);

    try {
      await axios.post("/api/events", {
        title: newEvent.title,
        start: newEvent.start,
        end: newEvent.end,
        recurrence: getSafeRecurrence(newEvent.recurrence),
      });

      resetEventForm();

      showToast("success", t.successCreate);
      loadEvents(updatedColors);
    } catch (error) {
      handleApiError(error, t.createError);
    }
  };

  const handleUpdateEvent = async () => {
    if (!selectedEvent) return;
    if (!validateEventForm()) return;

    const targetId = selectedEvent.master_id || selectedEvent.id;
    const updatedColors = saveColorForTitle(newEvent.title, selectedColor);

    try {
      await axios.put(`/api/events/${targetId}`, {
        title: newEvent.title,
        start: newEvent.start,
        end: newEvent.end,
        recurrence: getSafeRecurrence(newEvent.recurrence),
      });

      resetEventForm();

      showToast("success", t.successUpdate);
      loadEvents(updatedColors);
    } catch (error) {
      handleApiError(error, t.updateError);
    }
  };

  const deleteEventByScope = async (event, scope = "all") => {
    const targetId = event.master_id || event.id;

    await axios.delete(`/api/events/${targetId}`, {
      data: {
        scope,
        occurrence_start: event.start,
      },
    });
  };

  const confirmRecurringDelete = async (scope) => {
    if (!recurringDeleteDialog?.event) return;

    try {
      await deleteEventByScope(recurringDeleteDialog.event, scope);

      setRecurringDeleteDialog(null);
      resetEventForm();

      showToast("success", t.successDelete);
      loadEvents();
    } catch (error) {
      setRecurringDeleteDialog(null);
      handleApiError(error, t.deleteError);
    }
  };

  const handleDeleteEvent = async () => {
    if (!selectedEvent) return;

    if (selectedEvent.is_recurring) {
      setRecurringDeleteDialog({
        event: selectedEvent,
      });
      return;
    }

    setConfirmDialog({
      title: t.confirmDeleteTitle,
      message: t.confirmDeleteText,
      confirmText: t.confirmDeleteAction,
      cancelText: t.cancel,
      onConfirm: async () => {
        try {
          await deleteEventByScope(selectedEvent, "all");

          setConfirmDialog(null);
          resetEventForm();

          showToast("success", t.successDelete);
          loadEvents();
        } catch (error) {
          setConfirmDialog(null);
          handleApiError(error, t.deleteError);
        }
      },
    });
  };

  const handleEventDrop = async (info) => {
    const targetId =
      info.event.extendedProps?.master_id ||
      String(info.event.id).split("__")[0];

    try {
      await axios.put(`/api/events/${targetId}`, {
        title: info.event.title,
        start: formatDateForApi(info.event.start),
        end: formatDateForApi(info.event.end),
        recurrence: getSafeRecurrence(info.event.extendedProps?.recurrence),
      });

      showToast("success", t.successUpdate);
      loadEvents();
    } catch (error) {
      info.revert();
      handleApiError(error, t.updateError);
    }
  };

  const handleEventResize = async (info) => {
    const targetId =
      info.event.extendedProps?.master_id ||
      String(info.event.id).split("__")[0];

    try {
      await axios.put(`/api/events/${targetId}`, {
        title: info.event.title,
        start: formatDateForApi(info.event.start),
        end: formatDateForApi(info.event.end),
        recurrence: getSafeRecurrence(info.event.extendedProps?.recurrence),
      });

      showToast("success", t.successUpdate);
      loadEvents();
    } catch (error) {
      info.revert();
      handleApiError(error, t.updateError);
    }
  };

  const handleAutoPlan = async () => {
    if (!autoPlanTask.title.trim()) {
      showToast("error", t.enterTitle);
      return;
    }

    try {
      const response = await axios.post("/api/planner/auto-plan", autoPlanTask);

      setAutoPlanOpen(false);

      const plannedCount = response.data?.planned_count || 1;

      if (plannedCount > 1) {
        showToast("success", `${t.plannedMany}: ${plannedCount}`);
      } else {
        showToast("success", t.autoPlanSuccess);
      }

      loadEvents();
    } catch (error) {
      console.error(error);

      if (error?.response?.status === 409) {
        showToast("error", t.noFreeSlot);
        return;
      }

      showToast("error", t.autoPlanError);
    }
  };

  const searchEventsForDeletion = async () => {
    if (!deleteSearchQuery.trim()) {
      showToast("error", t.enterSearchTitle);
      return;
    }

    try {
      const response = await axios.get("/api/events/search", {
        params: {
          query: deleteSearchQuery.trim(),
        },
      });

      const formattedEvents = Array.isArray(response.data)
        ? response.data.map(normalizeEvent)
        : [];

      setDeleteSearchResults(formattedEvents);
      setSelectedDeleteIds([]);
    } catch (error) {
      handleApiError(error, t.deleteError);
    }
  };

  const toggleDeleteSelection = (eventId) => {
    setSelectedDeleteIds((current) => {
      if (current.includes(eventId)) {
        return current.filter((id) => id !== eventId);
      }

      return [...current, eventId];
    });
  };

  const handleBulkDeleteSelected = async () => {
    if (selectedDeleteIds.length === 0) {
      showToast("error", t.selectEventsFirst);
      return;
    }

    try {
      await axios.post("/api/events/bulk-delete", {
        event_ids: selectedDeleteIds,
      });

      setSelectedDeleteIds([]);
      await searchEventsForDeletion();

      showToast("success", t.bulkDeleteSuccess);
      loadEvents();
    } catch (error) {
      handleApiError(error, t.deleteError);
    }
  };

  const handleDeleteAllByTitle = async () => {
    if (!deleteSearchQuery.trim()) {
      showToast("error", t.enterSearchTitle);
      return;
    }

    setConfirmDialog({
      title: t.confirmDeleteTitle,
      message: `${t.deleteAllWithTitle}: "${deleteSearchQuery.trim()}"`,
      confirmText: t.confirmDeleteAction,
      cancelText: t.cancel,
      onConfirm: async () => {
        try {
          await axios.post("/api/events/bulk-delete", {
            delete_all_by_title: true,
            title: deleteSearchQuery.trim(),
          });

          setConfirmDialog(null);
          setDeleteSearchResults([]);
          setSelectedDeleteIds([]);

          showToast("success", t.bulkDeleteSuccess);
          loadEvents();
        } catch (error) {
          setConfirmDialog(null);
          handleApiError(error, t.deleteError);
        }
      },
    });
  };

  const closeModal = () => {
    resetEventForm();
  };

  const logout = async () => {
    try {
      await axios.post("/auth/logout");
    } catch (error) {
      console.error(error);
    } finally {
      setUser(null);
      setEvents([]);
      navigate("/");
    }
  };

  if (loading) {
    return <div className="loading">{t.loading}</div>;
  }

  return (
    <div className="app-wrapper">
      <header className="topbar sticky-topbar">
        <div className="topbar-left">
          <Link to="/" className="logo-link">
            {t.appName}
          </Link>
        </div>

        <div className="topbar-right">
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
            {lang === "en" ? "UA" : "EN"}
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
      </header>

      <Routes>
        <Route
          path="/"
          element={
            user ? (
              <Dashboard
                events={events}
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
                handleDateSelect={handleDateSelect}
                handleEventClick={handleEventClick}
                handleEventDrop={handleEventDrop}
                handleEventResize={handleEventResize}
                openCreateModal={openCreateModal}
                openAutoPlanModal={openAutoPlanModal}
                openDeleteManagerModal={openDeleteManagerModal}
                goPrev={goPrev}
                goNext={goNext}
                goToday={goToday}
                changeView={changeView}
                lang={lang}
                t={t}
              />
            ) : (
              <WelcomePage lang={lang} />
            )
          }
        />

        <Route path="/login" element={<Login setUser={setUser} lang={lang} />} />

        <Route
          path="/register"
          element={<Register setUser={setUser} lang={lang} />}
        />

        <Route
          path="/profile"
          element={
            <ProtectedRoute user={user}>
              <Profile user={user} lang={lang} />
            </ProtectedRoute>
          }
        />
      </Routes>

      {autoPlanOpen && (
        <div className="modal-overlay">
          <div className="modal modern-modal">
            <div className="modal-header">
              <div>
                <p className="eyebrow">{t.autoPlanning}</p>
                <h3>{t.autoPlanTitle}</h3>
                <p className="modal-description">{t.autoPlanDescription}</p>
              </div>

              <button
                type="button"
                className="icon-button"
                onClick={() => setAutoPlanOpen(false)}
              >
                ×
              </button>
            </div>

            <label>
              {t.taskTitle}
              <input
                type="text"
                value={autoPlanTask.title}
                onChange={(e) =>
                  setAutoPlanTask({
                    ...autoPlanTask,
                    title: e.target.value,
                  })
                }
              />
            </label>

            <label>
              {t.durationMinutes}
              <input
                type="number"
                min="15"
                step="15"
                value={autoPlanTask.duration_minutes}
                onChange={(e) =>
                  setAutoPlanTask({
                    ...autoPlanTask,
                    duration_minutes: Number(e.target.value),
                  })
                }
              />
            </label>

            <div className="datetime-grid">
              <label>
                {t.dateFrom}
                <input
                  type="date"
                  value={autoPlanTask.date_from}
                  onChange={(e) =>
                    setAutoPlanTask({
                      ...autoPlanTask,
                      date_from: e.target.value,
                    })
                  }
                />
              </label>

              <label>
                {t.dateTo}
                <input
                  type="date"
                  value={autoPlanTask.date_to}
                  onChange={(e) =>
                    setAutoPlanTask({
                      ...autoPlanTask,
                      date_to: e.target.value,
                    })
                  }
                />
              </label>
            </div>

            <div className="datetime-grid">
              <label>
                {t.dayStart}
                <input
                  type="time"
                  value={autoPlanTask.day_start}
                  onChange={(e) =>
                    setAutoPlanTask({
                      ...autoPlanTask,
                      day_start: e.target.value,
                    })
                  }
                />
              </label>

              <label>
                {t.dayEnd}
                <input
                  type="time"
                  value={autoPlanTask.day_end}
                  onChange={(e) =>
                    setAutoPlanTask({
                      ...autoPlanTask,
                      day_end: e.target.value,
                    })
                  }
                />
              </label>
            </div>

            <label>
              {t.preferredTime}
              <input
                type="time"
                value={autoPlanTask.preferred_time}
                onChange={(e) =>
                  setAutoPlanTask({
                    ...autoPlanTask,
                    preferred_time: e.target.value,
                  })
                }
              />
            </label>

            <div className="auto-repeat-block">
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={autoPlanTask.repeat_enabled}
                  onChange={(e) =>
                    setAutoPlanTask({
                      ...autoPlanTask,
                      repeat_enabled: e.target.checked,
                    })
                  }
                />
                {t.repeatAutoPlan}
              </label>

              {autoPlanTask.repeat_enabled && (
                <>
                  <label>
                    {t.timesPerWeek}
                    <input
                      type="number"
                      min="1"
                      max="7"
                      value={autoPlanTask.times_per_week}
                      onChange={(e) =>
                        setAutoPlanTask({
                          ...autoPlanTask,
                          times_per_week: Number(e.target.value),
                        })
                      }
                    />
                  </label>

                  <div className="preferred-days-block">
                    <p>{t.preferredDays}</p>

                    <div className="repeat-days-row">
                      {[
                        { code: "MO", uk: "Пн", en: "Mo" },
                        { code: "TU", uk: "Вт", en: "Tu" },
                        { code: "WE", uk: "Ср", en: "We" },
                        { code: "TH", uk: "Чт", en: "Th" },
                        { code: "FR", uk: "Пт", en: "Fr" },
                        { code: "SA", uk: "Сб", en: "Sa" },
                        { code: "SU", uk: "Нд", en: "Su" },
                      ].map((day) => {
                        const active = autoPlanTask.allowed_days.includes(day.code);

                        return (
                          <button
                            key={day.code}
                            type="button"
                            className={active ? "repeat-day active" : "repeat-day"}
                            onClick={() => {
                              const currentDays = autoPlanTask.allowed_days;

                              const nextDays = active
                                ? currentDays.filter((item) => item !== day.code)
                                : [...currentDays, day.code];

                              setAutoPlanTask({
                                ...autoPlanTask,
                                allowed_days: nextDays,
                              });
                            }}
                          >
                            {lang === "uk" ? day.uk : day.en}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </>
              )}
            </div>

            <div className="modal-buttons">
              <button type="button" onClick={() => setAutoPlanOpen(false)}>
                {t.cancel}
              </button>

              <button
                type="button"
                className="primary-button"
                onClick={handleAutoPlan}
              >
                ✨ {t.autoPlanButton}
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteManagerOpen && (
        <div className="modal-overlay">
          <div className="modal modern-modal delete-manager-modal">
            <div className="modal-header">
              <div>
                <p className="eyebrow">{t.manageDeletion}</p>
                <h3>{t.deleteManagerTitle}</h3>
                <p className="modal-description">{t.deleteManagerDescription}</p>
              </div>

              <button
                type="button"
                className="icon-button"
                onClick={() => setDeleteManagerOpen(false)}
              >
                ×
              </button>
            </div>

            <label>
              {t.searchByEventName}
              <input
                type="text"
                placeholder={t.searchPlaceholder}
                value={deleteSearchQuery}
                onChange={(e) => setDeleteSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    searchEventsForDeletion();
                  }
                }}
              />
            </label>

            <div className="modal-buttons delete-search-actions">
              <button type="button" onClick={searchEventsForDeletion}>
                {t.searchEvents}
              </button>

              <button
                type="button"
                className="danger-button"
                onClick={handleDeleteAllByTitle}
              >
                {t.deleteAllWithTitle}
              </button>
            </div>

            <div className="delete-results">
              {deleteSearchResults.length === 0 ? (
                <p className="empty-delete-result">{t.noDeleteResults}</p>
              ) : (
                deleteSearchResults.map((event) => (
                  <label key={event.id} className="delete-result-card">
                    <input
                      type="checkbox"
                      checked={selectedDeleteIds.includes(event.id)}
                      onChange={() => toggleDeleteSelection(event.id)}
                    />

                    <span>
                      <strong>{event.title}</strong>
                      <small>{formatEventDate(event.start)}</small>
                      {event.is_recurring && <em>{t.repeat}</em>}
                    </span>
                  </label>
                ))
              )}
            </div>

            <div className="delete-manager-footer">
              <p>
                {t.selectedForDelete}: <strong>{selectedDeleteIds.length}</strong>
              </p>

              <button
                type="button"
                className="danger-button"
                onClick={handleBulkDeleteSelected}
              >
                {t.deleteSelected}
              </button>
            </div>
          </div>
        </div>
      )}

      {recurringDeleteDialog && (
        <div className="confirm-overlay">
          <div className="confirm-dialog recurring-delete-dialog">
            <div className="confirm-icon">!</div>

            <h3>{t.recurringDeleteTitle}</h3>
            <p>{t.recurringDeleteDescription}</p>

            <div className="recurring-delete-actions">
              <button type="button" onClick={() => confirmRecurringDelete("this")}>
                {t.deleteOnlyThis}
              </button>

              <button type="button" onClick={() => confirmRecurringDelete("future")}>
                {t.deleteThisAndFuture}
              </button>

              <button
                type="button"
                className="danger-button"
                onClick={() => confirmRecurringDelete("all")}
              >
                {t.deleteWholeSeries}
              </button>
            </div>

            <button
              type="button"
              className="cancel-recurring-delete"
              onClick={() => setRecurringDeleteDialog(null)}
            >
              {t.cancel}
            </button>
          </div>
        </div>
      )}

      {toast && (
        <div className={`toast toast-${toast.type}`}>
          <div className="toast-icon">{toast.type === "success" ? "✓" : "!"}</div>

          <p>{toast.message}</p>

          <button type="button" onClick={() => setToast(null)}>
            ×
          </button>
        </div>
      )}

      {confirmDialog && (
        <div className="confirm-overlay">
          <div className="confirm-dialog">
            <div className="confirm-icon">!</div>

            <h3>{confirmDialog.title}</h3>
            <p>{confirmDialog.message}</p>

            <div className="confirm-actions">
              <button type="button" onClick={() => setConfirmDialog(null)}>
                {confirmDialog.cancelText}
              </button>

              <button
                type="button"
                className="danger-button"
                onClick={confirmDialog.onConfirm}
              >
                {confirmDialog.confirmText}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}