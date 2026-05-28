import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  CartesianGrid,
} from "recharts";

axios.defaults.withCredentials = true;

const WEEK_DAYS_UA = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"];

const PIE_COLORS = ["#38bdf8", "#8b5cf6", "#22c55e", "#f97316", "#ef4444", "#eab308"];

function startOfWeek(date) {
  const value = new Date(date);
  const day = value.getDay();
  const diff = value.getDate() - day + (day === 0 ? -6 : 1);

  value.setDate(diff);
  value.setHours(0, 0, 0, 0);

  return value;
}

function addDays(date, days) {
  const value = new Date(date);
  value.setDate(value.getDate() + days);
  return value;
}

function formatDateInput(date) {
  return date.toISOString().slice(0, 10);
}

function formatShortDate(date) {
  return new Intl.DateTimeFormat("uk-UA", {
    day: "2-digit",
    month: "short",
  }).format(date);
}

function normalizeNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) {
    return null;
  }

  return (
    <div className="analytics-tooltip">
      <strong>{label}</strong>
      {payload.map((item) => (
        <p key={item.dataKey || item.name}>
          <span>{item.name || item.dataKey}</span>
          <b>{item.value}</b>
        </p>
      ))}
    </div>
  );
}

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [weekStart, setWeekStart] = useState(startOfWeek(new Date()));

  const weekEnd = useMemo(() => addDays(weekStart, 6), [weekStart]);

  const filters = useMemo(
    () => ({
      date_from: formatDateInput(weekStart),
      date_to: formatDateInput(weekEnd),
    }),
    [weekStart, weekEnd]
  );

  const loadAnalytics = async () => {
    setLoading(true);

    try {
      const response = await axios.get("/api/analytics/dashboard", {
        params: filters,
      });

      setAnalytics(response.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, [filters.date_from, filters.date_to]);

  const weeklyLoad = useMemo(() => {
    const source = analytics?.weekly_load || [];

    return WEEK_DAYS_UA.map((dayName, index) => {
      const currentDate = addDays(weekStart, index);
      const isoDate = formatDateInput(currentDate);
      const found = source.find((item) => item.date === isoDate);

      return {
        day: dayName,
        date: isoDate,
        shortDate: formatShortDate(currentDate),
        hours: normalizeNumber(found?.hours),
      };
    });
  }, [analytics, weekStart]);

  const productivityData = useMemo(() => {
    return (analytics?.productivity_history || []).slice(-7).map((item) => ({
      date: item.date,
      score: normalizeNumber(item.productivity_score),
    }));
  }, [analytics]);

  const difficultyData = useMemo(() => {
    if (!analytics?.difficulty_distribution) {
      return [];
    }

    return Object.entries(analytics.difficulty_distribution)
      .filter(([, value]) => normalizeNumber(value) > 0)
      .map(([name, value]) => ({
        name: `Складність ${name}`,
        value: normalizeNumber(value),
      }));
  }, [analytics]);

  const completedData = useMemo(() => {
    return (analytics?.completed_vs_missed || [])
      .filter((item) => normalizeNumber(item.value) > 0)
      .map((item) => ({
        name: item.name,
        value: normalizeNumber(item.value),
      }));
  }, [analytics]);

  const summary = analytics?.summary || {};
  const maxDayLoad = Math.max(...weeklyLoad.map((item) => item.hours), 1);
  const totalWeekHours = weeklyLoad.reduce((sum, item) => sum + item.hours, 0);
  const busiestDay = weeklyLoad.reduce(
    (max, item) => (item.hours > max.hours ? item : max),
    weeklyLoad[0]
  );

  const summaryCards = [
    {
      label: "Виконано",
      value: summary.completed || 0,
      icon: "✅",
      className: "done",
      hint: "Завершені задачі",
    },
    {
      label: "Пропущено",
      value: summary.missed || 0,
      icon: "⚠️",
      className: "missed",
      hint: "Потребують уваги",
    },
    {
      label: "Заплановано",
      value: summary.planned || 0,
      icon: "📅",
      className: "planned",
      hint: "Активні дедлайни",
    },
    {
      label: "У процесі",
      value: summary.in_progress || 0,
      icon: "🔥",
      className: "progress",
      hint: "Поточна робота",
    },
  ];

  const goPreviousWeek = () => setWeekStart((current) => addDays(current, -7));
  const goNextWeek = () => setWeekStart((current) => addDays(current, 7));
  const goCurrentWeek = () => setWeekStart(startOfWeek(new Date()));

  if (loading && !analytics) {
    return (
      <main className="analytics-modern-page">
        <section className="analytics-loading-panel">
          <div className="analytics-loading-icon">📊</div>
          <h1>Завантаження аналітики</h1>
          <p>Підраховуємо навантаження, задачі та продуктивність.</p>
        </section>
      </main>
    );
  }

  return (
    <main className="analytics-modern-page">
      <section className="analytics-modern-hero">
        <div className="analytics-hero-content">
          <Link to="/" className="analytics-back-button">
            ← До календаря
          </Link>

          <span className="analytics-kicker">Analytics</span>

          <h1>Навчальне навантаження</h1>

          <p>
            Красивий тижневий огляд задач: години, дедлайни, складність і
            продуктивність без величезних сирих графіків.
          </p>
        </div>

        <div className="analytics-week-card">
          <span>Поточний тиждень</span>
          <strong>
            {formatShortDate(weekStart)} — {formatShortDate(weekEnd)}
          </strong>
          <p>Усього навантаження: {totalWeekHours.toFixed(1)} год</p>
        </div>
      </section>

      <section className="analytics-week-header">
        <div>
          <span className="analytics-kicker">Weekly overview</span>
          <h2>
            {formatShortDate(weekStart)} — {formatShortDate(weekEnd)}
          </h2>
        </div>

        <div className="analytics-week-controls">
          <button type="button" onClick={goPreviousWeek}>
            ‹
          </button>

          <button type="button" onClick={goCurrentWeek} className="current">
            Цей тиждень
          </button>

          <button type="button" onClick={goNextWeek}>
            ›
          </button>
        </div>
      </section>

      <section className="analytics-days-strip">
        {weeklyLoad.map((day) => {
          const percent = Math.min((day.hours / maxDayLoad) * 100, 100);
          const isBusy = day.date === busiestDay?.date && day.hours > 0;

          return (
            <article
              className={`analytics-day-tile ${isBusy ? "busy" : ""}`}
              key={day.date}
            >
              <div className="analytics-day-head">
                <span>{day.day}</span>
                <b>{day.shortDate}</b>
              </div>

              <div className="analytics-day-hours">
                <strong>{day.hours.toFixed(day.hours % 1 === 0 ? 0 : 1)}</strong>
                <span>год</span>
              </div>

              <div className="analytics-day-bar">
                <div style={{ width: `${percent}%` }} />
              </div>
            </article>
          );
        })}
      </section>

      <section className="analytics-summary-modern">
        {summaryCards.map((card) => (
          <article
            className={`analytics-summary-modern-card ${card.className}`}
            key={card.label}
          >
            <div className="analytics-card-icon">{card.icon}</div>
            <div>
              <span>{card.label}</span>
              <strong>{card.value}</strong>
              <p>{card.hint}</p>
            </div>
          </article>
        ))}
      </section>

      <section className="analytics-main-grid">
        <article className="analytics-panel analytics-panel-wide">
          <div className="analytics-panel-title">
            <div>
              <span>Load</span>
              <h3>Навантаження за днями</h3>
            </div>
            <p>Тільки вибраний тиждень, без зайвих старих дат.</p>
          </div>

          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={weeklyLoad} barSize={56}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="day" />
              <YAxis />
              <Tooltip content={<CustomTooltip />} />
              <Bar
                dataKey="hours"
                name="Години"
                fill="#3b82f6"
                radius={[16, 16, 8, 8]}
              />
            </BarChart>
          </ResponsiveContainer>
        </article>

        <article className="analytics-panel analytics-panel-wide">
          <div className="analytics-panel-title">
            <div>
              <span>Productivity</span>
              <h3>Продуктивність</h3>
            </div>
            <p>Останні 7 значень, щоб графік не перетворювався на шум.</p>
          </div>

          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={productivityData}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="date" />
              <YAxis domain={[0, 100]} />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="score"
                name="Продуктивність"
                stroke="#38bdf8"
                strokeWidth={4}
                dot={{ r: 5, fill: "#020617", stroke: "#38bdf8", strokeWidth: 3 }}
                activeDot={{ r: 7 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </article>

        <article className="analytics-panel">
          <div className="analytics-panel-title compact">
            <div>
              <span>Difficulty</span>
              <h3>Складність</h3>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={difficultyData}
                dataKey="value"
                nameKey="name"
                innerRadius={68}
                outerRadius={105}
                paddingAngle={5}
              >
                {difficultyData.map((entry, index) => (
                  <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </article>

        <article className="analytics-panel">
          <div className="analytics-panel-title compact">
            <div>
              <span>Status</span>
              <h3>Виконання</h3>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={completedData}
                dataKey="value"
                nameKey="name"
                innerRadius={68}
                outerRadius={105}
                paddingAngle={5}
              >
                {completedData.map((entry, index) => (
                  <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </article>
      </section>
    </main>
  );
}
