import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { cwd } from "node:process";
import { describe, expect, it } from "vitest";

const stylesheetPath = [resolve(cwd(), "src/index.css"), resolve(cwd(), "frontend/src/index.css")].find(existsSync);
if (!stylesheetPath) throw new Error("Unable to locate frontend/src/index.css");
const stylesheet = readFileSync(stylesheetPath, "utf8");

const WHITE_LUMINANCE = 1;

function relativeLuminance(hexColor: string): number {
  const channels = [0, 2, 4].map((offset) => Number.parseInt(hexColor.slice(offset + 1, offset + 3), 16) / 255);
  const linear = channels.map((channel) => (channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4));
  return linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722;
}

function contrastOnWhite(hexColor: string): number {
  return (WHITE_LUMINANCE + 0.05) / (relativeLuminance(hexColor) + 0.05);
}

function declaration(selector: string): string {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = stylesheet.match(new RegExp(`${escapedSelector}\\s*\\{([^}]*)\\}`));
  if (!match) throw new Error(`Missing declaration for ${selector}`);
  return match[1];
}

describe("shared accessibility styles", () => {
  it("keeps muted text token and shared descriptions at WCAG AA contrast on white", () => {
    const token = stylesheet.match(/--color-muted-2:\s*(#[0-9a-f]{6})/i)?.[1];
    expect(token).toBeDefined();
    expect(token?.toLowerCase()).toBe("#53657e");
    expect(contrastOnWhite(token as string)).toBeGreaterThanOrEqual(4.5);

    expect(declaration(".page-description")).toContain("color: var(--color-muted-2)");
    expect(declaration(".supporting-text")).toContain("color: var(--color-muted-2)");
  });

  it("removes known hover transforms when reduced motion is requested", () => {
    expect(stylesheet).toMatch(
      /@media \(prefers-reduced-motion: reduce\)[\s\S]*\[class~="group-hover:translate-x-1"\][\s\S]*transform: none !important;/,
    );
    expect(stylesheet).toMatch(
      /@media \(prefers-reduced-motion: reduce\)[\s\S]*\[class~="group-hover:scale-125"\][\s\S]*transform: none !important;/,
    );
  });
});
