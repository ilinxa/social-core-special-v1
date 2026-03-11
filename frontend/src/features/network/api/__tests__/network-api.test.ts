import { describe, it, expect, vi, beforeEach } from "vitest";

import {
  createFollowApi,
  unfollowApi,
  fetchFollowingApi,
  createConnectionRequestApi,
  disconnectUserApi,
  fetchConnectionsApi,
  fetchBusinessFollowersApi,
  removeBusinessFollowerApi,
  fetchBusinessConnectionsApi,
  createBusinessConnectionApi,
  disconnectBusinessConnectionApi,
  fetchNetworkStatsApi,
  fetchBusinessNetworkStatsApi,
} from "../network-api";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/lib/api-client";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedDelete = vi.mocked(apiClient.delete);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Follow API", () => {
  it("createFollowApi posts to /network/follow/", async () => {
    const result = { transaction_id: "txn-1", status: "pending" };
    mockedPost.mockResolvedValue({ data: result });

    const response = await createFollowApi({
      followee_type: "business",
      followee_id: "biz-1",
    });

    expect(mockedPost).toHaveBeenCalledWith("/network/follow/", {
      followee_type: "business",
      followee_id: "biz-1",
    });
    expect(response).toEqual(result);
  });

  it("unfollowApi deletes /network/follow/{id}/", async () => {
    mockedDelete.mockResolvedValue({});
    await unfollowApi("follow-1");
    expect(mockedDelete).toHaveBeenCalledWith("/network/follow/follow-1/");
  });

  it("fetchFollowingApi gets /network/following/", async () => {
    const data = { count: 1, results: [{ id: "f-1" }] };
    mockedGet.mockResolvedValue({ data });

    const response = await fetchFollowingApi({ type: "business" });

    expect(mockedGet).toHaveBeenCalledWith("/network/following/", {
      params: { type: "business" },
    });
    expect(response).toEqual(data);
  });
});

describe("User Connections API", () => {
  it("createConnectionRequestApi posts to /network/connections/request/", async () => {
    const result = { transaction_id: "txn-2", status: "pending" };
    mockedPost.mockResolvedValue({ data: result });

    const response = await createConnectionRequestApi({
      target_user_id: "user-1",
      note: "Hello!",
    });

    expect(mockedPost).toHaveBeenCalledWith("/network/connections/request/", {
      target_user_id: "user-1",
      note: "Hello!",
    });
    expect(response).toEqual(result);
  });

  it("disconnectUserApi deletes /network/connections/{id}/", async () => {
    mockedDelete.mockResolvedValue({});
    await disconnectUserApi("conn-1");
    expect(mockedDelete).toHaveBeenCalledWith("/network/connections/conn-1/");
  });

  it("fetchConnectionsApi gets /network/connections/", async () => {
    const data = { count: 2, results: [{ id: "c-1" }, { id: "c-2" }] };
    mockedGet.mockResolvedValue({ data });

    const response = await fetchConnectionsApi({ status: "active" });

    expect(mockedGet).toHaveBeenCalledWith("/network/connections/", {
      params: { status: "active" },
    });
    expect(response).toEqual(data);
  });
});

describe("Business Network API", () => {
  it("fetchBusinessFollowersApi gets /network/business/{slug}/followers/", async () => {
    const data = { count: 3, results: [] };
    mockedGet.mockResolvedValue({ data });

    const response = await fetchBusinessFollowersApi("my-biz");

    expect(mockedGet).toHaveBeenCalledWith(
      "/network/business/my-biz/followers/",
      { params: undefined },
    );
    expect(response).toEqual(data);
  });

  it("removeBusinessFollowerApi deletes /network/business/{slug}/followers/{id}/", async () => {
    mockedDelete.mockResolvedValue({});
    await removeBusinessFollowerApi("my-biz", "follow-1");
    expect(mockedDelete).toHaveBeenCalledWith(
      "/network/business/my-biz/followers/follow-1/",
    );
  });

  it("fetchBusinessConnectionsApi gets /network/business/{slug}/connections/", async () => {
    const data = { count: 0, results: [] };
    mockedGet.mockResolvedValue({ data });

    const response = await fetchBusinessConnectionsApi("my-biz");

    expect(mockedGet).toHaveBeenCalledWith(
      "/network/business/my-biz/connections/",
      { params: undefined },
    );
    expect(response).toEqual(data);
  });

  it("createBusinessConnectionApi posts to /network/business/{slug}/connections/request/", async () => {
    const result = { transaction_id: "txn-3", status: "pending" };
    mockedPost.mockResolvedValue({ data: result });

    const response = await createBusinessConnectionApi("my-biz", {
      target_account_type: "business",
      target_account_id: "other-biz",
    });

    expect(mockedPost).toHaveBeenCalledWith(
      "/network/business/my-biz/connections/request/",
      {
        target_account_type: "business",
        target_account_id: "other-biz",
      },
    );
    expect(response).toEqual(result);
  });

  it("disconnectBusinessConnectionApi deletes /network/business/{slug}/connections/{id}/", async () => {
    mockedDelete.mockResolvedValue({});
    await disconnectBusinessConnectionApi("my-biz", "conn-1");
    expect(mockedDelete).toHaveBeenCalledWith(
      "/network/business/my-biz/connections/conn-1/",
    );
  });
});

describe("Stats API", () => {
  it("fetchNetworkStatsApi gets /network/stats/", async () => {
    const data = { followers_count: 5, following_count: 3, connections_count: 2 };
    mockedGet.mockResolvedValue({ data });

    const response = await fetchNetworkStatsApi();

    expect(mockedGet).toHaveBeenCalledWith("/network/stats/");
    expect(response).toEqual(data);
  });

  it("fetchBusinessNetworkStatsApi gets /network/business/{slug}/stats/", async () => {
    const data = { followers_count: 10, following_count: 0, connections_count: 4 };
    mockedGet.mockResolvedValue({ data });

    const response = await fetchBusinessNetworkStatsApi("my-biz");

    expect(mockedGet).toHaveBeenCalledWith("/network/business/my-biz/stats/");
    expect(response).toEqual(data);
  });
});
