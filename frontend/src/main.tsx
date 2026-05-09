import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";

import App from "./App";
import "./styles/globals.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: "hsl(0 0% 100%)",
            border: "3px solid hsl(0 0% 10%)",
            borderRadius: "0",
            color: "hsl(0 0% 10%)",
            boxShadow: "4px 4px 0 hsl(0 0% 10%)",
            fontFamily: "Space Grotesk, sans-serif",
          },
        }}
      />
    </QueryClientProvider>
  </React.StrictMode>,
);
