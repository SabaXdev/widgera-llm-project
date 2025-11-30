import React, { useEffect, useState } from "react";
import {
  FieldDefinition,
  StructuredQueryResult,
  loginUser,
  registerUser,
  runStructuredQuery,
  uploadImage,
} from "./api";

type AuthMode = "login" | "register";

export const App: React.FC = () => {
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [token, setToken] = useState<string | null>(null);

  const [prompt, setPrompt] = useState("");
  const [fields, setFields] = useState<FieldDefinition[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadedImageId, setUploadedImageId] = useState<string | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<StructuredQueryResult | null>(null);

  useEffect(() => {
    const storedToken = window.localStorage.getItem("authToken");
    if (storedToken) {
      setToken(storedToken);
    }
  }, []);

  const resetWorkspaceState = () => {
    setPrompt("");
    setFields([]);
    setSelectedFile(null);
    setUploadedImageId(null);
    setResult(null);
    setError(null);
  };

  const resetAuthState = () => {
    setUsername("");
    setPassword("");
    setPasswordConfirm("");
    setAuthMode("login");
  };

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      if (authMode === "register") {
        await registerUser(username, password, passwordConfirm);
        setAuthMode("login");
        setPassword("");
        setPasswordConfirm("");
        return;
      }

      const { token: newToken } = await loginUser(username, password);
      setToken(newToken);
      window.localStorage.setItem("authToken", newToken);
      resetWorkspaceState();
      resetAuthState();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleLogout = () => {
    setToken(null);
    window.localStorage.removeItem("authToken");
    resetWorkspaceState();
    resetAuthState();
  };

  const updateFieldName = (index: number, name: string) => {
    setFields((prev) =>
      prev.map((f, i) => (i === index ? { ...f, name } : f))
    );
  };

  const updateFieldType = (index: number, type: "string" | "number") => {
    setFields((prev) =>
      prev.map((f, i) => (i === index ? { ...f, type } : f))
    );
  };

  const addField = () => {
    setFields((prev) => [...prev, { name: "", type: "string" }]);
  };

  const removeField = (index: number) => {
    setFields((prev) => prev.filter((_, i) => i !== index));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setSelectedFile(file);
    setUploadedImageId(null);
  };

  const ensureImageUploaded = async (): Promise<string | null> => {
    if (!selectedFile) return null;
    if (!token) throw new Error("You must be logged in to upload images.");
    if (uploadedImageId) return uploadedImageId;
    const imageId = await uploadImage(selectedFile, token);
    setUploadedImageId(imageId);
    return imageId;
  };

  const handleSubmitQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      setError("You must be logged in.");
      return;
    }
    if (!prompt.trim()) {
      setError("Prompt is required.");
      return;
    }
    if (fields.length === 0) {
      setError("Please add at least one field.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const imageId = await ensureImageUploaded();
      const res = await runStructuredQuery(
        prompt,
        fields.filter((f) => f.name.trim().length > 0),
        token,
        imageId
      );
      setResult(res);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="app-shell">
        <div className="card auth-card">
          <h1 className="title">Widgera</h1>
          <p className="subtitle">
            Structured responses from text + images, tailored to your fields.
          </p>

          <div className="tabs">
            <button
              className={authMode === "login" ? "tab active" : "tab"}
              onClick={() => {
                setAuthMode("login");
                setUsername("");
                setPassword("");
                setPasswordConfirm("");
                setError(null);
              }}
            >
              Login
            </button>
            <button
              className={authMode === "register" ? "tab active" : "tab"}
              onClick={() => {
                setAuthMode("register");
                setUsername("");
                setPassword("");
                setPasswordConfirm("");
                setError(null);
              }}
            >
              Register
            </button>
          </div>

          <form onSubmit={handleAuthSubmit} className="form">
            <label className="label">
              Username
              <input
                className="input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </label>

            <label className="label">
              Password
              <input
                type="password"
                className="input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>

            {authMode === "register" && (
              <label className="label">
                Confirm Password
                <input
                  type="password"
                  className="input"
                  value={passwordConfirm}
                  onChange={(e) => setPasswordConfirm(e.target.value)}
                  required
                />
              </label>
            )}

            {error && <div className="error">{error}</div>}

            <button type="submit" className="button primary">
              {authMode === "login" ? "Login" : "Create Account"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1 className="title">Widgera</h1>
          <p className="subtitle">
            Give a prompt, define your structure, and get a typed JSON answer.
          </p>
        </div>
        <button className="button ghost" onClick={handleLogout}>
          Logout
        </button>
      </header>

      <main className="layout">
        <section className="card">
          <h2 className="section-title">Prompt & Image</h2>
          <form onSubmit={handleSubmitQuery} className="column-gap">
            <label className="label">
              Prompt
              <textarea
                className="textarea"
                rows={4}
                placeholder="Describe what you want the model to extract..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
              />
            </label>

            <label className="label">
              Image (optional)
              <input type="file" accept="image/*" onChange={handleFileChange} />
              <span className="hint">
                The image is deduplicated per user using a content hash, so
                re-uploading the same file will reuse the stored copy.
              </span>
            </label>

            <h3 className="section-subtitle">Response Structure</h3>
            <div className="fields-grid">
              {fields.map((field, index) => (
                <div key={index} className="field-row">
                  <input
                    className="input"
                    placeholder="Field name (e.g. BirthYear)"
                    value={field.name}
                    onChange={(e) => updateFieldName(index, e.target.value)}
                  />
                  <select
                    className="select"
                    value={field.type}
                    onChange={(e) =>
                      updateFieldType(index, e.target.value as "string" | "number")
                    }
                  >
                    <option value="string">String</option>
                    <option value="number">Number</option>
                  </select>
                  <button
                    type="button"
                    className="button danger small"
                    onClick={() => removeField(index)}
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>

            <button
              type="button"
              className="button secondary"
              onClick={addField}
            >
              + Add Field
            </button>

            {error && <div className="error">{error}</div>}

            <button
              type="submit"
              className="button primary"
              disabled={loading}
            >
              {loading ? "Running query..." : "Submit"}
            </button>
          </form>
        </section>

        <section className="card">
          <h2 className="section-title">Structured Output</h2>
          {!result && <p className="hint">Run a query to see structured JSON here.</p>}
          {result && (
            <>
              {result.cached && (
                <div className="badge">Loaded from cache for this prompt + image</div>
              )}
              <pre className="result-json">
                {JSON.stringify(result.result, null, 2)}
              </pre>
            </>
          )}
        </section>
      </main>
    </div>
  );
};
