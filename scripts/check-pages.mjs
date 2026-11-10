import { appendFileSync } from "node:fs";

const { GITHUB_TOKEN, GITHUB_REPOSITORY, GITHUB_OUTPUT, GITHUB_STEP_SUMMARY } = process.env;
if (!GITHUB_TOKEN || !GITHUB_REPOSITORY || !GITHUB_OUTPUT) {
  throw new Error("This Pages availability check must run inside GitHub Actions.");
}
const response = await fetch("https://api.github.com/repos/" + GITHUB_REPOSITORY + "/pages", {
  headers: {
    Accept: "application/vnd.github+json",
    Authorization: "Bearer " + GITHUB_TOKEN,
    "X-GitHub-Api-Version": "2022-11-28",
  },
});
if (!response.ok && response.status !== 404) {
  throw new Error("GitHub Pages availability check failed with HTTP " + response.status);
}
const available = response.ok;
appendFileSync(GITHUB_OUTPUT, "available=" + available + "\n");
if (!available) {
  const message = "The site built successfully. Pages deployment is skipped because GitHub Pages is not enabled. A private repository needs GitHub Pro or another eligible plan. Enable Pages with GitHub Actions in repository settings, then run this workflow again.";
  console.log(message);
  if (GITHUB_STEP_SUMMARY) appendFileSync(GITHUB_STEP_SUMMARY, "### Pages deployment pending\n\n" + message + "\n");
}
