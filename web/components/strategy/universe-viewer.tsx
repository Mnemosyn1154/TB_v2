import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface Pair {
  name: string;
  market: string;
  stock_a: string;
  stock_b: string;
}

interface UniverseCode {
  code: string;
  market: string;
  name: string;
}

interface UniverseViewerProps {
  strategyKey: string;
  config: Record<string, unknown>;
}

/** Render pairs table for any strategy that has a `pairs` array */
function PairsView({ pairs }: { pairs: Pair[] }) {
  if (pairs.length === 0) return null;
  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>페어 이름</TableHead>
            <TableHead>시장</TableHead>
            <TableHead>종목 A</TableHead>
            <TableHead>종목 B</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {pairs.map((p) => (
            <TableRow key={p.name}>
              <TableCell className="font-medium">{p.name}</TableCell>
              <TableCell>
                <Badge variant="outline">{p.market}</Badge>
              </TableCell>
              <TableCell className="font-mono text-sm">{p.stock_a}</TableCell>
              <TableCell className="font-mono text-sm">{p.stock_b}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

/** Render universe codes grouped by market */
function UniverseCodesView({ codes }: { codes: UniverseCode[] }) {
  if (codes.length === 0) return null;
  const grouped = new Map<string, UniverseCode[]>();
  for (const c of codes) {
    const list = grouped.get(c.market) ?? [];
    list.push(c);
    grouped.set(c.market, list);
  }
  return (
    <div className="flex flex-col gap-3">
      {Array.from(grouped.entries()).map(([market, items]) => (
        <div key={market}>
          <span className="mb-1 block text-xs font-medium text-muted-foreground">
            {market} ({items.length}종목)
          </span>
          <div className="flex flex-wrap gap-1.5">
            {items.map((c) => (
              <Badge key={c.code} variant="outline" className="font-mono">
                {c.code} {c.name}
              </Badge>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

/** Detect and render ETF-like string fields (keys ending with _etf) */
function EtfView({ config }: { config: Record<string, unknown> }) {
  const items = Object.entries(config)
    .filter(([k, v]) => typeof v === "string" && k.includes("etf"))
    .map(([k, v]) => ({ label: k.replace(/_/g, " ").toUpperCase(), code: v as string }));
  if (items.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-3">
      {items.map((item) => (
        <div
          key={item.label}
          className="flex items-center gap-2 rounded-md border px-3 py-2"
        >
          <span className="text-xs text-muted-foreground">{item.label}</span>
          <span className="font-mono text-sm font-medium">{item.code}</span>
        </div>
      ))}
    </div>
  );
}

export function UniverseViewer({ strategyKey: _key, config }: UniverseViewerProps) {
  // Data-driven: render based on what fields exist in config
  const pairs = config.pairs as Pair[] | undefined;
  if (Array.isArray(pairs) && pairs.length > 0) {
    return <PairsView pairs={pairs} />;
  }

  const codes = config.universe_codes as UniverseCode[] | undefined;
  if (Array.isArray(codes) && codes.length > 0) {
    return <UniverseCodesView codes={codes} />;
  }

  // Check for ETF-like string fields
  const hasEtf = Object.keys(config).some((k) => k.includes("etf"));
  if (hasEtf) {
    return <EtfView config={config} />;
  }

  return null;
}
