// Day 6: prints reports/test-report.html to PDF with Playwright's Chromium (already installed for the test cases).
//   node report-pdf.mjs <in.html> <out.pdf>      — called by scripts/test_report_html.py
import { chromium } from "@playwright/test";
import { pathToFileURL } from "node:url";

const [input, output] = process.argv.slice(2);
if (!input || !output) {
  console.error("usage: node report-pdf.mjs <in.html> <out.pdf>");
  process.exit(2);
}
const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  await page.goto(pathToFileURL(input).href, { waitUntil: "load" });
  await page.emulateMedia({ media: "print" });
  await page.pdf({
    path: output,
    format: "A4",
    printBackground: true, // keeps the PASS / FAIL badge colours
    margin: { top: "12mm", bottom: "14mm", left: "10mm", right: "10mm" },
    displayHeaderFooter: true,
    headerTemplate: "<span></span>",
    footerTemplate:
      '<div style="font-size:8px;width:100%;text-align:center;color:#5b6475">' +
      'Báo cáo kiểm thử — trang <span class="pageNumber"></span>/<span class="totalPages"></span></div>',
  });
} finally {
  await browser.close();
}
