import type { Metadata } from "next";

import "@/app/globals.css";

export const metadata: Metadata = {
  title: "BusinessNext Loan Agent Dashboard",
  description: "Agentic dashboard for personal-loan customer shortlisting and outreach."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
