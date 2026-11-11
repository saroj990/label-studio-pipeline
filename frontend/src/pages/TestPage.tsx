import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import UploadDropzone from "../components/UploadDropzone";
import { api, Project } from "../api";

type TestLocationState = {
  justSaved?: boolean;
  modelFilename?: string;
};

export default function TestPage() {
  const { projectId } = useParams();
  const id = Number(projectId);
  const location = useLocation();
  const navState = (location.state ?? {}) as TestLocationState;

  const [project, setProject] = useState<Project | null>(null);
  const [modelFilename, setModelFilename] = useState<string | null>(
    navState.modelFilename ?? null,
  );
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [classifying, setClassifying] = useState(false);
  const [result, setResult] = useState<{
    prediction: string;
    scores: Record<string, number>;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.projects().then((list) => {
      setProject(list.find((p) => p.id === id) ?? null);
    });
    api.activeModel(id).then((active) => {
      if (active?.model_filename) setModelFilename(active.model_filename);
    }).catch(() => {
      /* no saved model yet */
    });
  }, [id]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  async function onFile(files: File[]) {
    const file = files[0];
    if (!file) return;
    setError(null);
    setResult(null);
    setClassifying(true);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(file));
    try {
      setResult(await api.predict(id, file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Classify failed");
    } finally {
      setClassifying(false);
    }
  }

  return (
    <div className="page workspace">
      <Link to={`/projects/${id}`}>← Workspace</Link>
      <h1>4. Test your model</h1>
      {project && (
        <p className="muted">
          {project.name} · classes: <strong>{project.class_a}</strong>,{" "}
          <strong>{project.class_b}</strong>
        </p>
      )}

      {navState.justSaved && (
        <div className="train-result">
          Model saved{modelFilename ? `: ${modelFilename}` : ""}. Upload a new
          photo below to see how it classifies.
        </div>
      )}

      {modelFilename && !navState.justSaved && (
        <p className="muted">
          Using saved model: <code>{modelFilename}</code>
        </p>
      )}

      {!modelFilename && (
        <p className="error">
          No saved model yet. Train and click <strong>Save model &amp; test</strong>{" "}
          in the workspace first.
        </p>
      )}

      <section className="flow-section">
        <UploadDropzone
          multiple={false}
          disabled={classifying || !modelFilename}
          title="Upload one photo to classify"
          hint="This image is only used for testing — not added to training data."
          onFiles={onFile}
        />
      </section>

      {previewUrl && (
        <div className="card test-preview">
          <img src={previewUrl} alt="Upload preview" />
        </div>
      )}

      {classifying && <p className="muted">Classifying…</p>}
      {error && <p className="error">{error}</p>}

      {result && project && (
        <div
          className={`card predict-result ${
            result.prediction === project.class_a ? "predict-a" : "predict-b"
          }`}
        >
          <p className="predict-label">Classification</p>
          <h2 className="predict-value">{result.prediction}</h2>
          <ul className="predict-scores">
            {[project.class_a, project.class_b].map((name) => (
              <li key={name}>
                <span>{name}</span>
                <span>{((result.scores[name] ?? 0) * 100).toFixed(1)}%</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
