export default function WelcomePage() {
  const handleGoogleLogin = () => {
    window.location.href = "http://127.0.0.1:5000/auth/google";
  };

  return (
    <div style={{ textAlign: "center", marginTop: "100px" }}>
      <h1>Adaptive Planner</h1>
      <p>Плануй свій час розумно</p>

      <button onClick={handleGoogleLogin}>
        Увійти через Google
      </button>
    </div>
  );
}