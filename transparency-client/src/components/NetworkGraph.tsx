// Интерактивный граф всей сети: force-directed, зум, перетаскивание узлов,
// клик по узлу → отчёт по сущности. Использует существующий эндпоинт /graph.
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as d3 from "d3";
import { primarySource } from "../data/sources";
import type { GraphPayload } from "../data/types";

const COLORS = { low: "#34c77b", medium: "#f0a832", high: "#ef5350" };
const LEVEL_RU: Record<string, string> = { low: "Низкий", medium: "Средний", high: "Высокий" };

export default function NetworkGraph({ onOpenEntity }: { onOpenEntity: (id: number) => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ["network-graph"],
    queryFn: () => primarySource().getGraph(),
  });

  const svgRef = useRef<SVGSVGElement>(null);
  const [filter, setFilter] = useState<"all" | "low" | "medium" | "high">("all");
  const [hovered, setHovered] = useState<{ name: string; score: number; level: string } | null>(null);

  useEffect(() => {
    if (!data || !svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const width = svgRef.current.clientWidth || 1100;
    const height = svgRef.current.clientHeight || 680;

    const filteredNodes = data.nodes.filter(
      (n) => filter === "all" || n.risk_level === filter
    );
    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    const filteredEdges = data.edges.filter(
      (e) => nodeIds.has(e.source) && nodeIds.has(e.target)
    );

    const nodes = filteredNodes.map((n) => ({ ...n }));
    const links = filteredEdges.map((e) => ({
      source: e.source,
      target: e.target,
      weight: e.weight,
    }));

    const g = svg.append("g");

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 5])
      .on("zoom", (event) => g.attr("transform", event.transform));
    svg.call(zoom);

    const simulation = d3.forceSimulation(nodes as any)
      .force("link", d3.forceLink(links as any).id((d: any) => d.id).distance(70))
      .force("charge", d3.forceManyBody().strength(-140))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(14));

    const link = g.append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", "#2a3a5c")
      .attr("stroke-opacity", 0.5)
      .attr("stroke-width", (d: any) => Math.max(0.5, Math.min(3, d.weight / 5)));

    const node = g.append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .style("cursor", "pointer");

    (node as any).call(d3.drag<SVGGElement, any>()
      .on("start", (event, d: any) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x; d.fy = d.y;
      })
      .on("drag", (event, d: any) => { d.fx = event.x; d.fy = event.y; })
      .on("end", (event, d: any) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null; d.fy = null;
      })
    );

    node.append("circle")
      .attr("r", (d: any) => 5 + d.risk_score * 14)
      .attr("fill", (d: any) => COLORS[d.risk_level as keyof typeof COLORS])
      .attr("stroke", "#0b1220")
      .attr("stroke-width", 1.5);

    node.append("title").text((d: any) =>
      `${d.name}\nриск: ${d.risk_score.toFixed(2)} (${LEVEL_RU[d.risk_level]})`
    );

    node.append("text")
      .text((d: any) => d.name.length > 22 ? d.name.slice(0, 21) + "…" : d.name)
      .attr("dy", (d: any) => 12 + d.risk_score * 14)
      .attr("text-anchor", "middle")
      .attr("fill", "#8ea0c2")
      .attr("font-size", 10)
      .attr("pointer-events", "none");

    node.on("click", (_event: any, d: any) => onOpenEntity(d.id));
    node.on("mouseenter", (_event: any, d: any) =>
      setHovered({ name: d.name, score: d.risk_score, level: d.risk_level })
    );
    node.on("mouseleave", () => setHovered(null));

    simulation.on("tick", () => {
      (link as any)
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);
      node.attr("transform", (d: any) => `translate(${d.x},${d.y})`);
    });

    return () => { simulation.stop(); };
  }, [data, filter, onOpenEntity]);

  if (isLoading) return <div className="card skeleton">Строим граф сети…</div>;
  if (!data) return <div className="card">Нет данных для графа.</div>;

  const counts = { low: 0, medium: 0, high: 0 };
  data.nodes.forEach((n) => counts[n.risk_level as keyof typeof counts]++);

  return (
    <div>
      <div className="card">
        <h3>Граф сети</h3>
        <p className="muted">
          {data.nodes.length} сущностей, {data.edges.length} связей.
          Перетаскивайте узлы, зумьте колесом мыши, клик по узлу — отчёт.
        </p>
        <div className="graph-toolbar">
          <div className="chips-row">
            {(["all", "high", "medium", "low"] as const).map((lvl) => (
              <button
                key={lvl}
                className={`chip chip-btn ${filter === lvl ? "active" : ""}`}
                onClick={() => setFilter(lvl)}
              >
                {lvl === "all" ? `все (${data.nodes.length})` :
                  `${LEVEL_RU[lvl]} (${counts[lvl]})`}
              </button>
            ))}
          </div>
          {hovered && (
            <div className="graph-hover">
              <b>{hovered.name}</b>
              <span className="muted"> — риск {hovered.score.toFixed(2)} ({LEVEL_RU[hovered.level]})</span>
            </div>
          )}
        </div>
      </div>
      <div className="card graph-card">
        <svg ref={svgRef} className="graph-svg" />
      </div>
      <div className="card">
        <div className="graph-legend">
          <span><i style={{ background: COLORS.high }} /> высокая степень риска</span>
          <span><i style={{ background: COLORS.medium }} /> средняя</span>
          <span><i style={{ background: COLORS.low }} /> низкая</span>
          <span className="muted">размер узла — оценка риска · толщина линии — вес контракта</span>
        </div>
      </div>
    </div>
  );
}