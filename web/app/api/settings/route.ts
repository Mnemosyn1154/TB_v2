import yaml from "js-yaml";
import { readFile, writeFile } from "fs/promises";
import { join } from "path";

const SETTINGS_PATH = join(process.cwd(), "..", "config", "settings.yaml");

export async function GET() {
  try {
    const content = await readFile(SETTINGS_PATH, "utf-8");
    const data = yaml.load(content);
    return Response.json({ data, error: null });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return Response.json({ data: null, error: message }, { status: 500 });
  }
}

export async function PUT(request: Request) {
  try {
    const body = await request.json();
    const content = yaml.dump(body, { indent: 2, lineWidth: 120 });
    await writeFile(SETTINGS_PATH, content, "utf-8");
    return Response.json({ data: body, error: null });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return Response.json({ data: null, error: message }, { status: 500 });
  }
}
