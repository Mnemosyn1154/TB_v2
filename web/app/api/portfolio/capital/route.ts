import { pythonGet, pythonPost } from "@/lib/python-proxy";

export async function GET() {
  try {
    const data = await pythonGet("/py/portfolio/capital");
    return Response.json(data);
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return Response.json({ data: null, error: message }, { status: 502 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const data = await pythonPost("/py/portfolio/capital", body);
    return Response.json(data);
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return Response.json({ data: null, error: message }, { status: 502 });
  }
}
