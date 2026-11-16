import { defineConfig, devices } from "@playwright/test";

// End-to-end tests start the real FastAPI backend (SQLite, in-process pub/sub) and the Next.js app.
const python = process.env.PYTHON ?? "python";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `${python} -m uvicorn app.main:app --port 8000`,
      cwd: "../backend",
      url: "http://localhost:8000/health",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        DATABASE_URL: "sqlite+aiosqlite:///./e2e.db",
        BCRYPT_ROUNDS: "4",
        SIMULATOR_STEP_SECONDS: "0.3",
        WAREHOUSE_DIR: "./e2e-warehouse",
      },
    },
    {
      command: "npm run start",
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
