import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, Project } from "../api";

export default function TestPage() {
  const { projectId } = useParams();
  const id = Number(projectId);
  const [project, setProject] = useState<Project | null>(null);
  const [result, setResult] = useState<{
    prediction: string;
    scores: Record<string, number>;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.projects().then((list) => {
      setProject(list.find((p) => p.id === id) ?? null);
    });
  }, [id]);

  async function onFile(file: File | undefined) {
    if (!file) return;
    setError(null);
    setResult(null);
    try {
      setResult(await api.predict(id, file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Predict failed");
    }
  }

  return (
    <div className="page narrow">
      <Link to={`/projects/${id}`}>← Workspace</Link>
      <h1>Test model</h1>
      {project && (
        <p className="muted">
          {project.name} · classes: {project.class_a}, {project.class_b}
        </p>
      )}

      <label className="card file-btn">
        Upload image to classify
        <input
          type="file"
          accept="image/*"
          hidden
          onChange={(e) => onFile(e.target.files?.[0])}
        />
      </label>

      {error && <p className="error">{error}</p>}

      {result && (
        <div className="card">
          <h2>Prediction: {result.prediction}</h2>
          <ul>
            {Object.entries(result.scores).map(([name, score]) => (
              <li key={name}>
                {name}: {(score * 100).toFixed(1)}%
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
