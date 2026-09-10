// @vitest-environment jsdom
import { describe, expect, it, vi, afterEach } from "vitest";
import { getBugReportUrl, LINKS } from "./brand";

describe("getBugReportUrl", () => {
  const originalUserAgent = typeof navigator !== "undefined" ? navigator.userAgent : "";
  const originalPlatform = typeof navigator !== "undefined" ? navigator.platform : "";
  const originalLanguage = typeof navigator !== "undefined" ? navigator.language : "";

  afterEach(() => {
    vi.restoreAllMocks();
    Object.defineProperty(window.navigator, "userAgent", {
      value: originalUserAgent,
      configurable: true,
    });
    Object.defineProperty(window.navigator, "platform", {
      value: originalPlatform,
      configurable: true,
    });
    Object.defineProperty(window.navigator, "language", {
      value: originalLanguage,
      configurable: true,
    });
    // Remove custom window overrides
    delete (window as any).Capacitor;
    delete (window as any).__TAURI__;
    delete (window as any).__TAURI_INTERNALS__;
    // Standalone
    Object.defineProperty(window.navigator, "standalone", {
      value: undefined,
      configurable: true,
    });
  });

  it("handles a default browser environment", () => {
    Object.defineProperty(window.navigator, "userAgent", {
      value: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      configurable: true,
    });

    const urlStr = getBugReportUrl();
    const url = new URL(urlStr);

    expect(url.origin).toBe("https://github.com");
    expect(url.pathname).toBe("/QTR-Games/QTR_pairing_process/issues/new");
    expect(url.searchParams.get("template")).toBe("bug_report.yml");
    expect(url.searchParams.get("area")).toBe("Web app (phone / browser)");
    expect(url.searchParams.get("version")).toBe("2.1.4");
    expect(url.searchParams.get("python")).toContain("macOS / Chrome");

    const logs = url.searchParams.get("logs") || "";
    expect(logs).toContain("App Environment: Web Browser");
    expect(logs).toContain("OS: macOS");
    expect(logs).toContain("Browser: Chrome");
  });

  it("detects Tauri Desktop environment", () => {
    Object.defineProperty(window.navigator, "userAgent", {
      value: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      configurable: true,
    });
    (window as any).__TAURI__ = {};

    const urlStr = getBugReportUrl();
    const url = new URL(urlStr);

    expect(url.searchParams.get("python")).toContain("Windows / Other / WebView");
    const logs = url.searchParams.get("logs") || "";
    expect(logs).toContain("App Environment: Tauri Desktop");
    expect(logs).toContain("OS: Windows");
    expect(logs).toContain("Browser: Other / WebView");
  });

  it("detects Capacitor Mobile environment", () => {
    Object.defineProperty(window.navigator, "userAgent", {
      value: "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
      configurable: true,
    });
    (window as any).Capacitor = {};

    const urlStr = getBugReportUrl();
    const url = new URL(urlStr);

    expect(url.searchParams.get("python")).toContain("Android / Chrome");
    const logs = url.searchParams.get("logs") || "";
    expect(logs).toContain("App Environment: Capacitor Mobile");
    expect(logs).toContain("OS: Android");
  });

  it("detects Standalone PWA environment", () => {
    Object.defineProperty(window.navigator, "userAgent", {
      value: "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
      configurable: true,
    });
    // Stub standalone
    Object.defineProperty(window.navigator, "standalone", {
      value: true,
      configurable: true,
    });

    const urlStr = getBugReportUrl();
    const url = new URL(urlStr);

    expect(url.searchParams.get("python")).toContain("iOS / Safari");
    const logs = url.searchParams.get("logs") || "";
    expect(logs).toContain("App Environment: Standalone PWA");
    expect(logs).toContain("OS: iOS");
    expect(logs).toContain("Browser: Safari");
  });

  it("is accessible via LINKS.bugs getter", () => {
    const bugsUrl = LINKS.bugs;
    expect(bugsUrl).toContain("https://github.com/QTR-Games/QTR_pairing_process/issues/new");
  });
});
