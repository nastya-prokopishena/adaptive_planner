import { useEffect, useMemo, useState } from "react";
import axios from "axios";

axios.defaults.withCredentials = true;

const COLORS = [
  "#2563eb",
  "#16a34a",
  "#dc2626",
  "#7c3aed",
  "#ea580c",
  "#0f766e",
  "#db2777",
  "#d97706",
  "#0891b2",
  "#4f46e5",
];

const TRANSLATIONS = {
  uk: {
    title: "Задачі та предмети",
    subtitle:
      "Тут можна створювати предмети, типи подій і задачі, а також відстежувати виконання.",
    subjects: "Предмети",
    eventTypes: "Типи подій",
    tasks: "Задачі",
    activity: "Історія активності",

    subjectName: "Назва предмету",
    teacher: "Викладач",
    description: "Опис",
    color: "Колір",
    createSubject: "Створити предмет",

    eventTypeName: "Назва типу",
    createEventType: "Створити тип",

    taskTitle: "Назва задачі",
    taskDescription: "Опис задачі",
    subject: "Предмет",
    event: "Подія",
    noSubject: "Без предмету",
    noEvent: "Без події",
    priority: "Пріоритет",
    low: "Низький",
    medium: "Середній",
    high: "Високий",
    dueDate: "Дедлайн",
    createTask: "Створити задачу",

    all: "Всі",
    planned: "Заплановано",
    done: "Виконано",
    missed: "Пропущено",

    markPlanned: "Заплановано",
    markDone: "Виконано",
    markMissed: "Пропущено",
    delete: "Видалити",

    noTasks: "Задач поки немає",
    noLogs: "Історія поки порожня",
    saved: "Збережено",
    error: "Сталася помилка",
  },

  en: {
    title: "Tasks and subjects",
    subtitle:
      "Here you can create subjects, event types and tasks, and track completion.",
    subjects: "Subjects",
    eventTypes: "Event types",
    tasks: "Tasks",
    activity: "Activity history",

    subjectName: "Subject name",
    teacher: "Teacher",
    description: "Description",
    color: "Color",
    createSubject: "Create subject",

    eventTypeName: "Type name",
    createEventType: "Create type",

    taskTitle: "Task title",
    taskDescription: "Task description",
    subject: "Subject",
    event: "Event",
    noSubject: "No subject",
    noEvent: "No event",
    priority: "Priority",
    low: "Low",
    medium: "Medium",
    high: "High",
    dueDate: "Due date",
    createTask: "Create task",

    all: "All",
    planned: "Planned",
    done: "Done",
    missed: "Missed",

    markPlanned: "Planned",
    markDone: "Done",
    markMissed: "Missed",
    delete: "Delete",

    noTasks: "No tasks yet",
    noLogs: "Activity history is empty",
    saved: "Saved",
    error: "Something went wrong",
  },
};

export default function TasksPanel({ events = [], lang = "uk" }) {
  const t = TRANSLATIONS[lang] || TRANSLATIONS.uk;

  const [subjects, setSubjects] = useState([]);
  const [eventTypes, setEventTypes] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [logs, setLogs] = useState([]);

  const [statusFilter, setStatusFilter] = useState("all");
  const [message, setMessage] = useState("");

  const [subjectForm, setSubjectForm] = useState({
    name: "",
    teacher: "",
    description: "",
    color: COLORS[0],
  });

  const [eventTypeForm, setEventTypeForm] = useState({
    name: "",
    color: COLORS[1],
  });

  const [taskForm, setTaskForm] = useState({
    title: "",
    description: "",
    subject_id: "",
    event_id: "",
    priority: "medium",
    due_date: "",
  });

  const filteredTasks = useMemo(() => {
    if (statusFilter === "all") {
      return tasks;
    }

    return tasks.filter((task) => task.status === statusFilter);
  }, [tasks, statusFilter]);

  const subjectById = useMemo(() => {
    const map = {};

    subjects.forEach((subject) => {
      map[String(subject.id)] = subject;
    });

    return map;
  }, [subjects]);

  const eventById = useMemo(() => {
    const map = {};

    events.forEach((event) => {
      map[String(event.master_id || event.id)] = event;
    });

    return map;
  }, [events]);

  const showMessage = (text) => {
    setMessage(text);

    setTimeout(() => {
      setMessage("");
    }, 2500);
  };

  const loadSubjects = async () => {
    const response = await axios.get("/api/subjects");
    setSubjects(Array.isArray(response.data) ? response.data : []);
  };

  const loadEventTypes = async () => {
    const response = await axios.get("/api/event-types");
    setEventTypes(Array.isArray(response.data) ? response.data : []);
  };

  const loadTasks = async () => {
    const response = await axios.get("/api/tasks");
    setTasks(Array.isArray(response.data) ? response.data : []);
  };

  const loadLogs = async () => {
    const response = await axios.get("/api/activity-logs");
    setLogs(Array.isArray(response.data) ? response.data : []);
  };

  const loadAll = async () => {
    try {
      await Promise.all([
        loadSubjects(),
        loadEventTypes(),
        loadTasks(),
        loadLogs(),
      ]);
    } catch (error) {
      console.error(error);
      showMessage(t.error);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const createSubject = async () => {
    if (!subjectForm.name.trim()) {
      return;
    }

    try {
      await axios.post("/api/subjects", subjectForm);

      setSubjectForm({
        name: "",
        teacher: "",
        description: "",
        color: COLORS[0],
      });

      await loadSubjects();
      showMessage(t.saved);
    } catch (error) {
      console.error(error);
      showMessage(t.error);
    }
  };

  const createEventType = async () => {
    if (!eventTypeForm.name.trim()) {
      return;
    }

    try {
      await axios.post("/api/event-types", eventTypeForm);

      setEventTypeForm({
        name: "",
        color: COLORS[1],
      });

      await loadEventTypes();
      showMessage(t.saved);
    } catch (error) {
      console.error(error);
      showMessage(t.error);
    }
  };

  const createTask = async () => {
    if (!taskForm.title.trim()) {
      return;
    }

    const payload = {
      ...taskForm,
      subject_id: taskForm.subject_id || null,
      event_id: taskForm.event_id || null,
      due_date: taskForm.due_date || null,
    };

    try {
      await axios.post("/api/tasks", payload);

      setTaskForm({
        title: "",
        description: "",
        subject_id: "",
        event_id: "",
        priority: "medium",
        due_date: "",
      });

      await Promise.all([loadTasks(), loadLogs()]);
      showMessage(t.saved);
    } catch (error) {
      console.error(error);
      showMessage(t.error);
    }
  };

  const updateTaskStatus = async (taskId, status) => {
    try {
      await axios.put(`/api/tasks/${taskId}/status`, { status });

      await Promise.all([loadTasks(), loadLogs()]);
      showMessage(t.saved);
    } catch (error) {
      console.error(error);
      showMessage(t.error);
    }
  };

  const deleteTask = async (taskId) => {
    try {
      await axios.delete(`/api/tasks/${taskId}`);

      await Promise.all([loadTasks(), loadLogs()]);
      showMessage(t.saved);
    } catch (error) {
      console.error(error);
      showMessage(t.error);
    }
  };

  const formatDate = (value) => {
    if (!value) return "";

    return new Intl.DateTimeFormat(lang === "uk" ? "uk-UA" : "en-US", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  };

  const getStatusLabel = (status) => {
    if (status === "done") return t.done;
    if (status === "missed") return t.missed;
    return t.planned;
  };

  const getPriorityLabel = (priority) => {
    if (priority === "low") return t.low;
    if (priority === "high") return t.high;
    return t.medium;
  };

  return (
    <section className="tasks-panel">
      <div className="tasks-panel-header">
        <div>
          <p className="eyebrow">{t.activity}</p>
          <h2>{t.title}</h2>
          <p>{t.subtitle}</p>
        </div>

        {message && <span className="task-message">{message}</span>}
      </div>

      <div className="tasks-grid">
        <div className="task-card">
          <h3>{t.subjects}</h3>

          <input
            type="text"
            placeholder={t.subjectName}
            value={subjectForm.name}
            onChange={(event) =>
              setSubjectForm({
                ...subjectForm,
                name: event.target.value,
              })
            }
          />

          <input
            type="text"
            placeholder={t.teacher}
            value={subjectForm.teacher}
            onChange={(event) =>
              setSubjectForm({
                ...subjectForm,
                teacher: event.target.value,
              })
            }
          />

          <textarea
            placeholder={t.description}
            value={subjectForm.description}
            onChange={(event) =>
              setSubjectForm({
                ...subjectForm,
                description: event.target.value,
              })
            }
          />

          <div className="color-row">
            {COLORS.map((color) => (
              <button
                key={color}
                type="button"
                className={
                  subjectForm.color === color ? "color-dot active" : "color-dot"
                }
                style={{ backgroundColor: color }}
                onClick={() =>
                  setSubjectForm({
                    ...subjectForm,
                    color,
                  })
                }
              />
            ))}
          </div>

          <button type="button" onClick={createSubject}>
            + {t.createSubject}
          </button>

          <div className="mini-list">
            {subjects.map((subject) => (
              <span key={subject.id}>
                <i style={{ backgroundColor: subject.color || COLORS[0] }} />
                {subject.name}
              </span>
            ))}
          </div>
        </div>

        <div className="task-card">
          <h3>{t.eventTypes}</h3>

          <input
            type="text"
            placeholder={t.eventTypeName}
            value={eventTypeForm.name}
            onChange={(event) =>
              setEventTypeForm({
                ...eventTypeForm,
                name: event.target.value,
              })
            }
          />

          <div className="color-row">
            {COLORS.map((color) => (
              <button
                key={color}
                type="button"
                className={
                  eventTypeForm.color === color ? "color-dot active" : "color-dot"
                }
                style={{ backgroundColor: color }}
                onClick={() =>
                  setEventTypeForm({
                    ...eventTypeForm,
                    color,
                  })
                }
              />
            ))}
          </div>

          <button type="button" onClick={createEventType}>
            + {t.createEventType}
          </button>

          <div className="mini-list">
            {eventTypes.map((eventType) => (
              <span key={eventType.id}>
                <i style={{ backgroundColor: eventType.color || COLORS[1] }} />
                {eventType.name}
              </span>
            ))}
          </div>
        </div>

        <div className="task-card task-create-card">
          <h3>{t.createTask}</h3>

          <input
            type="text"
            placeholder={t.taskTitle}
            value={taskForm.title}
            onChange={(event) =>
              setTaskForm({
                ...taskForm,
                title: event.target.value,
              })
            }
          />

          <textarea
            placeholder={t.taskDescription}
            value={taskForm.description}
            onChange={(event) =>
              setTaskForm({
                ...taskForm,
                description: event.target.value,
              })
            }
          />

          <select
            value={taskForm.subject_id}
            onChange={(event) =>
              setTaskForm({
                ...taskForm,
                subject_id: event.target.value,
              })
            }
          >
            <option value="">{t.noSubject}</option>

            {subjects.map((subject) => (
              <option key={subject.id} value={subject.id}>
                {subject.name}
              </option>
            ))}
          </select>

          <select
            value={taskForm.event_id}
            onChange={(event) =>
              setTaskForm({
                ...taskForm,
                event_id: event.target.value,
              })
            }
          >
            <option value="">{t.noEvent}</option>

            {events.map((event) => (
              <option key={event.id} value={event.master_id || event.id}>
                {event.title}
              </option>
            ))}
          </select>

          <select
            value={taskForm.priority}
            onChange={(event) =>
              setTaskForm({
                ...taskForm,
                priority: event.target.value,
              })
            }
          >
            <option value="low">{t.low}</option>
            <option value="medium">{t.medium}</option>
            <option value="high">{t.high}</option>
          </select>

          <input
            type="datetime-local"
            value={taskForm.due_date}
            onChange={(event) =>
              setTaskForm({
                ...taskForm,
                due_date: event.target.value,
              })
            }
          />

          <button type="button" onClick={createTask}>
            + {t.createTask}
          </button>
        </div>
      </div>

      <div className="task-board">
        <div className="task-board-header">
          <h3>{t.tasks}</h3>

          <div className="task-filters">
            {["all", "planned", "done", "missed"].map((status) => (
              <button
                key={status}
                type="button"
                className={statusFilter === status ? "active" : ""}
                onClick={() => setStatusFilter(status)}
              >
                {status === "all" ? t.all : getStatusLabel(status)}
              </button>
            ))}
          </div>
        </div>

        {filteredTasks.length === 0 ? (
          <p className="empty-tasks">{t.noTasks}</p>
        ) : (
          <div className="task-list">
            {filteredTasks.map((task) => {
              const subject = task.subject_id
                ? subjectById[String(task.subject_id)]
                : null;

              const relatedEvent = task.event_id
                ? eventById[String(task.event_id)]
                : null;

              return (
                <article key={task.id} className={`task-item ${task.status}`}>
                  <div>
                    <div className="task-item-top">
                      <h4>{task.title}</h4>
                      <span className={`status-pill ${task.status}`}>
                        {getStatusLabel(task.status)}
                      </span>
                    </div>

                    {task.description && <p>{task.description}</p>}

                    <div className="task-meta">
                      {subject && <span>{subject.name}</span>}
                      {relatedEvent && <span>{relatedEvent.title}</span>}
                      <span>{getPriorityLabel(task.priority)}</span>
                      {task.due_date && <span>{formatDate(task.due_date)}</span>}
                    </div>
                  </div>

                  <div className="task-actions">
                    <button
                      type="button"
                      onClick={() => updateTaskStatus(task.id, "planned")}
                    >
                      {t.markPlanned}
                    </button>

                    <button
                      type="button"
                      onClick={() => updateTaskStatus(task.id, "done")}
                    >
                      {t.markDone}
                    </button>

                    <button
                      type="button"
                      onClick={() => updateTaskStatus(task.id, "missed")}
                    >
                      {t.markMissed}
                    </button>

                    <button
                      type="button"
                      className="danger-button"
                      onClick={() => deleteTask(task.id)}
                    >
                      {t.delete}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>

      <div className="activity-log-card">
        <h3>{t.activity}</h3>

        {logs.length === 0 ? (
          <p className="empty-tasks">{t.noLogs}</p>
        ) : (
          <div className="activity-list">
            {logs.map((log) => (
              <div key={log.id} className="activity-item">
                <strong>{log.action}</strong>

                <span>
                  {log.old_status || "—"} → {log.new_status || "—"}
                </span>

                {log.details && <p>{log.details}</p>}

                <small>{formatDate(log.created_at)}</small>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}