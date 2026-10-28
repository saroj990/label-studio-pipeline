import { DragEvent, useRef, useState } from "react";

type Props = {
  disabled?: boolean;
  onFiles: (files: File[]) => void | Promise<void>;
};

export default function UploadDropzone({ disabled, onFiles }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  async function handleFiles(list: FileList | null) {
    if (!list?.length || disabled) return;
    const images = Array.from(list).filter((f) => f.type.startsWith("image/"));
    if (!images.length) return;
    await onFiles(images);
    if (inputRef.current) inputRef.current.value = "";
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    void handleFiles(e.dataTransfer.files);
  }

  return (
    <div
      className={`dropzone ${dragOver ? "dropzone-active" : ""} ${disabled ? "dropzone-disabled" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
      role="button"
      tabIndex={0}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        multiple
        hidden
        disabled={disabled}
        onChange={(e) => void handleFiles(e.target.files)}
      />
      <p className="dropzone-title">
        {disabled ? "Uploading…" : "Drop images here or click to browse"}
      </p>
      <p className="muted">Select many files at once · JPG, PNG, etc.</p>
    </div>
  );
}
