import "dotenv/config";
import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { apiRouter, healthPayload } from "./src/api/routes.js";

async function startServer() {
  const app = express();
  const PORT = Number(process.env.PORT || 3000);

  app.use(express.json({ limit: "1mb" }));
  app.use("/api", apiRouter);

  // /api/healthと同じ実状態を返す。固定ready値を持たない。
  app.get("/health", (_req, res) => res.json(healthPayload()));

  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({ server: { middlewareMode: true }, appType: "spa" });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (_req, res) => res.sendFile(path.join(distPath, "index.html")));
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`MINIDORA server listening on ${PORT}`);
  });
}

startServer().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
