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

export function UniverseViewer({ strategyKey, config }: UniverseViewerProps) {
  if (strategyKey === "stat_arb") {
    const pairs = (config.pairs ?? []) as Pair[];
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

  if (strategyKey === "dual_momentum") {
    const items = [
      { label: "KR ETF", code: config.kr_etf as string },
      { label: "US ETF", code: config.us_etf as string },
      { label: "KR 안전자산", code: config.safe_kr_etf as string },
      { label: "US 안전자산", code: config.safe_us_etf as string },
    ];
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

  if (strategyKey === "quant_factor") {
    const codes = (config.universe_codes ?? []) as UniverseCode[];
    if (codes.length === 0) return null;
    const krCodes = codes.filter((c) => c.market === "KR");
    const usCodes = codes.filter((c) => c.market === "US");
    return (
      <div className="flex flex-col gap-3">
        {[
          { label: "KR", items: krCodes },
          { label: "US", items: usCodes },
        ].map(
          ({ label, items }) =>
            items.length > 0 && (
              <div key={label}>
                <span className="mb-1 block text-xs font-medium text-muted-foreground">
                  {label} ({items.length}종목)
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {items.map((c) => (
                    <Badge key={c.code} variant="outline" className="font-mono">
                      {c.code} {c.name}
                    </Badge>
                  ))}
                </div>
              </div>
            )
        )}
      </div>
    );
  }

  return null;
}
