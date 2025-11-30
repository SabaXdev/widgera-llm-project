const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

export interface FieldDefinition {
  name: string;
  type: "string" | "number";
}

export interface StructuredQueryResult {
  result: Record<string, unknown>;
  cached: boolean;
}

export async function registerUser(
  username: string,
  password: string,
  passwordConfirm: string
): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, password_confirm: passwordConfirm }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Registration failed");
  }
}

export async function loginUser(
  username: string,
  password: string
): Promise<{ token: string }> {
  const form = new URLSearchParams();
  form.set("username", username);
  form.set("password", password);

  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Login failed");
  }

  const data = (await res.json()) as { access_token: string };
  return { token: data.access_token };
}

export async function uploadImage(file: File, token: string): Promise<string> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE_URL}/api/upload-image`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: form,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Image upload failed");
  }

  const data = (await res.json()) as { image_id: string };
  return data.image_id;
}

export async function runStructuredQuery(
  prompt: string,
  fields: FieldDefinition[],
  token: string,
  imageId?: string | null
): Promise<StructuredQueryResult> {
  const res = await fetch(`${API_BASE_URL}/api/structured-query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ prompt, fields, image_id: imageId ?? null }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Structured query failed");
  }

  return (await res.json()) as StructuredQueryResult;
}
