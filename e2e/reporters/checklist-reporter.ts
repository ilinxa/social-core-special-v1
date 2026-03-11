import type {
  Reporter,
  FullConfig,
  Suite,
  TestCase,
  TestResult,
  FullResult,
} from "@playwright/test/reporter";
import * as fs from "fs";
import * as path from "path";

// =============================================================================
// CHECKLIST REPORTER — Maps [U-XX] test titles to checklist report
// =============================================================================

interface ChecklistItem {
  id: string;
  title: string;
  status: "pass" | "fail" | "skip" | "not_covered";
  duration?: number;
  error?: string;
}

const U_PATTERN = /\[U-(\d+)\]/;

class ChecklistReporter implements Reporter {
  private results: Map<string, ChecklistItem> = new Map();

  onBegin(_config: FullConfig, _suite: Suite) {
    // Initialize all 99 items as not_covered
    for (let i = 1; i <= 99; i++) {
      const id = `U-${String(i).padStart(2, "0")}`;
      this.results.set(id, {
        id,
        title: "",
        status: "not_covered",
      });
    }
  }

  onTestEnd(test: TestCase, result: TestResult) {
    const match = test.title.match(U_PATTERN);
    if (!match) return;

    const num = parseInt(match[1], 10);
    const id = `U-${String(num).padStart(2, "0")}`;

    let status: ChecklistItem["status"];
    switch (result.status) {
      case "passed":
        status = "pass";
        break;
      case "failed":
      case "timedOut":
        status = "fail";
        break;
      case "skipped":
        status = "skip";
        break;
      default:
        status = "fail";
    }

    const existing = this.results.get(id);

    // If already tracked, only overwrite if previous was not_covered or this is a failure
    if (existing && existing.status !== "not_covered" && status !== "fail") {
      return;
    }

    this.results.set(id, {
      id,
      title: test.title,
      status,
      duration: result.duration,
      error:
        result.status === "failed"
          ? result.errors?.[0]?.message?.slice(0, 200)
          : undefined,
    });
  }

  async onEnd(result: FullResult) {
    const items = Array.from(this.results.values()).sort((a, b) =>
      a.id.localeCompare(b.id, undefined, { numeric: true })
    );

    const passed = items.filter((i) => i.status === "pass").length;
    const failed = items.filter((i) => i.status === "fail").length;
    const skipped = items.filter((i) => i.status === "skip").length;
    const notCovered = items.filter((i) => i.status === "not_covered").length;
    const testable = 97; // U-17, U-18 OAuth excluded

    // Console summary
    console.log("\n");
    console.log("═══════════════════════════════════════════════════");
    console.log("  E2E CHECKLIST REPORT (User Scope U-01 to U-99)");
    console.log("═══════════════════════════════════════════════════");
    console.log(`  Passed:      ${passed}`);
    console.log(`  Failed:      ${failed}`);
    console.log(`  Skipped:     ${skipped}`);
    console.log(`  Not covered: ${notCovered}`);
    console.log(`  Coverage:    ${passed}/${testable} testable items (${Math.round((passed / testable) * 100)}%)`);
    console.log(`  Overall:     ${result.status}`);
    console.log("═══════════════════════════════════════════════════");

    if (failed > 0) {
      console.log("\n  FAILURES:");
      items
        .filter((i) => i.status === "fail")
        .forEach((i) => {
          console.log(`    ${i.id}: ${i.title}`);
          if (i.error) console.log(`      → ${i.error}`);
        });
    }

    if (notCovered > 0) {
      console.log("\n  NOT COVERED:");
      items
        .filter((i) => i.status === "not_covered")
        .forEach((i) => console.log(`    ${i.id}`));
    }

    console.log("");

    // Write JSON report
    const reportsDir = path.join(__dirname, "..", "reports");
    if (!fs.existsSync(reportsDir)) {
      fs.mkdirSync(reportsDir, { recursive: true });
    }

    const report = {
      generated_at: new Date().toISOString(),
      overall_status: result.status,
      summary: { passed, failed, skipped, not_covered: notCovered, testable },
      items,
    };

    fs.writeFileSync(
      path.join(reportsDir, "e2e-checklist-report.json"),
      JSON.stringify(report, null, 2)
    );
  }
}

export default ChecklistReporter;
