import yaml from "js-yaml";
import { readFile, writeFile } from "fs/promises";
import { join } from "path";
import { type NextRequest } from "next/server";

const SETTINGS_PATH = join(process.cwd(), "..", "config", "settings.yaml");

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ key: string }> }
) {
  try {
    const { key } = await params;

    const content = await readFile(SETTINGS_PATH, "utf-8");
    const data = yaml.load(content) as Record<string, unknown>;
    const strategies = data.strategies as
      | Record<string, Record<string, unknown>>
      | undefined;

    if (!strategies || !strategies[key]) {
      return Response.json(
        { data: null, error: `Strategy '${key}' not found` },
        { status: 404 }
      );
    }

    delete strategies[key];
    const updated = yaml.dump(data, { indent: 2, lineWidth: 120 });
    await writeFile(SETTINGS_PATH, updated, "utf-8");

    return Response.json({ data: { key, deleted: true }, error: null });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return Response.json({ data: null, error: message }, { status: 500 });
  }
}
