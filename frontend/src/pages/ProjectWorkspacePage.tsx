import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, Project, Task, getToken } from "../api";

export default function ProjectWorkspacePage() {
  const { projectId } = useParams();
  const id = Number(projectId);
  const [project, setProject] = useState<Project | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [training, setTraining] = useState(false);

  const refresh = useCallback(async () => {
    const list = await api.projects();
    const p = list.find((x) => x.id === id);
    if (!p) throw new Error("Project not found");
    setProject(p);
    setTasks(await api.tasks(id));
  }, [id]);

  useEffect(() => {
    refresh().catch((e) => setError(String(e)));
  }, [refresh]);

  async function onUpload(files: FileList | null) {
    if (!files?.length) return;
    setError(null);
    try {
      const res = await api.upload(id, files);
      setMessage(`Uploaded ${res.count} file(s)`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  }

  async function onLabel(taskId: number, choice: string) {
    setError(null);
    try {
      await api.label(id, taskId, choice);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Label failed");
    }
  }

  async function onTrain() {
    setTraining(true);
    setError(null);
    setMessage(null);
    try {
      const res = await api.train(id);
      const device = res.metrics?.device ?? "unknown";
      setMessage(
        `Training done on ${device}. Accuracy: ${res.metrics?.training_accuracy}%`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Train failed");
    } finally {
      setTraining(false);
    }
  }

  async function openLabelStudio() {
    const { url } = await api.labelStudioUrl(id);
    window.open(url, "_blank");
  }

  async function downloadModel() {
    const token = getToken();
    const res = await fetch(api.downloadModelUrl(id), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error(await res.text());
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `project_${id}_model.pth`;
    a.click();
  }

  if (!project) return <div className="page">Loading…</div>;

  const counts = tasks.reduce(
    (acc, t) => {
      if (t.label === project.class_a) acc.a += 1;
      if (t.label === project.class_b) acc.b += 1;
      if (!t.label) acc.unlabeled += 1;
      return acc;
    },
    { a: 0, b: 0, unlabeled: 0 },
  );

  return (
    <div className="page">
      <header className="row">
        <div>
          <Link to="/">← Projects</Link>
          <h1>{project.name}</h1>
          <p className="muted">
            {project.class_a} / {project.class_b} · {counts.a + counts.b} labeled
          </p>
        </div>
        <Link to={`/projects/${id}/test`}>Test model</Link>
      </header>

      <div className="toolbar card row">
        <label className="file-btn">
          Upload images
          <input
            type="file"
            accept="image/*"
            multiple
            hidden
            onChange={(e) => onUpload(e.target.files)}
          />
        </label>
        <button type="button" className="secondary" onClick={openLabelStudio}>
          Open in Label Studio
        </button>
        <button type="button" onClick={refresh}>
          Refresh tasks
        </button>
        <button type="button" onClick={onTrain} disabled={training}>
          {training ? "Training…" : "Train model"}
        </button>
        <button type="button" className="secondary" onClick={() => downloadModel().catch(setError)}>
          Download model
        </button>
      </div>

      {message && <p className="success">{message}</p>}
      {error && <p className="error">{error}</p>}

      <div className="grid">
        {tasks.map((task) => (
          <article key={task.id} className="card thumb">
            {task.image_url ? (
              <img src={task.image_url} alt={task.filename ?? ""} />
            ) : (
              <div className="placeholder">No preview</div>
            )}
            <p>{task.filename ?? `Task ${task.id}`}</p>
            <p className="muted">{task.label ?? "Unlabeled"}</p>
            <div className="row">
              <button type="button" onClick={() => onLabel(task.id, project.class_a)}>
                {project.class_a}
              </button>
              <button
                type="button"
                className="secondary"
                onClick={() => onLabel(task.id, project.class_b)}
              >
                {project.class_b}
              </button>
            </div>
          </article>
        ))}
      </div>
      {!tasks.length && <p className="muted">Upload images to create labeling tasks.</p>}
    </div>
  );
}
