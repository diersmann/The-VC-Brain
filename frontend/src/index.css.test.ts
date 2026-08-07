import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { cwd } from "node:process";
import { describe, expect, it } from "vitest";

const stylesheetPath = [resolve(cwd(), "src/index.css"), resolve(cwd(), "frontend/src/index.css")].find(existsSync);
if (!stylesheetPath) throw new Error("Unable to locate frontend/src/index.css");
const stylesheet = readFileSync(stylesheetPath, "utf8");

function relativeLuminance(hexColor: string): number {
  const channels = [0, 2, 4].map((offset) => Number.parseInt(hexColor.slice(offset + 1, offset + 3), 16) / 255);
  const linear = channels.map((channel) => (channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4));
  return linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722;
}

function contrastRatio(foreground: string, background: string): number {
  const foregroundLuminance = relativeLuminance(foreground);
  const backgroundLuminance = relativeLuminance(background);
  return (
    (Math.max(foregroundLuminance, backgroundLuminance) + 0.05) /
    (Math.min(foregroundLuminance, backgroundLuminance) + 0.05)
  );
}

function token(name: string): string {
  const value = stylesheet.match(new RegExp(`${name}:\\s*(#[0-9a-f]{6})`, "i"))?.[1];
  if (!value) throw new Error(`Missing color token ${name}`);
  return value;
}

function declaration(selector: string): string {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = stylesheet.match(new RegExp(`${escapedSelector}\\s*\\{([^}]*)\\}`));
  if (!match) throw new Error(`Missing declaration for ${selector}`);
  return match[1];
}

describe("shared accessibility styles", () => {
  it("keeps muted text token and shared descriptions at WCAG AA contrast on white", () => {
    const muted2 = token("--color-muted-2");
    expect(muted2.toLowerCase()).toBe("#53657e");
    expect(contrastRatio(muted2, "#ffffff")).toBeGreaterThanOrEqual(4.5);
    for (const background of ["#d6e2f6", "#d5e1f6"]) {
      expect(contrastRatio(muted2, background), `${muted2} on ${background}`).toBeGreaterThanOrEqual(4.5);
    }

    expect(declaration(".page-description")).toContain("color: var(--color-muted-2)");
    expect(declaration(".supporting-text")).toContain("color: var(--color-muted-2)");
  });

  it("keeps muted labels at WCAG AA contrast on shared non-white surfaces", () => {
    const muted = token("--color-muted");
    expect(muted.toLowerCase()).toBe("#53657e");
    const surfaces = [token("--color-surface-2"), token("--color-surface-3"), "#d6e2f6", "#d5e1f6"];

    for (const surface of surfaces) {
      expect(contrastRatio(muted, surface), `${muted} on ${surface}`).toBeGreaterThanOrEqual(4.5);
    }

    expect(declaration(".eyebrow")).toContain("color: var(--color-muted)");
    expect(declaration(".data-label")).toContain("color: var(--color-muted)");
  });

  it("removes known hover transforms when reduced motion is requested", () => {
    const reducedMotion = stylesheet.match(/@media \(prefers-reduced-motion: reduce\)[\s\S]*$/)?.[0] ?? "";
    const resets = [
      {
        property: "translate",
        selectors: ['[class*="hover:translate-"]', '[class*="hover:-translate-"]', '[class*="group-hover:translate-"]', '[class*="group-hover:-translate-"]'],
      },
      { property: "scale", selectors: ['[class*="hover:scale-"]', '[class*="group-hover:scale-"]'] },
      {
        property: "rotate",
        selectors: ['[class*="hover:rotate-"]', '[class*="hover:-rotate-"]', '[class*="group-hover:rotate-"]', '[class*="group-hover:-rotate-"]'],
      },
    ];
    for (const { property, selectors } of resets) {
      for (const selector of selectors) expect(reducedMotion).toContain(selector);
      const selectorPattern = selectors.map((selector) => selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("[\\s\\S]*");
      expect(reducedMotion).toMatch(new RegExp(`${selectorPattern}[\\s\\S]*${property}: none !important;`));
    }
  });
});
