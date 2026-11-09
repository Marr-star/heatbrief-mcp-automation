let csrf = "";
export function setCsrf(value: string) {
  csrf = value;
}
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public details?: { field: string; message: string }[],
  ) {
    super(message);
  }
}
// The workspace keeps sessions in memory, so a server restart invalidates them.
// Quietly start a fresh session instead of asking the person to reload the page.
async function renewSession() {
  try {
    const response = await fetch("/api/bootstrap", {
      credentials: "same-origin",
    });
    if (!response.ok) return false;
    const data = (await response.json()) as { csrf?: string };
    if (!data.csrf) return false;
    csrf = data.csrf;
    return true;
  } catch {
    return false;
  }
}
async function send(path: string, init: RequestInit) {
  try {
    return await fetch(path, { ...init, credentials: "same-origin" });
  } catch {
    throw new ApiError(
      "Can't reach the HeatBrief workspace. Check that it is still running, then try again.",
      0,
    );
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
  retried = false,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body) headers.set("Content-Type", "application/json");
  if (options.method && options.method !== "GET")
    headers.set("X-HeatBrief-CSRF", csrf);
  const response = await send("/api" + path, { ...options, headers });
  if (!response.ok) {
    const error = await response.json().catch(() => ({
      message: "The workspace could not complete this request.",
    }));
    if (
      !retried &&
      response.status === 401 &&
      error.error === "session_expired" &&
      (await renewSession())
    ) {
      return api<T>(path, options, true);
    }
    throw new ApiError(
      error.message || "Request failed",
      response.status,
      error.details,
    );
  }
  return response.json() as Promise<T>;
}
export function downloadText(
  content: string,
  filename: string,
  type = "text/markdown;charset=utf-8",
) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export async function downloadPdf(id: string) {
  const url = "/api/briefings/" + encodeURIComponent(id) + "/pdf";
  let response = await send(url, {});
  if (response.status === 401 && (await renewSession()))
    response = await send(url, {});
  if (!response.ok)
    throw new Error("The PDF could not be generated. Try again.");
  const blobUrl = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = blobUrl;
  anchor.download = `heatbrief-${id}.pdf`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
}
