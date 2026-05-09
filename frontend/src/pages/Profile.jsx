export default function Profile({ user }) {
  const connectGoogle = () => {
    window.location.href = "/auth/google";
  };

  return (
    <div className="profile-container">
      <h2>Профіль</h2>

      <p>
        <strong>Email:</strong> {user?.email || "Невідомий користувач"}
      </p>

      <p>
        <strong>Тип входу:</strong> {user?.auth_provider || "local"}
      </p>

      <button type="button" onClick={connectGoogle}>
        Підключити Google Calendar
      </button>
    </div>
  );
}