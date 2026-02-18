import { pythonPost } from "@/lib/python-proxy";

export async function POST() {
  try {
    const data = await pythonPost("/py/bot/run");
    return Response.json(data);
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return Response.json({ data: null, error: message }, { status: 502 });
  }
}
