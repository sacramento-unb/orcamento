const API_BASE = import.meta.env.VITE_API_URL || "";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || "Não foi possível concluir a operação.");
  }
  return payload;
}

export const api = {
  summary: (month) => request(`/api/summary?month=${month}`),
  entries: () => request("/api/entries"),
  investments: (year) => request(`/api/investments?year=${year}`),
  exports: () => request("/api/exports"),
  createEntry: (entry) =>
    request("/api/entries", { method: "POST", body: JSON.stringify(entry) }),
  updateEntry: (id, entry) =>
    request(`/api/entries/${id}`, {
      method: "PUT",
      body: JSON.stringify(entry),
    }),
  deleteEntry: (id, month) =>
    request(`/api/entries/${id}?month=${month}`, { method: "DELETE" }),
  export: (month) =>
    request("/api/export", {
      method: "POST",
      body: JSON.stringify({ month }),
    }),
  previewBankFile: async (file) => {
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(`${API_BASE}/api/bank-import/preview`, {
      method: "POST",
      body: form,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || "Não foi possível ler o arquivo bancário.");
    }
    return payload;
  },
  confirmBankImport: (payload) =>
    request("/api/bank-import/confirm", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  downloadUrl: (url) => `${API_BASE}${url}`,
};
