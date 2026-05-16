"use client";

import { Activity } from "lucide-react";

import { titleCase } from "@/lib/format";
import type { WorkflowEvent } from "@/lib/types";

export function Timeline({ events }: { events: WorkflowEvent[] }) {
  return (
    <section className="panel-section timeline">
      <div className="section-title">
        <Activity size={17} aria-hidden />
        <h2>Activity timeline</h2>
      </div>
      {events.length === 0 ? (
        <p className="muted">No workflow events yet.</p>
      ) : (
        <ol>
          {events.map((event, index) => (
            <li key={`${event.event_type}-${index}`}>
              <strong>{titleCase(event.event_type)}</strong>
              <span>{event.message}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
