"use client";

import {
  CheckCircle2,
  Database,
  ListChecks,
  MessageSquareText,
  RefreshCw,
  Send,
  ShieldCheck,
  Users
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { CustomerDetailDrawer } from "@/components/CustomerDetailDrawer";
import { CustomerTable } from "@/components/CustomerTable";
import { FilterBar } from "@/components/FilterBar";
import { ResultsPanel } from "@/components/ResultsPanel";
import { Timeline } from "@/components/Timeline";
import { WorkflowPanel } from "@/components/WorkflowPanel";
import { emptyFilters, filterCustomers } from "@/lib/customers";
import {
  buildFilteredCohortPrompt,
  buildSelectedCustomersPrompt
} from "@/lib/prompts";
import type {
  AgentResponse,
  CatalogResponse,
  CustomerFilters,
  CustomerSummary,
  TopCustomer,
  WorkflowEvent
} from "@/lib/types";

export function Dashboard() {
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [catalog, setCatalog] = useState<CatalogResponse | null>(null);
  const [filters, setFilters] = useState<CustomerFilters>(emptyFilters);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [activeCustomer, setActiveCustomer] = useState<CustomerSummary | null>(null);
  const [objective, setObjective] = useState("Find customers likely to convert this month.");
  const [response, setResponse] = useState<AgentResponse | null>(null);
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    void loadInitialData();
  }, []);

  const filteredCustomers = useMemo(
    () => filterCustomers(customers, filters),
    [customers, filters]
  );
  const recommendations = useMemo(() => {
    const topCustomers = (response?.structured_result?.top_customers ?? []) as TopCustomer[];
    return new Map(topCustomers.map((customer) => [customer.customer_id, customer]));
  }, [response]);

  async function loadInitialData() {
    setLoading(true);
    setError("");
    try {
      const [customerResponse, catalogResponse] = await Promise.all([
        fetch("/api/customers"),
        fetch("/api/catalog")
      ]);
      if (!customerResponse.ok || !catalogResponse.ok) {
        throw new Error("Dashboard data could not be loaded.");
      }
      setCustomers((await customerResponse.json()).customers);
      setCatalog(await catalogResponse.json());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Dashboard data could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  async function invoke(prompt: string) {
    setLoading(true);
    setError("");
    try {
      const agentResponse = await fetch("/api/agent/invoke", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ prompt, sessionId })
      });
      const payload = await agentResponse.json();
      if (!agentResponse.ok) {
        throw new Error(payload.error || "Agent invocation failed.");
      }
      setResponse(payload);
      setSessionId(payload.session_id);
      setEvents((current) => [...current, ...(payload.events ?? [])]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Agent invocation failed.");
    } finally {
      setLoading(false);
    }
  }

  function runSelectedCustomers() {
    invoke(buildSelectedCustomersPrompt(selectedIds, objective));
  }

  function runFilteredCohort() {
    invoke(buildFilteredCohortPrompt(filters, objective));
  }

  function updateSelectedIds(ids: string[]) {
    setSelectedIds(ids);
    if (sessionId || response || events.length > 0) {
      setResponse(null);
      setEvents([]);
      setSessionId(null);
      setError("");
    }
  }

  const metrics = [
    { label: "Customers", value: customers.length, icon: Users },
    { label: "Visible", value: filteredCustomers.length, icon: Database },
    { label: "Selected", value: selectedIds.length, icon: CheckCircle2 },
    { label: "Checks", value: catalog?.checks.length ?? 0, icon: ListChecks },
    { label: "Styles", value: catalog?.styles.length ?? 0, icon: MessageSquareText }
  ];

  return (
    <main className="dashboard-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">BusinessNext AgentCore</p>
          <h1>Personal loan outreach dashboard</h1>
        </div>
        <button className="secondary-action" onClick={loadInitialData} disabled={loading}>
          <RefreshCw size={16} aria-hidden />
          Refresh
        </button>
      </header>

      <section className="metric-strip" aria-label="Dashboard metrics">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <div className="metric" key={metric.label}>
              <Icon size={18} aria-hidden />
              <span>{metric.label}</span>
              <strong>{metric.value}</strong>
            </div>
          );
        })}
      </section>

      {error ? <div className="notice error">{error}</div> : null}

      <div className="dashboard-grid">
        <section className="workspace">
          <FilterBar
            customers={customers}
            filters={filters}
            onChange={setFilters}
            objective={objective}
            onObjectiveChange={setObjective}
          />
          <CustomerTable
            customers={filteredCustomers}
            selectedIds={selectedIds}
            onSelectionChange={updateSelectedIds}
            onOpenCustomer={setActiveCustomer}
          />
          <ResultsPanel response={response} />
        </section>

        <aside className="side-panel">
          <WorkflowPanel
            catalog={catalog}
            response={response}
            loading={loading}
            selectedCount={selectedIds.length}
            visibleCount={filteredCustomers.length}
            onRunSelected={runSelectedCustomers}
            onRunFiltered={runFilteredCohort}
            onInvoke={invoke}
          />
          <section className="panel-section compact">
            <div className="section-title">
              <ShieldCheck size={17} aria-hidden />
              <h2>Human approvals</h2>
            </div>
            <p className="muted">
              Sensitive steps are gated by explicit approval tokens from AgentCore.
            </p>
          </section>
          <Timeline events={events} />
          {response?.status === "completed" && response.structured_result?.drafts ? (
            <button className="primary-action full-width" type="button">
              <Send size={16} aria-hidden />
              Outreach ready
            </button>
          ) : null}
        </aside>
      </div>

      <CustomerDetailDrawer
        customer={activeCustomer}
        recommendation={
          activeCustomer
            ? recommendations.get(activeCustomer.customerId)
            : undefined
        }
        onClose={() => setActiveCustomer(null)}
      />
    </main>
  );
}
