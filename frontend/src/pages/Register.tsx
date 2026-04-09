import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      await register(email, password);
      nav("/");
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "Ошибка регистрации");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <h1>Регистрация</h1>
      <form onSubmit={onSubmit} className="form">
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </label>
        <label>
          Пароль (мин. 8 символов)
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
          />
        </label>
        {err ? <p className="error">{err}</p> : null}
        <button type="submit" disabled={busy}>
          {busy ? "…" : "Создать аккаунт"}
        </button>
      </form>
      <p>
        Уже есть аккаунт? <Link to="/login">Вход</Link>
      </p>
    </div>
  );
}
