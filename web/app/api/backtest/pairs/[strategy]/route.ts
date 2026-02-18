import { pythonGet } from "@/lib/python-proxy";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ strategy: string }> }
) {
  try {
    const { strategy } = await params;
    const data = await pythonGet(`/py/backtest/pairs/${strategy}`);
    return Response.json(data);
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return Response.json({ data: null, error: message }, { status: 502 });
  }
}
