export default function Profile({ user }) {
  const connectGoogle = () => {
    window.location.href = '/login'; // OAuth endpoint
  };

  return (
    <div className="profile-container">
      <h2>Profile</h2>
      <p>Email: {user?.email}</p>
      <button onClick={connectGoogle}>Connect Google Calendar</button>
    </div>
  );
}