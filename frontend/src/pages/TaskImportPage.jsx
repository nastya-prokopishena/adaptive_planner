import { useEffect, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";

export default function TaskImportPage() {
  const [subjects, setSubjects] = useState([]);
  const [files, setFiles] = useState([]);
  const [text, setText] = useState("");
  const [selectedSubject, setSelectedSubject] = useState("");
  const [previews, setPreviews] = useState([]);
  const [modelInfo, setModelInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    loadSubjects();
    loadModelInfo();
  }, []);

  const showToast = (message, type = "success") => {
    setToast({ message, type });

    setTimeout(() => {
      setToast(null);
    }, 3500);
  };

  const loadSubjects = async () => {
    try {
      const response = await axios.get("/api/subjects");
      setSubjects(response.data || []);
    } catch (error) {
      console.error(error);
    }
  };

  const loadModelInfo = async () => {
    try {
      const response = await axios.get("/api/task-import/model-info");
      setModelInfo(response.data);
    } catch (error) {
      console.error(error);
      setModelInfo({ loaded: false });
    }
  };

  const analyzeText = async () => {
    if (!text.trim()) {
      showToast("Встав текст завдання", "error");
      return;
    }

    setLoading(true);

    try {
      const response = await axios.post("/api/task-import/analyze-text", {
        text,
        subject: selectedSubject,
      });

      const tasks = Array.isArray(response.data.tasks)
        ? response.data.tasks
        : [response.data];

      setPreviews(tasks.map(normalizePreview));

      showToast(`Знайдено задач: ${tasks.length}`, "success");
    } catch (error) {
      showToast(
        error.response?.data?.error || "Помилка аналізу тексту",
        "error"
      );
    } finally {
      setLoading(false);
    }
  };

  const analyzeFiles = async () => {
    if (!files.length) {
      showToast("Обери хоча б один файл", "error");
      return;
    }

    setLoading(true);

    const formData = new FormData();

    files.forEach((file) => {
      formData.append("files", file);
    });

    formData.append("subject", selectedSubject);

    try {
      const response = await axios.post(
        "/api/task-import/analyze-file",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
          withCredentials: true,
        }
      );

      const tasks = Array.isArray(response.data.tasks)
        ? response.data.tasks
        : [response.data];

      setPreviews(tasks.map(normalizePreview));

      showToast(`Знайдено задач: ${tasks.length}`, "success");
    } catch (error) {
      showToast(
        error.response?.data?.details ||
          error.response?.data?.error ||
          "Помилка аналізу файлів",
        "error"
      );
    } finally {
      setLoading(false);
    }
  };

  const normalizePreview = (preview) => {
    return {
      title: preview?.title || "Нова навчальна задача",
      subject: preview?.subject || selectedSubject || "Інше",
      subject_id: preview?.subject_id || null,
      subject_exists: Boolean(preview?.subject_exists),
      should_create_subject: Boolean(preview?.should_create_subject),
      task_type: preview?.task_type || "homework",
      description: makeReadableDescription(preview?.description || ""),
      keywords: Array.isArray(preview?.keywords) ? preview.keywords : [],
      estimated_duration_hours: Number(
        preview?.estimated_duration_hours || 1
      ),
      difficulty_score: Number(preview?.difficulty_score || 3),
      deadline: preview?.deadline || "",
      source_filename: preview?.source_filename || "",
      nlp_source: preview?.nlp_source || "ml_nlp",
    };
  };

  const makeReadableDescription = (value) => {
    const text = String(value || "")
      .replace(/\s+/g, " ")
      .replace(/Рис\.\s*\d+[^.]*\./gi, "")
      .replace(/Таблиця\s*\d+[^.]*\./gi, "")
      .replace(/Варіанти завдань[^.]*\./gi, "")
      .trim();

    if (text.length <= 700) {
      return text;
    }

    return `${text.slice(0, 700).trim()}...`;
  };

  const updatePreview = (index, field, value) => {
    setPreviews((prev) =>
      prev.map((item, itemIndex) =>
        itemIndex === index
          ? {
              ...item,
              [field]: value,
            }
          : item
      )
    );
  };

  const removePreview = (index) => {
    setPreviews((prev) => prev.filter((_, itemIndex) => itemIndex !== index));
  };

  const createSubjectIfNeeded = async (preview, index) => {
    if (!preview?.subject) {
      return null;
    }

    try {
      const response = await axios.post("/api/task-import/create-subject", {
        name: preview.subject,
      });

      await loadSubjects();

      updatePreview(index, "subject_id", response.data.id);
      updatePreview(index, "subject_exists", true);
      updatePreview(index, "should_create_subject", false);

      return response.data.id;
    } catch (error) {
      showToast("Не вдалося створити предмет", "error");
      return null;
    }
  };

  const createTask = async (preview, index, showNotification = true) => {
    let subjectId = preview.subject_id;

    if (preview.should_create_subject) {
      subjectId = await createSubjectIfNeeded(preview, index);

      if (!subjectId) {
        return false;
      }
    }

    try {
      await axios.post("/api/tasks", {
        title: preview.title,
        description: preview.description,
        subject: preview.subject,
        subject_id: subjectId,
        task_type: preview.task_type,
        keywords: preview.keywords,
        estimated_duration_hours: preview.estimated_duration_hours,
        difficulty_score: preview.difficulty_score,
        due_date: preview.deadline || null,
        status: "planned",
        priority: "medium",
        nlp_source: preview.source_filename ? "file" : "text",
      });

      removePreview(index);

      if (showNotification) {
        showToast("Задачу створено", "success");
      }

      return true;
    } catch (error) {
      showToast(
        error.response?.data?.error || "Не вдалося створити задачу",
        "error"
      );

      return false;
    }
  };

  const createAllTasks = async () => {
    if (!previews.length) {
      return;
    }

    let createdCount = 0;

    for (let index = previews.length - 1; index >= 0; index -= 1) {
      const created = await createTask(previews[index], index, false);

      if (created) {
        createdCount += 1;
      }
    }

    if (createdCount === 1) {
      showToast("Створено 1 задачу", "success");
    } else {
      showToast(`Створено задач: ${createdCount}`, "success");
    }
  };

  return (
    <main className="task-import-page">
      <section className="task-import-hero">
        <div>
          <p className="eyebrow">NLP / ML-модуль</p>
          <h1>Імпорт навчальних задач</h1>

          <p>
            Завантаж файли або встав текст завдання. Система автоматично
            визначить назву, предмет, тип, ключові слова, складність і
            орієнтовний час виконання.
          </p>

          {modelInfo && (
            <div
              className={
                modelInfo.loaded
                  ? "model-info-box success"
                  : "model-info-box warning"
              }
            >
              {modelInfo.loaded ? (
                <>
                  <strong>ML-модель активна</strong>

                  {modelInfo.fine_accuracy && (
                    <span>
                      Accuracy:
                      {(Number(modelInfo.fine_accuracy) * 100).toFixed(1)}%
                    </span>
                  )}
                </>
              ) : (
                <>
                  <strong>ML-модель не завантажена</strong>
                  <span>Буде використано fallback-оцінювання.</span>
                </>
              )}
            </div>
          )}
        </div>

        <Link to="/" className="secondary-button">
          Назад
        </Link>
      </section>

      <section className="task-import-grid">
        <div className="task-import-card">
          <h2>Дані для аналізу</h2>

          <label>Предмет</label>
          <select
            value={selectedSubject}
            onChange={(event) => setSelectedSubject(event.target.value)}
          >
            <option value="">Визначити автоматично</option>

            {subjects.map((subject) => (
              <option key={subject.id} value={subject.name}>
                {subject.name}
              </option>
            ))}
          </select>

          <label>Файли із завданнями</label>

          <input
            type="file"
            multiple
            accept=".txt,.pdf,.docx,.png,.jpg,.jpeg"
            onChange={(event) =>
              setFiles(Array.from(event.target.files || []))
            }
          />

          {files.length > 0 && (
            <div className="selected-files">
              {files.map((file, index) => (
                <span key={`${file.name}-${index}`}>{file.name}</span>
              ))}
            </div>
          )}

          <button
            type="button"
            className="primary-button full-width"
            onClick={analyzeFiles}
            disabled={loading}
          >
            {loading ? "Аналіз..." : "Аналізувати файли"}
          </button>

          <div className="task-import-divider">
            <span>або</span>
          </div>

          <label>Текст завдання</label>

          <textarea
            rows="9"
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Встав сюди текст завдання..."
          />

          <button
            type="button"
            className="secondary-action-button full-width"
            onClick={analyzeText}
            disabled={loading}
          >
            {loading ? "Аналіз..." : "Аналізувати текст"}
          </button>
        </div>
      </section>

      {loading && (
        <div className="task-loading">
          Виконується NLP/ML-аналіз...
        </div>
      )}

      {previews.length > 0 && (
        <section className="task-preview-section">
          <div className="task-preview-header">
            <div>
              <p className="eyebrow">Preview</p>
              <h2>Знайдено задач: {previews.length}</h2>
            </div>

            <button
              type="button"
              className="primary-button"
              onClick={createAllTasks}
              disabled={loading}
            >
              Створити всі задачі
            </button>
          </div>

          <div className="task-preview-list">
            {previews.map((preview, index) => (
              <article
                className="task-preview-card"
                key={`${preview.title}-${index}`}
              >
                <div className="task-preview-card-header">
                  <div>
                    {preview.source_filename && (
                      <p className="task-source">
                        Файл: {preview.source_filename}
                      </p>
                    )}
                  </div>

                  <button
                    type="button"
                    className="danger-button"
                    onClick={() => removePreview(index)}
                  >
                    Видалити
                  </button>
                </div>

                <label>Назва</label>
                <input
                  value={preview.title || ""}
                  onChange={(event) =>
                    updatePreview(index, "title", event.target.value)
                  }
                />

                <label>Предмет</label>
                <input
                  value={preview.subject || ""}
                  onChange={(event) =>
                    updatePreview(index, "subject", event.target.value)
                  }
                />

                <label>Тип задачі</label>

                <select
                  value={preview.task_type || "other"}
                  onChange={(event) =>
                    updatePreview(index, "task_type", event.target.value)
                  }
                >
                  <option value="laboratory">Лабораторна</option>
                  <option value="homework">Домашнє завдання</option>
                  <option value="project">Проєкт</option>
                  <option value="reading">Читання</option>
                  <option value="exam_preparation">
                    Підготовка до іспиту
                  </option>
                  <option value="other">Інше</option>
                </select>

                <label>Опис</label>

                <textarea
                  rows="5"
                  value={preview.description || ""}
                  onChange={(event) =>
                    updatePreview(index, "description", event.target.value)
                  }
                />

                <label>Ключові слова</label>

                <input
                  value={(preview.keywords || []).join(", ")}
                  onChange={(event) =>
                    updatePreview(
                      index,
                      "keywords",
                      event.target.value
                        .split(",")
                        .map((item) => item.trim())
                        .filter(Boolean)
                    )
                  }
                />

                <div className="task-preview-row">
                  <div>
                    <label>Тривалість, год</label>

                    <input
                      type="number"
                      min="0.5"
                      step="0.5"
                      value={preview.estimated_duration_hours || 1}
                      onChange={(event) =>
                        updatePreview(
                          index,
                          "estimated_duration_hours",
                          Number(event.target.value)
                        )
                      }
                    />
                  </div>

                  <div>
                    <label>Складність</label>

                    <select
                      value={preview.difficulty_score || 3}
                      onChange={(event) =>
                        updatePreview(
                          index,
                          "difficulty_score",
                          Number(event.target.value)
                        )
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

                <label>Дедлайн</label>

                <input
                  type="datetime-local"
                  value={preview.deadline ? preview.deadline.slice(0, 16) : ""}
                  onChange={(event) =>
                    updatePreview(index, "deadline", event.target.value)
                  }
                />

                <button
                  type="button"
                  className="primary-button full-width"
                  onClick={() => createTask(preview, index)}
                >
                  Створити задачу
                </button>
              </article>
            ))}
          </div>
        </section>
      )}

      {toast && (
        <div className={`app-toast ${toast.type}`}>
          {toast.message}
        </div>
      )}
    </main>
  );
}

