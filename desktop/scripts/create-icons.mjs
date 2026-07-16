import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const iconsDir = join(__dirname, "..", "src-tauri", "icons");

// Minimal 32x32 PNG (solid blue) — replace with branded assets before release.
const PNG_32 = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAI0lEQVR4Ae3OMQEAAAjDMMC/52ECvhBI0QAAAAAAAAAAwF0GWAABwZx0PgAAAABJRU5ErkJggg==",
  "base64",
);

mkdirSync(iconsDir, { recursive: true });
writeFileSync(join(iconsDir, "32x32.png"), PNG_32);
writeFileSync(join(iconsDir, "128x128.png"), PNG_32);
writeFileSync(join(iconsDir, "icon.png"), PNG_32);
writeFileSync(join(iconsDir, "icon.ico"), PNG_32);
console.log("Desktop icons written to src-tauri/icons");
