const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || data.error || "Request failed");
  }
  return data;
}

export function getRandomTopic(opts) {
  return request("/api/random-topic", opts);
}

export function getMyProblems(count = 1, opts) {
  return request(`/api/my-problems?count=${count}`, opts);
}

export function getCPBite(opts) {
  return request("/api/cp-bites", opts);
}

export function getCPBiteSources() {
  return request("/api/cp-bites/sources");
}

export function getHealth() {
  return request("/api/health");
}

export function sendExistingBiteToTelegram(mode, bite) {
  return request("/api/telegram/send-existing-bite", {
    method: "POST",
    body: JSON.stringify({ mode, bite }),
  });
}

export function syncLeetCodeProblems() {
  return request("/api/problems/sync-leetcode", {
    method: "POST",
  });
}

export function addProblem(url) {
  return request("/api/problems/add", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export function listProblems() {
  return request("/api/problems/list");
}
