"use client";

import Link from "next/link";
import styles from "./page.module.css";
import { ArrowRight, CheckCircle2, Code2, Shield, Zap, Webhook } from "lucide-react";

export default function Home() {
  return (
    <div className={styles.landing}>
      <header className={styles.navbar}>
        <div className={styles.brand}>Paytrack</div>
        <nav className={styles.navlinks}>
          <Link href="#features">Features</Link>
          <Link href="#pricing">Pricing</Link>
          <Link href="/auth" className={styles.linkMuted}>Sign in</Link>
          <Link href="/auth/register" className={styles.signup}>Get started</Link>
        </nav>
      </header>

      <main className={styles.heroSection}>
        <div className={styles.heroCopy}>
          <h1>
            The M-Pesa payments OS for builders
          </h1>
          <p>
            Collect, reconcile and payout at scale. Webhooks, SDKs and clear APIs designed for developers. Only 0.01% per collection.
          </p>
          <div className={styles.ctaRow}>
            <Link href="/auth/register" className={styles.ctaPrimary}>
              Start building
              <ArrowRight size={18} />
            </Link>
            <a href="#code" className={styles.ctaGhost}>See the code</a>
          </div>

          <ul className={styles.points}>
            <li><CheckCircle2 size={18}/> M-Pesa STK, C2B and B2C flows</li>
            <li><CheckCircle2 size={18}/> Idempotent APIs and signed webhooks</li>
            <li><CheckCircle2 size={18}/> Settlement and payouts automation</li>
          </ul>
        </div>

        <div className={styles.preview} aria-hidden>
          <div className={styles.previewHeader}>
            <span className={styles.badge}>Open</span>
            <div className={styles.previewActions}>
              <span>Invoice #42D42-0001</span>
              <button className={styles.smallBtn}>Copy link</button>
            </div>
          </div>
          <div className={styles.previewBody}>
            <div className={styles.detailCard}>
              <div className={styles.detailRow}><span>Client</span><strong>Cloud Newton</strong></div>
              <div className={styles.detailRow}><span>Email</span><strong>cloudnew@gmail.com</strong></div>
              <div className={styles.detailRow}><span>Reference</span><strong>#42D42-0001</strong></div>
              <a className={styles.pdfBtn} href="/receipt">View receipt</a>
            </div>
            <div className={styles.historyCard}>
              <h4>History</h4>
              <div className={styles.historyItem}>Invoice was sent to client</div>
              <div className={styles.historyItem}>Invoice was finalized</div>
              <div className={styles.historyItem}>Invoice was created</div>
            </div>
            <div className={styles.itemsCard}>
              <h4>Items</h4>
              <div className={styles.itemRow}><span>UX/UI Design for Mobile app</span><strong>KES 1,150.52</strong></div>
              <div className={styles.itemRow}><span>UX/UI Design for Landing page</span><strong>KES 550.52</strong></div>
            </div>
          </div>
        </div>
      </main>

      <section id="features" className={styles.features}>
        <div className={styles.feature}><Zap/><h3>Blazing fast</h3><p>Low latency callbacks and retries built in.</p></div>
        <div className={styles.feature}><Webhook/><h3>Webhooks</h3><p>Signed payloads, retries and replay protection.</p></div>
        <div className={styles.feature}><Shield/><h3>Secure</h3><p>Token-scoped keys and IP allow-listing.</p></div>
        <div className={styles.feature}><Code2/><h3>SDKs</h3><p>Type-safe SDKs and Postman collection.</p></div>
      </section>

      <section id="code" className={styles.codeBlock}>
        <div className={styles.codeHeader}>Create a collection</div>
        <pre>
{`curl -X POST https://api.paytrack.dev/v1/collections \\\n+  -H "Authorization: Bearer sk_test_***" \\\n+  -H "Content-Type: application/json" \\\n+  -d '{
    "amount": 2250.65,
    "currency": "KES",
    "customer": { "phone": "+254700000000" },
    "metadata": { "invoice": "42D42-0001" }
  }'`}
        </pre>
      </section>

      <section id="pricing" className={styles.pricing}>
        <div className={styles.priceCard}>
          <div className={styles.priceHeader}>Simple pricing</div>
          <div className={styles.priceValue}>0.01%</div>
          <div className={styles.priceNote}>per successful collection</div>
          <ul className={styles.priceList}>
            <li><CheckCircle2 size={18}/> No monthly fees</li>
            <li><CheckCircle2 size={18}/> Free test mode</li>
            <li><CheckCircle2 size={18}/> Instant settlements & payouts</li>
          </ul>
          <Link href="/auth/register" className={styles.ctaPrimary}>
            Get started
            <ArrowRight size={18} />
          </Link>
        </div>
      </section>

      <footer className={styles.footer}>
        <span>© {new Date().getFullYear()} Paytrack</span>
        <div className={styles.footerLinks}>
          <a href="#pricing">Pricing</a>
          <a href="#features">Features</a>
          <Link href="/auth">Sign in</Link>
        </div>
      </footer>
    </div>
  );
}
