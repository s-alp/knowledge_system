import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import "./index.css";

// React のエントリポイント。StrictMode で副作用の書き方崩れを早めに見つける。
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
