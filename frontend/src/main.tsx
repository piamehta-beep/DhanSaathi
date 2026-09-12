import React from "react";
import ReactDOM from "react-dom/client";
import "./i18n";
import "./index.css";
import App from "./App";

async function boot() {
  if (import.meta.env.DEV) {
    // axe runs in dev only and reports to the console (brief §12).
    const axe = (await import("@axe-core/react")).default;
    await axe(React, ReactDOM, 1000);
  }
  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
}
boot();
