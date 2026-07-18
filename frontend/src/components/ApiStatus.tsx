import { useEffect, useState } from "react";

import { fetchHealth } from "../api/health";

type ApiState = "checking" | "online" | "offline";

export function ApiStatus() {
  const [state, setState] = useState<ApiState>("checking");

  useEffect(() => {
    const controller = new AbortController();
    void fetchHealth(controller.signal)
      .then(() => setState("online"))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setState("offline");
      });

    return () => controller.abort();
  }, []);

  if (state === "checking") {
    return (
      <span className="inline-flex items-center gap-2 text-sm text-gray-500">
        <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
        Checking API
      </span>
    );
  }

  const online = state === "online";
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
        online ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
      }`}
    >
      {online ? "API online" : "API offline"}
    </span>
  );
}
