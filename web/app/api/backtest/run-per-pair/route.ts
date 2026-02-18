import { pythonPost } from "@/lib/python-proxy";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const data = await pythonPost("/py/backtest/run-per-pair", body);
    return Response.json(data);
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return Response.json({ data: null, error: message }, { status: 502 });
  }
}
