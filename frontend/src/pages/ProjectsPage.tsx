import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, Project, setToken } from "../api";

export default function ProjectsPage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [classA, setClassA] = useState("accepted");
  const [classB, setClassB] = useState("rejected");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setProjects(await api.projects());
  }

  useEffect(() => {
    load().catch((e) => setError(String(e)));
  }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.createProject({ name, class_a: classA, class_b: classB });
      setName("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  return (
    <div className="page">
      <header className="row">
        <h1>Projects</h1>
        <button
          type="button"
          className="secondary"
          onClick={() => {
            setToken(null);
            navigate("/login");
          }}
        >
          Log out
        </button>
      </header>

      <form className="card" onSubmit={onCreate}>
        <h2>New project</h2>
        <label>
          Name
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <div className="row">
          <label>
            Class A
            <input value={classA} onChange={(e) => setClassA(e.target.value)} required />
          </label>
          <label>
            Class B
            <input value={classB} onChange={(e) => setClassB(e.target.value)} required />
          </label>
        </div>
        {error && <p className="error">{error}</p>}
        <button type="submit">Create (links Label Studio project)</button>
      </form>

      <ul className="project-list">
        {projects.map((p) => (
          <li key={p.id} className="card">
            <strong>{p.name}</strong>
            <span className="muted">
              {p.class_a} / {p.class_b}
            </span>
            <div className="row">
              <Link to={`/projects/${p.id}`}>Workspace</Link>
              <Link to={`/projects/${p.id}/test`}>Test model</Link>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
