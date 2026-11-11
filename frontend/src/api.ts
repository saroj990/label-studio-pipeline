const TOKEN_KEY = "amp_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export type User = { id: number; email: string };
export type Project = {
  id: number;
  name: string;
  class_a: string;
  class_b: string;
  label_studio_project_id: number | null;
};
export type Task = {
  id: number;
  image_url: string;
  filename: string | null;
  label: string | null;
};

export type TrainProgressEvent = {
  stage: string;
  message?: string;
  epoch?: number;
  total_epochs?: number;
  loss?: number;
  training_accuracy?: number;
  run_id?: number;
  model_filename?: string;
  model_path?: string;
  metrics?: Record<string, unknown>;
};

export const api = {
  register: (email: string, password: string) =>
    request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  login: async (email: string, password: string) => {
    const data = await request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setToken(data.access_token);
  },
  me: () => request<User>("/auth/me"),
  projects: () => request<Project[]>("/projects"),
  createProject: (body: {
    name: string;
    class_a: string;
    class_b: string;
  }) =>
    request<Project>("/projects", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  tasks: (projectId: number) =>
    request<Task[]>(`/projects/${projectId}/tasks`),
  /** Use the same field name repeatedly so FastAPI receives a list of files. */
  upload: (projectId: number, files: FileList | File[]) => {
    const form = new FormData();
    Array.from(files).forEach((f) => form.append("files", f));
    return request<{ uploaded: string[]; count: number }>(
      `/projects/${projectId}/upload`,
      { method: "POST", body: form },
    );
  },
  label: (projectId: number, taskId: number, choice: string) =>
    request(`/projects/${projectId}/tasks/${taskId}/label`, {
      method: "POST",
      body: JSON.stringify({ choice }),
    }),
  train: (projectId: number) =>
    request<{
      run_id: number;
      status: string;
      metrics?: Record<string, unknown>;
      model_filename?: string;
      model_path?: string;
    }>(`/projects/${projectId}/train`, { method: "POST" }),

  trainStream: async (
    projectId: number,
    onEvent: (event: TrainProgressEvent) => void,
  ) => {
    const token = getToken();
    const response = await fetch(`/projects/${projectId}/train/stream`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const body = await response.json();
        detail = body.detail ?? JSON.stringify(body);
      } catch {
        /* ignore */
      }
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    if (!response.body) throw new Error("No response body");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";
      for (const part of parts) {
        const line = part.split("\n").find((l) => l.startsWith("data: "));
        if (!line) continue;
        const event = JSON.parse(line.slice(6)) as TrainProgressEvent;
        onEvent(event);
        if (event.stage === "error") {
          throw new Error(event.message ?? "Training failed");
        }
      }
    }
  },
  labelStudioUrl: (projectId: number) =>
    request<{ url: string }>(`/projects/${projectId}/label-studio-url`),
  predict: async (projectId: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<{ prediction: string; scores: Record<string, number> }>(
      `/projects/${projectId}/predict`,
      { method: "POST", body: form },
    );
  },
  downloadModelUrl: (projectId: number) => `/projects/${projectId}/models/latest`,

  saveModel: (projectId: number, runId?: number) =>
    request<{
      run_id: number;
      model_filename: string;
      model_path: string;
      saved: boolean;
    }>(`/projects/${projectId}/models/save`, {
      method: "POST",
      body: JSON.stringify(runId != null ? { run_id: runId } : {}),
    }),

  activeModel: (projectId: number) =>
    request<{
      run_id: number;
      model_filename: string;
      model_path: string;
      saved: boolean;
    } | null>(`/projects/${projectId}/models/active`),
};

/** Route gallery images through the Vite proxy when possible. */
export function taskImageSrc(imageUrl: string): string {
  try {
    const parsed = new URL(imageUrl);
    if (parsed.pathname.startsWith("/api/media/")) {
      return `${parsed.pathname}${parsed.search}`;
    }
  } catch {
    /* relative or invalid */
  }
  if (imageUrl.startsWith("/api/media/")) return imageUrl;
  return imageUrl;
}
