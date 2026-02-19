import { pythonPost } from "@/lib/python-proxy";

export async function POST(request: Request) {
  try {
    const { action } = await request.json();
    const path =
      action === "start"
        ? "/py/bot/scheduler/start"
        : "/py/bot/scheduler/stop";
    const data = await pythonPost(path);
    return Response.json(data);
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return Response.json({ data: null, error: message }, { status: 502 });
  }
}
