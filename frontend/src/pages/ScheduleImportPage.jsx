import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

const DAY_INDEX = {
  SU: 0,
  MO: 1,
  TU: 2,
  WE: 3,
  TH: 4,
  FR: 5,
  SA: 6,
};

const EVENT_TYPE_LABELS = {
  lecture: "Лекція",
  laboratory: "Лабораторна",
  practice: "Практична",
  seminar: "Семінар",
  consultation: "Консультація",
  exam: "Іспит",
  credit: "Залік",
  class: "Заняття",
  unknown: "Не визначено",
};

const WEEK_PATTERN_LABELS = {
  weekly: "Щотижня",
  odd: "Непарні",
  even: "Парні",
};

const SUPPORTED_FORMATS = [
  "PDF",
  "Excel: XLSX / XLS",
  "DOCX",
  "TXT / CSV",
  "Фото: JPG / PNG / WEBP",
  "Текст вручну",
];

function formatDateLocal(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function generateDatesForDay(startDate, endDate, dayCode) {
  const targetDay = DAY_INDEX[dayCode];

  if (targetDay === undefined || !startDate || !endDate) {
    return [];
  }

  const start = new Date(`${startDate}T00:00:00`);
  const end = new Date(`${endDate}T23:59:59`);

  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    return [];
  }

  const dates = [];
  const current = new Date(start);

  while (current <= end) {
    if (current.getDay() === targetDay) {
      dates.push(formatDateLocal(current));
    }

    current.setDate(current.getDate() + 1);
  }

  return dates;
}

function getAcademicWeekNumber(date, semesterStart) {
  const current = new Date(`${date}T00:00:00`);
  const start = new Date(`${semesterStart}T00:00:00`);

  if (Number.isNaN(current.getTime()) || Number.isNaN(start.getTime())) {
    return null;
  }

  const diffMs = current.getTime() - start.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays < 0) {
    return null;
  }

  return Math.floor(diffDays / 7) + 1;
}

function filterDatesByWeekPattern(dates, weekPattern, semesterStart) {
  if (!weekPattern || weekPattern === "weekly") {
    return dates;
  }

  return dates.filter((date) => {
    const weekNumber = getAcademicWeekNumber(date, semesterStart);

    if (!weekNumber) {
      return false;
    }

    if (weekPattern === "odd") {
      return weekNumber % 2 === 1;
    }

    if (weekPattern === "even") {
      return weekNumber % 2 === 0;
    }

    return true;
  });
}

function toISODateTime(date, time) {
  if (!date || !time) return null;
  return `${date}T${time}:00`;
}

function addMinutesToTime(time, minutesToAdd = 80) {
  if (!time) return "";

  const [hours, minutes] = time.split(":").map(Number);

  if (Number.isNaN(hours) || Number.isNaN(minutes)) {
    return "";
  }

  const totalMinutes = hours * 60 + minutes + minutesToAdd;
  const newHours = Math.floor(totalMinutes / 60) % 24;
  const newMinutes = totalMinutes % 60;

  return `${String(newHours).padStart(2, "0")}:${String(newMinutes).padStart(
    2,
    "0"
  )}`;
}

function buildEventTitle(event) {
  const typeLabel = EVENT_TYPE_LABELS[event.event_type] || "Заняття";
  const weekLabel = WEEK_PATTERN_LABELS[event.week_pattern] || "";
  const parts = [];

  if (event.subject) parts.push(event.subject);
  if (typeLabel && typeLabel !== "Заняття") parts.push(`(${typeLabel})`);
  if (weekLabel && event.week_pattern !== "weekly") parts.push(`[${weekLabel}]`);
  if (event.room) parts.push(`ауд. ${event.room}`);

  return parts.join(" ").trim() || "Навчальна подія";
}

export default function ScheduleImportPage({ loadEvents }) {
  const [inputMode, setInputMode] = useState("file");

  const [file, setFile] = useState(null);
  const [rawText, setRawText] = useState("");

  const [groupName, setGroupName] = useState("");
  const [subgroup, setSubgroup] = useState("");
  const [semesterStart, setSemesterStart] = useState("");
  const [semesterEnd, setSemesterEnd] = useState("");

  const [previewEvents, setPreviewEvents] = useState([]);
  const [importId, setImportId] = useState(null);

  const [loadingPreview, setLoadingPreview] = useState(false);
  const [importing, setImporting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const selectedFileName = file ? file.name : "Файл не вибрано";

  const validEventsCount = useMemo(() => {
    return previewEvents.filter(
      (event) =>
        event.subject &&
        event.day_of_week &&
        event.start_time &&
        event.end_time
    ).length;
  }, [previewEvents]);

  const eventsNeedReviewCount = useMemo(() => {
    return previewEvents.filter((event) => event.needs_review).length;
  }, [previewEvents]);

  const handlePreview = async (event) => {
    event.preventDefault();

    setError("");
    setMessage("");
    setLoadingPreview(true);

    try {
      let response;

      if (inputMode === "file") {
        if (!file) {
          setError("Обери файл розкладу.");
          setLoadingPreview(false);
          return;
        }

        const formData = new FormData();

        formData.append("file", file);
        formData.append("group_name", groupName);
        formData.append("subgroup", subgroup);

        response = await axios.post("/api/schedule-import/preview", formData, {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        });
      } else {
        if (!rawText.trim()) {
          setError("Встав текст розкладу.");
          setLoadingPreview(false);
          return;
        }

        response = await axios.post("/api/schedule-import/preview", {
          raw_text: rawText,
          group_name: groupName,
          subgroup,
        });
      }

      const events = response.data?.events || [];

      setImportId(response.data?.import_id || null);
      setPreviewEvents(
        events.map((item) => ({
          ...item,
          week_pattern: item.week_pattern || "weekly",
        }))
      );

      if (events.length === 0) {
        setMessage("Події не знайдено. Перевір файл, групу або підгрупу.");
      } else {
        setMessage(`Знайдено подій: ${events.length}`);
      }
    } catch (err) {
      setError(
        err.response?.data?.details ||
          err.response?.data?.error ||
          "Не вдалося сформувати preview розкладу."
      );
    } finally {
      setLoadingPreview(false);
    }
  };

  const updatePreviewEvent = (index, field, value) => {
    setPreviewEvents((prev) =>
      prev.map((item, itemIndex) =>
        itemIndex === index
          ? {
              ...item,
              [field]: value,
              needs_review: false,
            }
          : item
      )
    );
  };

  const updateStartTimeWithAutoEnd = (index, startTime) => {
    setPreviewEvents((prev) =>
      prev.map((item, itemIndex) => {
        if (itemIndex !== index) return item;

        const autoEndTime = addMinutesToTime(startTime, 80);

        return {
          ...item,
          start_time: startTime,
          end_time:
            !item.end_time || item.end_time <= startTime
              ? autoEndTime
              : item.end_time,
          needs_review: false,
        };
      })
    );
  };

  const removePreviewEvent = (index) => {
    setPreviewEvents((prev) =>
      prev.filter((_, itemIndex) => itemIndex !== index)
    );
  };

  const clearImportForm = () => {
    setFile(null);
    setRawText("");
    setPreviewEvents([]);
    setMessage("");
    setError("");
    setImportId(null);
  };

  const handleImportToCalendar = async () => {
    setError("");
    setMessage("");

    if (!semesterStart || !semesterEnd) {
      setError("Вкажи початок і кінець семестру.");
      return;
    }

    const validEvents = previewEvents.filter(
      (event) =>
        event.subject &&
        event.day_of_week &&
        event.start_time &&
        event.end_time
    );

    if (validEvents.length === 0) {
      setError("Немає валідних подій для імпорту.");
      return;
    }

    setImporting(true);

    let createdCount = 0;
    let failedCount = 0;

    try {
      for (const previewEvent of validEvents) {
        const allDates = generateDatesForDay(
          semesterStart,
          semesterEnd,
          previewEvent.day_of_week
        );

        const dates = filterDatesByWeekPattern(
          allDates,
          previewEvent.week_pattern || "weekly",
          semesterStart
        );

        for (const date of dates) {
          const start = toISODateTime(date, previewEvent.start_time);
          const end = toISODateTime(date, previewEvent.end_time);

          if (!start || !end) {
            failedCount += 1;
            continue;
          }

          const title = buildEventTitle(previewEvent);

          try {
            await axios.post("/api/events", {
              title,
              start,
              end,
              subject: previewEvent.subject,
              event_type: previewEvent.event_type || "class",
              teacher: previewEvent.teacher || "",
              room: previewEvent.room || "",
              group_name: previewEvent.group_name || groupName || "",
              subgroup: previewEvent.subgroup || subgroup || "",
              week_pattern: previewEvent.week_pattern || "weekly",
              source: "schedule_import",
              import_id: importId,
            });

            createdCount += 1;
          } catch {
            failedCount += 1;
          }
        }
      }

      setMessage(
        `Імпорт завершено. Створено подій: ${createdCount}. Помилок: ${failedCount}.`
      );

      if (typeof loadEvents === "function") {
        loadEvents();
      }
    } catch {
      setError("Не вдалося імпортувати події в календар.");
    } finally {
      setImporting(false);
    }
  };

  return (
    <main className="schedule-import-page">
      <section className="schedule-import-hero">
        <div className="schedule-import-hero-main">
          <Link to="/" className="back-link">
            ← Назад до Dashboard
          </Link>

          <p className="eyebrow">Імпорт навчального розкладу</p>

          <h1>Завантаж розклад і перенеси пари в календар</h1>

          <p>
            Можна завантажити PDF, Excel, DOCX, TXT, CSV, фото розкладу або
            просто вставити текст вручну. Система сформує preview подій, які
            можна перевірити й відредагувати перед імпортом.
          </p>
        </div>

        <div className="format-card">
          <h3>Підтримувані формати</h3>

          <div className="format-list">
            {SUPPORTED_FORMATS.map((format) => (
              <span key={format}>{format}</span>
            ))}
          </div>

          <p>
            Для фото розкладу використовується AI/OCR-обробка, а для PDF,
            Excel, DOCX, TXT і CSV — попереднє зчитування файлу та AI-аналіз.
          </p>
        </div>
      </section>

      <section className="schedule-import-card">
        <div className="mode-switch">
          <button
            type="button"
            className={inputMode === "file" ? "active" : ""}
            onClick={() => {
              setInputMode("file");
              setError("");
              setMessage("");
            }}
          >
            📎 Завантажити файл
          </button>

          <button
            type="button"
            className={inputMode === "text" ? "active" : ""}
            onClick={() => {
              setInputMode("text");
              setError("");
              setMessage("");
            }}
          >
            ✍️ Вставити текст
          </button>
        </div>

        <form className="schedule-import-form" onSubmit={handlePreview}>
          {inputMode === "file" ? (
            <div className="upload-box">
              <input
                id="schedule-file"
                type="file"
                accept=".pdf,.xlsx,.xls,.csv,.doc,.docx,.txt,.jpg,.jpeg,.png,.webp"
                onChange={(event) =>
                  setFile(event.target.files?.[0] || null)
                }
              />

              <label htmlFor="schedule-file">
                <div className="upload-icon">⬆️</div>

                <strong>Натисни, щоб вибрати файл розкладу</strong>

                <span>{selectedFileName}</span>

                <small>
                  Підтримуються PDF, Excel, DOCX, TXT, CSV та фото. Перед
                  імпортом у календар система покаже preview подій.
                </small>
              </label>
            </div>
          ) : (
            <label className="text-mode-field">
              Текст розкладу
              <textarea
                rows="8"
                placeholder="Наприклад: Понеділок 08:30-09:50 КН-31 підгр. 2 Методи машинного навчання лаб. доц. Петренко І.О. 301"
                value={rawText}
                onChange={(event) => setRawText(event.target.value)}
              />
            </label>
          )}

          <div className="form-grid">
            <label>
              Група
              <input
                type="text"
                placeholder="Наприклад: КН-31"
                value={groupName}
                onChange={(event) => setGroupName(event.target.value)}
              />
            </label>

            <label>
              Підгрупа
              <input
                type="text"
                placeholder="Наприклад: 1 або 2"
                value={subgroup}
                onChange={(event) => setSubgroup(event.target.value)}
              />
            </label>

            <label>
              Початок семестру
              <input
                type="date"
                value={semesterStart}
                onChange={(event) => setSemesterStart(event.target.value)}
              />
            </label>

            <label>
              Кінець семестру
              <input
                type="date"
                value={semesterEnd}
                onChange={(event) => setSemesterEnd(event.target.value)}
              />
            </label>
          </div>

          <div className="actions-row">
            <button type="submit" disabled={loadingPreview}>
              {loadingPreview ? "Формую preview..." : "Сформувати preview"}
            </button>

            <button
              type="button"
              className="secondary-button"
              onClick={clearImportForm}
            >
              Очистити
            </button>
          </div>
        </form>

        {message && <div className="success-message">{message}</div>}
        {error && <div className="error-message">{error}</div>}
      </section>

      {previewEvents.length > 0 && (
        <section className="preview-section">
          <div className="preview-header">
            <div>
              <p className="eyebrow">Preview</p>

              <h2>Імпортовані події</h2>

              <p>
                Валідних подій: {validEventsCount} / {previewEvents.length}.
                Потребують перевірки: {eventsNeedReviewCount}.
              </p>
            </div>

            <button
              type="button"
              onClick={handleImportToCalendar}
              disabled={importing || validEventsCount === 0}
            >
              {importing ? "Імпортую..." : "Імпортувати в календар"}
            </button>
          </div>

          <div className="table-wrapper">
            <table className="preview-table">
              <thead>
                <tr>
                  <th>Предмет</th>
                  <th>Тип</th>
                  <th>День</th>
                  <th>Тижні</th>
                  <th>Початок</th>
                  <th>Кінець</th>
                  <th>Викладач</th>
                  <th>Аудиторія</th>
                  <th>Група</th>
                  <th>Підгрупа</th>
                  <th>Confidence</th>
                  <th></th>
                </tr>
              </thead>

              <tbody>
                {previewEvents.map((event, index) => (
                  <tr
                    key={`${event.subject}-${index}`}
                    className={event.needs_review ? "needs-review-row" : ""}
                  >
                    <td>
                      <input
                        value={event.subject || ""}
                        onChange={(e) =>
                          updatePreviewEvent(index, "subject", e.target.value)
                        }
                      />
                    </td>

                    <td>
                      <select
                        value={event.event_type || "class"}
                        onChange={(e) =>
                          updatePreviewEvent(
                            index,
                            "event_type",
                            e.target.value
                          )
                        }
                      >
                        <option value="class">Заняття</option>
                        <option value="lecture">Лекція</option>
                        <option value="laboratory">Лабораторна</option>
                        <option value="practice">Практична</option>
                        <option value="seminar">Семінар</option>
                        <option value="consultation">Консультація</option>
                        <option value="exam">Іспит</option>
                        <option value="credit">Залік</option>
                      </select>
                    </td>

                    <td>
                      <select
                        value={event.day_of_week || ""}
                        onChange={(e) =>
                          updatePreviewEvent(
                            index,
                            "day_of_week",
                            e.target.value
                          )
                        }
                      >
                        <option value="">Не визначено</option>
                        <option value="MO">Пн</option>
                        <option value="TU">Вт</option>
                        <option value="WE">Ср</option>
                        <option value="TH">Чт</option>
                        <option value="FR">Пт</option>
                        <option value="SA">Сб</option>
                        <option value="SU">Нд</option>
                      </select>
                    </td>

                    <td>
                      <select
                        value={event.week_pattern || "weekly"}
                        onChange={(e) =>
                          updatePreviewEvent(
                            index,
                            "week_pattern",
                            e.target.value
                          )
                        }
                      >
                        <option value="weekly">Щотижня</option>
                        <option value="odd">Непарні</option>
                        <option value="even">Парні</option>
                      </select>
                    </td>

                    <td>
                      <input
                        type="time"
                        value={event.start_time || ""}
                        onChange={(e) =>
                          updateStartTimeWithAutoEnd(index, e.target.value)
                        }
                      />
                    </td>

                    <td>
                      <input
                        type="time"
                        value={event.end_time || ""}
                        onChange={(e) =>
                          updatePreviewEvent(index, "end_time", e.target.value)
                        }
                      />
                    </td>

                    <td>
                      <input
                        value={event.teacher || ""}
                        onChange={(e) =>
                          updatePreviewEvent(index, "teacher", e.target.value)
                        }
                      />
                    </td>

                    <td>
                      <input
                        value={event.room || ""}
                        onChange={(e) =>
                          updatePreviewEvent(index, "room", e.target.value)
                        }
                      />
                    </td>

                    <td>
                      <input
                        value={event.group_name || ""}
                        onChange={(e) =>
                          updatePreviewEvent(
                            index,
                            "group_name",
                            e.target.value
                          )
                        }
                      />
                    </td>

                    <td>
                      <input
                        value={event.subgroup || ""}
                        onChange={(e) =>
                          updatePreviewEvent(index, "subgroup", e.target.value)
                        }
                      />
                    </td>

                    <td>
                      <span className="confidence-badge">
                        {event.confidence ?? 0}
                      </span>
                    </td>

                    <td>
                      <button
                        type="button"
                        className="danger-button"
                        onClick={() => removePreviewEvent(index)}
                      >
                        ×
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="preview-note">
            <p>
              Події будуть створені в межах вибраного періоду семестру з
              урахуванням тижнів: щотижня, парні або непарні.
            </p>

            <p>
              Якщо змінити час початку пари, кінець автоматично розрахується як
              +80 хвилин. Якщо потрібно, його можна відредагувати вручну.
            </p>
          </div>
        </section>
      )}
    </main>
  );
}