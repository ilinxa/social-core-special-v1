import { describe, it, expect } from "vitest";

import { buildFormDataIfNeeded } from "./form-data-utils";

describe("buildFormDataIfNeeded", () => {
  it("returns the original object when no File values exist", () => {
    const data = { name: "Test", count: 42, active: true };

    const result = buildFormDataIfNeeded(data);

    expect(result).toBe(data);
    expect(result).not.toBeInstanceOf(FormData);
  });

  it("returns FormData when a File value exists", () => {
    const file = new File(["content"], "test.png", { type: "image/png" });
    const data = { name: "Test", avatar: file };

    const result = buildFormDataIfNeeded(data);

    expect(result).toBeInstanceOf(FormData);
  });

  it("appends File instances correctly", () => {
    const file = new File(["content"], "test.png", { type: "image/png" });
    const data = { avatar: file };

    const result = buildFormDataIfNeeded(data) as FormData;

    expect(result.get("avatar")).toBe(file);
  });

  it("converts null to empty string in FormData", () => {
    const file = new File(["content"], "test.png", { type: "image/png" });
    const data = { avatar: file, old_image: null };

    const result = buildFormDataIfNeeded(data) as FormData;

    expect(result.get("old_image")).toBe("");
  });

  it("converts undefined to empty string in FormData", () => {
    const file = new File(["content"], "test.png", { type: "image/png" });
    const data = { avatar: file, missing: undefined };

    const result = buildFormDataIfNeeded(data) as FormData;

    expect(result.get("missing")).toBe("");
  });

  it("JSON.stringifies objects in FormData", () => {
    const file = new File(["content"], "test.png", { type: "image/png" });
    const nested = { key: "value", num: 123 };
    const data = { avatar: file, metadata: nested };

    const result = buildFormDataIfNeeded(data) as FormData;

    expect(result.get("metadata")).toBe(JSON.stringify(nested));
  });

  it("JSON.stringifies arrays in FormData", () => {
    const file = new File(["content"], "test.png", { type: "image/png" });
    const data = { avatar: file, tags: ["a", "b", "c"] };

    const result = buildFormDataIfNeeded(data) as FormData;

    expect(result.get("tags")).toBe(JSON.stringify(["a", "b", "c"]));
  });

  it("converts number primitives to strings in FormData", () => {
    const file = new File(["content"], "test.png", { type: "image/png" });
    const data = { avatar: file, count: 42 };

    const result = buildFormDataIfNeeded(data) as FormData;

    expect(result.get("count")).toBe("42");
  });

  it("converts boolean primitives to strings in FormData", () => {
    const file = new File(["content"], "test.png", { type: "image/png" });
    const data = { avatar: file, active: true };

    const result = buildFormDataIfNeeded(data) as FormData;

    expect(result.get("active")).toBe("true");
  });

  it("converts string primitives as-is in FormData", () => {
    const file = new File(["content"], "test.png", { type: "image/png" });
    const data = { avatar: file, name: "Test User" };

    const result = buildFormDataIfNeeded(data) as FormData;

    expect(result.get("name")).toBe("Test User");
  });

  it("handles empty object (no File) by returning original", () => {
    const data = {};

    const result = buildFormDataIfNeeded(data);

    expect(result).toBe(data);
  });

  it("handles multiple File values", () => {
    const file1 = new File(["a"], "a.png", { type: "image/png" });
    const file2 = new File(["b"], "b.png", { type: "image/png" });
    const data = { logo: file1, banner: file2, name: "Test" };

    const result = buildFormDataIfNeeded(data) as FormData;

    expect(result).toBeInstanceOf(FormData);
    expect(result.get("logo")).toBe(file1);
    expect(result.get("banner")).toBe(file2);
    expect(result.get("name")).toBe("Test");
  });
});
