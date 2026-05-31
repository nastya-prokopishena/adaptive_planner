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

const t = {
  title: "Задачі та предмети",
  subtitle:
    "Створюй предмети, типи подій і задачі. Для задач можна вручну вказати дедлайн або залишити його для автопланування.",
  subjects: "Предмети",
  eventTypes: "Типи подій",
  tasks: "Задачі",
  activity: "Керування задачами",

  subjectName: "Назва предмету",
  teacher: "Викладач",
  description: "Опис",
  createSubject: "Створити предмет",

  eventTypeName: "Назва типу",
  createEventType: "Створити тип",

  taskTitle: "Назва задачі",
  taskDescription: "Опис задачі",
  noSubject: "Без предмету",
  noEvent: "Без події",

  low: "Низький",
  medium: "Середній",
  high: "Високий",

  createTask: "Створити задачу",

  all: "Всі",
  planned: "Заплановано",
  done: "Виконано",
  missed: "Пропущено",

  edit: "Редагувати",
  save: "Зберегти",
  cancel: "Скасувати",
  delete: "Видалити",

  noTasks: "Задач поки немає",
  noLogs: "Історія поки порожня",
  saved: "Збережено",
  error: "Сталася помилка",

  duration: "Час",
  difficulty: "Складність",
  taskType: "Тип",
  keywords: "Ключові слова",
  dueDate: "Дата дедлайну",
  dueTime: "Час дедлайну",
  noDueDate: "Без дати",
  autoReplanned: "Пропущені задачі були автоматично переплановані",
  replannedBadge: "Переплановано",
  replanLimitReached: "Ліміт переносів вичерпано",
  replanAttemptsLeft: "залишилось",

  groupedView: "За предметами",
  listView: "Списком",
};

export default function TasksPanel({ events = [] }) {
  const [subjects, setSubjects] = useState([]);
  const [eventTypes, setEventTypes] = useState([]);
  const [tasks, setTasks] = useState([]);

  const [statusFilter, setStatusFilter] = useState("all");
  const [taskViewMode, setTaskViewMode] = useState("grouped");
  const [message, setMessage] = useState("");
  const [selectedTask, setSelectedTask] = useState(null);

  const [editingSubjectId, setEditingSubjectId] = useState(null);
  const [editingEventTypeId, setEditingEventTypeId] = useState(null);
  const [editingTaskId, setEditingTaskId] = useState(null);

  const [editSubjectForm, setEditSubjectForm] = useState({});
  const [editEventTypeForm, setEditEventTypeForm] = useState({});
  const [editTaskForm, setEditTaskForm] = useState({});

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
    task_type: "homework",
    estimated_duration_hours: 1,
    difficulty_score: 3,
    due_date_date: "",
    due_date_time: "",
  });

  const filteredTasks = useMemo(() => {
    if (statusFilter === "all") return tasks;
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

  const groupedTasks = useMemo(() => {
    const groups = {};

    filteredTasks.forEach((task) => {
      const subject = task.subject_id
        ? subjectById[String(task.subject_id)]
        : null;

      const subjectName = subject?.name || task.subject || "Без предмету";
      const subjectColor = subject?.color || COLORS[9];

      if (!groups[subjectName]) {
        groups[subjectName] = {
          name: subjectName,
          color: subjectColor,
          tasks: [],
        };
      }

      groups[subjectName].tasks.push(task);
    });

    return Object.values(groups);
  }, [filteredTasks, subjectById]);

  useEffect(() => {
    loadAll();
  }, []);

  const showMessage = (text, timeout = 3500) => {
    setMessage(text);
    setTimeout(() => setMessage(""), timeout);
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
    const response = await axios.get("/api/tasks", {
      params: { include_meta: 1 },
    });

    if (Array.isArray(response.data)) {
      setTasks(response.data);
      return;
    }

    const loadedTasks = Array.isArray(response.data?.tasks)
      ? response.data.tasks
      : [];

    setTasks(loadedTasks);

    const replannedCount = Number(response.data?.auto_replanned_count || 0);

    if (replannedCount > 0) {
      showMessage(
        `${t.autoReplanned}: ${replannedCount}`,
        4500,
      );
    }
  };


  const loadAll = async () => {
    try {
      await Promise.all([
        loadSubjects(),
        loadEventTypes(),
        loadTasks(),
      ]);
    } catch (error) {
      console.error(error);
      showMessage(t.error);
    }
  };

  const createSubject = async () => {
    if (!subjectForm.name.trim()) return;

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

  const startEditSubject = (subject) => {
    setEditingSubjectId(subject.id);
    setEditSubjectForm({
      name: subject.name || "",
      teacher: subject.teacher || "",
      description: subject.description || "",
      color: subject.color || COLORS[0],
    });
  };

  const saveSubject = async (subjectId) => {
    if (!editSubjectForm.name?.trim()) return;

    try {
      await axios.put(`/api/subjects/${subjectId}`, editSubjectForm);
      setEditingSubjectId(null);
      setEditSubjectForm({});
      await loadSubjects();
      showMessage(t.saved);
    } catch (error) {
      console.error(error);
      showMessage(t.error);
    }
  };

  const createEventType = async () => {
    if (!eventTypeForm.name.trim()) return;

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

  const startEditEventType = (eventType) => {
    setEditingEventTypeId(eventType.id);
    setEditEventTypeForm({
      name: eventType.name || "",
      color: eventType.color || COLORS[1],
    });
  };

  const saveEventType = async (eventTypeId) => {
    if (!editEventTypeForm.name?.trim()) return;

    try {
      await axios.put(`/api/event-types/${eventTypeId}`, editEventTypeForm);
      setEditingEventTypeId(null);
      setEditEventTypeForm({});
      await loadEventTypes();
      showMessage(t.saved);
    } catch (error) {
      console.error(error);
      showMessage(t.error);
    }
  };


  const splitDueDate = (value) => {
    if (!value) {
      return {
        date: "",
        time: "",
      };
    }

    const normalized = String(value).slice(0, 16);
    const [date = "", time = ""] = normalized.split("T");

    return {
      date,
      time,
    };
  };

  const buildDueDate = (date, time) => {
    if (!date) {
      return null;
    }

    return `${date}T${time || "12:00"}`;
  };

  const openNativePicker = (event) => {
    const input = event.currentTarget;

    if (typeof input.showPicker === "function") {
      try {
        input.showPicker();
      } catch {
        input.focus();
      }
    }
  };

  const autoPickManualTaskDeadline = async () => {
    if (!taskForm.title.trim()) {
      showMessage("Спочатку введи назву задачі.");
      return;
    }

    try {
      const response = await axios.post("/api/tasks/auto-deadline", {
        title: taskForm.title,
        description: taskForm.description,
        subject_id: taskForm.subject_id || null,
        event_id: taskForm.event_id || null,
        priority: taskForm.priority || "medium",
        task_type: taskForm.task_type || "homework",
        estimated_duration_hours: Number(
          taskForm.estimated_duration_hours || 1
        ),
        difficulty_score: Number(taskForm.difficulty_score || 3),
        mode: "subject_based",
      });

      const dueDate = response.data?.due_date;

      if (!dueDate) {
        showMessage("Не вдалося підібрати дедлайн.");
        return;
      }

      const parsedDate = new Date(dueDate);

      setTaskForm({
        ...taskForm,
        due_date_date: parsedDate.toISOString().slice(0, 10),
        due_date_time: parsedDate.toTimeString().slice(0, 5),
      });

      showMessage("Дедлайн підібрано автоматично.");
    } catch (error) {
      console.error(error);
      showMessage(
        error.response?.data?.error || "Не вдалося автоматично підібрати дедлайн."
      );
    }
  };

  const createTask = async () => {
    if (!taskForm.title.trim()) return;

    try {
      await axios.post("/api/tasks", {
        ...taskForm,
        subject_id: taskForm.subject_id || null,
        event_id: taskForm.event_id || null,
        task_type: taskForm.task_type || "homework",
        estimated_duration_hours: Number(
          taskForm.estimated_duration_hours || 1
        ),
        difficulty_score: Number(taskForm.difficulty_score || 3),
        due_date: buildDueDate(taskForm.due_date_date, taskForm.due_date_time),
      });

      setTaskForm({
        title: "",
        description: "",
        subject_id: "",
        event_id: "",
        priority: "medium",
        task_type: "homework",
        estimated_duration_hours: 1,
        difficulty_score: 3,
        due_date_date: "",
        due_date_time: "",
      });

      await loadTasks();
      showMessage(t.saved);
    } catch (error) {
      console.error(error);
      showMessage(t.error);
    }
  };

  const startEditTask = (task) => {
    setEditingTaskId(task.id);

    const dueDateParts = splitDueDate(task.due_date);

    setEditTaskForm({
      title: task.title || "",
      description: task.description || "",
      subject_id: task.subject_id || "",
      event_id: task.event_id || "",
      priority: task.priority || "medium",
      due_date_date: dueDateParts.date,
      due_date_time: dueDateParts.time,
      task_type: task.task_type || "homework",
      estimated_duration_hours: task.estimated_duration_hours || 1,
      difficulty_score: task.difficulty_score || 3,
      keywords: Array.isArray(task.keywords) ? task.keywords.join(", ") : "",
    });
  };

  const saveTask = async (taskId) => {
    if (!editTaskForm.title?.trim()) return;

    const keywords = editTaskForm.keywords
      ? editTaskForm.keywords
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean)
      : [];

    try {
      await axios.put(`/api/tasks/${taskId}`, {
        title: editTaskForm.title,
        description: editTaskForm.description,
        subject_id: editTaskForm.subject_id || null,
        event_id: editTaskForm.event_id || null,
        priority: editTaskForm.priority || "medium",
        due_date: buildDueDate(
          editTaskForm.due_date_date,
          editTaskForm.due_date_time
        ),
        task_type: editTaskForm.task_type || "homework",
        estimated_duration_hours: Number(
          editTaskForm.estimated_duration_hours || 1
        ),
        difficulty_score: Number(editTaskForm.difficulty_score || 3),
        keywords,
      });

      setEditingTaskId(null);
      setEditTaskForm({});
      await loadTasks();
      showMessage(t.saved);
    } catch (error) {
      console.error(error);
      showMessage(t.error);
    }
  };

  const updateTaskStatus = async (taskId, status) => {
    try {
      await axios.put(`/api/tasks/${taskId}/status`, { status });
      await loadTasks();
      showMessage(t.saved);
    } catch (error) {
      console.error(error);
      showMessage(t.error);
    }
  };

  const deleteTask = async (taskId) => {
    try {
      await axios.delete(`/api/tasks/${taskId}`);
      await loadTasks();
      showMessage(t.saved);
    } catch (error) {
      console.error(error);
      showMessage(t.error);
    }
  };

  const formatDate = (value) => {
    if (!value) return "";

    return new Intl.DateTimeFormat("uk-UA", {
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

  const getTaskTypeLabel = (type) => {
    const labels = {
      laboratory: "Лабораторна",
      homework: "Практична / домашня",
      project: "Проєкт",
      reading: "Самостійна / читання",
      exam_preparation: "Підготовка до іспиту",
      other: "Інше",
    };

    return labels[type] || labels.other;
  };

  const getDifficultyLabel = (score) => {
    const labels = {
      1: "Легка",
      2: "Нижче середньої",
      3: "Середня",
      4: "Складна",
      5: "Дуже складна",
    };

    return labels[Number(score)] || "Не визначено";
  };

  const getTaskSubjectName = (task, subject) => {
    if (subject?.name) return subject.name;
    if (task.subject) return task.subject;
    return null;
  };

  const getTaskDetails = (task) => {
    const subject = task.subject_id ? subjectById[String(task.subject_id)] : null;

    return {
      subject,
      subjectName: getTaskSubjectName(task, subject),
    };
  };

  const getAutoReplanInfo = (task) => {
    const count = Number(task.auto_replan_count || 0);
    const limit = Number(task.auto_replan_limit || 3);
    const attemptsLeft = Number(
      task.auto_replan_attempts_left ?? Math.max(limit - count, 0)
    );
    const limitReached = Boolean(task.auto_replan_limit_reached);

    return {
      count,
      limit,
      attemptsLeft,
      limitReached,
      shouldShow: count > 0 || limitReached,
    };
  };

  const renderAutoReplanBadge = (task, compact = false) => {
    const info = getAutoReplanInfo(task);

    if (!info.shouldShow) return null;

    const badgeText = info.limitReached
      ? `${t.replanLimitReached}: ${info.count}/${info.limit}`
      : `${t.replannedBadge}: ${info.count}/${info.limit}`;

    const title = info.limitReached
      ? "Автоматичне перепланування більше не виконуватиметься для цієї задачі."
      : `Автоматичне перепланування було виконано. ${t.replanAttemptsLeft}: ${info.attemptsLeft}.`;

    return (
      <span
        className={`task-replan-badge ${info.limitReached ? "limit" : ""} ${
          compact ? "compact" : ""
        }`}
        title={title}
      >
        🔁 {badgeText}
      </span>
    );
  };

  const renderStatusSelect = (task) => (
    <select
      className={`status-select status-${task.status || "planned"}`}
      value={task.status || "planned"}
      onClick={(event) => event.stopPropagation()}
      onChange={(event) => updateTaskStatus(task.id, event.target.value)}
    >
      <option value="planned">Заплановано</option>
      <option value="done">Виконано</option>
      <option value="missed">Пропущено</option>
    </select>
  );


  const renderFormHint = (text) => (
    <p className="form-field-hint">{text}</p>
  );

  const renderFieldLabel = (title, hint) => (
    <div className="task-field-label">
      <span>{title}</span>
      {hint && renderFormHint(hint)}
    </div>
  );


  const renderTaskEditForm = (task) => (
    <div className="task-edit-form">
      <input
        value={editTaskForm.title || ""}
        placeholder={t.taskTitle}
        onChange={(event) =>
          setEditTaskForm({
            ...editTaskForm,
            title: event.target.value,
          })
        }
      />

      <textarea
        value={editTaskForm.description || ""}
        placeholder={t.taskDescription}
        onChange={(event) =>
          setEditTaskForm({
            ...editTaskForm,
            description: event.target.value,
          })
        }
      />

      <select
        value={editTaskForm.subject_id || ""}
        onChange={(event) =>
          setEditTaskForm({
            ...editTaskForm,
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
        value={editTaskForm.event_id || ""}
        onChange={(event) =>
          setEditTaskForm({
            ...editTaskForm,
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
        value={editTaskForm.task_type || "homework"}
        onChange={(event) =>
          setEditTaskForm({
            ...editTaskForm,
            task_type: event.target.value,
          })
        }
      >
        <option value="laboratory">Лабораторна</option>
        <option value="homework">Практична / домашня</option>
        <option value="project">Проєкт</option>
        <option value="reading">Самостійна / читання</option>
        <option value="exam_preparation">Підготовка до іспиту</option>
        <option value="other">Інше</option>
      </select>

      <select
        value={editTaskForm.difficulty_score || 3}
        onChange={(event) =>
          setEditTaskForm({
            ...editTaskForm,
            difficulty_score: event.target.value,
          })
        }
      >
        <option value={1}>Легка</option>
        <option value={2}>Нижче середньої</option>
        <option value={3}>Середня</option>
        <option value={4}>Складна</option>
        <option value={5}>Дуже складна</option>
      </select>

      <input
        type="number"
        min="0.5"
        step="0.5"
        value={editTaskForm.estimated_duration_hours || 1}
        onChange={(event) =>
          setEditTaskForm({
            ...editTaskForm,
            estimated_duration_hours: event.target.value,
          })
        }
      />

      <select
        value={editTaskForm.priority || "medium"}
        onChange={(event) =>
          setEditTaskForm({
            ...editTaskForm,
            priority: event.target.value,
          })
        }
      >
        <option value="low">{t.low}</option>
        <option value="medium">{t.medium}</option>
        <option value="high">{t.high}</option>
      </select>

      <label className="task-date-label">{t.dueDate}</label>

      <input
        className="task-date-input"
        type="date"
        value={editTaskForm.due_date_date || ""}
        onClick={openNativePicker}
        onFocus={openNativePicker}
        onChange={(event) =>
          setEditTaskForm({
            ...editTaskForm,
            due_date_date: event.target.value,
          })
        }
      />

      <label className="task-date-label">{t.dueTime}</label>

      <input
        className="task-time-input"
        type="time"
        value={editTaskForm.due_date_time || ""}
        onClick={openNativePicker}
        onFocus={openNativePicker}
        onChange={(event) =>
          setEditTaskForm({
            ...editTaskForm,
            due_date_time: event.target.value,
          })
        }
      />

      <input
        value={editTaskForm.keywords || ""}
        placeholder={t.keywords}
        onChange={(event) =>
          setEditTaskForm({
            ...editTaskForm,
            keywords: event.target.value,
          })
        }
      />

      <div className="edit-actions">
        <button type="button" onClick={() => saveTask(task.id)}>
          {t.save}
        </button>

        <button
          type="button"
          className="secondary-mini-btn"
          onClick={() => setEditingTaskId(null)}
        >
          {t.cancel}
        </button>
      </div>
    </div>
  );

  const renderTaskMeta = (task, subjectName) => (
    <div className="task-meta">
      {task.task_type && (
        <span className="task-chip task-chip-type">
          {t.taskType}: {getTaskTypeLabel(task.task_type)}
        </span>
      )}

      {task.difficulty_score && (
        <span className="task-chip task-chip-difficulty">
          {t.difficulty}: {getDifficultyLabel(task.difficulty_score)}
        </span>
      )}

      {task.estimated_duration_hours && (
        <span className="task-chip task-chip-duration">
          ⏱ {t.duration}: {task.estimated_duration_hours} год
        </span>
      )}

      {task.due_date && (
        <span className="task-chip task-chip-deadline">
          Дедлайн: {formatDate(task.due_date)}
        </span>
      )}

      {renderAutoReplanBadge(task)}

      {subjectName && (
        <span className="task-chip task-chip-subject">{subjectName}</span>
      )}

      <span className="task-chip task-chip-priority">
        {getPriorityLabel(task.priority)}
      </span>
    </div>
  );

  const renderListTask = (task) => {
    const { subjectName } = getTaskDetails(task);

    return (
      <article
        key={task.id}
        className={`task-item compact-list-task ${task.status}`}
        onClick={() => setSelectedTask(task)}
      >
        <div className="compact-list-main">
          <div className="task-item-top">
            <h4>{task.title}</h4>
          </div>

          {editingTaskId === task.id ? (
            <div onClick={(event) => event.stopPropagation()}>
              {renderTaskEditForm(task)}
            </div>
          ) : (
            renderTaskMeta(task, subjectName)
          )}
        </div>

        <div
          className="task-actions"
          onClick={(event) => event.stopPropagation()}
        >
          <button type="button" onClick={() => startEditTask(task)}>
            {t.edit}
          </button>

          {renderStatusSelect(task)}

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
  };

  const renderCompactTask = (task) => (
    <article
      key={task.id}
      className={`compact-task-card ${task.status}`}
      onClick={() => setSelectedTask(task)}
    >
      {editingTaskId === task.id ? (
        <div onClick={(event) => event.stopPropagation()}>
          {renderTaskEditForm(task)}
        </div>
      ) : (
        <>
          <div className="compact-task-title">
            <span className="task-doc-icon">▧</span>
            <h4>{task.title}</h4>
          </div>

          <div className="compact-task-footer">
            <span className={`compact-status ${task.status}`}>
              {getStatusLabel(task.status)}
            </span>

            {task.estimated_duration_hours && (
              <span>{task.estimated_duration_hours} год</span>
            )}

            {task.difficulty_score && (
              <span>{getDifficultyLabel(task.difficulty_score)}</span>
            )}

            {task.due_date && (
              <span className="task-chip-deadline">
                Дедлайн: {formatDate(task.due_date)}
              </span>
            )}

            {renderAutoReplanBadge(task, true)}
          </div>

          <div
            className="compact-task-actions"
            onClick={(event) => event.stopPropagation()}
          >
            <button type="button" onClick={() => startEditTask(task)}>
              {t.edit}
            </button>

            {renderStatusSelect(task)}

            <button
              type="button"
              className="danger-button"
              onClick={() => deleteTask(task.id)}
            >
              {t.delete}
            </button>
          </div>
        </>
      )}
    </article>
  );

  const renderTaskModal = () => {
    if (!selectedTask) return null;

    const { subjectName } = getTaskDetails(selectedTask);

    return (
      <div
        className="task-modal-backdrop"
        onClick={() => setSelectedTask(null)}
      >
        <div
          className="task-modal"
          onClick={(event) => event.stopPropagation()}
        >
          <div className="task-modal-header">
            <div>
              <p className="eyebrow">Деталі задачі</p>
              <h2>{selectedTask.title}</h2>
            </div>

            <button type="button" onClick={() => setSelectedTask(null)}>
              ✕
            </button>
          </div>

          <p className="task-modal-description">
            {selectedTask.description || "Опис відсутній"}
          </p>

          <div className="task-modal-meta">
            {selectedTask.task_type && (
              <span>Тип: {getTaskTypeLabel(selectedTask.task_type)}</span>
            )}

            {selectedTask.difficulty_score && (
              <span>
                Складність: {getDifficultyLabel(selectedTask.difficulty_score)}
              </span>
            )}

            <span>Час: {selectedTask.estimated_duration_hours || "—"} год</span>
            <span>Статус: {getStatusLabel(selectedTask.status)}</span>
            <span>Пріоритет: {getPriorityLabel(selectedTask.priority)}</span>

            {selectedTask.due_date && (
              <span>Дедлайн: {formatDate(selectedTask.due_date)}</span>
            )}

            {renderAutoReplanBadge(selectedTask)}

            {subjectName && <span>Предмет: {subjectName}</span>}
          </div>

          <div className="task-modal-actions">
            <button
              type="button"
              onClick={() => {
                startEditTask(selectedTask);
                setSelectedTask(null);
              }}
            >
              {t.edit}
            </button>

            {renderStatusSelect(selectedTask)}

            <button
              type="button"
              className="danger-button"
              onClick={() => {
                deleteTask(selectedTask.id);
                setSelectedTask(null);
              }}
            >
              {t.delete}
            </button>
          </div>
        </div>
      </div>
    );
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

      <div className="tasks-grid tasks-management-layout">
        <div className="tasks-side-column">
          <div className="task-card subject-create-card">
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
                style={{ "--color-dot-bg": color }}
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

          <div className="compact-edit-list">
            {subjects.map((subject) => (
              <div
                key={subject.id}
                className={`compact-edit-item ${
                  editingSubjectId === subject.id ? "editing" : ""
                }`}
                onClick={() => {
                  if (editingSubjectId !== subject.id) {
                    startEditSubject(subject);
                  }
                }}
              >
                {editingSubjectId === subject.id ? (
                  <div
                    className="inline-edit-form"
                    onClick={(event) => event.stopPropagation()}
                  >
                    <input
                      value={editSubjectForm.name || ""}
                      placeholder={t.subjectName}
                      onChange={(event) =>
                        setEditSubjectForm({
                          ...editSubjectForm,
                          name: event.target.value,
                        })
                      }
                    />

                    <input
                      value={editSubjectForm.teacher || ""}
                      placeholder={t.teacher}
                      onChange={(event) =>
                        setEditSubjectForm({
                          ...editSubjectForm,
                          teacher: event.target.value,
                        })
                      }
                    />

                    <textarea
                      value={editSubjectForm.description || ""}
                      placeholder={t.description}
                      onChange={(event) =>
                        setEditSubjectForm({
                          ...editSubjectForm,
                          description: event.target.value,
                        })
                      }
                    />

                    <div className="color-row compact-colors">
                      {COLORS.map((color) => (
                        <button
                          key={color}
                          type="button"
                          className={
                            editSubjectForm.color === color
                              ? "color-dot active"
                              : "color-dot"
                          }
                          style={{ "--color-dot-bg": color }}
                          onClick={() =>
                            setEditSubjectForm({
                              ...editSubjectForm,
                              color,
                            })
                          }
                        />
                      ))}
                    </div>

                    <div className="edit-actions">
                      <button
                        type="button"
                        onClick={() => saveSubject(subject.id)}
                      >
                        {t.save}
                      </button>

                      <button
                        type="button"
                        className="secondary-mini-btn"
                        onClick={() => setEditingSubjectId(null)}
                      >
                        {t.cancel}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="compact-view-row">
                    <span
                      className="subject-color-dot"
                      style={{ backgroundColor: subject.color || COLORS[0] }}
                    />
                    <span>{subject.name}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
          </div>

          <div className="task-card event-type-create-card">
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
                  eventTypeForm.color === color
                    ? "color-dot active"
                    : "color-dot"
                }
                style={{ "--color-dot-bg": color }}

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

          <div className="compact-edit-list">
            {eventTypes.map((eventType) => (
              <div
                key={eventType.id}
                className={`compact-edit-item ${
                  editingEventTypeId === eventType.id ? "editing" : ""
                }`}
                onClick={() => {
                  if (editingEventTypeId !== eventType.id) {
                    startEditEventType(eventType);
                  }
                }}
              >
                {editingEventTypeId === eventType.id ? (
                  <div
                    className="inline-edit-form"
                    onClick={(event) => event.stopPropagation()}
                  >
                    <input
                      value={editEventTypeForm.name || ""}
                      placeholder={t.eventTypeName}
                      onChange={(event) =>
                        setEditEventTypeForm({
                          ...editEventTypeForm,
                          name: event.target.value,
                        })
                      }
                    />

                    <div className="color-row compact-colors">
                      {COLORS.map((color) => (
                        <button
                          key={color}
                          type="button"
                          className={
                            editEventTypeForm.color === color
                              ? "color-dot active"
                              : "color-dot"
                          }
                          style={{ "--color-dot-bg": color }}
                          onClick={() =>
                            setEditEventTypeForm({
                              ...editEventTypeForm,
                              color,
                            })
                          }
                        />
                      ))}
                    </div>

                    <div className="edit-actions">
                      <button
                        type="button"
                        onClick={() => saveEventType(eventType.id)}
                      >
                        {t.save}
                      </button>

                      <button
                        type="button"
                        className="secondary-mini-btn"
                        onClick={() => setEditingEventTypeId(null)}
                      >
                        {t.cancel}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="compact-view-row">
                    <span
                      className="subject-color-dot"
                      style={{ backgroundColor: eventType.color || COLORS[1] }}
                    />
                    <span>{eventType.name}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
          </div>
        </div>

        <div className="tasks-main-column">
          <div className="task-card task-create-card">
          <div className="task-create-heading">
            <h3>{t.createTask}</h3>
            <p>
              Заповни задачу вручну. Дедлайн можна вказати самостійно або підібрати автоматично.
            </p>
          </div>

          <div className="task-form-section">
            {renderFieldLabel(
              "Назва задачі",
              "Наприклад: Лабораторна №3."
            )}

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

            {renderFieldLabel(
              "Опис",
              "Умова або короткі деталі."
            )}

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
          </div>

          <div className="task-form-section">
            {renderFieldLabel(
              "Предмет",
              "Для групування і планування по парах."
            )}

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

            {renderFieldLabel(
              "Подія / пара",
              "Необов’язково."
            )}

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
          </div>

          <div className="task-form-section task-form-grid-2">
            <div>
              {renderFieldLabel(
                "Пріоритет",
                "Терміновість виконання."
              )}

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
            </div>

            <div>
              {renderFieldLabel(
                "Тип задачі",
                "Тип роботи для ML."
              )}

              <select
                value={taskForm.task_type}
                onChange={(event) =>
                  setTaskForm({
                    ...taskForm,
                    task_type: event.target.value,
                  })
                }
              >
                <option value="homework">Практична / домашня</option>
                <option value="laboratory">Лабораторна</option>
                <option value="project">Проєкт</option>
                <option value="reading">Самостійна / читання</option>
                <option value="exam_preparation">Підготовка до іспиту</option>
                <option value="other">Інше</option>
              </select>
            </div>

            <div>
              {renderFieldLabel(
                "Тривалість, год",
                "Оцінка часу."
              )}

              <input
                type="number"
                min="0.5"
                step="0.5"
                value={taskForm.estimated_duration_hours}
                onChange={(event) =>
                  setTaskForm({
                    ...taskForm,
                    estimated_duration_hours: event.target.value,
                  })
                }
              />
            </div>

            <div>
              {renderFieldLabel(
                "Складність",
                "1 легко, 5 складно."
              )}

              <select
                value={taskForm.difficulty_score}
                onChange={(event) =>
                  setTaskForm({
                    ...taskForm,
                    difficulty_score: event.target.value,
                  })
                }
              >
                <option value={1}>1 — легка</option>
                <option value={2}>2 — нижче середньої</option>
                <option value={3}>3 — середня</option>
                <option value={4}>4 — складна</option>
                <option value={5}>5 — дуже складна</option>
              </select>
            </div>
          </div>

          <div className="task-form-section task-deadline-section">
            {renderFieldLabel(
              "Дедлайн",
              "Можна залишити порожнім."
            )}

            <div className="task-form-grid-2">
              <input
                className="task-date-input"
                type="date"
                value={taskForm.due_date_date}
                onClick={openNativePicker}
                onFocus={openNativePicker}
                onChange={(event) =>
                  setTaskForm({
                    ...taskForm,
                    due_date_date: event.target.value,
                  })
                }
              />

              <input
                className="task-time-input"
                type="time"
                value={taskForm.due_date_time}
                onClick={openNativePicker}
                onFocus={openNativePicker}
                onChange={(event) =>
                  setTaskForm({
                    ...taskForm,
                    due_date_time: event.target.value,
                  })
                }
              />
            </div>
          </div>

          <div className="task-create-actions-row">
            <button
              type="button"
              className="task-auto-deadline-button"
              onClick={autoPickManualTaskDeadline}
            >
              ✨ Підібрати дедлайн
            </button>

            <button type="button" className="task-create-submit" onClick={createTask}>
              + {t.createTask}
            </button>
          </div>
          </div>
        </div>
      </div>

      <div className="task-board">
        <div className="task-board-header">
          <h3>{t.tasks}</h3>

          <div className="task-board-controls">
            <div className="task-view-toggle">
              <button
                type="button"
                className={taskViewMode === "grouped" ? "active" : ""}
                onClick={() => setTaskViewMode("grouped")}
              >
                {t.groupedView}
              </button>

              <button
                type="button"
                className={taskViewMode === "list" ? "active" : ""}
                onClick={() => setTaskViewMode("list")}
              >
                {t.listView}
              </button>
            </div>

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
        </div>

        {filteredTasks.length === 0 ? (
          <p className="empty-tasks">{t.noTasks}</p>
        ) : taskViewMode === "grouped" ? (
          <div className="subject-task-board">
            {groupedTasks.map((group) => (
              <section key={group.name} className="subject-column">
                <div
                  className="subject-column-title"
                  style={{ backgroundColor: group.color }}
                >
                  {group.name}
                </div>

                <div className="subject-column-list">
                  {group.tasks.map((task) => renderCompactTask(task))}
                </div>
              </section>
            ))}
          </div>
        ) : (
          <div className="task-list">
            {filteredTasks.map((task) => renderListTask(task))}
          </div>
        )}
      </div>

      {renderTaskModal()}
    </section>
  );
}