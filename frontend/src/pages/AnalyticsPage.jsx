import { useEffect, useState } from "react";
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
} from "recharts";

axios.defaults.withCredentials = true;

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState(null);
  const [filters, setFilters] = useState({
    date_from: "",
    date_to: "",
  });

  const loadAnalytics = async () => {
    const response = await axios.get("/api/analytics/dashboard", {
      params: {
        date_from: filters.date_from || undefined,
        date_to: filters.date_to || undefined,
      },
    });

    setAnalytics(response.data);
  };

  useEffect(() => {
    loadAnalytics();
  }, []);

  if (!analytics) {
    return <main className="analytics-page">Завантаження аналітики...</main>;
  }

  const difficultyData = Object.entries(
    analytics.difficulty_distribution || {}
  ).map(([name, value]) => ({
    name: `Складність ${name}`,
    value,
  }));

  return (
    <main className="analytics-page">
      <section className="dashboard-header">
        <div>
          <p className="eyebrow">Analytics</p>
          <h1>Аналітика навчального навантаження</h1>
          <p>
            Тут відображається статистика виконання задач, складність,
            навантаження за днями та історія продуктивності.
          </p>
        </div>
      </section>

      <section className="analytics-filters">
        <label>
          Від
          <input
            type="date"
            value={filters.date_from}
            onChange={(event) =>
              setFilters({
                ...filters,
                date_from: event.target.value,
              })
            }
          />
        </label>

        <label>
          До
          <input
            type="date"
            value={filters.date_to}
            onChange={(event) =>
              setFilters({
                ...filters,
                date_to: event.target.value,
              })
            }
          />
        </label>

        <button type="button" onClick={loadAnalytics}>
          Застосувати
        </button>
      </section>

      <section className="compact-stats">
        <div>
          <span>Виконано</span>
          <strong>{analytics.summary.completed}</strong>
        </div>

        <div>
          <span>Пропущено</span>
          <strong>{analytics.summary.missed}</strong>
        </div>

        <div>
          <span>Заплановано</span>
          <strong>{analytics.summary.planned}</strong>
        </div>

        <div>
          <span>У процесі</span>
          <strong>{analytics.summary.in_progress}</strong>
        </div>
      </section>

      <section className="analytics-grid">
        <div className="analytics-card">
          <h3>Навантаження за днями</h3>

          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={analytics.weekly_load}>
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="hours" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="analytics-card">
          <h3>Історія продуктивності</h3>

          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={analytics.productivity_history}>
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line dataKey="productivity_score" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="analytics-card">
          <h3>Розподіл складності</h3>

          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={difficultyData}
                dataKey="value"
                nameKey="name"
                outerRadius={90}
                label
              >
                {difficultyData.map((entry, index) => (
                  <Cell key={entry.name} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="analytics-card">
          <h3>Виконано / пропущено</h3>

          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={analytics.completed_vs_missed}
                dataKey="value"
                nameKey="name"
                outerRadius={90}
                label
              >
                {analytics.completed_vs_missed.map((entry) => (
                  <Cell key={entry.name} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </section>
    </main>
  );
}