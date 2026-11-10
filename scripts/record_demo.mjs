// Records the demo walkthrough as a video (Playwright), against the REAL app with your real keys.
//   1) start GigBid:  python -m uvicorn apps.api.main:app --port 8000
//   2) cd apps/web && node ../../scripts/record_demo.mjs
// Output: demo-video/*.webm (about 3 minutes). Add your voice-over in any editor (e.g. Clipchamp on Windows).
// Shows: inbox -> evidence-backed proposal -> approval, a scam skipped, an injected instruction ignored, a client reply.
import { chromium } from "@playwright/test";
import fs from "node:fs";

const BASE = process.env.BASE_URL ?? "http://127.0.0.1:8000";
const env = Object.fromEntries(fs.readFileSync("../../.env", "utf8").split("\n").map((l) => l.match(/^([A-Z_]+)=([^#\s]*)/)).filter(Boolean).map((m) => [m[1], m[2]]));
const pause = (ms) => new Promise((r) => setTimeout(r, ms));
const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 1280, height: 800 }, recordVideo: { dir: "demo-video", size: { width: 1280, height: 800 } } });
const p = await ctx.newPage();
const caption = (text) => p.evaluate((t) => {
  let el = document.getElementById("demo-cap");
  if (!el) { el = document.createElement("div"); el.id = "demo-cap"; Object.assign(el.style, { position: "fixed", top: "12px", left: "50%", transform: "translateX(-50%)", background: "#1B2A4A", color: "#FFE58A", padding: "10px 18px", borderRadius: "10px", font: "700 18px system-ui", zIndex: 99999 }); document.body.appendChild(el); }
  el.textContent = t;
}, text);

await p.goto(BASE + "/login");
await caption("GigBid: bid on the work you can prove"); await pause(4000);
await p.fill("input[type=email]", env.REVIEWER_EMAIL); await p.fill("input[type=password]", env.REVIEWER_PASSWORD);
await p.click("button.btn-primary"); await p.waitForURL("**/inbox");
await caption("1. Scout pulls new jobs from saved searches"); await p.click("text=Check for new jobs");
for (let i = 0; i < 18; i++) { await pause(5000); await p.reload(); await caption("Agents analyse each job in parallel: fit, risk, requirements"); }
await caption("Ranked by fit, with risk badges, price and Connects"); await pause(5000);
const skip = p.locator(".ledger-row", { hasText: /asks for free work|scam|off the platform/i }).first();
if (await skip.count()) { await skip.click(); await caption("2. A scam caught: skipped with the reason shown"); await pause(8000); await p.goBack(); }
const inj = p.locator(".ledger-row").filter({ has: p.locator("text=Hidden instructions") }).first();
if (await inj.count()) { await inj.click(); await caption("3. Injected instruction in the post: detected and ignored"); await pause(8000); await p.goBack(); }
const draft = p.locator(".ledger-row", { hasText: "Needs your approval" }).first();
await draft.click(); await caption("4. Every highlighted claim links to portfolio evidence"); await pause(3000);
const claim = p.locator("mark.claim").first(); if (await claim.count()) { await claim.hover(); await pause(6000); }
await caption("Critic, claim checker and Compliance Guard ran before you see it"); await pause(6000);
await caption("Dry-run preview: what will be sent and what it costs"); await pause(5000);
await p.click("text=Approve and send"); await caption("Nothing is sent until you approve"); await pause(10000);
await p.goto(BASE + "/pipeline"); await caption("5. Pipeline updates from marketplace events"); await pause(6000);
await p.goto(BASE + "/messages"); await caption("6. Client replies get a suggested answer, approved before sending"); await pause(4000);
const thread = p.locator(".ledger-row").first();
if (await thread.count()) { await thread.click(); await p.click("text=Suggest a reply"); await pause(25000); }
await p.goto(BASE + "/settings"); await caption("Style memory: only promoted rules, deletable by you"); await pause(6000);
await ctx.close(); await b.close();
console.log("Saved video in apps/web/demo-video/");
