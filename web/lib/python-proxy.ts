const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000";
const PYTHON_API_SECRET = process.env.PYTHON_API_SECRET || "";

export async function pythonGet(path: string) {
  const res = await fetch(`${PYTHON_API_URL}${path}`, {
    headers: { "X-Internal-Secret": PYTHON_API_SECRET },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Python API error: ${res.status}`);
  return res.json();
}

export async function pythonPost(path: string, body?: unknown) {
  const res = await fetch(`${PYTHON_API_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Internal-Secret": PYTHON_API_SECRET,
    },
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Python API error: ${res.status}`);
  return res.json();
}
