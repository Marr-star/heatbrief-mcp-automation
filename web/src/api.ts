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
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body) headers.set("Content-Type", "application/json");
  if (options.method && options.method !== "GET")
    headers.set("X-HeatBrief-CSRF", csrf);
  const response = await fetch("/api" + path, {
    ...options,
    headers,
    credentials: "same-origin",
  });
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({
        message: "The workspace could not complete this request.",
      }));
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
  const response = await fetch(
    "/api/briefings/" + encodeURIComponent(id) + "/pdf",
    { credentials: "same-origin" },
  );
  if (!response.ok)
    throw new Error("The PDF could not be generated. Try again.");
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `heatbrief-${id}.pdf`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
