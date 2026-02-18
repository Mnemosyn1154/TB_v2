import { pythonGet } from "@/lib/python-proxy";

export async function GET() {
  try {
    const data = await pythonGet("/py/portfolio");
    return Response.json(data);
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return Response.json({ data: null, error: message }, { status: 502 });
  }
}
