import { describe, it, expect, vi, beforeEach } from "vitest";

// ---------------------------------------------------------------------------
// Mocks — must be defined before importing the module under test
// ---------------------------------------------------------------------------

const mockRedirect = vi.fn();
const mockNext = vi.fn();

vi.mock("next/server", () => ({
  NextResponse: {
    redirect: (...args: unknown[]) => {
      mockRedirect(...args);
      return { type: "redirect" };
    },
    next: () => {
      mockNext();
      return { type: "next" };
    },
  },
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createMockRequest(pathname: string, hasSession = false) {
  return {
    nextUrl: new URL(`http://localhost:3000${pathname}`),
    url: "http://localhost:3000",
    cookies: {
      get: (name: string) =>
        name === "has_session" && hasSession ? { value: "1" } : undefined,
    },
  } as any;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("middleware", () => {
  let middleware: (request: any) => any;

  beforeEach(async () => {
    vi.clearAllMocks();
    const mod = await import("@/middleware");
    middleware = mod.middleware;
  });

  it("redirects unauthenticated user on protected route to /login with callbackUrl", () => {
    const request = createMockRequest("/home", false);

    middleware(request);

    expect(mockRedirect).toHaveBeenCalledTimes(1);
    const redirectUrl = mockRedirect.mock.calls[0][0] as URL;
    expect(redirectUrl.pathname).toBe("/login");
    expect(redirectUrl.searchParams.get("callbackUrl")).toBe("/home");
    expect(mockNext).not.toHaveBeenCalled();
  });

  it("redirects authenticated user on auth route to /home", () => {
    const request = createMockRequest("/login", true);

    middleware(request);

    expect(mockRedirect).toHaveBeenCalledTimes(1);
    const redirectUrl = mockRedirect.mock.calls[0][0] as URL;
    expect(redirectUrl.pathname).toBe("/home");
    expect(mockNext).not.toHaveBeenCalled();
  });

  it("does NOT redirect authenticated user on /login-callback (BUG-F02 fix)", () => {
    // "/login-callback" should NOT match "/login" auth route since
    // the check is pathname === route || pathname.startsWith(route + "/")
    // "/login-callback" !== "/login" and does NOT start with "/login/"
    const request = createMockRequest("/login-callback", true);

    middleware(request);

    expect(mockNext).toHaveBeenCalledTimes(1);
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it("allows unauthenticated users through public routes", () => {
    const request = createMockRequest("/", false);

    middleware(request);

    expect(mockNext).toHaveBeenCalledTimes(1);
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it("allows unauthenticated users through /explore", () => {
    const request = createMockRequest("/explore", false);

    middleware(request);

    expect(mockNext).toHaveBeenCalledTimes(1);
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it("allows unauthenticated users through auth routes", () => {
    const request = createMockRequest("/login", false);

    middleware(request);

    expect(mockNext).toHaveBeenCalledTimes(1);
    expect(mockRedirect).not.toHaveBeenCalled();
  });

  it("allows authenticated users through protected routes", () => {
    const request = createMockRequest("/home", true);

    middleware(request);

    expect(mockNext).toHaveBeenCalledTimes(1);
    expect(mockRedirect).not.toHaveBeenCalled();
  });
});
