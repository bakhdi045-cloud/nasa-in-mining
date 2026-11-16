// Generates src/contract.gen.ts and src/study.gen.ts from the Pydantic schemas (the Pydantic models are the source of truth).
import { readFileSync, writeFileSync } from "node:fs";
import { compile } from "json-schema-to-typescript";

const targets = [
  ["../contract/mining_case.schema.json", "MiningCase", "./src/contract.gen.ts"],
  ["../contract/surface_study.schema.json", "SurfaceStudy", "./src/study.gen.ts"],
];
for (const [schemaPath, name, outPath] of targets) {
  const schema = JSON.parse(readFileSync(new URL(schemaPath, import.meta.url), "utf-8"));
  const ts = await compile(schema, name, {
    bannerComment: `/* Generated from ${schemaPath.replace("../", "")} by \`npm run contract\`. Do not edit. */`,
    additionalProperties: false,
    unreachableDefinitions: true,
    style: { printWidth: 120 },
  });
  writeFileSync(new URL(outPath, import.meta.url), ts);
  console.log("written", outPath);
}
