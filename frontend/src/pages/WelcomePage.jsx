import { Link } from "react-router-dom";

export default function WelcomePage() {
  const handleGoogleLogin = () => {
    window.location.href = "/auth/google";
  };

  return (
    <div className="welcome-page">
      <h1>Adaptive Planner</h1>

      <p>
        Плануй навчання, відпочинок та особисті справи в одному адаптивному
        календарі.
      </p>

      <div className="welcome-actions">
        <Link to="/register">
          <button type="button">Створити акаунт</button>
        </Link>

        <Link to="/login">
          <button type="button">Увійти</button>
        </Link>

        <button type="button" onClick={handleGoogleLogin}>
          Увійти через Google
        </button>
      </div>
    </div>
  );
}