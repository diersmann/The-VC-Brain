import { describe, expect, test } from "vitest";
import { buildSourcingQueryPlan } from "./sourcingQueryPlan";

describe("sourcing query planner", () => {
  test("separates source-supported geography from downstream intent", () => {
    const plan = buildSourcingQueryPlan("technical founder, Berlin, AI infra, enterprise traction, no prior VC backing");

    expect(plan.geography).toEqual(["Berlin"]);
    expect(plan.clauses.map((clause) => clause.kind)).toEqual(["role", "geography", "sector", "traction", "exclusion"]);
    expect(plan.clauses.find((clause) => clause.kind === "geography")?.forwardedToSource).toBe(true);
    expect(plan.downstreamClauseCount).toBe(4);
    expect(plan.corrections).toEqual([]);
  });

  test("asks for a geography when the source cannot apply one", () => {
    const plan = buildSourcingQueryPlan("AI infrastructure founders with enterprise traction");

    expect(plan.geography).toEqual([]);
    expect(plan.corrections[0]).toMatch(/Add a geography/);
    expect(plan.downstreamClauseCount).toBe(1);
  });
});
