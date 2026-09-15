import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "SAMCO CTO Standards Hub",
  description: "Unified Technical, Tender, Planning and Cost Control corporate data system"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <header className="topbar">
            <div className="brand">
              <div><strong>SAMCO CTO HUB</strong><br/><small>Corporate Standards & Controls</small></div>
              <div><small>Chief Technical Officer | <strong>Eng. Ola Essam</strong></small></div>
            </div>
            <nav className="nav">
              <a href="/">Home</a><a href="/intake">Project Intake</a><a href="/technical">Technical</a><a href="/tender">Tender</a><a href="/planning">Planning</a><a href="/cost-control">Cost Control</a><a href="/system">System</a><a href="/admin" className="admin">Admin Control</a>
            </nav>
          </header>
          {children}
          <footer className="footer">
            <span>Chief Technical Officer | <b>Eng. Ola Essam</b></span>
            <span>Engineered & Developed | <b>Eng. Ahmed Labib</b> <sup>©2026</sup></span>
          </footer>
        </div>
      </body>
    </html>
  );
}
