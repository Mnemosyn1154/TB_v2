import { pythonGet, pythonPost } from "@/lib/python-proxy";

export async function GET() {
  try {
    const data = await pythonGet("/py/bot/kill-switch");
    return Response.json(data);
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return Response.json({ data: null, error: message }, { status: 502 });
  }
}

export async function POST(request: Request) {
  try {
    const { action } = await request.json();
    const path =
      action === "activate"
        ? "/py/bot/kill-switch/activate"
        : "/py/bot/kill-switch/deactivate";
    const data = await pythonPost(path);
    return Response.json(data);
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return Response.json({ data: null, error: message }, { status: 502 });
  }
}
