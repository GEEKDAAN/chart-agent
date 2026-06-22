import assert from "node:assert/strict";
import test from "node:test";

import { checkBackendHealth, runtimeHealthStatus } from "../src/health.js";

test("reports runtime ok when FastAPI health endpoint is reachable", async () => {
  const health = await runtimeHealthStatus("http://backend.test", {
    fetchImpl: async (input) => {
      assert.equal(String(input), "http://backend.test/health");
      return Response.json({ status: "ok" }, { status: 200 });
    }
  });

  assert.equal(health.status, "ok");
  assert.equal(health.backend.reachable, true);
  assert.equal(health.backend.statusCode, 200);
});

test("reports runtime degraded when FastAPI health endpoint returns an error", async () => {
  const health = await runtimeHealthStatus("http://backend.test/", {
    fetchImpl: async (input) => {
      assert.equal(String(input), "http://backend.test/health");
      return new Response("failed", { status: 500 });
    }
  });

  assert.equal(health.status, "degraded");
  assert.equal(health.backend.reachable, false);
  assert.equal(health.backend.status, "unreachable");
  assert.equal(health.backend.statusCode, 500);
});

test("reports backend unreachable when health request throws", async () => {
  const health = await checkBackendHealth("http://backend.test", {
    fetchImpl: async () => {
      throw new Error("connection refused");
    }
  });

  assert.equal(health.reachable, false);
  assert.equal(health.status, "unreachable");
  assert.equal(health.error, "connection refused");
});
