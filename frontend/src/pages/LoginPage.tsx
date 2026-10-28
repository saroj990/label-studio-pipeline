import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";

export default function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "register") {
        await api.register(email, password);
        await api.login(email, password);
      } else {
        await api.login(email, password);
      }
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page narrow">
      <h1>Acceptance Model Pipeline</h1>
      <p className="muted">Host training with Label Studio · MPS/CUDA when available</p>
      <form className="card" onSubmit={onSubmit}>
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={loading}>
          {loading ? "…" : mode === "login" ? "Log in" : "Register"}
        </button>
      </form>
      <p>
        {mode === "login" ? "No account?" : "Have an account?"}{" "}
        <button
          type="button"
          className="link"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "Register" : "Log in"}
        </button>
      </p>
      <p>
        <Link to="/">Skip to projects</Link> (requires login)
      </p>
    </div>
  );
}
