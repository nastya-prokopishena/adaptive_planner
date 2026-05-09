import { useState } from "react";
import axios from "axios";
import { Link, useNavigate } from "react-router-dom";

export default function Register({ setUser }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const res = await axios.post(
        "/auth/register",
        {
          email,
          password,
        },
        {
          withCredentials: true,
        }
      );

      setUser(res.data);
      navigate("/");
    } catch (err) {
      console.error(err);
      alert("Не вдалося зареєструватися. Можливо, такий email вже існує.");
    }
  };

  const handleGoogleLogin = () => {
    window.location.href = "/auth/google";
  };

  return (
    <div className="auth-container">
      <h2>Реєстрація</h2>

      <form onSubmit={handleSubmit}>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <input
          type="password"
          placeholder="Пароль"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        <button type="submit">Зареєструватися</button>
      </form>

      <button type="button" onClick={handleGoogleLogin}>
        Зареєструватися через Google
      </button>

      <p>
        Вже маєш акаунт? <Link to="/login">Увійти</Link>
      </p>
    </div>
  );
}