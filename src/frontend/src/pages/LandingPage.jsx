import React from 'react';
import { Link } from 'react-router-dom';
import {
  Database, Zap, Shield, Server, BarChart3, FileSearch,
  ArrowRight, ChevronRight,
} from 'lucide-react';
import Button from '../components/common/Button';
import Card from '../components/common/Card';
import Chip from '../components/common/Chip';

const FEATURES = [
  {
    icon: Database,
    title: 'Natural Language SQL',
    desc: 'Type questions in plain English. Get production-ready SQL — validated, optimized, and explained.',
  },
  {
    icon: Zap,
    title: '5-Agent Pipeline',
    desc: 'Schema understanding → Generation → Validation → Optimization → Explanation. Every query goes through 5 AI agents.',
  },
  {
    icon: Shield,
    title: 'On-Premise Deployable',
    desc: 'Your data never leaves your firewall. Run entirely on-premise with local LLMs for regulated industries.',
  },
  {
    icon: Server,
    title: 'Multi-DB Support',
    desc: 'PostgreSQL, MySQL, MSSQL, Oracle — one interface for all your databases with dialect-aware SQL.',
  },
  {
    icon: BarChart3,
    title: 'Smart Visualizations',
    desc: 'Charts auto-selected based on your data shape. Bar, line, pie, or table — the system infers the best fit.',
  },
  {
    icon: FileSearch,
    title: 'Audit & Compliance',
    desc: 'Full query provenance log — who asked what, when, and what SQL was generated. SOC2, HIPAA, GDPR ready.',
  },
];

const PIPELINE_STEPS = [
  { label: 'Schema', color: 'secondary' },
  { label: 'Generate', color: 'secondary' },
  { label: 'Validate', color: 'secondary' },
  { label: 'Optimize', color: 'secondary' },
  { label: 'Explain', color: 'secondary' },
];

export default function LandingPage() {
  return (
    <div className="landing">
      {/* Nav */}
      <nav className="landing-nav">
        <div className="flex items-center gap-sm">
          <span className="navbar-brand-icon">
            <Database size={18} />
          </span>
          <span className="navbar-brand-text">QueryPilot</span>
        </div>
        <div className="flex items-center gap-sm">
          <Link to="/chat">
            <Button variant="primary" size="sm">Launch App</Button>
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="landing-hero">
        <h1 className="landing-hero-title">
          Ask your database <span>anything.</span>
        </h1>
        <p className="landing-hero-subtitle">
          Enterprise-grade natural language SQL — on-premise, schema-aware, access-controlled, and auditable. Your data never leaves your firewall.
        </p>
        <div className="landing-hero-actions">
          <Link to="/chat">
            <Button variant="secondary" icon={ArrowRight}>
              Try It Now
            </Button>
          </Link>
          <Link to="/connections">
            <Button variant="primary" icon={Database}>
              Connect Your Database
            </Button>
          </Link>
        </div>
      </section>

      {/* Pipeline */}
      <section className="landing-pipeline">
        <h2 className="landing-features-title">The 5-Agent Pipeline</h2>
        <p className="text-body-md text-muted" style={{ maxWidth: '600px', margin: '0 auto' }}>
          Every question passes through five specialized AI agents — ensuring your query is correct, efficient, and understandable.
        </p>
        <div className="landing-pipeline-steps">
          {PIPELINE_STEPS.map((step, idx) => (
            <div key={step.label} className="landing-pipeline-step">
              {idx > 0 && (
                <ChevronRight size={18} className="landing-pipeline-arrow" />
              )}
              <Chip variant={step.color}>{step.label}</Chip>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="landing-features">
        <h2 className="landing-features-title">Built for enterprise teams</h2>
        <div className="landing-features-grid">
          {FEATURES.map((feature) => (
            <Card key={feature.title} bordered hoverable className="landing-feature-card">
              <div className="landing-feature-icon">
                <feature.icon size={22} />
              </div>
              <h3 className="landing-feature-title">{feature.title}</h3>
              <p className="landing-feature-desc">{feature.desc}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <p>© 2026 QueryPilot — Autonomous SQL Database Analyst</p>
      </footer>
    </div>
  );
}
