import { describe, it, expect, vi, beforeEach } from "vitest";

import {
  fetchCurrentUserApi,
  updateUsernameApi,
  updateProfileApi,
  uploadAvatarApi,
  deleteAvatarApi,
  checkUsernameApi,
  fetchUserByUsernameApi,
} from "./users-api";

import type { User, UserProfile } from "@/types";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    patch: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/lib/api-client";

const mockUser: User = {
  id: "550e8400-e29b-41d4-a716-446655440000",
  email: "test@example.com",
  username: "testuser",
  is_active: true,
  is_verified: true,
  is_complete: true,
  can_create_business: true,
  is_staff: false,
  is_superuser: false,
  date_joined: "2026-01-01T00:00:00Z",
  last_login: null,
  profile: {
    first_name: "",
    last_name: "",
    full_name: "",
    display_name: "testuser",
    phone: "",
    avatar_url: null,
    has_avatar: false,
    timezone: "UTC",
    language: "en",
    bio: "",
    country: "",
    city: "",
    tags: [],
    is_public: true,
  },
};

const mockProfile: UserProfile = {
  first_name: "John",
  last_name: "Doe",
  full_name: "John Doe",
  display_name: "johndoe",
  phone: "+1234567890",
  avatar_url: null,
  has_avatar: false,
  timezone: "UTC",
  language: "en",
  bio: "",
  country: "",
  city: "",
  tags: [],
  is_public: true,
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("fetchCurrentUserApi", () => {
  it("calls GET /users/me/ and returns user", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockUser });

    const result = await fetchCurrentUserApi();

    expect(apiClient.get).toHaveBeenCalledWith("/users/me/");
    expect(result).toEqual(mockUser);
  });

  it("propagates rejection on failure", async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error("Unauthorized"));

    await expect(fetchCurrentUserApi()).rejects.toThrow("Unauthorized");
  });
});

describe("updateUsernameApi", () => {
  it("calls PATCH /users/me/ with username", async () => {
    const updated = { ...mockUser, username: "newname" };
    vi.mocked(apiClient.patch).mockResolvedValue({ data: updated });

    const result = await updateUsernameApi({ username: "newname" });

    expect(apiClient.patch).toHaveBeenCalledWith("/users/me/", { username: "newname" });
    expect(result.username).toBe("newname");
  });
});

describe("updateProfileApi", () => {
  it("calls PATCH /users/me/profile/ with data", async () => {
    vi.mocked(apiClient.patch).mockResolvedValue({ data: mockProfile });

    const result = await updateProfileApi({ first_name: "John", last_name: "Doe" });

    expect(apiClient.patch).toHaveBeenCalledWith("/users/me/profile/", {
      first_name: "John",
      last_name: "Doe",
    });
    expect(result).toEqual(mockProfile);
  });
});

describe("uploadAvatarApi", () => {
  it("calls POST /users/me/avatar/ with FormData", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockProfile });
    const file = new File(["test"], "avatar.png", { type: "image/png" });

    const result = await uploadAvatarApi(file);

    expect(apiClient.post).toHaveBeenCalledWith(
      "/users/me/avatar/",
      expect.any(FormData),
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    expect(result).toEqual(mockProfile);
  });
});

describe("deleteAvatarApi", () => {
  it("calls DELETE /users/me/avatar/", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({});

    await deleteAvatarApi();

    expect(apiClient.delete).toHaveBeenCalledWith("/users/me/avatar/");
  });
});

describe("checkUsernameApi", () => {
  it("calls GET /users/check-username/ with username param", async () => {
    const response = { available: true, is_current: false };
    vi.mocked(apiClient.get).mockResolvedValue({ data: response });

    const result = await checkUsernameApi("testname");

    expect(apiClient.get).toHaveBeenCalledWith("/users/check-username/", {
      params: { username: "testname" },
    });
    expect(result).toEqual(response);
  });

  it("propagates errors", async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error("Bad Request"));

    await expect(checkUsernameApi("ab")).rejects.toThrow("Bad Request");
  });
});

describe("fetchUserByUsernameApi", () => {
  it("calls GET /users/{username}/ and returns public profile", async () => {
    const response = {
      id: "550e8400-e29b-41d4-a716-446655440000",
      username: "johndoe",
      is_verified: true,
      is_complete: true,
      date_joined: "2026-01-01T00:00:00Z",
      profile: {
        first_name: "John",
        last_name: "Doe",
        full_name: "John Doe",
        display_name: "John Doe",
        avatar_url: null,
        has_avatar: false,
        bio: "Hello world",
        country: "US",
        city: "New York",
        tags: ["developer"],
        is_public: true,
      },
      _permissions: {
        is_own_profile: false,
        can_edit_profile: false,
      },
    };
    vi.mocked(apiClient.get).mockResolvedValue({ data: response });

    const result = await fetchUserByUsernameApi("johndoe");

    expect(apiClient.get).toHaveBeenCalledWith("/users/johndoe/");
    expect(result).toEqual(response);
  });

  it("propagates 404 errors", async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error("Not Found"));

    await expect(fetchUserByUsernameApi("nonexistent")).rejects.toThrow("Not Found");
  });
});
