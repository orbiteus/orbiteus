import { describe, expect, it } from "vitest";
import { NextRequest } from "next/server";
import { proxy } from "./proxy";

function req(path: string, cookie?: string) {
  const url = new URL(path, "https://demo.orbiteus.com");
  const headers = cookie ? { cookie } : undefined;
  return new NextRequest(url, { headers });
}

describe("proxy auth gate", () => {
  it("redirects unauthenticated / to /welcome", () => {
    const res = proxy(req("/"));
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("https://demo.orbiteus.com/welcome");
  });

  it("redirects unauthenticated app routes to /login with next", () => {
    const res = proxy(req("/base/user"));
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("https://demo.orbiteus.com/login?next=%2Fbase%2Fuser");
  });

  it("allows /welcome without a cookie", () => {
    const res = proxy(req("/welcome"));
    expect(res.status).toBe(200);
  });
});
