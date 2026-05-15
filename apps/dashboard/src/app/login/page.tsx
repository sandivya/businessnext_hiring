import { LoginForm } from "@/components/LoginForm";

export default function LoginPage() {
  return (
    <main className="login-shell">
      <section className="login-panel" aria-label="Dashboard sign in">
        <div>
          <p className="eyebrow">BusinessNext AgentCore</p>
          <h1>Loan outreach dashboard</h1>
          <p className="muted">
            Sign in to operate the customer shortlisting and outreach workflow.
          </p>
        </div>
        <LoginForm />
      </section>
    </main>
  );
}
