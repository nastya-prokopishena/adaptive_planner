export default function LoginButton() {
  const handleLogin = () => {
    window.location.href = "/auth/google";
  };

  return (
    <button type="button" onClick={handleLogin}>
      Увійти через Google
    </button>
  );
}