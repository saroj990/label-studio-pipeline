import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import UploadDropzone from "../components/UploadDropzone";
import { api, Project, Task, getToken, taskImageSrc } from "../api";

export default function ProjectWorkspacePage() {
  const { projectId } = useParams();
  const id = Number(projectId);
  const [project, setProject] = useState<Project | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [training, setTraining] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [filter, setFilter] = useState<"all" | "unlabeled" | "labeled">("all");
  const [labelingId, setLabelingId] = useState<number | null>(null);

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

  async function onUpload(files: File[]) {
    setError(null);
    setUploading(true);
    try {
      const dt = new DataTransfer();
      files.forEach((f) => dt.items.add(f));
      await api.upload(id, dt.files);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function onLabel(taskId: number, choice: string) {
    setError(null);
    setLabelingId(taskId);
    try {
      await api.label(id, taskId, choice);
      setTasks((prev) =>
        prev.map((t) => (t.id === taskId ? { ...t, label: choice } : t)),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Label failed");
      await refresh();
    } finally {
      setLabelingId(null);
    }
  }

  async function onTrain() {
    setTraining(true);
    setError(null);
    try {
      await api.train(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Train failed");
    } finally {
      setTraining(false);
    }
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

  const sortedTasks = useMemo(() => {
    const copy = [...tasks];
    copy.sort((a, b) => {
      const au = a.label ? 1 : 0;
      const bu = b.label ? 1 : 0;
      if (au !== bu) return au - bu;
      return b.id - a.id;
    });
    if (filter === "unlabeled") return copy.filter((t) => !t.label);
    if (filter === "labeled") return copy.filter((t) => t.label);
    return copy;
  }, [tasks, filter]);

  if (!project) return <div className="page">Loading…</div>;

  const counts = tasks.reduce(
    (acc, t) => {
      if (t.label === project.class_a) acc.a += 1;
      else if (t.label === project.class_b) acc.b += 1;
      else acc.unlabeled += 1;
      return acc;
    },
    { a: 0, b: 0, unlabeled: 0 },
  );

  const canTrain = counts.a >= 2 && counts.b >= 2;

  return (
    <div className="page workspace">
      <header className="workspace-header">
        <div>
          <Link to="/">← Projects</Link>
          <h1>{project.name}</h1>
          <p className="muted">
            {counts.unlabeled} to label · {project.class_a}: {counts.a} ·{" "}
            {project.class_b}: {counts.b}
          </p>
        </div>
        <Link to={`/projects/${id}/test`} className="text-btn">
          Test model →
        </Link>
      </header>

      <section className="flow-section">
        <h2 className="flow-step">1. Upload photos</h2>
        <UploadDropzone disabled={uploading} onFiles={onUpload} />
      </section>

      <section className="flow-section">
        <div className="gallery-head">
          <h2 className="flow-step">2. Label in gallery</h2>
          <div className="filter-tabs" role="tablist">
            {(["all", "unlabeled", "labeled"] as const).map((key) => (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={filter === key}
                className={filter === key ? "tab active" : "tab"}
                onClick={() => setFilter(key)}
              >
                {key === "all" && `All (${tasks.length})`}
                {key === "unlabeled" && `Need label (${counts.unlabeled})`}
                {key === "labeled" && `Done (${counts.a + counts.b})`}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="error">{error}</p>}

        {!tasks.length && !uploading && (
          <p className="muted empty-gallery">
            No images yet. Upload above — they will appear here for labeling.
          </p>
        )}

        <div className="grid">
          {sortedTasks.map((task) => {
            const labeledA = task.label === project.class_a;
            const labeledB = task.label === project.class_b;
            return (
              <article
                key={task.id}
                className={`card thumb ${labeledA ? "thumb-a" : ""} ${labeledB ? "thumb-b" : ""}`}
              >
                {task.image_url ? (
                  <img
                    src={taskImageSrc(task.image_url)}
                    alt={task.filename ?? ""}
                    loading="lazy"
                  />
                ) : (
                  <div className="placeholder">No preview</div>
                )}
                <p className="thumb-name">{task.filename ?? `Image ${task.id}`}</p>
                <p className="label-badge">
                  {task.label ?? "Pick a label"}
                </p>
                <div className="label-actions">
                  <button
                    type="button"
                    className={labeledA ? "label-btn selected-a" : "label-btn"}
                    disabled={labelingId === task.id}
                    onClick={() => onLabel(task.id, project.class_a)}
                  >
                    {project.class_a}
                  </button>
                  <button
                    type="button"
                    className={labeledB ? "label-btn selected-b" : "label-btn secondary"}
                    disabled={labelingId === task.id}
                    onClick={() => onLabel(task.id, project.class_b)}
                  >
                    {project.class_b}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <details className="card advanced">
        <summary>Train &amp; export</summary>
        <p className="muted">
          Need at least 2 images per class.{" "}
          {!canTrain && "(not enough labeled images yet)"}
        </p>
        <div className="row">
          <button type="button" onClick={onTrain} disabled={training || !canTrain}>
            {training ? "Training…" : "Train model"}
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => downloadModel().catch((e) => setError(String(e)))}
          >
            Download model
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() =>
              api.labelStudioUrl(id).then(({ url }) => window.open(url, "_blank"))
            }
          >
            Open in Label Studio
          </button>
        </div>
      </details>
    </div>
  );
}
